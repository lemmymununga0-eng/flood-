import { useCallback, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { ErrorState, LoadingState } from "../components/ui/States";
import { canManageAlerts, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { createAlert, fetchLocations } from "../services/api";
import type { AlertCreated } from "../types";

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
  const [sendSms, setSendSms] = useState(false);
  const [phones, setPhones] = useState("");
  const [result, setResult] = useState<AlertCreated | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!locationId) {
      setError("Select a location.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const recipients = phones.split(/[\n,;]+/).map((n) => n.trim()).filter(Boolean);
      const created = await createAlert({
        title,
        risk_level: riskLevel,
        location_id: locationId,
        message,
        audience,
        channels: sendSms ? "Dashboard,SMS" : "Dashboard",
        sms_recipients: sendSms ? recipients : [],
      });
      if (sendSms) {
        setResult(created);
      } else {
        navigate("/alerts");
      }
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

  if (result) {
    const simulated = result.sms_provider === "simulated";
    return (
      <div>
        <div className="page-header">
          <h1>Alert issued</h1>
          <p>
            "{result.title}" is saved and visible on the alerts page.
            {simulated
              ? " SMS is in demo mode: nothing was actually sent."
              : " SMS was handed to the provider."}
          </p>
        </div>
        <div className="card" style={{ maxWidth: 520 }}>
          <h3>SMS delivery ({result.sms_provider})</h3>
          {result.sms_delivery.length === 0 && (
            <p className="text-secondary">
              No SMS recipients: no numbers were typed and no subscribers are registered for this
              area. Add some under SMS Subscribers.
            </p>
          )}
          <ul style={{ paddingLeft: "1.1rem" }}>
            {result.sms_delivery.map((d, i) => (
              <li key={i}>
                <strong>{d.to}</strong> — {d.status}
                <span className="text-muted"> ({d.detail})</span>
              </li>
            ))}
          </ul>
          <button className="btn btn-primary" onClick={() => navigate("/alerts")}>
            View alerts
          </button>
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
            <label className="check-row">
              <input type="checkbox" checked disabled /> Dashboard (always)
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={sendSms}
                onChange={(e) => setSendSms(e.target.checked)}
              />{" "}
              Also send by SMS (demo)
            </label>
          </div>
          {sendSms && (
            <div className="field">
              <label htmlFor="phones">Phone numbers</label>
              <textarea
                id="phones"
                rows={2}
                placeholder="+260971234567, +260961234567"
                value={phones}
                onChange={(e) => setPhones(e.target.value)}
              />
              <p className="text-muted" style={{ margin: "0.25rem 0 0" }}>
                International format. These are extra, one-off numbers (not stored). Registered
                subscribers for this area are texted automatically — manage them under SMS Subscribers.
              </p>
            </div>
          )}
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
