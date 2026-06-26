// frontend/src/components/ui/Input.tsx
import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = "", ...props }, ref) => (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-sm font-medium text-gray-700">{label}</label>
      )}
      <input
        ref={ref}
        className={`w-full rounded-lg border px-3 py-2 text-sm
          placeholder:text-gray-400
          focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent
          disabled:bg-gray-50 disabled:text-gray-500
          ${error ? "border-red-400" : "border-gray-300"}
          ${className}`}
        {...props}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  )
);

Input.displayName = "Input";
