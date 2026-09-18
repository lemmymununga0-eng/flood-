import type { ReactNode } from "react";
import { AuthProvider } from "./context/AuthContext";

// Composes every app-wide provider in one place. Currently just AuthProvider — the
// app's sole top-level provider — but future providers (theme, query client, etc.)
// have a single named place to be added without touching App.tsx's route tree.
export function AppProviders({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
