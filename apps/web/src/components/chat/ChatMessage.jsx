import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity,
  Check,
  Copy,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { submitFeedback } from "../../api/agent.js";
import { AgentTimeline } from "./AgentTimeline.jsx";
import { InlineCitation } from "./InlineCitation.jsx";
import { RefusalCard } from "./RefusalCard.jsx";

export function ChatMessage({
  message,
  onSelectCitation,
  onOpenTrace,
  isStreaming = false,
}) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [rating, setRating] = useState(null);

  const handleCopy = () => {
    if (message.content) {
      navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleFeedback = async (value) => {
    if (!message.trace_id) return;
    setRating(value);
    try {
      await submitFeedback({ trace_id: message.trace_id, rating: value });
    } catch (e) {
      console.error("Feedback submission error", e);
    }
  };

  // Replace text citation brackets [Document: ... | Section: ... | "..."]
  // with numbered InlineCitation components
  const renderContentWithCitations = (content) => {
    if (!content) return null;
    const citations = message.citations || [];

    // If refusal card should be displayed
    if (message.refused) {
      return (
        <RefusalCard
          message={message.content}
          query={message.query}
        />
      );
    }

    // Split text by citation pattern
    const citationRegex =
      /\[(?:Document:\s*)?([^|]+?)\s*\|\s*(?:Section:\s*)?([^|]+?)\s*\|\s*["“](.+?)["”]\s*\]/gi;

    let parts = [];
    let lastIndex = 0;
    let match;
    let citationCounter = 1;

    while ((match = citationRegex.exec(content)) !== null) {
      const matchStart = match.index;
      const matchEnd = citationRegex.lastIndex;

      if (matchStart > lastIndex) {
        parts.push(content.slice(lastIndex, matchStart));
      }

      const docTitle = match[1].trim();
      const secTitle = match[2].trim();
      const span = match[3].trim();

      const existingCitation =
        citations.find(
          (c) =>
            c.quoted_span?.toLowerCase().includes(span.toLowerCase()) ||
            span.toLowerCase().includes(c.quoted_span?.toLowerCase())
        ) || {
          document_title: docTitle,
          section_title: secTitle,
          quoted_span: span,
          is_verified: true,
        };

      const cIndex = citationCounter++;
      parts.push(
        <InlineCitation
          key={`cit-${matchStart}`}
          index={cIndex}
          citation={existingCitation}
          onSelect={onSelectCitation}
        />
      );

      lastIndex = matchEnd;
    }

    if (lastIndex < content.length) {
      parts.push(content.slice(lastIndex));
    }

    return (
      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground leading-relaxed text-sm">
        {parts.map((p, i) =>
          typeof p === "string" ? (
            <ReactMarkdown key={i} remarkPlugins={[remarkGfm]}>
              {p}
            </ReactMarkdown>
          ) : (
            p
          )
        )}
      </div>
    );
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-4">
        <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl bg-surface-subtle border border-border px-4 py-2.5 text-sm text-foreground shadow-sm">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 mb-6 group">
      {/* Assistant Avatar */}
      <div className="h-7 w-7 rounded-lg bg-accent text-accent-foreground font-bold text-xs flex items-center justify-center shrink-0 shadow-sm mt-0.5">
        Ct
      </div>

      <div className="flex-1 min-w-0 space-y-2">
        {/* Agent Step Progress Timeline */}
        <AgentTimeline
          steps={message.steps || []}
          isStreaming={isStreaming}
        />

        {/* Content Body */}
        <div className="py-1">
          {renderContentWithCitations(message.content)}
        </div>

        {/* Action Controls Footer (shown once completed) */}
        {!isStreaming && message.content && (
          <div className="flex items-center gap-1 text-muted-foreground pt-1 select-none">
            <button
              type="button"
              onClick={handleCopy}
              title="Copy answer"
              className="p-1 rounded hover:bg-surface-subtle hover:text-foreground transition-colors"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-success" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>

            <button
              type="button"
              onClick={() => handleFeedback(1)}
              title="Helpful answer"
              className={`p-1 rounded hover:bg-surface-subtle transition-colors ${
                rating === 1 ? "text-accent" : "hover:text-foreground"
              }`}
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </button>

            <button
              type="button"
              onClick={() => handleFeedback(-1)}
              title="Not helpful"
              className={`p-1 rounded hover:bg-surface-subtle transition-colors ${
                rating === -1 ? "text-danger" : "hover:text-foreground"
              }`}
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </button>

            {message.trace_id && (
              <button
                type="button"
                onClick={() => onOpenTrace(message.trace_id)}
                className="flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono hover:bg-surface-subtle hover:text-foreground transition-colors ml-2 border border-border/50"
              >
                <Activity className="h-3 w-3 text-accent" />
                <span>View steps</span>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

