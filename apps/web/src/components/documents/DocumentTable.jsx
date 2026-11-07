import React, { useState } from "react";
import {
  Database,
  ExternalLink,
  FileText,
  Search,
  Trash2,
} from "lucide-react";
import { deleteDocument } from "../../api/documents.js";
import { StatusChip } from "./StatusChip.jsx";

export function DocumentTable({
  documents = [],
  onSelectDocument,
  onRefresh,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const filteredDocs = documents.filter((doc) =>
    (doc.title || "").toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleDelete = async (id, title) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"?`)) return;
    setDeletingId(id);
    try {
      await deleteDocument(id);
      if (onRefresh) onRefresh();
    } catch (err) {
      alert(`Failed to delete document: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search Filter Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search documents by title..."
            className="w-full h-9 pl-9 pr-3 rounded-lg border border-input bg-surface text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>

        <div className="text-xs text-muted-foreground font-mono">
          {filteredDocs.length} of {documents.length} documents
        </div>
      </div>

      {/* Table Container */}
      <div className="rounded-xl border border-border bg-surface overflow-hidden shadow-sm">
        {filteredDocs.length === 0 ? (
          <div className="p-8 text-center space-y-3">
            <div className="h-10 w-10 rounded-full bg-surface-subtle text-muted-foreground mx-auto flex items-center justify-center">
              <Database className="h-5 w-5" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                No documents found
              </p>
              <p className="text-xs text-muted-foreground max-w-md mx-auto">
                Upload a PDF or text file above to get started.
              </p>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-subtle/60 border-b border-border/80 text-muted-foreground font-medium uppercase font-mono text-[10px]">
                <tr>
                  <th className="px-4 py-3">Document Title</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-right">Sections processed</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredDocs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="hover:bg-surface-subtle/50 transition-colors group"
                  >
                    <td className="px-4 py-3 font-medium text-foreground">
                      <div className="flex items-center gap-2 max-w-md truncate">
                        <FileText className="h-4 w-4 text-accent shrink-0" />
                        <span className="truncate" title={doc.title}>
                          {doc.title}
                        </span>
                      </div>
                    </td>

                    <td className="px-4 py-3 text-muted-foreground font-mono text-[11px]">
                      {doc.file_type?.split("/")[1] || doc.file_type}
                    </td>

                    <td className="px-4 py-3">
                      <StatusChip status={doc.status} error={doc.error_message} />
                    </td>

                    <td className="px-4 py-3 text-right font-mono font-semibold text-foreground">
                      {doc.chunk_count}
                    </td>

                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => onSelectDocument(doc.id)}
                          title="Inspect chunks outline"
                          className="p-1 rounded text-muted-foreground hover:text-accent hover:bg-surface-subtle transition-colors"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </button>

                        <button
                          type="button"
                          disabled={deletingId === doc.id}
                          onClick={() => handleDelete(doc.id, doc.title)}
                          title="Delete document"
                          className="p-1 rounded text-muted-foreground hover:text-danger hover:bg-danger-subtle transition-colors"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

