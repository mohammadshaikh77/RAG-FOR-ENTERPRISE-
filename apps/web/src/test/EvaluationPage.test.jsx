import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { EvaluationPage } from "../pages/EvaluationPage.jsx";
import * as evalApi from "../api/eval.js";

describe("EvaluationPage Component", () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  it("renders evaluation metrics and quality gate banner", async () => {
    vi.spyOn(evalApi, "getEvaluationSummary").mockResolvedValue({
      timestamp: "2026-11-05T05:54:56.114946+00:00",
      total_queries: 100,
      gate_passed: true,
      retrieval_ablations: {
        hybrid: {
          mrr: 0.5389,
          recall_at_5: 0.76,
          hit_rate_at_5: 0.84,
        },
      },
      agent_eval: {
        citations: { total: 16, verified: 16, precision: 1.0 },
        refusal: { true_refusal_rate: 1.0, false_refusal_rate: 0.0, correctly_refused: 7, total_unanswerable: 7 },
        latency: { p50_ms: 11.2, p90_ms: 18.3, p95_ms: 24.1, mean_ms: 9.4 },
        judge: { avg_faithfulness: 5.0, avg_correctness: 5.0, verdicts: [] },
      },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <EvaluationPage />
      </QueryClientProvider>
    );

    // Verify title and CI quality gate banner
    expect(await screen.findByText("Evaluation Harness & Quality Gate")).toBeInTheDocument();
    expect(screen.getByText("CI Quality Gate: PASSED")).toBeInTheDocument();
    expect(screen.getByText("Citation Precision")).toBeInTheDocument();
    expect(screen.getAllByText("100.0%").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("True Refusal Rate")).toBeInTheDocument();
  });
});
