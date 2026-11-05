import React, { useEffect, useRef, useState } from "react";
import { ArrowUp, CornerDownLeft, Sparkles } from "lucide-react";

const SUGGESTIONS = [
  "What is the boxed warning for lisinopril regarding pregnancy?",
  "What are the common side effects of lisinopril?",
  "What precautions are mentioned for kidney problems?",
  "What are the contraindications of lisinopril?",
];

export function MessageComposer({ onSend, isLoading }) {
  const [input, setInput] = useState("");
  const textareaRef = useRef(null);

  // Auto-resize textarea height based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        160
      )}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="w-full max-w-prose mx-auto px-4 sm:px-0">
      {/* Quick Suggestion Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 scrollbar-none select-none">
        <Sparkles className="h-3.5 w-3.5 text-accent shrink-0 ml-1" />
        {SUGGESTIONS.map((sug, i) => (
          <button
            key={i}
            type="button"
            disabled={isLoading}
            onClick={() => {
              setInput(sug);
              if (textareaRef.current) textareaRef.current.focus();
            }}
            className="text-[11px] px-2.5 py-1 rounded-full border border-border bg-surface hover:bg-surface-subtle text-muted-foreground hover:text-foreground shrink-0 transition-colors"
          >
            {sug}
          </button>
        ))}
      </div>

      {/* Input Box Container */}
      <form
        onSubmit={handleSubmit}
        className="relative flex flex-col rounded-xl border border-border bg-surface shadow-sm focus-within:ring-2 focus-within:ring-accent focus-within:border-accent transition-all duration-150 overflow-hidden"
      >
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask something about your documents..."
          rows={1}
          disabled={isLoading}
          className="w-full resize-none bg-transparent px-4 py-3.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none max-h-40 min-h-[48px]"
        />

        <div className="flex items-center justify-between px-3 py-2 bg-surface-subtle/50 border-t border-border/40 text-xs">
          <div className="flex items-center gap-1.5 text-muted-foreground text-[11px]">
            <CornerDownLeft className="h-3 w-3" />
            <span>Enter to send</span>
          </div>

          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            aria-label="Send message"
            className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-accent-foreground hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </div>
      </form>
    </div>
  );
}

