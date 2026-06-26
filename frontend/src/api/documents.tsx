// frontend/src/api/documents.ts
import type {
  Document,
  DocumentListResponse,
  DocumentUploadResponse,
} from "../types";
import { apiClient } from "./axios";

export const documentsApi = {
  upload: async (
    file: File,
    description?: string
  ): Promise<DocumentUploadResponse> => {
    const form = new FormData();
    form.append("file", file);
    if (description) form.append("description", description);

    const res = await apiClient.post<DocumentUploadResponse>(
      "/documents/upload",
      form,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return res.data;
  },

  list: async (limit = 20, offset = 0): Promise<DocumentListResponse> => {
    const res = await apiClient.get<DocumentListResponse>("/documents", {
      params: { limit, offset },
    });
    return res.data;
  },

  get: async (id: string): Promise<Document> => {
    const res = await apiClient.get<Document>(`/documents/${id}`);
    return res.data;
  },

  getStatus: async (id: string): Promise<Document> => {
    const res = await apiClient.get<Document>(`/documents/${id}/status`);
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },
};