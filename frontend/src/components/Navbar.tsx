import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../services/auth-context";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/downloads", label: "Downloads" },
  { to: "/infrastructure", label: "Infra" },
];

export default function Navbar() {
  const { logout } = useAuth();
  const { pathname } = useLocation();

  return (
    <nav className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-5xl mx-auto px-4 flex items-center justify-between h-14">
        <div className="flex items-center gap-6">
          <Link to="/" className="text-lg font-bold text-blue-400">Seedbox</Link>
          <div className="hidden sm:flex gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`px-3 py-1.5 rounded text-sm transition-colors ${
                  pathname === item.to
                    ? "bg-gray-700 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>
        <button onClick={logout} className="text-sm text-gray-400 hover:text-white transition-colors">
          Sair
        </button>
      </div>

      {/* Mobile nav */}
      <div className="sm:hidden flex gap-1 px-4 pb-2">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`px-3 py-1.5 rounded text-sm flex-1 text-center ${
              pathname === item.to ? "bg-gray-700 text-white" : "text-gray-400"
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
