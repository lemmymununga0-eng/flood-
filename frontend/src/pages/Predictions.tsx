import { useCallback } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchPredictions } from "../services/api";

export default function Predictions() {
  const [state, retry] = useFetch(useCallback(fetchPredictions, []));

  return (
    <div>
      <div className="page-header">
        <h1>AI Flood Predictions</h1>
        <p>Model-generated flood-risk estimates for monitored locations.</p>
      </div>

      {state.status === "loading" && <LoadingState label="Loading predictions" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No prediction data available"
          detail="No model has been trained yet (roadmap Phases 5–9 haven't started). A real number here would have to be fabricated, which this project does not do."
        />
      )}
      {state.status === "success" && state.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Location</th>
                <th>Risk</th>
                <th>Probability</th>
                <th>Predicted at</th>
                <th>Model</th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((p) => (
                <tr key={p.id}>
                  <td>{p.location_id}</td>
                  <td>{p.risk_level}</td>
                  <td>{(p.prediction_probability * 100).toFixed(0)}%</td>
                  <td>{p.predicted_at}</td>
                  <td>{p.model_version_id}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="record-cards">
            {state.data.map((p) => (
              <div className="record-card" key={p.id}>
                <strong>Location {p.location_id}</strong>
                <div className="text-secondary">
                  {p.risk_level} — {(p.prediction_probability * 100).toFixed(0)}%
                </div>
                <div className="text-muted">
                  {p.predicted_at} · model {p.model_version_id}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
