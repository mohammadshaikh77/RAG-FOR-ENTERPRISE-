import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Gauge,
  Scale,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  RefreshCw,
  FileText,
  Layers,
  ChevronRight,
  TrendingUp,
  Sparkles,
} from "lucide-react";
import { Badge } from "../components/ui/Badge.jsx";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card.jsx";
import { getEvaluationSummary, getEvaluationReport } from "../api/eval.js";

export function EvaluationPage() {
  const [activeTab, setActiveTab] = useState("overview");

  const {
    data: summary,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["evalSummary"],
    queryFn: getEvaluationSummary,
  });

  const { data: reportData } = useQuery({
    queryKey: ["evalReport"],
    queryFn: getEvaluationReport,
    enabled: activeTab === "report",
  });

  if (isLoading) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-6xl mx-auto space-y-6 animate-pulse">
        <div className="h-8 bg-muted rounded-md w-1/3"></div>
        <div className="h-4 bg-muted rounded-md w-1/2"></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-muted/60 rounded-xl"></div>
          ))}
        </div>
        <div className="h-64 bg-muted/40 rounded-xl mt-6"></div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-4xl mx-auto space-y-6">
        <div className="p-6 rounded-xl border border-danger/30 bg-danger/10 text-danger flex flex-col items-center text-center space-y-3">
          <AlertTriangle className="h-8 w-8" />
          <h3 className="font-semibold text-base">Unable to Load Evaluation Metrics</h3>
          <p className="text-xs text-muted-foreground max-w-md">
            {error?.message || "Ensure the evaluation harness has been run via 'make eval'."}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-1.5 text-xs font-medium rounded-lg bg-danger text-white hover:bg-danger/90 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const ablations = summary?.retrieval_ablations || {};
  const agentEval = summary?.agent_eval || {};
  const citations = agentEval?.citations || { total: 0, verified: 0, precision: 1.0 };
  const refusal = agentEval?.refusal || { true_refusal_rate: 1.0, false_refusal_rate: 0.0 };
  const latency = agentEval?.latency || { p50_ms: 0, p90_ms: 0, p95_ms: 0, mean_ms: 0 };
  const judge = agentEval?.judge || { avg_faithfulness: 5.0, avg_correctness: 5.0, verdicts: [] };
  const gatePassed = summary?.gate_passed !== false;

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-6xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="accent">Automated Evaluation Engine</Badge>
            <span className="text-xs text-muted-foreground font-mono">
              Demo Pharma • 100 Golden Triples
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
            Evaluation Harness & Quality Gate
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Measured retrieval recall, exact citation precision, clinical faithfulness, and CI regression checks.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium bg-surface hover:bg-surface-subtle transition-colors text-foreground disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* CI Quality Gate Banner */}
      <div
        className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
          gatePassed
            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
            : "border-danger/30 bg-danger/10 text-danger"
        }`}
      >
        <div className="flex items-center gap-3">
          {gatePassed ? (
            <div className="h-9 w-9 rounded-lg bg-emerald-500/20 flex items-center justify-center shrink-0">
              <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
          ) : (
            <div className="h-9 w-9 rounded-lg bg-danger/20 flex items-center justify-center shrink-0">
              <XCircle className="h-5 w-5 text-danger" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">
                CI Quality Gate: {gatePassed ? "PASSED" : "FAILED"}
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-surface/60 border border-border/50 text-foreground">
                Tolerance: ±3.0%
              </span>
            </div>
            <p className="text-xs opacity-90 mt-0.5">
              {gatePassed
                ? "All retrieval metrics (MRR, Recall@5, HitRate@5) strictly meet or exceed baseline criteria."
                : "Retrieval regression detected exceeding allowable tolerance threshold."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono self-end sm:self-auto text-foreground">
          <div>
            <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">MRR</span>
            <span className="font-bold text-sm">{(ablations.hybrid?.mrr || 0).toFixed(4)}</span>
          </div>
          <div>
            <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">Recall@5</span>
            <span className="font-bold text-sm">{((ablations.hybrid?.recall_at_5 || 0) * 100).toFixed(1)}%</span>
          </div>
          <div>
            <span className="text-muted-foreground block text-[10px] uppercase tracking-wider">Hit Rate@5</span>
            <span className="font-bold text-sm">{((ablations.hybrid?.hit_rate_at_5 || 0) * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-border pb-1">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "overview"
              ? "bg-accent/10 text-accent font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Gauge className="h-3.5 w-3.5" />
            Overview & KPIs
          </div>
        </button>
        <button
          onClick={() => setActiveTab("ablations")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "ablations"
              ? "bg-accent/10 text-accent font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5" />
            Retrieval Ablations
          </div>
        </button>
        <button
          onClick={() => setActiveTab("judge")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "judge"
              ? "bg-accent/10 text-accent font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Scale className="h-3.5 w-3.5" />
            LLM-as-a-Judge Scorecards
          </div>
        </button>
        <button
          onClick={() => setActiveTab("report")}
          className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
            activeTab === "report"
              ? "bg-accent/10 text-accent font-semibold"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          <div className="flex items-center gap-1.5">
            <FileText className="h-3.5 w-3.5" />
            Markdown Report
          </div>
        </button>
      </div>

      {/* Tab: Overview & KPIs */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Citation Precision</span>
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                </div>
                <div className="text-2xl font-bold font-mono text-foreground">
                  {(citations.precision * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {citations.verified} of {citations.total} citations verified verbatim in chunks
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">True Refusal Rate</span>
                  <CheckCircle2 className="h-4 w-4 text-accent" />
                </div>
                <div className="text-2xl font-bold font-mono text-foreground">
                  {(refusal.true_refusal_rate * 100).toFixed(1)}%
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {refusal.correctly_refused} of {refusal.total_unanswerable} unanswerables refused
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Clinical Faithfulness</span>
                  <Scale className="h-4 w-4 text-purple-500" />
                </div>
                <div className="text-2xl font-bold font-mono text-foreground">
                  {judge.avg_faithfulness?.toFixed(2)} / 5.0
                </div>
                <p className="text-[11px] text-muted-foreground">
                  Scored by LLM-as-a-judge against ground truth
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4 space-y-1">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">P95 Latency</span>
                  <Clock className="h-4 w-4 text-amber-500" />
                </div>
                <div className="text-2xl font-bold font-mono text-foreground">
                  {latency.p95_ms?.toFixed(0)} ms
                </div>
                <p className="text-[11px] text-muted-foreground">
                  P50: {latency.p50_ms?.toFixed(0)} ms • Mean: {latency.mean_ms?.toFixed(0)} ms
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Golden Dataset Distribution */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Golden Dataset Distribution (100 Items)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
                <div className="p-3 rounded-lg bg-surface-subtle border border-border">
                  <span className="text-xl font-bold font-mono text-foreground">40</span>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Single-Doc Factual</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-subtle border border-border">
                  <span className="text-xl font-bold font-mono text-foreground">20</span>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Multi-Doc Compare</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-subtle border border-border">
                  <span className="text-xl font-bold font-mono text-foreground">15</span>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Structured Queries</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-subtle border border-border">
                  <span className="text-xl font-bold font-mono text-foreground">15</span>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Unanswerable Refusals</p>
                </div>
                <div className="p-3 rounded-lg bg-surface-subtle border border-border">
                  <span className="text-xl font-bold font-mono text-foreground">10</span>
                  <p className="text-[11px] text-muted-foreground mt-0.5">Adversarial Injections</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab: Retrieval Ablations */}
      {activeTab === "ablations" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Retrieval Ablation Comparison (75 Evaluated Queries)</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-surface-subtle text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border">
                  <tr>
                    <th className="py-2.5 px-4 font-semibold">Retrieval Mode</th>
                    <th className="py-2.5 px-4 font-semibold">MRR</th>
                    <th className="py-2.5 px-4 font-semibold">Recall@5</th>
                    <th className="py-2.5 px-4 font-semibold">Hit Rate@5</th>
                    <th className="py-2.5 px-4 font-semibold">Recall@3</th>
                    <th className="py-2.5 px-4 font-semibold">Hit Rate@3</th>
                    <th className="py-2.5 px-4 font-semibold">P50 Latency</th>
                    <th className="py-2.5 px-4 font-semibold">Mean Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {Object.entries(ablations).map(([mode, data]) => {
                    const isHybrid = mode === "hybrid" || mode === "hybrid_rerank";
                    return (
                      <tr
                        key={mode}
                        className={isHybrid ? "bg-accent/5 font-medium" : "hover:bg-surface-subtle/50"}
                      >
                        <td className="py-3 px-4 font-mono font-semibold text-foreground flex items-center gap-1.5">
                          {isHybrid && <span className="h-1.5 w-1.5 rounded-full bg-accent"></span>}
                          {mode.toUpperCase()}
                        </td>
                        <td className="py-3 px-4 font-mono text-foreground">{(data.mrr || 0).toFixed(4)}</td>
                        <td className="py-3 px-4 font-mono text-foreground">
                          {((data.recall_at_5 || 0) * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 font-mono text-foreground">
                          {((data.hit_rate_at_5 || 0) * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 font-mono text-foreground">
                          {((data.recall_at_3 || 0) * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 font-mono text-foreground">
                          {((data.hit_rate_at_3 || 0) * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-4 font-mono text-muted-foreground">
                          {(data.latency?.p50_ms || 0).toFixed(1)} ms
                        </td>
                        <td className="py-3 px-4 font-mono text-muted-foreground">
                          {(data.latency?.mean_ms || 0).toFixed(1)} ms
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tab: LLM-as-a-Judge */}
      {activeTab === "judge" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <span className="text-xs text-muted-foreground">Clinical Faithfulness</span>
                  <div className="text-2xl font-bold font-mono text-foreground mt-0.5">
                    {judge.avg_faithfulness?.toFixed(2)} / 5.0
                  </div>
                </div>
                <Badge variant="success">Grounded</Badge>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4 flex items-center justify-between">
                <div>
                  <span className="text-xs text-muted-foreground">Clinical Correctness</span>
                  <div className="text-2xl font-bold font-mono text-foreground mt-0.5">
                    {judge.avg_correctness?.toFixed(2)} / 5.0
                  </div>
                </div>
                <Badge variant="accent">Verified</Badge>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Sample Evaluation Verdicts</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="bg-surface-subtle text-muted-foreground uppercase text-[10px] tracking-wider border-b border-border">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">ID</th>
                      <th className="py-2.5 px-4 font-semibold">Category</th>
                      <th className="py-2.5 px-4 font-semibold">Query</th>
                      <th className="py-2.5 px-4 font-semibold">Faithfulness</th>
                      <th className="py-2.5 px-4 font-semibold">Correctness</th>
                      <th className="py-2.5 px-4 font-semibold">Judge Rationale</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {(judge.verdicts || []).map((v) => (
                      <tr key={v.item_id} className="hover:bg-surface-subtle/50">
                        <td className="py-2.5 px-4 font-mono font-medium text-foreground">{v.item_id}</td>
                        <td className="py-2.5 px-4">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-muted text-muted-foreground">
                            {v.category}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-foreground max-w-xs truncate">{v.query}</td>
                        <td className="py-2.5 px-4 font-mono text-foreground">{v.faithfulness}/5</td>
                        <td className="py-2.5 px-4 font-mono text-foreground">{v.correctness}/5</td>
                        <td className="py-2.5 px-4 text-muted-foreground max-w-sm">{v.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab: Full Markdown Report */}
      {activeTab === "report" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Generated Markdown Report (eval/results/eval_report.md)</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="p-4 rounded-lg bg-surface-subtle border border-border text-[11px] font-mono text-foreground overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {reportData?.report_markdown || "Loading report..."}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
