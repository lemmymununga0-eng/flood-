import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { ErrorState, LoadingState } from "../components/ui/States";
import { canManageAlerts, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { createAlert, fetchLocations } from "../services/api";

export default function CreateAlert() {
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const navigate = useNavigate();
  const { user, status } = useAuth();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [riskLevel, setRiskLevel] = useState("high");
  const [locationId, setLocationId] = useState<number | "">("");
  const [message, setMessage] = useState("");
  const [audience, setAudience] = useState("Public");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!locationId) {
      setError("Select a location.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createAlert({
        title,
        risk_level: riskLevel,
        location_id: locationId,
        message,
        audience,
        channels: "Dashboard",
      });
      navigate("/alerts");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "checking") {
    return <LoadingState label="Checking your session" />;
  }

  if (!canManageAlerts(user)) {
    return (
      <div>
        <div className="page-header">
          <h1>Create Alert</h1>
        </div>
        <div className="card" style={{ maxWidth: 480 }}>
          <p className="text-secondary">
            Issuing an alert requires an ADMIN, ANALYST, or OPERATOR account — enforced
            by the server, not just hidden in this screen.
            {status === "anonymous" ? " You're not signed in." : ` You're signed in as ${user?.role}.`}
          </p>
          {status === "anonymous" && (
            <Link className="btn btn-primary" to="/login">
              Sign in
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="alerts" />
          Create Alert
        </h1>
        <p>This creates a real record via the backend — visible on /alerts immediately.</p>
      </div>

      {locState.status === "loading" && <LoadingState label="Loading locations" />}
      {locState.status === "error" && <ErrorState detail={locState.message} />}

      {locState.status === "success" && (
        <form className="card" style={{ maxWidth: 520 }} onSubmit={onSubmit}>
          <div className="field">
            <label htmlFor="title">Alert title</label>
            <input id="title" required value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="risk">Risk level</label>
            <select id="risk" value={riskLevel} onChange={(e) => setRiskLevel(e.target.value)}>
              <option value="low">Low</option>
              <option value="moderate">Moderate</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="location">Location</label>
            <select
              id="location"
              required
              value={locationId}
              onChange={(e) => setLocationId(Number(e.target.value))}
            >
              <option value="">Select a location…</option>
              {locState.data.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="message">Message</label>
            <textarea id="message" required rows={3} value={message} onChange={(e) => setMessage(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="audience">Audience</label>
            <input id="audience" value={audience} onChange={(e) => setAudience(e.target.value)} />
          </div>
          <div className="field">
            <label>Delivery channel</label>
            <p className="text-muted" style={{ margin: 0 }}>
              Dashboard only — no SMS/email provider is configured in this build.
            </p>
          </div>
          {error && <ErrorState title="Could not create alert" detail={error} />}
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Issuing…" : "Issue Alert"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
