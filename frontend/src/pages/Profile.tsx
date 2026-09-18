import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function initials(nameOrEmail: string): string {
  const trimmed = nameOrEmail.trim();
  if (!trimmed) return "?";
  const parts = trimmed.split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return trimmed.slice(0, 2).toUpperCase();
}

export default function Profile() {
  const { user, status, logout } = useAuth();

  if (status === "checking") {
    return (
      <div>
        <div className="page-header">
          <h1>Profile</h1>
        </div>
        <p className="text-secondary">Checking your session…</p>
      </div>
    );
  }

  if (status === "anonymous" || !user) {
    return (
      <div>
        <div className="page-header">
          <h1>Profile</h1>
        </div>
        <div className="card" style={{ maxWidth: 480 }}>
          <p className="text-secondary">You're not signed in.</p>
          <Link className="btn btn-primary" to="/login">
            Sign in
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>Profile</h1>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "1.25rem" }}>
          <span className="avatar avatar-lg">{initials(user.full_name || user.email)}</span>
          <div>
            <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>{user.full_name || user.email}</div>
            <div className="text-muted">{user.role}</div>
          </div>
        </div>
        <dl style={{ margin: 0 }}>
          <dt className="text-muted">Name</dt>
          <dd style={{ marginLeft: 0, marginBottom: "0.75rem" }}>{user.full_name || "—"}</dd>
          <dt className="text-muted">Email</dt>
          <dd style={{ marginLeft: 0, marginBottom: "0.75rem" }}>{user.email}</dd>
          <dt className="text-muted">Role</dt>
          <dd style={{ marginLeft: 0, marginBottom: "0.75rem" }}>{user.role}</dd>
          <dt className="text-muted">Account created</dt>
          <dd style={{ marginLeft: 0, marginBottom: "0.75rem" }}>{new Date(user.created_at).toLocaleString()}</dd>
        </dl>
        <button className="btn btn-secondary" type="button" onClick={logout}>
          Sign out
        </button>
      </div>
    </div>
  );
}
