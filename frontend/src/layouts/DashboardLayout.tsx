import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { NAV_PRIMARY, NAV_SECONDARY } from "../constants";
import { Icon } from "../components/ui/icons";

function initials(nameOrEmail: string): string {
  const trimmed = nameOrEmail.trim();
  if (!trimmed) return "?";
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return trimmed.slice(0, 2).toUpperCase();
}

export default function DashboardLayout() {
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
              <Icon name={item.icon} />
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
              <Icon name={item.icon} />
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
          <div className="topbar-actions">
            <NavLink to="/notifications" className="btn btn-secondary">
              Notifications
            </NavLink>
            {status === "authenticated" && user && (
              <NavLink to="/profile" className="avatar" title={user.full_name || user.email}>
                {initials(user.full_name || user.email)}
              </NavLink>
            )}
          </div>
        </header>
        <div className="page-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
