import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { NAV_PRIMARY, NAV_SECONDARY } from "../constants";
import BrandMark from "../components/ui/BrandMark";
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
      {/* The drawer (z-index 40) sits above the topbar (z-index 30) that holds the
          hamburger, so once open the toggle is covered and cannot close it. This
          backdrop and the in-drawer close button below give it two ways out. */}
      {open && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Primary navigation">
        <div className="sidebar-brand">
          <BrandMark variant="stacked" size={32} />
          <button
            type="button"
            className="btn sidebar-close"
            aria-label="Close navigation"
            onClick={() => setOpen(false)}
          >
            ✕
          </button>
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
