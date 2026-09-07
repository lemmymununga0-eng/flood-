import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

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
          <NavLink to="/profile" className="nav-item">
            Admin User
          </NavLink>
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
