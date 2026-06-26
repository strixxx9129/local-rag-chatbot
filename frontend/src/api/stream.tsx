// frontend/src/api/stream.ts
/**
 * SSE streaming client using fetch + ReadableStream.
 *
 * Why fetch instead of EventSource?
 *   EventSource only supports GET and cannot set custom headers (no Auth).
 *   fetch with a ReadableStream supports POST, custom headers, and works
 *   perfectly for SSE.
 *
 * Event types received from the backend:
 *   status   → show progress indicator
 *   token    → append to current message
 *   metadata → update citations + conversation ID
 *   done     → stream finished
 *   error    → show error state
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export interface StreamEvent {
  type: "status" | "token" | "metadata" | "done" | "error";
  content: string | StreamMetadata;
}

export interface StreamMetadata {
  conversation_id: string;
  message_id: string;
  citations: StreamCitation[];
  model: string;
  retrieved_chunks: number;
  search_mode: string;
}

export interface StreamCitation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number: number | null;
  content_snippet: string;
  relevance_score: number;
}

export interface StreamChatOptions {
  question: string;
  document_id?: string;
  conversation_id?: string;
  top_k?: number;
  use_hybrid?: boolean;
  vector_weight?: number;
  fts_weight?: number;
  onStatus?: (message: string) => void;
  onToken?: (token: string) => void;
  onMetadata?: (metadata: StreamMetadata) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
}

export async function streamChat(options: StreamChatOptions): Promise<void> {
  const token = localStorage.getItem("access_token");

  const response = await fetch(`${BASE_URL}/stream/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      Accept: "text/event-stream",
    },
    body: JSON.stringify({
      question: options.question,
      document_id: options.document_id,
      conversation_id: options.conversation_id,
      top_k: options.top_k ?? 5,
      use_hybrid: options.use_hybrid ?? true,
      vector_weight: options.vector_weight ?? 0.6,
      fts_weight: options.fts_weight ?? 0.4,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message = (errorData as { detail?: string }).detail ?? "Stream request failed";
    options.onError?.(message);
    return;
  }

  if (!response.body) {
    options.onError?.("No response body from server");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      // Decode the chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newline
      const lines = buffer.split("\n\n");

      // Process all complete events (all but the last which may be partial)
      for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i].trim();
        if (!line.startsWith("data: ")) continue;

        const jsonStr = line.slice(6); // remove "data: " prefix
        try {
          const event: StreamEvent = JSON.parse(jsonStr);
          handleEvent(event, options);
        } catch {
          // Malformed JSON — skip
        }
      }

      // Keep the incomplete last chunk in buffer
      buffer = lines[lines.length - 1];
    }
  } finally {
    reader.releaseLock();
  }
}

function handleEvent(event: StreamEvent, options: StreamChatOptions): void {
  switch (event.type) {
    case "status":
      options.onStatus?.(event.content as string);
      break;

    case "token":
      options.onToken?.(event.content as string);
      break;

    case "metadata":
      options.onMetadata?.(event.content as StreamMetadata);
      break;

    case "done":
      options.onDone?.();
      break;

    case "error":
      options.onError?.(event.content as string);
      break;
  }
}