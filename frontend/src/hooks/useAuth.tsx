// frontend/src/hooks/useAuth.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/auth";
import { useAuthStore } from "../store/authStore";
import type { LoginRequest, RegisterRequest } from "../types";

export function useLogin() {
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: (res) => {
      setAuth(res.user, res.access_token, res.refresh_token);
      navigate("/dashboard");
    },
  });
}

export function useRegister() {
  const { setAuth } = useAuthStore();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (res) => {
      setAuth(res.user, res.access_token, res.refresh_token);
      navigate("/dashboard");
    },
  });
}

export function useLogout() {
  const { logout } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      logout();
      queryClient.clear();
      navigate("/login");
    },
  });
}