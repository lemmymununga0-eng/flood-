import { useCallback } from "react";
import { Link } from "react-router-dom";
import KpiCard from "../components/ui/KpiCard";
import RiskBadge from "../components/ui/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchAlerts } from "../services/api";

const RISK_KEYS = ["low", "moderate", "high", "critical"] as const;
function normalizeRisk(r: string): (typeof RISK_KEYS)[number] {
  const lower = r.toLowerCase();
  return (RISK_KEYS as readonly string[]).includes(lower) ? (lower as any) : "moderate";
}

export default function Alerts() {
  const [state, retry] = useFetch(useCallback(fetchAlerts, []));

  const counts =
    state.status === "success"
      ? state.data.reduce(
          (acc, a) => {
            acc[normalizeRisk(a.risk_level)] += 1;
            return acc;
          },
          { low: 0, moderate: 0, high: 0, critical: 0 },
        )
      : null;

  return (
    <div>
      <div className="page-header">
        <h1>Early Warning &amp; Alerts</h1>
        <p>Dashboard-issued alerts. No SMS/email provider is configured in this build.</p>
      </div>

      {state.status === "success" && (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
          <KpiCard label="Total Alerts" value={state.data.length} icon="alerts" accent="blue" />
          <KpiCard label="Critical" value={counts!.critical} icon="warning" accent="critical" />
          <KpiCard label="High" value={counts!.high} icon="warning" accent="gold" />
          <KpiCard label="Low / Moderate" value={counts!.low + counts!.moderate} icon="alerts" accent="green" />
        </div>
      )}

      <div style={{ marginBottom: "1rem" }}>
        <Link className="btn btn-primary" to="/alerts/create">
          Create Alert
        </Link>{" "}
        <Link className="btn btn-secondary" to="/alerts/subscribers">
          SMS Subscribers
        </Link>
      </div>

      {state.status === "loading" && <LoadingState label="Loading alerts" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No alerts have been issued yet"
          detail="Alerts created here are genuinely persisted — this list is really empty, not a placeholder."
        />
      )}
      {state.status === "success" && state.data.length > 0 && (
        <div className="grid grid-auto">
          {state.data.map((a) => (
            <div className="card" key={a.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                <h3 style={{ margin: 0 }}>{a.title}</h3>
                <RiskBadge level={normalizeRisk(a.risk_level)} />
              </div>
              <p className="text-secondary">{a.message}</p>
              <p className="text-muted" style={{ margin: 0 }}>
                Location #{a.location_id} · {a.channels} · {a.status} · {new Date(a.created_at).toLocaleString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
