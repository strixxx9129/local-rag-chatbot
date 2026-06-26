// frontend/src/pages/DashboardPage.tsx
import { Link } from "react-router-dom";
import { FileText, MessageSquare, Upload, CheckCircle, Clock } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { useDocuments } from "../hooks/useDocuments";
import { Spinner } from "../components/ui/Spinner";

export function DashboardPage() {
  const { user } = useAuthStore();
  const { data, isLoading } = useDocuments();

  const docs = data?.documents ?? [];
  const readyCount = docs.filter((d) => d.status === "ready").length;
  const processingCount = docs.filter(
    (d) => d.status === "pending" || d.status === "processing"
  ).length;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Welcome back, {user?.username} 👋
        </h1>
        <p className="text-gray-500 mt-1">
          Your local RAG chatbot is ready.
        </p>
      </div>

      {/* Stats */}
      {isLoading ? (
        <div className="flex items-center gap-2 text-gray-500">
          <Spinner size="sm" /> Loading stats...
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <StatCard
            icon={<FileText className="w-5 h-5 text-indigo-600" />}
            label="Total Documents"
            value={data?.total ?? 0}
            bg="bg-indigo-50"
          />
          <StatCard
            icon={<CheckCircle className="w-5 h-5 text-green-600" />}
            label="Ready to Chat"
            value={readyCount}
            bg="bg-green-50"
          />
          <StatCard
            icon={<Clock className="w-5 h-5 text-yellow-600" />}
            label="Processing"
            value={processingCount}
            bg="bg-yellow-50"
          />
        </div>
      )}

      {/* Quick actions */}
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
        <QuickAction
          to="/documents"
          icon={<Upload className="w-5 h-5 text-indigo-600" />}
          title="Upload Document"
          description="Add a new PDF to your library"
        />
        <QuickAction
          to="/chat"
          icon={<MessageSquare className="w-5 h-5 text-indigo-600" />}
          title="Start Chatting"
          description="Ask questions about your documents"
        />
      </div>
    </div>
  );
}

function StatCard({
  icon, label, value, bg,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  bg: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className={`inline-flex items-center justify-center w-10 h-10 rounded-lg ${bg} mb-3`}>
        {icon}
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}

function QuickAction({
  to, icon, title, description,
}: {
  to: string;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-start gap-3 p-4 bg-white border border-gray-200
                 rounded-xl hover:border-indigo-300 hover:shadow-sm transition-all"
    >
      <div className="mt-0.5">{icon}</div>
      <div>
        <p className="font-medium text-gray-900 text-sm">{title}</p>
        <p className="text-xs text-gray-500 mt-0.5">{description}</p>
      </div>
    </Link>
  );
}