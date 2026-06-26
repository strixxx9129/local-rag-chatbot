// frontend/src/pages/DocumentsPage.tsx
import { useState } from "react";
import { FileText, Trash2, Upload, CheckCircle,
         Clock, XCircle, AlertCircle } from "lucide-react";
import { useDocuments, useUploadDocument, useDeleteDocument } from "../hooks/useDocuments";
import { Button } from "../components/ui/Button";
import { Spinner } from "../components/ui/Spinner";
import { Alert } from "../components/ui/Alert";
import type { Document, DocumentStatus } from "../types";
import { formatDistanceToNow } from "date-fns";

const StatusBadge = ({ status }: { status: DocumentStatus }) => {
  const config = {
    ready:      { icon: CheckCircle, text: "Ready",      cls: "text-green-700  bg-green-50  border-green-200"  },
    processing: { icon: Clock,       text: "Processing", cls: "text-yellow-700 bg-yellow-50 border-yellow-200" },
    pending:    { icon: Clock,       text: "Pending",    cls: "text-blue-700   bg-blue-50   border-blue-200"   },
    failed:     { icon: XCircle,     text: "Failed",     cls: "text-red-700    bg-red-50    border-red-200"    },
  }[status];

  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium
                      px-2 py-0.5 rounded-full border ${config.cls}`}>
      <Icon className="w-3 h-3" />
      {config.text}
    </span>
  );
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentsPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const { data, isLoading } = useDocuments();
  const upload = useUploadDocument();
  const deleteDoc = useDeleteDocument();

  const handleFile = (file: File) => {
    setUploadError(null);
    if (file.type !== "application/pdf") {
      setUploadError("Only PDF files are supported.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setUploadError("File must be under 50 MB.");
      return;
    }
    upload.mutate({ file });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  return (
    <div className="p-8 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Upload PDFs to chat with them.
        </p>
      </div>

      {/* Upload zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center
                    transition-colors mb-6
                    ${isDragging
                      ? "border-indigo-400 bg-indigo-50"
                      : "border-gray-300 hover:border-gray-400 bg-white"}`}
      >
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm font-medium text-gray-700">
          Drag & drop a PDF here, or{" "}
          <label className="text-indigo-600 cursor-pointer hover:underline">
            browse
            <input
              type="file"
              accept=".pdf"
              className="sr-only"
              onChange={handleFileInput}
            />
          </label>
        </p>
        <p className="text-xs text-gray-400 mt-1">PDF only · Max 50 MB</p>
        {upload.isPending && (
          <div className="absolute inset-0 flex items-center justify-center
                          bg-white/80 rounded-xl">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Spinner size="sm" /> Uploading...
            </div>
          </div>
        )}
      </div>

      {uploadError && (
        <div className="mb-4">
          <Alert type="error">{uploadError}</Alert>
        </div>
      )}
      {upload.isError && (
        <div className="mb-4">
          <Alert type="error">Upload failed. Please try again.</Alert>
        </div>
      )}
      {upload.isSuccess && (
        <div className="mb-4">
          <Alert type="success">
            Document uploaded! Processing has started.
          </Alert>
        </div>
      )}

      {/* Document list */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <Spinner size="sm" /> Loading documents...
        </div>
      ) : data?.documents.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-40" />
          <p className="text-sm">No documents yet. Upload a PDF to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {data?.documents.map((doc) => (
            <DocumentRow
              key={doc.id}
              doc={doc}
              onDelete={() => deleteDoc.mutate(doc.id)}
              isDeleting={deleteDoc.isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DocumentRow({
  doc,
  onDelete,
  isDeleting,
}: {
  doc: Document;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  return (
    <div className="flex items-center gap-4 p-4 bg-white border border-gray-200
                    rounded-xl hover:border-gray-300 transition-colors">
      <div className="flex-shrink-0 w-10 h-10 bg-indigo-50 rounded-lg
                      flex items-center justify-center">
        <FileText className="w-5 h-5 text-indigo-600" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="font-medium text-gray-900 text-sm truncate">{doc.title}</p>
          <StatusBadge status={doc.status} />
        </div>
        <p className="text-xs text-gray-400">
          {formatBytes(doc.file_size)}
          {doc.page_count != null && ` · ${doc.page_count} pages`}
          {doc.chunk_count > 0 && ` · ${doc.chunk_count} chunks`}
          {" · "}
          {formatDistanceToNow(new Date(doc.created_at), { addSuffix: true })}
        </p>
        {doc.error_message && (
          <p className="text-xs text-red-500 mt-0.5 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {doc.error_message}
          </p>
        )}
      </div>

      <Button
        variant="ghost"
        size="sm"
        onClick={onDelete}
        loading={isDeleting}
        className="text-red-500 hover:text-red-700 hover:bg-red-50 flex-shrink-0"
      >
        <Trash2 className="w-4 h-4" />
      </Button>
    </div>
  );
}