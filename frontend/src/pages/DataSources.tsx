import { useCallback, useState } from "react";
import { Icon } from "../components/ui/icons";
import KpiCard from "../components/ui/KpiCard";
import StatusBadge from "../components/ui/StatusBadge";
import { ErrorState, LoadingState } from "../components/ui/States";
import { canManageAlerts, useAuth } from "../context/AuthContext";
import { useFetch } from "../hooks/useFetch";
import { checkDataSource, fetchDataSources } from "../services/api";
import type { DataSourceEntry } from "../types";

function toBadgeStatus(status: DataSourceEntry["last_check_status"]): "operational" | "unavailable" | "unknown" {
  if (status === "ok") return "operational";
  if (status === "failed") return "unavailable";
  return "unknown";
}

export default function DataSources() {
  const [state, retry] = useFetch(useCallback(fetchDataSources, []));
  const { user } = useAuth();
  const [checkingId, setCheckingId] = useState<number | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  async function runCheck(id: number) {
    setCheckingId(id);
    setCheckError(null);
    try {
      await checkDataSource(id);
      retry();
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : "Check failed");
    } finally {
      setCheckingId(null);
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="data-sources" />
          Data Sources
        </h1>
        <p>
          The real catalog of external data this project depends on. Status reflects the
          last real connectivity check — see docs/DATA-SOURCES.md for why NASA POWER and
          DMMU/WARMA are currently unreachable from this development environment.
        </p>
      </div>

      {state.status === "success" && (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
          <KpiCard
            label="Operational"
            value={state.data.filter((s) => s.last_check_status === "ok").length}
            icon="data-sources"
            accent="green"
          />
          <KpiCard
            label="Failed"
            value={state.data.filter((s) => s.last_check_status === "failed").length}
            icon="warning"
            accent="critical"
          />
          <KpiCard
            label="Unknown"
            value={state.data.filter((s) => s.last_check_status === "unknown").length}
            icon="data-sources"
            accent="gold"
          />
        </div>
      )}

      {state.status === "loading" && <LoadingState label="Loading data sources" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {checkError && <ErrorState title="Check failed" detail={checkError} />}

      {state.status === "success" && (
        <div className="grid grid-auto">
          {state.data.map((s) => (
            <div className="card" key={s.id}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <h3 style={{ margin: 0 }}>{s.name}</h3>
                <StatusBadge status={toBadgeStatus(s.last_check_status)} />
              </div>
              <p className="text-secondary">{s.category}</p>
              <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
                {s.description}
              </p>
              <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
                Last checked:{" "}
                {s.last_checked_at ? new Date(s.last_checked_at).toLocaleString() : "never"}
                {s.last_check_detail ? ` — ${s.last_check_detail}` : ""}
              </p>
              {canManageAlerts(user) && (
                <button
                  className="btn btn-secondary"
                  type="button"
                  disabled={checkingId === s.id}
                  onClick={() => runCheck(s.id)}
                >
                  {checkingId === s.id ? "Checking…" : "Check now"}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
