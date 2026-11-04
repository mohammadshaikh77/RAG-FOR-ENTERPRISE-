import React, { useState } from "react";
import {
  Calculator,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  FileSearch,
  Layers,
  Loader2,
} from "lucide-react";
import { formatLatency } from "../../lib/utils.js";

const TOOL_ICONS = {
  search_documents: FileSearch,
  get_section: Layers,
  compare_documents: Layers,
  query_structured_data: Database,
  calculator: Calculator,
};

const TOOL_LABELS = {
  search_documents: "Searching clinical labels",
  get_section: "Reading section content",
  compare_documents: "Comparing drug labels",
  query_structured_data: "Querying structured metadata",
  calculator: "Computing dosage calculation",
};

export function AgentTimeline({ steps = [], isStreaming = false }) {
  const [expanded, setExpanded] = useState(false);

  if (!steps || steps.length === 0) return null;

  const totalToolCalls = steps.reduce(
    (acc, step) => acc + (step.tool_calls ? step.tool_calls.length : 0),
    0
  );
  const totalLatencyMs = steps.reduce(
    (acc, step) => acc + (step.latency_ms || 0),
    0
  );

  // When streaming and still working: show active progress banner
  if (isStreaming) {
    const lastStep = steps[steps.length - 1];
    const lastToolCall =
      lastStep?.tool_calls && lastStep.tool_calls.length > 0
        ? lastStep.tool_calls[lastStep.tool_calls.length - 1]
        : null;

    const toolName = lastToolCall?.name || "search_documents";
    const Icon = TOOL_ICONS[toolName] || Loader2;
    const label = TOOL_LABELS[toolName] || "Reasoning through documents...";

    return (
      <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-surface-subtle border border-border/60 text-xs text-muted-foreground animate-pulse mb-3 select-none">
        <Icon className="h-4 w-4 text-accent animate-spin" />
        <span className="font-medium text-foreground">{label}</span>
        <span className="text-[11px] text-muted-foreground font-mono ml-auto">
          Step {steps.length}
        </span>
      </div>
    );
  }

  // Once finished: render expandable "How I got this answer" row
  return (
    <div className="border border-border/60 rounded-lg bg-surface-subtle/50 mb-3 text-xs overflow-hidden select-none">
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full px-3 py-2 text-left hover:bg-surface-subtle transition-colors"
      >
        <div className="flex items-center gap-2 text-muted-foreground">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-accent" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-accent" />
          )}
          <span className="font-medium text-foreground">
            How I got this answer
          </span>
          <span className="text-muted-foreground">
            ({totalToolCalls} {totalToolCalls === 1 ? "tool used" : "tools used"}
            {totalLatencyMs > 0 ? ` · ${formatLatency(totalLatencyMs)}` : ""})
          </span>
        </div>
        <CheckCircle2 className="h-3.5 w-3.5 text-accent shrink-0" />
      </button>

      {expanded && (
        <div className="px-3 pb-3 pt-1 space-y-2 border-t border-border/40 font-mono">
          {steps.map((step, idx) => (
            <div key={idx} className="space-y-1">
              {step.tool_calls?.map((tc, tcIdx) => {
                const Icon = TOOL_ICONS[tc.name] || FileSearch;
                return (
                  <div
                    key={tcIdx}
                    className="flex items-center justify-between py-1 px-2 rounded bg-surface border border-border/40 text-[11px]"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <Icon className="h-3 w-3 text-accent shrink-0" />
                      <span className="font-semibold text-foreground">
                        {tc.name}
                      </span>
                      {tc.arguments && (
                        <span className="text-muted-foreground truncate max-w-[280px]">
                          {typeof tc.arguments === "string"
                            ? tc.arguments
                            : JSON.stringify(tc.arguments)}
                        </span>
                      )}
                    </div>
                    {step.latency_ms > 0 && (
                      <span className="text-[10px] text-muted-foreground shrink-0 ml-2">
                        {formatLatency(step.latency_ms)}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

