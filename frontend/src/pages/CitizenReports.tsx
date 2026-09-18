import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import KpiCard from "../components/ui/KpiCard";
import StatusBadge from "../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { canManageAlerts, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { fetchCitizenReports, moderateCitizenReport, submitCitizenReport } from "../services/api";

function statusBadge(status: string): "operational" | "unavailable" | "unknown" {
  if (status === "verified") return "operational";
  if (status === "rejected") return "unavailable";
  return "unknown";
}

export default function CitizenReports() {
  const [state, retry] = useFetch(useCallback(fetchCitizenReports, []));
  const { user, status: authStatus } = useAuth();
  const [description, setDescription] = useState("");
  const [severity, setSeverity] = useState("moderate");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [moderatingId, setModeratingId] = useState<number | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    try {
      await submitCitizenReport({ description, severity });
      setDescription("");
      retry();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Could not submit report");
    } finally {
      setSubmitting(false);
    }
  }

  async function onModerate(id: number, next: "verified" | "rejected") {
    setModeratingId(id);
    try {
      await moderateCitizenReport(id, next, "");
      retry();
    } finally {
      setModeratingId(null);
    }
  }

  const counts =
    state.status === "success"
      ? state.data.reduce(
          (acc, r) => {
            if (r.status === "verified") acc.verified += 1;
            else if (r.status === "rejected") acc.rejected += 1;
            else acc.pending += 1;
            return acc;
          },
          { pending: 0, verified: 0, rejected: 0 },
        )
      : null;

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="reports" />
          Citizen Flood Reports
        </h1>
        <p>
          Community-submitted flooding reports, pending verification. Real submissions
          against the backend — see docs/api-inventory.md.
        </p>
      </div>

      {counts && (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
          <KpiCard label="Pending" value={counts.pending} icon="reports" accent="gold" />
          <KpiCard label="Verified" value={counts.verified} icon="reports" accent="green" />
          <KpiCard label="Rejected" value={counts.rejected} icon="reports" accent="critical" />
        </div>
      )}

      {authStatus === "authenticated" ? (
        <form className="card" style={{ maxWidth: 520, marginBottom: "1.5rem" }} onSubmit={onSubmit}>
          <h3 style={{ marginTop: 0 }}>Submit a ground report</h3>
          <div className="field">
            <label htmlFor="description">What are you seeing?</label>
            <textarea
              id="description"
              required
              minLength={5}
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="severity">Severity</label>
            <select id="severity" value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="low">Low</option>
              <option value="moderate">Moderate</option>
              <option value="high">High</option>
              <option value="unknown">Not sure</option>
            </select>
          </div>
          {formError && <ErrorState title="Could not submit" detail={formError} />}
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Submitting…" : "Submit report"}
          </button>
        </form>
      ) : (
        <div className="card" style={{ maxWidth: 520, marginBottom: "1.5rem" }}>
          <p className="text-secondary" style={{ margin: 0 }}>
            <Link to="/login">Sign in</Link> to submit a ground report.
          </p>
        </div>
      )}

      {state.status === "loading" && <LoadingState label="Loading citizen reports" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No citizen reports have been submitted"
          detail="This is a real, empty result from GET /api/v1/citizen-reports — not a placeholder."
        />
      )}
      {state.status === "success" && state.data.length > 0 && (
        <div className="grid grid-auto">
          {state.data.map((r) => (
            <div className="card" key={r.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                <span className="text-muted">{new Date(r.submitted_at).toLocaleString()}</span>
                <StatusBadge status={statusBadge(r.status)} />
              </div>
              <p style={{ marginBottom: "0.3rem" }}>{r.description}</p>
              <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
                Severity: {r.severity}
                {r.location_id ? ` · Location #${r.location_id}` : ""}
              </p>
              {r.review_note && <p className="text-muted">Review note: {r.review_note}</p>}
              {canManageAlerts(user) && r.status === "pending" && (
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                  <button
                    className="btn btn-secondary"
                    type="button"
                    disabled={moderatingId === r.id}
                    onClick={() => onModerate(r.id, "verified")}
                  >
                    Verify
                  </button>
                  <button
                    className="btn btn-secondary"
                    type="button"
                    disabled={moderatingId === r.id}
                    onClick={() => onModerate(r.id, "rejected")}
                  >
                    Reject
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
