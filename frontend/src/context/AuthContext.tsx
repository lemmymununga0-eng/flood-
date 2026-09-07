import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { AuthUser, LoginInputData, RegisterInput } from "../types";
import { ApiError, fetchMe, getStoredToken, login as apiLogin, register as apiRegister, setStoredToken } from "../services/api";

interface AuthContextValue {
  user: AuthUser | null;
  status: "checking" | "authenticated" | "anonymous";
  login: (input: LoginInputData) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<"checking" | "authenticated" | "anonymous">("checking");

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setStatus("anonymous");
      return;
    }
    fetchMe()
      .then((u) => {
        setUser(u);
        setStatus("authenticated");
      })
      .catch(() => {
        // Stored token is expired/invalid — a real check found this, not an assumption.
        setStoredToken(null);
        setUser(null);
        setStatus("anonymous");
      });
  }, []);

  const login = useCallback(async (input: LoginInputData) => {
    const result = await apiLogin(input);
    setStoredToken(result.access_token);
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const result = await apiRegister(input);
    setStoredToken(result.access_token);
    setUser(result.user);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo(() => ({ user, status, login, register, logout }), [user, status, login, register, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}

export function canManageAlerts(user: AuthUser | null): boolean {
  return !!user && ["ADMIN", "ANALYST", "OPERATOR"].includes(user.role);
}

export { ApiError };
