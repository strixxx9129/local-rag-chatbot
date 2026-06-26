// frontend/src/components/ui/Alert.tsx
import type { ReactNode } from "react";
import { AlertCircle, CheckCircle, Info, XCircle } from "lucide-react";

interface AlertProps {
  type?: "success" | "error" | "info" | "warning";
  children: ReactNode;
}

const styles = {
  success: { bg: "bg-green-50 border-green-200", text: "text-green-800", Icon: CheckCircle },
  error:   { bg: "bg-red-50 border-red-200",     text: "text-red-800",   Icon: XCircle },
  info:    { bg: "bg-blue-50 border-blue-200",    text: "text-blue-800",  Icon: Info },
  warning: { bg: "bg-yellow-50 border-yellow-200",text: "text-yellow-800",Icon: AlertCircle },
};

export function Alert({ type = "info", children }: AlertProps) {
  const { bg, text, Icon } = styles[type];
  return (
    <div className={`flex items-start gap-2 rounded-lg border p-3 ${bg}`}>
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${text}`} />
      <p className={`text-sm ${text}`}>{children}</p>
    </div>
  );
}
