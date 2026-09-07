import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/api";

export default function Signup() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await register({ email, password, full_name: fullName });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create your account. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="public-page">
      <header className="public-topbar">
        <div style={{ fontWeight: 700 }}>FLOODSHIELD ZAMBIA</div>
      </header>
      <div className="card auth-card">
        <h1 style={{ marginTop: 0 }}>Create an account</h1>
        <p className="text-secondary" style={{ marginTop: 0 }}>
          Public self-registration always creates a CITIZEN account (can submit ground
          reports). ADMIN/ANALYST/OPERATOR/RESEARCHER accounts are granted separately —
          see <code>docs/backend-architecture.md</code>.
        </p>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="fullName">Full name</label>
            <input id="fullName" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Optional" />
          </div>
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.org"
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters"
            />
          </div>
          {error && (
            <p className="text-secondary" style={{ color: "var(--risk-critical, #c94a4a)" }}>
              {error}
            </p>
          )}
          <button className="btn btn-primary" type="submit" style={{ width: "100%" }} disabled={submitting}>
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="text-muted" style={{ marginTop: "1rem" }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
