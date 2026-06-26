// frontend/src/store/chatStore.ts
import { create } from "zustand";
import type { ChatMessage, Citation } from "../types";

interface ChatState {
  messages: ChatMessage[];
  conversationId: string | null;
  selectedDocumentId: string | null;
  isLoading: boolean;

  setSelectedDocument: (id: string | null) => void;
  addUserMessage: (content: string) => string;
  addLoadingMessage: () => string;
  resolveMessage: (
    id: string,
    content: string,
    citations?: Citation[]
  ) => void;
  setMessageError: (id: string, error: string) => void;
  setConversationId: (id: string) => void;
  clearChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  conversationId: null,
  selectedDocumentId: null,
  isLoading: false,

  setSelectedDocument: (id) =>
    set({ selectedDocumentId: id, messages: [], conversationId: null }),

  addUserMessage: (content) => {
    const id = crypto.randomUUID();
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: "user", content, isLoading: false },
      ],
    }));
    return id;
  },

  addLoadingMessage: () => {
    const id = crypto.randomUUID();
    set((state) => ({
      messages: [
        ...state.messages,
        { id, role: "assistant", content: "", isLoading: true },
      ],
      isLoading: true,
    }));
    return id;
  },

  resolveMessage: (id, content, citations) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id
          ? { ...m, content, citations, isLoading: false, error: undefined }
          : m
      ),
      isLoading: false,
    })),

  setMessageError: (id, error) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, content: error, isLoading: false, error } : m
      ),
      isLoading: false,
    })),

  setConversationId: (id) => set({ conversationId: id }),

  clearChat: () =>
    set({ messages: [], conversationId: null, isLoading: false }),
}));
