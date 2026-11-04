import React, { useRef, useState } from "react";
import { AlertCircle, CheckCircle2, FileUp, Loader2, Upload } from "lucide-react";
import { uploadDocument } from "../../api/documents.js";
import { formatBytes } from "../../lib/utils.js";

const MAX_FILE_SIZE = 15 * 1024 * 1024; // 15 MB

export function UploadZone({ onUploadComplete }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState([]);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  const handleFiles = async (fileList) => {
    setError(null);
    const files = Array.from(fileList);
    if (!files.length) return;

    // Validate files
    for (const file of files) {
      if (file.size > MAX_FILE_SIZE) {
        setError(`File "${file.name}" exceeds the 15MB limit.`);
        return;
      }
    }

    const newUploads = files.map((f) => ({
      name: f.name,
      size: f.size,
      status: "uploading",
    }));
    setUploadingFiles(newUploads);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      try {
        await uploadDocument(file);
        setUploadingFiles((prev) =>
          prev.map((item, idx) =>
            idx === i ? { ...item, status: "completed" } : item
          )
        );
      } catch (err) {
        setUploadingFiles((prev) =>
          prev.map((item, idx) =>
            idx === i
              ? { ...item, status: "error", error: err.message }
              : item
          )
        );
      }
    }

    if (onUploadComplete) {
      onUploadComplete();
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div className="space-y-3">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 sm:p-8 text-center cursor-pointer transition-all duration-150 select-none ${
          isDragging
            ? "border-accent bg-accent-subtle/50"
            : "border-border hover:border-accent/50 hover:bg-surface-subtle/40 bg-surface"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.html,.htm,.json"
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
        />

        <div className="flex flex-col items-center justify-center space-y-2">
          <div className="h-10 w-10 rounded-full bg-accent-subtle text-accent flex items-center justify-center mb-1">
            <Upload className="h-5 w-5" />
          </div>

          <div className="space-y-1">
            <p className="text-sm font-semibold text-foreground">
              Drop drug labels or documents here, or{" "}
              <span className="text-accent hover:underline">browse</span>
            </p>
            <p className="text-xs text-muted-foreground font-mono">
              Supported: PDF, Digital Text, HTML, openFDA JSON (up to 15MB)
            </p>
          </div>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-danger-subtle/50 border border-danger/20 text-xs text-danger">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Progress upload queue */}
      {uploadingFiles.length > 0 && (
        <div className="space-y-1.5 p-3 rounded-lg border border-border bg-surface-subtle/40 text-xs font-mono">
          <span className="text-[11px] font-semibold text-muted-foreground block mb-1">
            Upload Queue:
          </span>
          {uploadingFiles.map((item, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between py-1 border-b border-border/40 last:border-b-0"
            >
              <div className="flex items-center gap-2 truncate">
                <FileUp className="h-3.5 w-3.5 text-accent shrink-0" />
                <span className="text-foreground truncate max-w-[200px] sm:max-w-[300px]">
                  {item.name}
                </span>
                <span className="text-muted-foreground">
                  ({formatBytes(item.size)})
                </span>
              </div>

              {item.status === "uploading" && (
                <Loader2 className="h-3.5 w-3.5 text-accent animate-spin shrink-0" />
              )}
              {item.status === "completed" && (
                <CheckCircle2 className="h-3.5 w-3.5 text-success shrink-0" />
              )}
              {item.status === "error" && (
                <span className="text-danger text-[10px] truncate max-w-[150px]">
                  {item.error || "Failed"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

