// frontend/src/components/layout/Sidebar.tsx
import { NavLink } from "react-router-dom";
import {
  Bot,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
} from "lucide-react";
import { useAuthStore } from "../../store/authStore";
import { useLogout } from "../../hooks/useAuth";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/documents",  icon: FileText,        label: "Documents"  },
  { to: "/chat",       icon: MessageSquare,   label: "Chat"       },
];

export function Sidebar() {
  const { user } = useAuthStore();
  const logout = useLogout();

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-gray-900 text-white">
      {/* Logo */}
      <div className="flex items-center gap-2 px-6 py-5 border-b border-gray-700">
        <Bot className="w-7 h-7 text-indigo-400" />
        <span className="font-bold text-lg tracking-tight">RAG Chat</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-4 py-6 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
               transition-colors
               ${isActive
                 ? "bg-indigo-600 text-white"
                 : "text-gray-400 hover:bg-gray-800 hover:text-white"
               }`
            }
          >
            <Icon className="w-4 h-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User + logout */}
      <div className="px-4 py-4 border-t border-gray-700">
        <div className="flex items-center gap-3 px-3 py-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-indigo-500 flex items-center
                          justify-center text-sm font-semibold">
            {user?.username?.[0]?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.username}</p>
            <p className="text-xs text-gray-400 truncate">{user?.email}</p>
          </div>
        </div>
        <button
          onClick={() => logout.mutate()}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm
                     text-gray-400 hover:text-white hover:bg-gray-800
                     rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}