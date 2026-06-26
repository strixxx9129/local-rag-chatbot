// frontend/src/pages/RegisterPage.tsx
import { useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { Bot } from "lucide-react";
import { useRegister } from "../hooks/useAuth";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Alert";

export function RegisterPage() {
  const [form, setForm] = useState({
    email: "",
    username: "",
    password: "",
    full_name: "",
  });
  const register = useRegister();

  const set = (field: string) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    register.mutate(form);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14
                          bg-indigo-600 rounded-2xl mb-4">
            <Bot className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Create account</h1>
          <p className="text-gray-500 mt-1 text-sm">Start chatting with your documents</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          {register.error && (
            <div className="mb-4">
              <Alert type="error">
                {(register.error as { response?: { data?: { detail?: string } } })
                  ?.response?.data?.detail ?? "Registration failed. Please try again."}
              </Alert>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Full name"
              placeholder="Jane Doe"
              value={form.full_name}
              onChange={set("full_name")}
            />
            <Input
              label="Username"
              placeholder="janedoe"
              value={form.username}
              onChange={set("username")}
              required
            />
            <Input
              label="Email"
              type="email"
              placeholder="jane@example.com"
              value={form.email}
              onChange={set("email")}
              required
            />
            <Input
              label="Password"
              type="password"
              placeholder="Min 8 chars, 1 uppercase, 1 number"
              value={form.password}
              onChange={set("password")}
              required
            />
            <Button
              type="submit"
              className="w-full"
              loading={register.isPending}
              size="lg"
            >
              Create account
            </Button>
          </form>
        </div>

        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-indigo-600 font-medium hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
