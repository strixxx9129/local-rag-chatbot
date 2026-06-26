// frontend/src/types/index.ts

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface Document {
  id: string;
  user_id: string;
  title: string;
  filename: string;
  file_size: number;
  mime_type: string;
  page_count: number | null;
  chunk_count: number;
  status: DocumentStatus;
  error_message: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
}

export interface DocumentUploadResponse {
  id: string;
  title: string;
  filename: string;
  file_size: number;
  status: DocumentStatus;
  message: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_title: string;
  page_number: number | null;
  content_snippet: string;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  message_id: string;
  citations: Citation[];
  model: string;
  retrieved_chunks: number;
  search_mode: string;
}

export interface Conversation {
  id: string;
  title: string;
  document_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  citations?: Citation[];
}

// Local chat message — includes optimistic UI fields
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  isLoading?: boolean;
  error?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface ChatRequest {
  question: string;
  document_id?: string;
  conversation_id?: string;
  top_k?: number;
  use_hybrid?: boolean;
  vector_weight?: number;
  fts_weight?: number;
}

export interface ApiError {
  detail: string;
}