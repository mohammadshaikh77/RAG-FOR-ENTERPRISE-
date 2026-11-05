/**
 * Evaluation API service for fetching benchmark results, ablations, and CI quality gate status.
 */

import { apiFetch } from "./client.js";

/**
 * Fetches the latest evaluation summary, ablation matrix, and LLM judge scorecards.
 * @returns {Promise<any>}
 */
export async function getEvaluationSummary() {
  return apiFetch("/eval/summary");
}

/**
 * Fetches the markdown evaluation report.
 * @returns {Promise<{ report_markdown: string }>}
 */
export async function getEvaluationReport() {
  return apiFetch("/eval/report");
}

/**
 * Fetches the reference baseline for the CI regression gate.
 * @returns {Promise<any>}
 */
export async function getEvaluationBaseline() {
  return apiFetch("/eval/baseline");
}
