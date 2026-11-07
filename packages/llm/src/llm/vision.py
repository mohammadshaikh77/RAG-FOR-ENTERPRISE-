"""Multimodal document figure and diagram captioner using Gemini Vision."""

import asyncio
import base64
from typing import Any

import httpx
import structlog

from apps.api.src.config import get_settings
from llm.rate_limiter import TokenBucketLimiter

logger = structlog.get_logger(__name__)
settings = get_settings()

CAPTION_PROMPT = (
    "You are an expert technical and clinical document intelligence assistant. "
    "Analyze the provided diagram, chart, chemical structure, or clinical figure from a document. "
    "Provide a detailed, factual textual description including: "
    "1) Figure title or heading (if visible), "
    "2) Visual type (e.g., bar chart, line graph, flow diagram, chemical formula, pharmacokinetic plot), "
    "3) All visible axis labels, data points, dosages, percentages, units, or text strings, "
    "4) The key clinical or technical takeaway. "
    "Be direct and factual. Avoid conversational filler."
)


class VisionCaptioner:
    """Asynchronous, rate-limited vision captioner with hash-based deduplication caching."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3.5-flash",
        rate_limit_rpm: int = 8,
        timeout: float = 25.0,
    ) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model = model
        self.timeout = timeout
        self.rate_limiter = TokenBucketLimiter(requests_per_minute=rate_limit_rpm, name="gemini_vision")
        self._cache: dict[str, str] = {}

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and settings.multimodal_enabled)

    async def caption_image(
        self,
        image_bytes: bytes,
        image_hash: str,
        image_format: str = "png",
        caption_hint: str = "",
        max_retries: int = 3,
    ) -> str:
        """Captions a single figure using Gemini Vision with rate limiting, cache, and hint fallback."""
        if not self.is_available():
            return caption_hint or "Embedded document diagram"

        # Check in-memory hash cache
        if image_hash in self._cache:
            logger.info("Vision caption cache hit", image_hash=image_hash[:12])
            return self._cache[image_hash]

        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        mime = f"image/{image_format.lower()}"
        if mime == "image/jpg":
            mime = "image/jpeg"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        prompt = CAPTION_PROMPT
        if caption_hint:
            prompt += f"\n\nNearby page context: {caption_hint}"

        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": b64_data}},
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 300},
        }

        for attempt in range(max_retries):
            await self.rate_limiter.acquire()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload)

                    if resp.status_code == 429:
                        wait_sec = 2.0 * (attempt + 1)
                        logger.warning("Gemini Vision 429 backoff", attempt=attempt, wait_sec=wait_sec)
                        await asyncio.sleep(wait_sec)
                        continue

                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts:
                                caption = str(parts[0].get("text", "")).strip()
                                if caption:
                                    self._cache[image_hash] = caption
                                    logger.info("Figure caption generated", image_hash=image_hash[:12], chars=len(caption))
                                    return str(caption)

                    logger.warning("Gemini Vision non-200 response", status=resp.status_code, body=resp.text[:200])

            except Exception as e:
                logger.warning("Gemini Vision request error", attempt=attempt, error=str(e))
                await asyncio.sleep(1.0 * (attempt + 1))

        # Fallback to local nearby caption hint if vision call fails or times out
        fallback = caption_hint or "Document figure / diagram"
        self._cache[image_hash] = fallback
        return fallback


_global_vision_captioner: VisionCaptioner | None = None


def get_vision_captioner() -> VisionCaptioner:
    global _global_vision_captioner
    if _global_vision_captioner is None:
        _global_vision_captioner = VisionCaptioner()
    return _global_vision_captioner
