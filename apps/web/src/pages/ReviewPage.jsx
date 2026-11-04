import React from "react";
import { Eye, Lock, UserCheck } from "lucide-react";
import { Badge } from "../components/ui/Badge.jsx";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card.jsx";

export function ReviewPage() {
  return (
    <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Badge variant="warning">Phase 7 Guardrails</Badge>
          <span className="text-xs text-muted-foreground font-mono">
            Safety & Containment
          </span>
        </div>
        <h2 className="text-xl font-bold tracking-tight text-foreground">
          Human-in-the-Loop Review & Guardrails
        </h2>
        <p className="text-xs text-muted-foreground mt-0.5">
          Adversarial protection, prompt injection defenses, and confidence-gated
          review queues.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Lock className="h-4 w-4 text-accent" />
              <CardTitle>Prompt Injection Defense</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground leading-relaxed">
            <p>
              Treats all retrieved document chunks as untrusted input:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>
                <strong className="text-foreground">Context Boundary Isolation:</strong>{" "}
                Isolates clinical context within strict XML guardrails.
              </li>
              <li>
                <strong className="text-foreground">Adversarial Canary Testing:</strong>{" "}
                Measures defense against indirect injection inside label inserts.
              </li>
              <li>
                <strong className="text-foreground">PII Redaction:</strong> Masks
                patient IDs and confidential formulation details.
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <UserCheck className="h-4 w-4 text-accent" />
              <CardTitle>Human Review Queue</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-2 text-xs text-muted-foreground leading-relaxed">
            <p>
              Automated routing for clinical safety verification:
            </p>
            <ul className="list-disc pl-4 space-y-1">
              <li>
                <strong className="text-foreground">Confidence Thresholds:</strong> Flags
                queries with marginal retrieval scores for manual review.
              </li>
              <li>
                <strong className="text-foreground">Discrepancy Resolution:</strong>{" "}
                Clinical staff reviewer workflow to approve or refine answers.
              </li>
              <li>
                <strong className="text-foreground">Audit Compliance:</strong> Complete
                regulatory trail for high-consequence drug decisions.
              </li>
            </ul>
          </CardContent>
        </Card>
      </div>

      <div className="p-4 rounded-xl border border-border bg-surface-subtle/50 text-xs text-muted-foreground flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Eye className="h-4 w-4 text-muted-foreground shrink-0" />
          <span>
            Human-in-the-loop review queue and automated injection benchmarks
            will be activated in Phase 7.
          </span>
        </div>
        <span className="font-mono text-[11px] text-muted-foreground">Coming in Phase 7</span>
      </div>
    </div>
  );
}

