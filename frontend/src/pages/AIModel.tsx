import { useCallback } from "react";
import StatusBadge from "../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchModels } from "../services/api";

export default function AIModel() {
  const [state, retry] = useFetch(useCallback(fetchModels, []));

  return (
    <div>
      <div className="page-header">
        <h1>AI Model Intelligence</h1>
        <p>Active model information, performance, and explainability — from the real model registry.</p>
      </div>

      {state.status === "loading" && <LoadingState label="Loading model registry" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No trained model exists yet"
          detail="Roadmap Phases 5–9 (Baseline Models through Model Packaging) have not started — see docs/ROADMAP.md and docs/ML-METHODOLOGY.md. This queries the real GET /api/v1/models endpoint (backend/app/api/model_registry.py); it returns an empty list because model_versions is genuinely empty, not because the endpoint doesn't exist. Model type, version, training date, dataset window, and performance metrics will appear here once training actually happens, populated with real measured numbers only."
        />
      )}
      {state.status === "success" && state.data.length > 0 && (
        <div className="grid grid-auto">
          {state.data.map((m) => (
            <div className="card" key={m.id}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <h3 style={{ margin: 0 }}>
                  {m.model_type} v{m.version}
                </h3>
                <StatusBadge status={m.is_active ? "operational" : "degraded"} />
              </div>
              <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
                Trained on data from {new Date(m.training_period_start).toLocaleDateString()} –{" "}
                {new Date(m.training_period_end).toLocaleDateString()}
              </p>
              <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
                Registered {new Date(m.registered_at).toLocaleString()}
              </p>
              <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.8rem" }}>{m.metrics_json}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
