import React from "react";
import { AlertCircle, FileSearch, Sparkles } from "lucide-react";

export function RefusalCard({ message, query: _query }) {
  return (
    <div className="rounded-lg border border-warning/30 bg-warning-subtle/30 p-4 space-y-3 text-foreground my-2 select-none animate-fade-in">
      <div className="flex items-center gap-2.5">
        <div className="h-7 w-7 rounded-full bg-warning-subtle text-warning flex items-center justify-center shrink-0 border border-warning/20">
          <AlertCircle className="h-4 w-4" />
        </div>
        <div>
          <h4 className="text-sm font-semibold leading-tight text-foreground">
            Not found in your documents
          </h4>
          <span className="text-[11px] text-muted-foreground">
            Strict Hallucination Guardrail Active
          </span>
        </div>
      </div>

      <p className="text-xs text-foreground/90 leading-relaxed">
        {message ||
          "I cannot answer this question based on the provided documents as no relevant clinical evidence was found."}
      </p>

      <div className="pt-2 border-t border-warning/20 flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground font-mono">
        <span className="flex items-center gap-1">
          <FileSearch className="h-3 w-3 text-muted-foreground" />
          Retrieved 0 high-confidence chunks
        </span>
        <span className="flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-accent" />
          Zero ungrounded speculation permitted
        </span>
      </div>
    </div>
  );
}

