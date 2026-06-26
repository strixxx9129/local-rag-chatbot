// frontend/src/api/rag.ts
import type { ChatRequest, ChatResponse, Conversation } from "../types";
import { apiClient } from "./axios";

export const ragApi = {
  chat: async (data: ChatRequest): Promise<ChatResponse> => {
    const res = await apiClient.post<ChatResponse>("/rag/chat", data, {
      timeout: 180000,
    });
    return res.data;
  },

  listConversations: async (): Promise<{ conversations: Conversation[]; total: number }> => {
    const res = await apiClient.get("/rag/conversations");
    return res.data;
  },

  getConversation: async (id: string) => {
    const res = await apiClient.get(`/rag/conversations/${id}`);
    return res.data;
  },
};
