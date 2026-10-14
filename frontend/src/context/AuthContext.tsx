import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { AuthUser, LoginInputData, RegisterInput } from "../types";
import { fetchMe, getStoredToken, login as apiLogin, register as apiRegister, setStoredToken } from "../services/api";
import { SESSION_EXPIRED_EVENT } from "../services/http";
import { ALERT_MANAGER_ROLES } from "../constants";

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

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setStatus("anonymous");
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, onExpired);
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

/** SMS (recipients, composing, sending, history) is ADMIN-only — enforced server-side too. */
export function canSendSms(user: AuthUser | null): boolean {
  return !!user && user.role === "ADMIN";
}

export function canManageAlerts(user: AuthUser | null): boolean {
  return !!user && ALERT_MANAGER_ROLES.includes(user.role);
}
