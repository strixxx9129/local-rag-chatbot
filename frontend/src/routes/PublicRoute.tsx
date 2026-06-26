// frontend/src/routes/PublicRoute.tsx
import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export function PublicRoute() {
  const { isAuthenticated } = useAuthStore();
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />;
}