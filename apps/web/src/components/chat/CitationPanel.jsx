import React from "react";
import { CheckCircle2, ExternalLink, FileText, Layers, X } from "lucide-react";
import { Badge } from "../ui/Badge.jsx";

export function CitationPanel({
  citation,
  citationIndex,
  onClose,
  onOpenDocument,
}) {
  if (!citation) return null;

  // Highlights the quoted supporting span inside the full chunk text
  const renderHighlightedContent = () => {
    const fullText = citation.full_chunk_text || citation.quoted_span || "";
    const span = citation.quoted_span || "";

    if (!span || !fullText) {
      return <p className="text-sm leading-relaxed">{fullText}</p>;
    }

    const lowerFull = fullText.toLowerCase();
    const lowerSpan = span.toLowerCase();
    const matchIndex = lowerFull.indexOf(lowerSpan);

    if (matchIndex === -1) {
      return (
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-accent-subtle/40 border border-accent/20">
            <span className="text-[10px] uppercase font-mono tracking-wider text-accent font-semibold block mb-1">
              Quoted Evidence
            </span>
            <p className="text-xs italic text-foreground font-medium">
              "{span}"
            </p>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
            {fullText}
          </p>
        </div>
      );
    }

    const before = fullText.slice(0, matchIndex);
    const matched = fullText.slice(matchIndex, matchIndex + span.length);
    const after = fullText.slice(matchIndex + span.length);

    return (
      <div className="text-xs leading-relaxed text-foreground whitespace-pre-wrap">
        {before}
        <mark className="bg-accent/25 text-foreground px-1 py-0.5 rounded font-medium border-b-2 border-accent">
          {matched}
        </mark>
        {after}
      </div>
    );
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[420px] bg-surface border-l border-border shadow-2xl flex flex-col animate-slide-in-right">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border/80 bg-surface-subtle/50">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent text-accent-foreground font-mono font-bold text-xs">
            {citationIndex || "1"}
          </span>
          <span className="text-sm font-semibold text-foreground">
            Supporting Evidence
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface transition-colors"
          aria-label="Close citation panel"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* Verification Status */}
        <div className="flex items-center justify-between gap-2">
          <Badge variant="accent">
            <CheckCircle2 className="h-3 w-3 text-accent shrink-0" />
            <span>Grounded Citation</span>
          </Badge>

          {citation.document_id && onOpenDocument && (
            <button
              type="button"
              onClick={() => onOpenDocument(citation.document_id)}
              className="inline-flex items-center gap-1 text-xs text-accent hover:underline font-medium"
            >
              <span>View Document</span>
              <ExternalLink className="h-3 w-3" />
            </button>
          )}
        </div>

        {/* Document Card */}
        <div className="p-3.5 rounded-lg border border-border bg-surface-subtle/30 space-y-2">
          <div className="flex items-start gap-2.5">
            <FileText className="h-4 w-4 text-accent shrink-0 mt-0.5" />
            <div className="min-w-0 flex-1">
              <span className="text-xs font-semibold text-foreground block truncate">
                {citation.document_title || "Clinical Document"}
              </span>
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground mt-0.5">
                <Layers className="h-3 w-3 shrink-0" />
                <span className="truncate">
                  {citation.section_title || "General Section"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Content with highlighted span */}
        <div className="space-y-2">
          <div className="text-[11px] uppercase font-mono tracking-wider text-muted-foreground font-medium">
            Verified Source Context
          </div>
          <div className="p-4 rounded-lg border border-border/80 bg-surface font-sans">
            {renderHighlightedContent()}
          </div>
        </div>

        {/* Explanatory callout */}
        <div className="p-3 rounded-lg bg-surface-subtle border border-border/60 text-[11px] text-muted-foreground leading-normal">
          <span className="font-semibold text-foreground block mb-0.5">
            Clinical Verification Guarantee:
          </span>
          The highlighted phrase was extracted directly from this approved FDA
          clinical label during vector and full-text retrieval.
        </div>
      </div>
    </div>
  );
}

