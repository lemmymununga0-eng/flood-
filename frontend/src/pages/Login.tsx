import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import BrandMark from "../components/ui/BrandMark";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login({ email, password });
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-split">
      <div className="auth-panel">
        <div style={{ marginBottom: "2rem" }}>
          <BrandMark />
        </div>
        <div className="card auth-card">
          <h1 style={{ marginTop: 0 }}>Welcome back</h1>
          <p className="text-secondary" style={{ marginTop: 0 }}>
            Sign in to view flood-risk intelligence and manage alerts.
          </p>
          <form onSubmit={onSubmit}>
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
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            {error && (
              <p className="text-secondary" style={{ color: "var(--risk-critical, #c94a4a)" }}>
                {error}
              </p>
            )}
            <button className="btn btn-primary" type="submit" style={{ width: "100%" }} disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="text-muted" style={{ marginTop: "1rem" }}>
            No account? <Link to="/signup">Create one</Link>
          </p>
        </div>
      </div>
      <div className="auth-visual" aria-hidden="true">
        <svg viewBox="0 0 300 400" preserveAspectRatio="xMidYMid slice">
          <defs>
            <linearGradient id="authg1" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--brand-blue)" />
              <stop offset="100%" stopColor="var(--brand-green)" />
            </linearGradient>
          </defs>
          <g fill="none" strokeWidth="1.5" opacity="0.5">
            <path d="M40 -20 Q80 100 40 220 T40 420" stroke="var(--brand-blue)" />
            <path d="M100 -20 Q140 100 100 220 T100 420" stroke="url(#authg1)" />
            <path d="M160 -20 Q200 100 160 220 T160 420" stroke="var(--brand-green)" />
            <path d="M220 -20 Q260 100 220 220 T220 420" stroke="var(--brand-gold-2)" />
          </g>
        </svg>
        <p className="auth-tagline">
          AI-powered flood prediction and early-warning intelligence for Zambia. Better
          data. Clearer decisions.
        </p>
      </div>
    </div>
  );
}
