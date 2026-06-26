// frontend/src/pages/ChatPage.tsx
import { FormEvent, useEffect, useRef, useState } from "react";
import {
  Bot, Send, User, FileText, X,
  ChevronDown, Loader2,
} from "lucide-react";
import { useDocuments } from "../hooks/useDocuments";
import { useStreamChat } from "../hooks/useStreamChat";
import { useChatStore } from "../store/chatStore";
import type { Citation } from "../types";

export function ChatPage() {
  const [input, setInput] = useState("");
  const [showDocPicker, setShowDocPicker] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { data: docsData } = useDocuments();
  const { sendMessage, isStreaming, statusMessage } = useStreamChat();
  const {
    messages,
    selectedDocumentId,
    setSelectedDocument,
    clearChat,
  } = useChatStore();

  const readyDocs = docsData?.documents.filter((d) => d.status === "ready") ?? [];
  const selectedDoc = readyDocs.find((d) => d.id === selectedDocumentId);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 128)}px`;
  }, [input]);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = input.trim();
    if (!q || isStreaming) return;
    setInput("");
    sendMessage(q);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-6 py-3 border-b
                      border-gray-200 bg-white shadow-sm">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-indigo-600" />
          <h1 className="font-semibold text-gray-900 text-sm">RAG Chat</h1>
        </div>

        <div className="flex items-center gap-3">
          {/* Document picker */}
          <div className="relative">
            <button
              onClick={() => setShowDocPicker(!showDocPicker)}
              className="flex items-center gap-2 text-sm border border-gray-200
                         rounded-lg px-3 py-1.5 bg-white hover:bg-gray-50
                         transition-colors"
            >
              <FileText className="w-4 h-4 text-gray-400" />
              <span className="text-gray-700 max-w-[140px] truncate text-xs">
                {selectedDoc?.title ?? "All documents"}
              </span>
              <ChevronDown className="w-3 h-3 text-gray-400" />
            </button>

            {showDocPicker && (
              <>
                {/* Backdrop */}
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowDocPicker(false)}
                />
                <div className="absolute right-0 top-9 z-20 w-64 bg-white
                                border border-gray-200 rounded-xl shadow-lg py-1">
                  <button
                    onClick={() => {
                      setSelectedDocument(null);
                      clearChat();
                      setShowDocPicker(false);
                    }}
                    className="w-full text-left px-4 py-2 text-sm
                               hover:bg-gray-50 text-gray-700"
                  >
                    All documents
                  </button>
                  {readyDocs.map((doc) => (
                    <button
                      key={doc.id}
                      onClick={() => {
                        setSelectedDocument(doc.id);
                        clearChat();
                        setShowDocPicker(false);
                      }}
                      className={`w-full text-left px-4 py-2 text-sm
                                  hover:bg-gray-50 truncate
                                  ${doc.id === selectedDocumentId
                                    ? "text-indigo-600 font-medium"
                                    : "text-gray-700"
                                  }`}
                    >
                      {doc.title}
                    </button>
                  ))}
                  {readyDocs.length === 0 && (
                    <p className="px-4 py-2 text-sm text-gray-400">
                      No ready documents
                    </p>
                  )}
                </div>
              </>
            )}
          </div>

          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-xs text-gray-400 hover:text-gray-600
                         flex items-center gap-1 transition-colors"
            >
              <X className="w-3 h-3" /> Clear
            </button>
          )}
        </div>
      </div>

      {/* ── Status bar ──────────────────────────────────────────────────── */}
      {isStreaming && statusMessage && (
        <div className="flex items-center gap-2 px-6 py-2 bg-indigo-50
                        border-b border-indigo-100 text-xs text-indigo-700">
          <Loader2 className="w-3 h-3 animate-spin" />
          {statusMessage}
        </div>
      )}

      {/* ── Messages ────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full
                          text-gray-400 gap-3">
            <Bot className="w-12 h-12 opacity-20" />
            <p className="text-sm text-center max-w-xs">
              {selectedDoc
                ? `Ask anything about "${selectedDoc.title}"`
                : "Select a document above, or ask across all your documents"}
            </p>
          </div>
        )}

        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              {msg.role === "assistant" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full
                                bg-indigo-100 flex items-center justify-center
                                self-end">
                  <Bot className="w-4 h-4 text-indigo-600" />
                </div>
              )}

              <div className="flex flex-col gap-2 max-w-[75%]">
                <div
                  className={`rounded-2xl px-4 py-3 text-sm leading-relaxed
                    ${msg.role === "user"
                      ? "bg-indigo-600 text-white rounded-tr-sm"
                      : msg.error
                        ? "bg-red-50 text-red-700 border border-red-200 rounded-tl-sm"
                        : "bg-white text-gray-800 border border-gray-200 rounded-tl-sm shadow-sm"
                    }`}
                >
                  {msg.isLoading && !msg.content ? (
                    <div className="flex items-center gap-2 text-gray-400">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Thinking...</span>
                    </div>
                  ) : (
                    <>
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {/* Blinking cursor while streaming */}
                      {msg.isLoading && msg.content && (
                        <span className="inline-block w-0.5 h-4 bg-gray-400
                                         animate-pulse ml-0.5 align-text-bottom" />
                      )}
                    </>
                  )}
                </div>

                {/* Citations */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs text-gray-400 font-medium px-1">
                      Sources
                    </p>
                    {msg.citations.map((c, i) => (
                      <CitationCard
                        key={c.chunk_id}
                        citation={c}
                        index={i + 1}
                      />
                    ))}
                  </div>
                )}
              </div>

              {msg.role === "user" && (
                <div className="flex-shrink-0 w-8 h-8 rounded-full
                                bg-gray-200 flex items-center justify-center
                                self-end">
                  <User className="w-4 h-4 text-gray-600" />
                </div>
              )}
            </div>
          ))}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* ── Input ───────────────────────────────────────────────────────── */}
      <div className="border-t border-gray-200 bg-white px-4 py-4">
        <form
          onSubmit={handleSubmit}
          className="flex items-end gap-3 max-w-3xl mx-auto"
        >
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as unknown as FormEvent);
              }
            }}
            placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
            rows={1}
            disabled={isStreaming}
            className="flex-1 resize-none rounded-xl border border-gray-300
                       px-4 py-3 text-sm focus:outline-none focus:ring-2
                       focus:ring-indigo-500 focus:border-transparent
                       disabled:bg-gray-50 disabled:text-gray-400
                       transition-colors"
            style={{ minHeight: "48px", maxHeight: "128px" }}
          />
          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className="flex-shrink-0 w-11 h-11 bg-indigo-600
                       hover:bg-indigo-700 disabled:opacity-40
                       disabled:cursor-not-allowed rounded-xl
                       flex items-center justify-center transition-colors
                       focus:outline-none focus:ring-2 focus:ring-indigo-500
                       focus:ring-offset-2"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            ) : (
              <Send className="w-4 h-4 text-white" />
            )}
          </button>
        </form>
        <p className="text-center text-xs text-gray-400 mt-2">
          Powered by {selectedDoc ? selectedDoc.title : "your documents"} ·
          Local Ollama
        </p>
      </div>
    </div>
  );
}

function CitationCard({
  citation,
  index,
}: {
  citation: Citation;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <button
      onClick={() => setExpanded(!expanded)}
      className="w-full text-left bg-gray-50 hover:bg-gray-100
                 border border-gray-200 rounded-lg px-3 py-2
                 transition-colors"
    >
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-indigo-600
                         bg-indigo-50 border border-indigo-200
                         rounded px-1.5 py-0.5 flex-shrink-0">
          [{index}]
        </span>
        <span className="text-xs font-medium text-gray-700 truncate">
          {citation.document_title}
        </span>
        {citation.page_number != null && (
          <span className="text-xs text-gray-400 flex-shrink-0">
            p. {citation.page_number}
          </span>
        )}
        <span className="ml-auto text-xs text-gray-400 flex-shrink-0">
          {Math.round(citation.relevance_score * 100)}%
        </span>
      </div>

      {expanded && (
        <p className="mt-2 text-xs text-gray-500 leading-relaxed
                      border-t border-gray-200 pt-2 text-left">
          {citation.content_snippet}
        </p>
      )}
    </button>
  );
}