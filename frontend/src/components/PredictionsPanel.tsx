import { useCallback } from "react";
import { fetchPredictions } from "../services/api";
import { useFetch } from "../hooks/useFetch";

export default function PredictionsPanel() {
  const [state, retry] = useFetch(useCallback(fetchPredictions, []));

  return (
    <section className="panel">
      <h2>Flood-risk predictions</h2>
      {state.status === "loading" && <p className="hint">Loading predictions…</p>}
      {state.status === "error" && (
        <div className="error-box">
          <p>Unable to retrieve predictions.</p>
          <p className="hint">{state.message}</p>
          <button onClick={retry}>Retry</button>
        </div>
      )}
      {state.status === "success" && state.data.length === 0 && (
        <div className="empty-state">
          <p>No prediction data is available yet.</p>
          <p className="hint">
            No model has been trained (Phases 5–9 of the roadmap haven't started). This
            is not a bug — a real number here would have to be fabricated, which this
            project's rules explicitly forbid.
          </p>
        </div>
      )}
      {state.status === "success" && state.data.length > 0 && (
        <ul>
          {state.data.map((p) => (
            <li key={p.id}>
              Location {p.location_id}: {p.risk_level} ({(p.prediction_probability * 100).toFixed(0)}%),
              horizon {p.prediction_horizon}, model {p.model_version_id}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
