// frontend/src/hooks/useChat.ts
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { ragApi } from "../api/rag";
import { useChatStore } from "../store/chatStore";
import type { ChatRequest } from "../types";

export function useSendMessage() {
  const {
    addUserMessage,
    addLoadingMessage,
    resolveMessage,
    setMessageError,
    setConversationId,
    conversationId,
    selectedDocumentId,
  } = useChatStore();

  return useMutation({
    mutationFn: async (question: string) => {
      addUserMessage(question);
      const loadingId = addLoadingMessage();

      const request: ChatRequest = {
        question,
        document_id: selectedDocumentId ?? undefined,
        conversation_id: conversationId ?? undefined,
        top_k: 5,
        use_hybrid: true,
      };

      try {
        const response = await ragApi.chat(request);
        resolveMessage(loadingId, response.answer, response.citations);
        setConversationId(response.conversation_id);
        return response;
      } catch (err: unknown) {
        const message = axios.isAxiosError(err) && err.code === "ECONNABORTED"
          ? "The local model is still taking too long to respond. Try asking again, or use a smaller/faster Ollama chat model."
          : err instanceof Error
            ? err.message
            : "Something went wrong";
        setMessageError(loadingId, `Error: ${message}`);
        throw err;
      }
    },
  });
}
