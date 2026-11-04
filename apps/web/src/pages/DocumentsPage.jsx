import React, { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { listDocuments } from "../api/documents.js";
import { DocumentDrawer } from "../components/documents/DocumentDrawer.jsx";
import { DocumentTable } from "../components/documents/DocumentTable.jsx";
import { UploadZone } from "../components/documents/UploadZone.jsx";
import { Button } from "../components/ui/Button.jsx";

export function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [inspectDocId, setInspectDocId] = useState(null);

  const fetchDocs = async () => {
    try {
      const data = await listDocuments();
      setDocuments(data || []);
    } catch (err) {
      console.error("Failed to load documents", err);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  // Poll while any document is in processing or queued
  useEffect(() => {
    const hasPending = documents.some(
      (d) => d.status === "processing" || d.status === "queued"
    );
    if (!hasPending) return;

    const interval = setInterval(fetchDocs, 3000);
    return () => clearInterval(interval);
  }, [documents]);

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-8 max-w-5xl mx-auto space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">
            Document Repository
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Upload PDF, HTML, or text files for structure-aware parsing and
            hybrid indexing.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchDocs}
          className="self-start sm:self-auto gap-1.5"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Refresh</span>
        </Button>
      </div>

      {/* Upload Zone */}
      <UploadZone onUploadComplete={fetchDocs} />

      {/* Document Table */}
      <DocumentTable
        documents={documents}
        onSelectDocument={(id) => setInspectDocId(id)}
        onRefresh={fetchDocs}
      />

      {/* Slide-out details drawer */}
      {inspectDocId && (
        <DocumentDrawer
          documentId={inspectDocId}
          onClose={() => setInspectDocId(null)}
        />
      )}
    </div>
  );
}

