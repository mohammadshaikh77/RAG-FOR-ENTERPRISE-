import React, { useEffect, useRef, useState } from "react";
import {
  Plus,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { queryAgent, queryAgentStream } from "../api/agent.js";
import { ChatMessage } from "../components/chat/ChatMessage.jsx";
import { CitationPanel } from "../components/chat/CitationPanel.jsx";
import { MessageComposer } from "../components/chat/MessageComposer.jsx";
import { TraceDrawer } from "../components/chat/TraceDrawer.jsx";
import { DocumentDrawer } from "../components/documents/DocumentDrawer.jsx";

const WELCOME_STARTERS = [
  {
    title: "Pregnancy Warning",
    query: "What is the boxed warning for lisinopril regarding pregnancy?",
    desc: "Check pregnancy and fetal toxicity warnings.",
  },
  {
    title: "Side Effects",
    query: "What are the common side effects of lisinopril?",
    desc: "Find reported adverse reactions and symptoms.",
  },
  {
    title: "Kidney Precautions",
    query: "What precautions are mentioned for patients with kidney problems?",
    desc: "Review renal impairment guidance and monitoring.",
  },
  {
    title: "Unsupported Question",
    query: "What is the recommended dosage for martian-fake-drug-xyz?",
    desc: "See how Cite honestly says when info is missing.",
  },
];

export function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const [activeCitationIndex, setActiveCitationIndex] = useState(1);
  const [activeTraceId, setActiveTraceId] = useState(null);
  const [inspectDocumentId, setInspectDocumentId] = useState(null);

  const scrollRef = useRef(null);

  // Auto-scroll to bottom as messages stream
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isStreaming]);

  const handleSendMessage = async (queryText) => {
    if (!queryText.trim() || isStreaming) return;

    const userMessage = {
      role: "user",
      content: queryText,
      timestamp: new Date().toISOString(),
    };

    const assistantPlaceholder = {
      role: "assistant",
      content: "",
      query: queryText,
      citations: [],
      steps: [],
      isStreaming: true,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setIsStreaming(true);

    try {
      // Stream via SSE
      queryAgentStream(
        { query: queryText },
        (eventType, data) => {
          setMessages((prev) => {
            const updated = [...prev];
            const last = { ...updated[updated.length - 1] };
            if (!last || last.role !== "assistant") return prev;

            if (eventType === "step_start") {
              const currentSteps = last.steps || [];
              last.steps = [
                ...currentSteps,
                { step_index: data.step_index, tool_calls: [] },
              ];
            } else if (eventType === "tool_start") {
              const currentSteps = [...(last.steps || [])];
              if (currentSteps.length > 0) {
                const curStep = { ...currentSteps[currentSteps.length - 1] };
                curStep.tool_calls = [
                  ...(curStep.tool_calls || []),
                  { name: data.tool_name, arguments: data.arguments },
                ];
                currentSteps[currentSteps.length - 1] = curStep;
                last.steps = currentSteps;
              }
            } else if (eventType === "token") {
              last.content = (last.content || "") + (data.delta || "");
            } else if (eventType === "done") {
              last.content = data.final_answer || last.content;
              last.citations = data.citations || [];
              last.trace_id = data.trace_id;
              last.refused = data.refused;
              last.isStreaming = false;
            } else if (eventType === "error") {
              last.content = `Error during reasoning: ${data.error}`;
              last.isStreaming = false;
            }

            updated[updated.length - 1] = last;
            return updated;
          });
        },
        async (err) => {
          console.warn("SSE stream interrupted, falling back to sync API", err);
          // Fallback to synchronous queryAgent
          try {
            const syncRes = await queryAgent({ query: queryText });
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: syncRes.final_answer,
                query: queryText,
                citations: syncRes.citations,
                trace_id: syncRes.trace_id,
                refused: syncRes.refused,
                steps: [],
                isStreaming: false,
              };
              return updated;
            });
          } catch (syncErr) {
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = {
                role: "assistant",
                content: `Error: ${syncErr.message || "Failed to process question"}`,
                isStreaming: false,
              };
              return updated;
            });
          } finally {
            setIsStreaming(false);
          }
        },
        () => {
          setIsStreaming(false);
        }
      );
    } catch (err) {
      console.error("Agent query error", err);
      setIsStreaming(false);
    }
  };

  const handleSelectCitation = (citation, index) => {
    setActiveCitation(citation);
    setActiveCitationIndex(index);
  };

  const handleNewChat = () => {
    setMessages([]);
    setActiveCitation(null);
    setActiveTraceId(null);
  };

  return (
    <div className="flex h-full w-full overflow-hidden relative">
      {/* Messages & Composer Container */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Top Chat Action Bar */}
        <div className="flex items-center justify-between px-4 sm:px-6 py-2 border-b border-border/40 bg-surface/50 text-xs">
          <div className="flex items-center gap-2 text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-success" />
            <span className="text-[11px] font-medium text-foreground">
              Ready
            </span>
          </div>

          <button
            type="button"
            onClick={handleNewChat}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-border bg-surface hover:bg-surface-subtle text-foreground text-xs font-medium transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>New Chat</span>
          </button>
        </div>

        {/* Scrollable Message History */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 scroll-smooth"
        >
          {messages.length === 0 ? (
            /* Empty State / Welcome Screen */
            <div className="max-w-prose mx-auto pt-8 sm:pt-14 space-y-6 text-center select-none animate-fade-in">
              <div className="h-12 w-12 rounded-2xl bg-accent text-accent-foreground mx-auto flex items-center justify-center font-bold text-xl shadow-md">
                Ct
              </div>

              <div className="space-y-2">
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
                  Ask questions
                </h2>
                <p className="text-xs sm:text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                  Ask questions about the documents you have uploaded.
                </p>
              </div>

              {/* Starter Question Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left pt-4">
                {WELCOME_STARTERS.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleSendMessage(item.query)}
                    className="p-3.5 rounded-xl border border-border bg-surface hover:border-accent/50 hover:bg-surface-subtle/50 transition-all text-left space-y-1 group"
                  >
                    <span className="text-xs font-semibold text-foreground group-hover:text-accent flex items-center justify-between">
                      {item.title}
                      <Sparkles className="h-3 w-3 text-muted-foreground group-hover:text-accent transition-colors" />
                    </span>
                    <span className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                      {item.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-prose mx-auto">
              {messages.map((msg, i) => (
                <ChatMessage
                  key={i}
                  message={msg}
                  isStreaming={msg.isStreaming && isStreaming}
                  onSelectCitation={handleSelectCitation}
                  onOpenTrace={(id) => setActiveTraceId(id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Bottom Composer and Medical Disclaimer */}
        <div className="border-t border-border/60 bg-surface/80 backdrop-blur-sm pt-3 pb-2 shrink-0">
          <MessageComposer
            onSend={handleSendMessage}
            isLoading={isStreaming}
          />

          <div className="text-[11px] text-muted-foreground text-center pt-2 pb-1 font-mono select-none flex items-center justify-center gap-1.5">
            <ShieldAlert className="h-3 w-3 text-muted-foreground/70" />
            <span>
              Answers are generated from your documents and may be wrong. Not
              medical advice.
            </span>
          </div>
        </div>
      </div>

      {/* Right Slide-in Citation Panel */}
      {activeCitation && (
        <CitationPanel
          citation={activeCitation}
          citationIndex={activeCitationIndex}
          onClose={() => setActiveCitation(null)}
          onOpenDocument={(id) => setInspectDocumentId(id)}
        />
      )}

      {/* Execution Trace Drawer */}
      {activeTraceId && (
        <TraceDrawer
          traceId={activeTraceId}
          onClose={() => setActiveTraceId(null)}
        />
      )}

      {/* Document Detail Preview Drawer */}
      {inspectDocumentId && (
        <DocumentDrawer
          documentId={inspectDocumentId}
          onClose={() => setInspectDocumentId(null)}
        />
      )}
    </div>
  );
}

