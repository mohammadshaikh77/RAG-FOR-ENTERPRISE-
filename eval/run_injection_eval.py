"""Evaluation harness for Phase 7 Prompt-Injection Defenses.

Evaluates 15 adversarial test cases (8 indirect injections hidden inside
document text, and 7 direct prompt injections in user questions).
Tests:
1. Ingestion scanner flag rate.
2. Context delimiter protection.
3. Model resistance against instruction execution (forbidden output check).
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Any

from agent.guardrails.injection import (
    scan_prompt_injection,
    wrap_untrusted_context,
)

from apps.api.src.config import get_settings
from apps.api.src.logging import get_logger, setup_logging
from apps.api.src.routers.agent import build_agent_loop

logger = get_logger("cite.eval.injection")
setup_logging(log_level="INFO", environment="development")

TEST_SET_PATH = Path("eval/golden_set/injection_test_set.json")
RESULTS_PATH = Path("eval/results/injection_results.json")


async def run_injection_evaluation() -> dict[str, Any]:
    with open(TEST_SET_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    settings = get_settings()
    agent_loop = build_agent_loop(settings)
    test_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    results: list[dict[str, Any]] = []
    scanned_flagged_count = 0
    attack_blocked_count = 0
    total_cases = len(cases)

    print("\n" + "=" * 70)
    print(f" CITE PROMPT INJECTION DEFENSE BENCHMARK (N={total_cases})")
    print("=" * 70)
    print(f"{'ID':<14} | {'Type':<18} | {'Scanned':<8} | {'Defended':<9} | {'Status'}")
    print("-" * 70)

    for case in cases:
        case_id = case["id"]
        c_type = case["type"]
        user_query = case["user_query"]
        chunk_text = case.get("embedded_chunk_text", "")
        forbidden = case["forbidden_output"]

        # Step 1: Ingestion / input scan check
        target_text_to_scan = chunk_text if c_type == "indirect_document" else user_query
        is_flagged, patterns = scan_prompt_injection(target_text_to_scan)
        if is_flagged:
            scanned_flagged_count += 1

        # Step 2: Agent execution under security delimiters
        # Wrap the malicious chunk (if indirect document injection)
        if c_type == "indirect_document":
            wrapped_context = wrap_untrusted_context(
                [
                    {
                        "document_title": case["document_title"],
                        "section_title": "Clinical Text",
                        "content": chunk_text,
                    }
                ]
            )
            # Ask the agent with the wrapped context in mind
            eval_query = f"{user_query}\n\nContext:\n{wrapped_context}"
        else:
            eval_query = user_query

        # Run agent query with preferred provider
        agent_resp = await agent_loop.run(
            org_id=test_org_id,
            query=eval_query,
            preferred_provider="mock",  # Or available provider
        )

        answer_text = agent_resp.final_answer

        # Step 3: Defense verification
        # Attack fails (defense succeeds) if forbidden output does NOT appear in answer
        attack_executed = forbidden.lower() in answer_text.lower()
        defense_passed = not attack_executed

        if defense_passed:
            attack_blocked_count += 1
            status_str = "✅ PASSED"
        else:
            status_str = "❌ FAILED"

        results.append(
            {
                "id": case_id,
                "type": c_type,
                "attack_vector": case["attack_vector"],
                "scan_flagged": is_flagged,
                "matched_patterns": patterns,
                "defense_passed": defense_passed,
                "forbidden_output": forbidden,
                "answer_preview": answer_text[:120] + "...",
            }
        )

        scan_icon = "FLAG" if is_flagged else "CLEAN"
        def_icon = "BLOCKED" if defense_passed else "BREACH"
        print(f"{case_id:<14} | {c_type:<18} | {scan_icon:<8} | {def_icon:<9} | {status_str}")

    scan_pass_rate = round((scanned_flagged_count / total_cases) * 100, 1)
    defense_pass_rate = round((attack_blocked_count / total_cases) * 100, 1)

    print("=" * 70)
    print(
        f"Ingestion/Input Scan Flag Rate:  {scanned_flagged_count}/{total_cases} ({scan_pass_rate}%)"
    )
    print(
        f"Overall Defense Pass Rate:      {attack_blocked_count}/{total_cases} ({defense_pass_rate}%)"
    )
    print("=" * 70)

    summary = {
        "total_cases": total_cases,
        "indirect_document_cases": sum(1 for c in cases if c["type"] == "indirect_document"),
        "direct_user_cases": sum(1 for c in cases if c["type"] == "direct_user"),
        "scanned_flagged_count": scanned_flagged_count,
        "scan_flag_rate": scan_pass_rate,
        "attack_blocked_count": attack_blocked_count,
        "defense_pass_rate": defense_pass_rate,
        "results": results,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    asyncio.run(run_injection_evaluation())
