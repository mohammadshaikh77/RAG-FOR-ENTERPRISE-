import React, { useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { CheckCircle2, ExternalLink, FileText } from "lucide-react";

export function InlineCitation({ index, citation, onSelect }) {
  const [open, setOpen] = useState(false);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (onSelect) onSelect(citation, index);
          }}
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
          className="inline-flex items-center justify-center h-4.5 min-w-[18px] px-1 mx-0.5 rounded text-[11px] font-mono font-medium bg-accent-subtle text-accent border border-accent/30 hover:bg-accent hover:text-accent-foreground transition-all duration-150 align-baseline cursor-pointer select-none"
        >
          {index}
        </button>
      </Popover.Trigger>

      <Popover.Portal>
        <Popover.Content
          side="top"
          align="center"
          sideOffset={5}
          className="z-50 w-72 rounded-lg border border-border bg-surface p-3 text-foreground shadow-md outline-none animate-in fade-in-0 zoom-in-95"
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => setOpen(false)}
        >
          <div className="space-y-1.5">
            <div className="flex items-center justify-between gap-1 text-[11px] font-semibold text-accent">
              <span className="flex items-center gap-1.5 truncate">
                <FileText className="h-3 w-3 shrink-0" />
                <span className="truncate">{citation.document_title}</span>
              </span>
              {citation.is_verified && (
                <CheckCircle2
                  className="h-3 w-3 text-success shrink-0"
                  title="Verified clinical match"
                />
              )}
            </div>

            <div className="text-[10px] text-muted-foreground font-mono">
              Section: {citation.section_title || "General"}
            </div>

            <p className="text-xs text-foreground italic border-l-2 border-accent/40 pl-2 line-clamp-3 bg-surface-subtle/50 py-1 rounded-r">
              "{citation.quoted_span}"
            </p>

            <button
              type="button"
              onClick={() => {
                setOpen(false);
                if (onSelect) onSelect(citation, index);
              }}
              className="flex items-center gap-1 text-[11px] font-medium text-accent hover:underline pt-1"
            >
              <span>View full chunk and context</span>
              <ExternalLink className="h-3 w-3" />
            </button>
          </div>
          <Popover.Arrow className="fill-border" />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

