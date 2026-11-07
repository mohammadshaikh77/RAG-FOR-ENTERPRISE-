import React from "react";
import { AlertCircle, CheckCircle2, Clock, Loader2 } from "lucide-react";
import { Badge } from "../ui/Badge.jsx";

export function StatusChip({ status, error }) {
  const norm = (status || "").toLowerCase();

  if (norm === "completed" || norm === "ready") {
    return (
      <Badge variant="success">
        <CheckCircle2 className="h-3 w-3 text-success shrink-0" />
        <span>Ready</span>
      </Badge>
    );
  }

  if (norm === "processing") {
    return (
      <Badge variant="warning">
        <Loader2 className="h-3 w-3 text-warning shrink-0 animate-spin" />
        <span>Processing</span>
      </Badge>
    );
  }

  if (norm === "failed") {
    return (
      <Badge variant="danger" title={error || "Ingestion failed"}>
        <AlertCircle className="h-3 w-3 text-danger shrink-0" />
        <span>Failed</span>
      </Badge>
    );
  }

  const label = status
    ? status.charAt(0).toUpperCase() + status.slice(1).toLowerCase()
    : "Queued";

  return (
    <Badge variant="default" title={error}>
      <Clock className="h-3 w-3 text-muted-foreground shrink-0" />
      <span>{label}</span>
    </Badge>
  );
}
