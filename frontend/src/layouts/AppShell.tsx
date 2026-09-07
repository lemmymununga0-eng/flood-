import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_PRIMARY = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/risk-map", label: "Risk Map" },
  { to: "/predictions", label: "Predictions" },
  { to: "/analytics", label: "Analytics" },
  { to: "/historical-events", label: "Historical Events" },
  { to: "/alerts", label: "Alerts" },
  { to: "/reports", label: "Citizen Reports" },
  { to: "/ai-model", label: "AI Model" },
  { to: "/data-sources", label: "Data Sources" },
  { to: "/system-status", label: "System Status" },
];

const NAV_SECONDARY = [
  { to: "/settings", label: "Settings" },
  { to: "/about", label: "Help & About" },
];

export default function AppShell() {
  const [open, setOpen] = useState(false);
  const { user, status, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Primary navigation">
        <div className="sidebar-brand">
          <span className="mark" aria-hidden="true" />
          <span>
            FLOODSHIELD
            <br />
            ZAMBIA
          </span>
        </div>
        <nav className="sidebar-nav">
          {NAV_PRIMARY.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              onClick={() => setOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
          <div className="nav-section-label">System</div>
          {NAV_SECONDARY.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              onClick={() => setOpen(false)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          {status === "authenticated" && user ? (
            <>
              <NavLink to="/profile" className="nav-item">
                {user.full_name || user.email} · {user.role}
              </NavLink>
              <button
                type="button"
                className="nav-item"
                style={{ width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer" }}
                onClick={() => {
                  logout();
                  navigate("/login");
                }}
              >
                Sign out
              </button>
            </>
          ) : (
            <NavLink to="/login" className="nav-item">
              Sign in
            </NavLink>
          )}
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button
            className="btn menu-toggle"
            aria-label="Toggle navigation"
            onClick={() => setOpen((v) => !v)}
          >
            ☰
          </button>
          <span className="topbar-title">Flood Intelligence Platform</span>
          <NavLink to="/notifications" className="btn btn-secondary">
            Notifications
          </NavLink>
        </header>
        <div className="page-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
