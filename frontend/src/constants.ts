// Single source of truth for the app's role set and primary navigation — previously
// duplicated as separate literals in types/index.ts and context/AuthContext.tsx.

export const ALL_ROLES = ["ADMIN", "ANALYST", "OPERATOR", "RESEARCHER", "CITIZEN"] as const;
export type Role = (typeof ALL_ROLES)[number];

export const ALERT_MANAGER_ROLES: readonly Role[] = ["ADMIN", "ANALYST", "OPERATOR"];

export const NAV_PRIMARY = [
  { to: "/dashboard", label: "Dashboard", icon: "dashboard" },
  { to: "/risk-map", label: "Risk Map", icon: "map" },
  { to: "/predictions", label: "Predictions", icon: "predictions" },
  { to: "/analytics", label: "Analytics", icon: "analytics" },
  { to: "/historical-events", label: "Historical Events", icon: "historical-events" },
  { to: "/alerts", label: "Alerts", icon: "alerts" },
  { to: "/reports", label: "Citizen Reports", icon: "reports" },
  { to: "/ai-model", label: "AI Model", icon: "ai-model" },
  { to: "/data-sources", label: "Data Sources", icon: "data-sources" },
  { to: "/system-status", label: "System Status", icon: "system-status" },
];

export const NAV_SECONDARY = [
  { to: "/settings", label: "Settings", icon: "settings" },
  { to: "/about", label: "Help & About", icon: "about" },
];
