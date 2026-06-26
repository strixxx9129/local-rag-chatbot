// frontend/src/pages/LoginPage.tsx
import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { Bot } from "lucide-react";
import { useLogin } from "../hooks/useAuth";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Alert";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useLogin();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate({ email, password });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14
                          bg-indigo-600 rounded-2xl mb-4">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back</h1>
          <p className="text-gray-500 mt-1 text-sm">Sign in to your RAG Chat account</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          {login.error && (
            <div className="mb-4">
              <Alert type="error">
                {(login.error as { response?: { data?: { detail?: string } } })
                  ?.response?.data?.detail ?? "Invalid email or password"}
              </Alert>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <Button
              type="submit"
              className="w-full"
              loading={login.isPending}
              size="lg"
            >
              Sign in
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Don't have an account?{" "}
          <Link to="/register" className="text-indigo-600 font-medium hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
