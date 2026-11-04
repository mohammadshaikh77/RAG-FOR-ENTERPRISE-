import React, { useEffect, useState } from "react";
import {
  Activity,
  Cpu,
  Layers,
  Sparkles,
  Timer,
  X,
  Zap,
} from "lucide-react";
import { getTraceDetail } from "../../api/agent.js";
import { formatLatency } from "../../lib/utils.js";
import { Badge } from "../ui/Badge.jsx";
import { Skeleton } from "../ui/Skeleton.jsx";

export function TraceDrawer({ traceId, onClose }) {
  const [trace, setTrace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!traceId) return;
    setLoading(true);
    getTraceDetail(traceId)
      .then((data) => {
        setTrace(data);
        setError(null);
      })
      .catch((err) => {
        setError(err.message || "Failed to load trace");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [traceId]);

  if (!traceId) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[480px] bg-surface border-l border-border shadow-2xl flex flex-col animate-slide-in-right font-sans">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-subtle/50">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-accent" />
          <span className="text-sm font-semibold text-foreground">
            Execution Audit Trace
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {loading && (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-32 w-full rounded-lg" />
            <Skeleton className="h-40 w-full rounded-lg" />
          </div>
        )}

        {error && (
          <div className="p-3.5 rounded-lg border border-danger/30 bg-danger-subtle/30 text-xs text-danger">
            {error}
          </div>
        )}

        {trace && (
          <div className="space-y-4">
            {/* Telemetry Stats Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-3 rounded-lg border border-border bg-surface-subtle/40 space-y-1">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-medium">
                  <Timer className="h-3.5 w-3.5 text-accent" />
                  Latency
                </span>
                <span className="text-base font-bold font-mono text-foreground block">
                  {formatLatency(trace.latency_ms)}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-border bg-surface-subtle/40 space-y-1">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-medium">
                  <Zap className="h-3.5 w-3.5 text-accent" />
                  Total Tokens
                </span>
                <span className="text-base font-bold font-mono text-foreground block">
                  {trace.tokens_total.toLocaleString()}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-border bg-surface-subtle/40 space-y-1">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-medium">
                  <Cpu className="h-3.5 w-3.5 text-accent" />
                  Provider / Model
                </span>
                <span className="text-xs font-semibold font-mono text-foreground block truncate">
                  {trace.provider} · {trace.model}
                </span>
              </div>

              <div className="p-3 rounded-lg border border-border bg-surface-subtle/40 space-y-1">
                <span className="text-[11px] text-muted-foreground flex items-center gap-1.5 font-medium">
                  <Layers className="h-3.5 w-3.5 text-accent" />
                  Tool Calls
                </span>
                <span className="text-base font-bold font-mono text-foreground block">
                  {trace.tool_calls_count} calls
                </span>
              </div>
            </div>

            {/* Token Breakdown Bar */}
            <div className="p-3 rounded-lg border border-border bg-surface space-y-1.5 text-xs font-mono">
              <div className="flex justify-between text-muted-foreground text-[11px]">
                <span>Prompt: {trace.tokens_prompt}</span>
                <span>Completion: {trace.tokens_completion}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden flex">
                <div
                  className="bg-accent h-full"
                  style={{
                    width: `${
                      (trace.tokens_prompt / Math.max(1, trace.tokens_total)) * 100
                    }%`,
                  }}
                  title="Prompt tokens"
                />
                <div
                  className="bg-accent/40 h-full"
                  style={{
                    width: `${
                      (trace.tokens_completion /
                        Math.max(1, trace.tokens_total)) *
                      100
                    }%`,
                  }}
                  title="Completion tokens"
                />
              </div>
            </div>

            {/* Step-by-Step History */}
            <div className="space-y-2">
              <div className="text-[11px] uppercase font-mono tracking-wider text-muted-foreground font-semibold">
                Reasoning Steps ({trace.steps?.length || 0})
              </div>

              <div className="space-y-2">
                {trace.steps?.map((step, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg border border-border bg-surface-subtle/30 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-foreground font-mono">
                        Step {step.step_index}
                      </span>
                      {step.latency_ms > 0 && (
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {formatLatency(step.latency_ms)}
                        </span>
                      )}
                    </div>

                    {step.tool_calls?.map((tc, tcIdx) => (
                      <div key={tcIdx} className="space-y-1 font-mono text-[11px]">
                        <Badge variant="accent">
                          <Sparkles className="h-3 w-3" />
                          <span>{tc.name}</span>
                        </Badge>
                        <pre className="p-2 rounded bg-surface border border-border text-[10px] overflow-x-auto text-muted-foreground">
                          {JSON.stringify(tc.arguments, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </div>

            {/* Trace Identifier */}
            <div className="pt-2 border-t border-border/60 text-[10px] text-muted-foreground font-mono flex items-center justify-between">
              <span>Trace ID:</span>
              <span className="truncate max-w-[260px]">{trace.id}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

