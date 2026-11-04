import { apiFetch, getStoredToken } from "./client.js";

/**
 * Synchronous query execution.
 * @param {{ query: string, max_steps?: number, session_id?: string, preferred_provider?: string }} payload
 * @returns {Promise<any>}
 */
export async function queryAgent(payload) {
  return apiFetch("/agent/query", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Streams agent progress events and tokens via SSE.
 * @param {{ query: string, max_steps?: number, session_id?: string, preferred_provider?: string }} payload
 * @param {function(string, any): void} onEvent - callback for (eventType, data)
 * @param {function(Error): void} onError - error callback
 * @param {function(): void} onDone - completion callback
 * @returns {function(): void} abort controller cancel function
 */
export function queryAgentStream(payload, onEvent, onError, onDone) {
  const controller = new AbortController();
  const token = getStoredToken();

  const headers = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  fetch("/api/agent/query/stream", {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        let errText = `Stream error ${response.status}`;
        try {
          const errJson = await response.json();
          errText = errJson.detail || errText;
        } catch (_e) {
          // Non-JSON response
        }
        throw new Error(errText);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let isReading = true;

      while (isReading) {
        const { done, value } = await reader.read();
        if (done) {
          isReading = false;
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const block of lines) {
          if (!block.trim()) continue;
          let eventName = "message";
          let dataStr = "";

          const blockLines = block.split("\n");
          for (const line of blockLines) {
            if (line.startsWith("event: ")) {
              eventName = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.slice(6).trim();
            }
          }

          if (dataStr) {
            try {
              const parsedData = JSON.parse(dataStr);
              onEvent(eventName, parsedData);
            } catch (e) {
              onEvent(eventName, dataStr);
            }
          }
        }
      }

      if (onDone) onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        if (onError) onError(err);
      }
    });

  return () => controller.abort();
}

/**
 * Lists past agent audit traces for the tenant.
 * @param {{ limit?: number, offset?: number, session_id?: string }} [params={}]
 * @returns {Promise<Array<any>>}
 */
export async function listTraces(params = {}) {
  const queryParams = new URLSearchParams();
  if (params.limit) queryParams.set("limit", params.limit.toString());
  if (params.offset) queryParams.set("offset", params.offset.toString());
  if (params.session_id) queryParams.set("session_id", params.session_id);

  const qs = queryParams.toString();
  return apiFetch(`/agent/traces${qs ? `?${qs}` : ""}`);
}

/**
 * Retrieves full step-by-step trace details.
 * @param {string} traceId
 * @returns {Promise<any>}
 */
export async function getTraceDetail(traceId) {
  return apiFetch(`/agent/traces/${traceId}`);
}

/**
 * Submits user rating feedback for an answer.
 * @param {{ trace_id: string, rating: number, comment?: string }} payload
 * @returns {Promise<any>}
 */
export async function submitFeedback(payload) {
  return apiFetch("/agent/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

