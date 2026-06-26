// frontend/src/api/auth.ts
import type { AccessTokenResponse, LoginRequest, RegisterRequest, TokenResponse } from "../types/index";
import { apiClient } from "./axios";

export const authApi = {
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/register", data);
    return res.data;
  },

  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const res = await apiClient.post<TokenResponse>("/auth/login", data);
    return res.data;
  },

  logout: async (): Promise<void> => {
    await apiClient.post("/auth/logout");
  },

  me: async () => {
    const res = await apiClient.get("/auth/me");
    return res.data;
  },

  refresh: async (refreshToken: string): Promise<AccessTokenResponse> => {
    const res = await apiClient.post<AccessTokenResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return res.data;
  },
};