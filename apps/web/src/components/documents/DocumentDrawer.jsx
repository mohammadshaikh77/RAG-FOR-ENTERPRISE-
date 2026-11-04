import React, { useEffect, useState } from "react";
import { FileText, Hash, X } from "lucide-react";
import { getDocument, getDocumentChunks } from "../../api/documents.js";
import { Badge } from "../ui/Badge.jsx";
import { Skeleton } from "../ui/Skeleton.jsx";
import { StatusChip } from "./StatusChip.jsx";

export function DocumentDrawer({ documentId, onClose }) {
  const [doc, setDoc] = useState(null);
  const [chunks, setChunks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!documentId) return;
    setLoading(true);
    Promise.all([getDocument(documentId), getDocumentChunks(documentId)])
      .then(([docData, chunksData]) => {
        setDoc(docData);
        setChunks(chunksData || []);
      })
      .catch((err) => {
        console.error("Failed to load document details", err);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [documentId]);

  if (!documentId) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full sm:w-[460px] bg-surface border-l border-border shadow-2xl flex flex-col animate-slide-in-right">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-surface-subtle/50">
        <div className="flex items-center gap-2 truncate pr-2">
          <FileText className="h-4 w-4 text-accent shrink-0" />
          <span className="text-sm font-semibold text-foreground truncate">
            {doc?.title || "Document Details"}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close document drawer"
          className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-surface transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-32 w-full rounded-lg" />
            <Skeleton className="h-48 w-full rounded-lg" />
          </div>
        ) : doc ? (
          <div className="space-y-4">
            {/* Metadata Card */}
            <div className="p-3.5 rounded-lg border border-border bg-surface-subtle/30 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground font-medium">
                  Ingestion Status:
                </span>
                <StatusChip status={doc.status} />
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground font-medium">
                  Total Chunks:
                </span>
                <span className="font-mono font-bold text-foreground">
                  {doc.chunk_count}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-muted-foreground font-medium">
                  File Type:
                </span>
                <span className="font-mono text-muted-foreground">
                  {doc.file_type}
                </span>
              </div>

              <div className="pt-2 border-t border-border/40 text-[10px] text-muted-foreground font-mono flex items-center gap-1 truncate">
                <Hash className="h-3 w-3 shrink-0" />
                <span className="truncate">Hash: {doc.file_hash}</span>
              </div>
            </div>

            {/* Chunk Previews */}
            <div className="space-y-2">
              <div className="text-[11px] uppercase font-mono tracking-wider text-muted-foreground font-semibold flex items-center justify-between">
                <span>Structure-Aware Chunks ({chunks.length})</span>
                <Badge variant="default">{chunks.length} chunks</Badge>
              </div>

              <div className="space-y-2">
                {chunks.map((chunk) => (
                  <div
                    key={chunk.id}
                    className="p-3 rounded-lg border border-border/80 bg-surface space-y-1.5 text-xs font-sans"
                  >
                    <div className="flex items-center justify-between gap-1 text-[11px] font-mono text-accent">
                      <span className="font-semibold truncate">
                        {chunk.section_title || "General Section"}
                      </span>
                      <span className="text-muted-foreground shrink-0 text-[10px]">
                        {chunk.token_count} tokens
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                      {chunk.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

