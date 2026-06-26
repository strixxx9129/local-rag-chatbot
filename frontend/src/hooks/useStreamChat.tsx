import { useCallback, useRef, useState } from "react";
import { streamChat } from "../api/stream";
import type { StreamMetadata } from "../api/stream";
import { useChatStore } from "../store/chatStore";
import type { Citation } from "../types";

interface StreamState {
  isStreaming: boolean;
  statusMessage: string;
  error: string | null;
}

export function useStreamChat() {
  const [state, setState] = useState<StreamState>({
    isStreaming: false,
    statusMessage: "",
    error: null,
  });

  const loadingIdRef = useRef<string | null>(null);

  const {
    addUserMessage,
    addLoadingMessage,
    resolveMessage,
    setMessageError,
    setConversationId,
    conversationId,
    selectedDocumentId,
  } = useChatStore();

  const sendMessage = useCallback(
    async (question: string) => {
      if (!question.trim() || state.isStreaming) return;

      addUserMessage(question);

      const loadingId = addLoadingMessage();
      loadingIdRef.current = loadingId;

      setState({ isStreaming: true, statusMessage: "", error: null });

      let accumulated = "";

      await streamChat({
        question,
        document_id: selectedDocumentId ?? undefined,
        conversation_id: conversationId ?? undefined,
        top_k: 5,
        use_hybrid: true,

        onStatus: (message) => {
          setState((prev) => ({ ...prev, statusMessage: message }));
        },

        onToken: (token) => {
          accumulated += token;
          const id = loadingIdRef.current;
          if (id) {
            useChatStore.setState((store) => ({
              messages: store.messages.map((m) =>
                m.id === id
                  ? { ...m, content: accumulated, isLoading: true }
                  : m
              ),
            }));
          }
        },

        onMetadata: (metadata: StreamMetadata) => {
          setConversationId(metadata.conversation_id);
          const id = loadingIdRef.current;
          if (id) {
            const citations: Citation[] = metadata.citations.map((c) => ({
              chunk_id: c.chunk_id,
              document_id: c.document_id,
              document_title: c.document_title,
              page_number: c.page_number,
              content_snippet: c.content_snippet,
              relevance_score: c.relevance_score,
            }));
            resolveMessage(id, accumulated, citations);
            loadingIdRef.current = null;
          }
        },

        onDone: () => {
          const id = loadingIdRef.current;
          if (id) {
            resolveMessage(id, accumulated);
            loadingIdRef.current = null;
          }
          setState({ isStreaming: false, statusMessage: "", error: null });
        },

        onError: (message) => {
          const id = loadingIdRef.current;
          if (id) {
            setMessageError(id, `Error: ${message}`);
            loadingIdRef.current = null;
          }
          setState({ isStreaming: false, statusMessage: "", error: message });
        },
      });

      setState((prev) => ({ ...prev, isStreaming: false, statusMessage: "" }));
    },
    [
      state.isStreaming,
      addUserMessage,
      addLoadingMessage,
      resolveMessage,
      setMessageError,
      setConversationId,
      conversationId,
      selectedDocumentId,
    ]
  );

  return { ...state, sendMessage };
}