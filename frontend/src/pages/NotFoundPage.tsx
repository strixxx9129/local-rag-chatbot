// frontend/src/pages/NotFoundPage.tsx
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center
                    bg-gray-50 text-center px-4">
      <p className="text-6xl font-bold text-gray-200 mb-4">404</p>
      <h1 className="text-xl font-semibold text-gray-900 mb-2">Page not found</h1>
      <p className="text-gray-500 text-sm mb-6">
        The page you're looking for doesn't exist.
      </p>
      <Link to="/dashboard">
        <Button>Go to Dashboard</Button>
      </Link>
    </div>
  );
}