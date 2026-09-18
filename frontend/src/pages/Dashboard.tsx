import { useCallback } from "react";
import { Link } from "react-router-dom";
import KpiCard from "../components/ui/KpiCard";
import RiskBadge from "../components/ui/RiskBadge";
import StatusBadge from "../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import {
  fetchAlerts,
  fetchFloodEvents,
  fetchLocations,
  fetchPredictions,
  fetchSystemStatus,
} from "../services/api";

const RISK_KEYS = ["low", "moderate", "high", "critical"] as const;
function normalizeRisk(r: string): (typeof RISK_KEYS)[number] {
  const lower = r.toLowerCase();
  return (RISK_KEYS as readonly string[]).includes(lower) ? (lower as any) : "moderate";
}

export default function Dashboard() {
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const [eventsState] = useFetch(useCallback(fetchFloodEvents, []));
  const [alertsState] = useFetch(useCallback(fetchAlerts, []));
  const [predState] = useFetch(useCallback(fetchPredictions, []));
  const [statusState, retryStatus] = useFetch(useCallback(fetchSystemStatus, []));

  const activeAlertsCount = alertsState.status === "success" ? alertsState.data.length : null;

  return (
    <div>
      <div className="page-header">
        <h1>Flood Intelligence Overview</h1>
        <p>
          Monitor current risk, weather conditions and early-warning activity across
          monitored locations.
        </p>
      </div>
      <div className="demo-banner">
        Early development skeleton. KPIs below are computed from real database records
        — a metric reading "0" or "unavailable" means that data genuinely doesn't exist
        yet, not a placeholder.
      </div>

      <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
        <KpiCard
          label="Active Alerts"
          value={activeAlertsCount ?? "…"}
          note="Dashboard-issued alerts"
          icon="alerts"
          accent={activeAlertsCount && activeAlertsCount > 0 ? "critical" : "blue"}
        />
        <KpiCard
          label="Monitored Locations"
          value={locState.status === "success" ? locState.data.length : "…"}
          icon="map"
          accent="green"
        />
        <KpiCard
          label="Flood Events on Record"
          value={eventsState.status === "success" ? eventsState.data.length : "…"}
          note="Reported, not a validated label"
          icon="historical-events"
          accent="gold"
        />
        <KpiCard
          label="Latest Prediction"
          value={predState.status === "success" && predState.data.length === 0 ? "None yet" : "…"}
          note="No model trained (Phases 5–9)"
          icon="predictions"
          accent="blue"
        />
      </div>

      <div className="grid grid-auto">
        <div className="card">
          <h2>Risk map</h2>
          <p className="text-secondary">
            No live risk overlay exists yet (no trained model). See real monitored
            locations on the map.
          </p>
          <Link className="btn btn-primary" to="/risk-map">
            Open Risk Map
          </Link>
        </div>

        <div className="card">
          <h2>Recent warnings</h2>
          {alertsState.status === "loading" && <LoadingState label="Loading alerts" />}
          {alertsState.status === "error" && <ErrorState detail={alertsState.message} />}
          {alertsState.status === "success" && alertsState.data.length === 0 && (
            <EmptyState title="No warnings issued yet" />
          )}
          {alertsState.status === "success" && alertsState.data.length > 0 && (
            <div>
              {alertsState.data.slice(-4).reverse().map((a) => (
                <div className="alert-row" key={a.id}>
                  <div>
                    <div>{a.title}</div>
                    <div className="alert-meta">
                      Location #{a.location_id} · {new Date(a.created_at).toLocaleString()}
                    </div>
                  </div>
                  <RiskBadge level={normalizeRisk(a.risk_level)} />
                </div>
              ))}
            </div>
          )}
          <Link className="btn btn-secondary" to="/alerts" style={{ marginTop: "0.6rem" }}>
            View all
          </Link>
        </div>

        <div className="card">
          <h2>Recent flood events</h2>
          {eventsState.status === "loading" && <LoadingState label="Loading flood events" />}
          {eventsState.status === "error" && <ErrorState detail={eventsState.message} />}
          {eventsState.status === "success" && (
            <ul style={{ margin: 0, paddingLeft: "1.1rem" }}>
              {eventsState.data.slice(-4).reverse().map((ev) => (
                <li key={ev.id} className="text-secondary" style={{ marginBottom: "0.3rem" }}>
                  <strong>{ev.event_id}</strong> — {ev.start_date} — {ev.provinces}
                </li>
              ))}
            </ul>
          )}
          <Link className="btn btn-secondary" to="/historical-events" style={{ marginTop: "0.6rem" }}>
            View all
          </Link>
        </div>

        <div className="card">
          <h2>System status</h2>
          {statusState.status === "loading" && <LoadingState label="Loading system status" />}
          {statusState.status === "error" && (
            <ErrorState detail={statusState.message} onRetry={retryStatus} />
          )}
          {statusState.status === "success" && (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {statusState.data.components.map((c) => (
                <li key={c.name} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span className="text-secondary">{c.name}</span>
                  <StatusBadge status={c.status} />
                </li>
              ))}
            </ul>
          )}
          <Link className="btn btn-secondary" to="/system-status" style={{ marginTop: "0.6rem" }}>
            Full status
          </Link>
        </div>
      </div>
    </div>
  );
}
