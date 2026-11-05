import React, { useState, useEffect } from "react";
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Edit3,
  Eye,
  FileText,
  Filter,
  RefreshCw,
  ShieldAlert,
  UserCheck,
  XCircle,
} from "lucide-react";
import { Badge } from "../components/ui/Badge.jsx";
import { Button } from "../components/ui/Button.jsx";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/Card.jsx";
import {
  fetchReviewQueue,
  fetchReviewQueueItem,
  submitReviewAction,
} from "../api/reviewQueue.js";

export function ReviewPage() {
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [editingMode, setEditingMode] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [actionNote, setActionNote] = useState("");
  const [rateLimitBanner, setRateLimitBanner] = useState(null);
  const [error, setError] = useState(null);

  const loadQueue = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchReviewQueue(filter);
      setItems(data);
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      if (err.status === 429) {
        setRateLimitBanner(err.message || "Too many requests, try again in a few seconds.");
      } else {
        setError(err.message || "Failed to load review queue.");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQueue();
  }, [filter]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedDetail(null);
      return;
    }
    const loadDetail = async () => {
      try {
        setDetailLoading(true);
        const detail = await fetchReviewQueueItem(selectedId);
        setSelectedDetail(detail);
        setEditedText(detail.edited_answer || detail.answer);
        setEditingMode(false);
        setActionNote("");
      } catch (err) {
        if (err.status === 429) {
          setRateLimitBanner(err.message);
        } else {
          setError(err.message);
        }
      } finally {
        setDetailLoading(false);
      }
    };
    loadDetail();
  }, [selectedId]);

  const handleAction = async (action) => {
    if (!selectedId) return;
    try {
      setActionLoading(true);
      const updated = await submitReviewAction(
        selectedId,
        action,
        action === "edit" ? editedText : null,
        actionNote || null
      );
      setSelectedDetail(updated);
      setEditingMode(false);
      // Refresh list to update badge
      setItems((prev) =>
        prev.map((item) =>
          item.id === selectedId
            ? {
                ...item,
                status: updated.status,
                answer: updated.edited_answer || updated.answer,
                reviewed_by: updated.reviewed_by,
              }
            : item
        )
      );
    } catch (err) {
      if (err.status === 429) {
        setRateLimitBanner(err.message);
      } else {
        alert(`Failed to apply action: ${err.message}`);
      }
    } finally {
      setActionLoading(false);
    }
  };

  const getTriggerBadge = (reason) => {
    switch (reason) {
      case "flagged_injection_chunk":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <ShieldAlert className="h-3 w-3" /> Injection Flag
          </span>
        );
      case "unexpected_refusal":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <AlertTriangle className="h-3 w-3" /> Unexpected Refusal
          </span>
        );
      case "low_confidence":
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <Clock className="h-3 w-3" /> Low Confidence
          </span>
        );
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "accepted":
        return <Badge variant="success">Accepted</Badge>;
      case "rejected":
        return <Badge variant="destructive">Rejected</Badge>;
      case "edited":
        return <Badge variant="accent">Edited & Approved</Badge>;
      case "pending":
      default:
        return <Badge variant="warning">Pending Review</Badge>;
    }
  };

  return (
    <div className="h-full flex flex-col p-4 sm:p-6 max-w-7xl mx-auto space-y-4">
      {/* Rate Limit Banner */}
      {rateLimitBanner && (
        <div className="p-3 bg-amber-500/15 border border-amber-500/30 rounded-xl text-amber-300 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{rateLimitBanner}</span>
          </div>
          <button
            onClick={() => setRateLimitBanner(null)}
            className="text-amber-400 hover:text-amber-200 text-xs font-semibold px-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Answers that need checking
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Review answers that Cite couldn't confidently verify.
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <div className="flex items-center bg-surface-subtle p-1 rounded-lg border border-border text-xs">
            {["all", "pending", "accepted", "rejected", "edited"].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2.5 py-1 rounded capitalize font-medium transition-all ${
                  filter === f
                    ? "bg-accent text-accent-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={loadQueue}
            disabled={loading}
            className="gap-1.5 text-xs h-8"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Main Content Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
        {/* Left Column: List of items */}
        <div className="lg:col-span-5 flex flex-col border border-border rounded-xl bg-card overflow-hidden">
          <div className="p-3 border-b border-border bg-surface-subtle/50 flex items-center justify-between text-xs font-semibold text-foreground">
            <span>Items for Review ({items.length})</span>
            <span className="text-muted-foreground capitalize">{filter} items</span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-border">
            {loading ? (
              <div className="p-8 text-center text-xs text-muted-foreground">
                <RefreshCw className="h-5 w-5 animate-spin mx-auto mb-2 text-accent" />
                Loading review queue items...
              </div>
            ) : items.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted-foreground space-y-2">
                <UserCheck className="h-8 w-8 text-muted-foreground/40 mx-auto" />
                <p className="font-semibold text-foreground">No answers need checking right now.</p>
                <p>All queries have passed automatic checks.</p>
              </div>
            ) : (
              items.map((item) => (
                <div
                  key={item.id}
                  onClick={() => setSelectedId(item.id)}
                  className={`p-3.5 cursor-pointer transition-colors text-xs space-y-1.5 ${
                    selectedId === item.id
                      ? "bg-accent/10 border-l-4 border-accent"
                      : "hover:bg-surface-subtle/70"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    {getTriggerBadge(item.trigger_reason)}
                    {getStatusBadge(item.status)}
                  </div>
                  <p className="font-medium text-foreground line-clamp-2">
                    {item.query}
                  </p>
                  <p className="text-muted-foreground line-clamp-1 text-[11px]">
                    {item.answer}
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1">
                    <span>{new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    {item.reviewed_by && (
                      <span className="text-accent truncate max-w-[140px]">
                        ✓ {item.reviewed_by}
                      </span>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Detail View & Actions */}
        <div className="lg:col-span-7 flex flex-col border border-border rounded-xl bg-card overflow-hidden">
          {detailLoading ? (
            <div className="flex-1 flex items-center justify-center p-8 text-xs text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin mr-2 text-accent" />
              Loading item details...
            </div>
          ) : !selectedDetail ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-xs text-muted-foreground space-y-2">
              <Eye className="h-8 w-8 text-muted-foreground/30" />
              <p className="font-medium text-foreground">Select an item from the queue</p>
              <p>Review the question, generated response, and retrieved source chunks.</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
              {/* Item Header */}
              <div className="flex items-start justify-between gap-4 border-b border-border pb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    {getTriggerBadge(selectedDetail.trigger_reason)}
                    {getStatusBadge(selectedDetail.status)}
                    <span className="text-[10px] font-mono text-muted-foreground">
                      ID: {selectedDetail.id.slice(0, 8)}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-foreground">
                    {selectedDetail.query}
                  </h3>
                </div>
              </div>

              {/* Answer Box */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                    <FileText className="h-3.5 w-3.5 text-accent" />
                    Agent Response
                  </label>
                  {!editingMode && (
                    <button
                      onClick={() => setEditingMode(true)}
                      className="text-xs text-accent hover:underline flex items-center gap-1"
                    >
                      <Edit3 className="h-3 w-3" /> Edit Response
                    </button>
                  )}
                </div>

                {editingMode ? (
                  <div className="space-y-2">
                    <textarea
                      value={editedText}
                      onChange={(e) => setEditedText(e.target.value)}
                      rows={5}
                      className="w-full text-xs p-3 rounded-lg border border-accent bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                      placeholder="Modify or provide corrected clinical answer..."
                    />
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setEditingMode(false);
                          setEditedText(selectedDetail.edited_answer || selectedDetail.answer);
                        }}
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="accent"
                        size="sm"
                        onClick={() => handleAction("edit")}
                        disabled={actionLoading}
                      >
                        Save & Approve Revision
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="p-3.5 rounded-lg border border-border bg-surface-subtle text-xs text-foreground leading-relaxed whitespace-pre-wrap">
                    {selectedDetail.edited_answer || selectedDetail.answer}
                  </div>
                )}
              </div>

              {/* Retrieved Chunks Accordion */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                  <Eye className="h-3.5 w-3.5 text-accent" />
                  Retrieved Chunks Context ({selectedDetail.retrieved_chunks?.length || 0})
                </label>

                <div className="space-y-2">
                  {selectedDetail.retrieved_chunks?.map((chunk, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-lg border text-xs space-y-1 ${
                        chunk.is_flagged_injection
                          ? "border-rose-500/50 bg-rose-500/10"
                          : "border-border bg-card"
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] font-medium text-foreground">
                        <span className="truncate max-w-[70%]">
                          {chunk.document_title || "Document"} — {chunk.section_title || "General"}
                        </span>
                        {chunk.is_flagged_injection && (
                          <span className="text-[10px] text-rose-400 font-bold bg-rose-500/20 px-1.5 py-0.5 rounded">
                            SUSPICIOUS CHUNK
                          </span>
                        )}
                      </div>
                      <p className="text-muted-foreground text-[11px] whitespace-pre-wrap">
                        {chunk.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Reviewer Note Input */}
              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-semibold text-foreground">
                  Reviewer Notes (Optional)
                </label>
                <input
                  type="text"
                  value={actionNote}
                  onChange={(e) => setActionNote(e.target.value)}
                  placeholder="e.g., Verified against FDA package insert section 5.1..."
                  className="w-full text-xs p-2.5 rounded-lg border border-border bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              {/* Action Buttons Bar */}
              <div className="flex items-center justify-between pt-4 border-t border-border">
                <div className="text-[11px] text-muted-foreground">
                  {selectedDetail.reviewed_by ? (
                    <span>Last reviewed by <strong className="text-foreground">{selectedDetail.reviewed_by}</strong></span>
                  ) : (
                    <span>Awaiting clinical staff review</span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleAction("reject")}
                    disabled={actionLoading}
                    className="gap-1.5 text-xs"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    Reject Answer
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setEditingMode(true)}
                    disabled={actionLoading || editingMode}
                    className="gap-1.5 text-xs"
                  >
                    <Edit3 className="h-3.5 w-3.5" />
                    Edit Answer
                  </Button>
                  <Button
                    variant="success"
                    size="sm"
                    onClick={() => handleAction("accept")}
                    disabled={actionLoading}
                    className="gap-1.5 text-xs"
                  >
                    <CheckCircle className="h-3.5 w-3.5" />
                    Accept Answer
                  </Button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
