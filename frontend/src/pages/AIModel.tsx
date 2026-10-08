import { useCallback } from "react";
import { Icon } from "../components/ui/icons";
import StatusBadge from "../components/ui/StatusBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchModels } from "../services/api";

export default function AIModel() {
  const [state, retry] = useFetch(useCallback(fetchModels, []));

  return (
    <div>
      <div className="page-header">
        <h1 style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <Icon name="ai-model" />
          AI Model Intelligence
        </h1>
        <p>Active model information, performance, and explainability — from the real model registry.</p>
      </div>

      {state.status === "loading" && <LoadingState label="Loading model registry" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No trained model exists yet"
          detail="No model version has been registered yet. Once one is, its type, training window and measured performance — including how it compares with simple baselines — will appear here."
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
              <pre className="metrics-block">{m.metrics_json}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
