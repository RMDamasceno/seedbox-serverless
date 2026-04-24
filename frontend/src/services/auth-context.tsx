import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { login as apiLogin, clearToken, isAuthenticated as checkAuth } from "./api";

interface AuthContextType {
  isAuthenticated: boolean;
  login: (password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authed, setAuthed] = useState(checkAuth);

  const login = useCallback(async (password: string) => {
    await apiLogin(password);
    setAuthed(true);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setAuthed(false);
  }, []);

  return (
    <AuthContext.Provider value={{ isAuthenticated: authed, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
