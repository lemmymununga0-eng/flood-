import { useCallback } from "react";
import StatusBadge from "../components/ui/StatusBadge";
import { ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchSystemStatus } from "../services/api";

export default function SystemStatusPage() {
  const [state, retry] = useFetch(useCallback(fetchSystemStatus, []));

  return (
    <div>
      <div className="page-header">
        <h1>System Status</h1>
        <p>Live, computed at request time — nothing below is a hardcoded "Operational."</p>
      </div>

      {state.status === "loading" && <LoadingState label="Checking system status" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && (
        <>
          <p className="text-muted">
            Last checked: {new Date(state.data.checked_at).toLocaleString()}
          </p>
          <div className="grid grid-auto">
            {state.data.components.map((c) => (
              <div className="card" key={c.name}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <h3 style={{ margin: 0 }}>{c.name}</h3>
                  <StatusBadge status={c.status} />
                </div>
                <p className="text-secondary">{c.detail}</p>
                {c.response_time_ms != null && (
                  <p className="text-muted" style={{ margin: 0 }}>
                    Response time: {c.response_time_ms}ms
                  </p>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
