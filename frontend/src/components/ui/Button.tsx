// frontend/src/components/ui/Button.tsx
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Spinner } from "./Spinner";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  children: ReactNode;
}

const variants = {
  primary: "bg-indigo-600 hover:bg-indigo-700 text-white",
  secondary: "bg-gray-100 hover:bg-gray-200 text-gray-900",
  danger: "bg-red-600 hover:bg-red-700 text-white",
  ghost: "hover:bg-gray-100 text-gray-700",
};

const sizes = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium
        transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      {children}
    </button>
  );
}
