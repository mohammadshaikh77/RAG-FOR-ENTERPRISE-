import React from "react";
import { Gauge, Scale, Sparkles } from "lucide-react";
import { Badge } from "../components/ui/Badge.jsx";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card.jsx";

export function EvaluationPage() {
  return (
    <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Badge variant="accent">Phase 6 Centerpiece</Badge>
          <span className="text-xs text-muted-foreground font-mono">
            Automated Quality Gate
          </span>
        </div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Evaluation Harness & Benchmark Matrix
        </h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Grounded accuracy, citation precision, and model comparisons with
          honest, measured numbers.
        </p>
      </div>

      {/* Planned Feature Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Gauge className="h-4 w-4 text-accent" />
              <CardTitle>Retrieval Metrics (LLM-Free)</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground leading-relaxed">
            <p>
              Automated deterministic checks running against our golden label
              dataset without paid API costs:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>
                <strong className="text-foreground">Recall@k & Hit Rate:</strong>{" "}
                Measures target chunk capture across Top 3, 5, and 10.
              </li>
              <li>
                <strong className="text-foreground">MRR (Mean Reciprocal Rank):</strong>{" "}
                Evaluates ranking quality under reciprocal rank fusion.
              </li>
              <li>
                <strong className="text-foreground">CI Regression Gate:</strong> Fails
                pull requests if retrieval metrics drop below baseline.json.
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Scale className="h-4 w-4 text-accent" />
              <CardTitle>Clinical Faithfulness & Refusal</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground leading-relaxed">
            <p>
              LLM-as-a-judge evaluation scoring grounded responses with a fixed
              rubric:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>
                <strong className="text-foreground">Citation Precision:</strong>{" "}
                Verifies that quoted spans strictly support the stated claims.
              </li>
              <li>
                <strong className="text-foreground">Refusal Accuracy:</strong>{" "}
                Tests that unanswerable queries cleanly refuse rather than guess.
              </li>
              <li>
                <strong className="text-foreground">Model Comparison:</strong>{" "}
                Side-by-side ablations: Groq vs Gemini vs local Ollama.
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <div className="p-4 rounded-xl border border-border bg-surface-subtle/50 text-xs text-muted-foreground flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Sparkles className="h-4 w-4 text-accent shrink-0" />
          <span>
            Evaluation harness execution will be enabled in Phase 6 via{" "}
            <code className="px-1.5 py-0.5 rounded bg-muted text-foreground font-mono">
              make eval
            </code>
            .
          </span>
        </div>
        <span className="font-mono text-[11px] text-accent">TBD (run make eval)</span>
      </div>
    </div>
  );
}

