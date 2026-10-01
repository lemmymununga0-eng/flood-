import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import KpiCard from "../components/ui/KpiCard";
import RiskBadge from "../components/ui/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations, fetchPredictions, requestPrediction } from "../services/api";
import type { RiskPredictionResponse } from "../types";

const RISK_KEYS = ["low", "moderate", "high", "critical"] as const;
function normalizeRisk(r: string): (typeof RISK_KEYS)[number] {
  const lower = r.toLowerCase();
  return (RISK_KEYS as readonly string[]).includes(lower) ? (lower as any) : "moderate";
}

const WEATHER_FIELDS = [
  { key: "precipitation_mm", label: "Rainfall (mm/day)", step: "0.01" },
  { key: "temperature_c", label: "Mean temperature (°C)", step: "0.1" },
  { key: "temperature_max_c", label: "Max temperature (°C)", step: "0.1" },
  { key: "temperature_min_c", label: "Min temperature (°C)", step: "0.1" },
  { key: "relative_humidity_pct", label: "Relative humidity (%)", step: "0.1" },
  { key: "wind_speed_10m_ms", label: "Wind speed at 10 m (m/s)", step: "0.1" },
] as const;

type WeatherKey = (typeof WEATHER_FIELDS)[number]["key"];

export default function Predictions() {
  const [state, retry] = useFetch(useCallback(fetchPredictions, []));
  const [locState] = useFetch(useCallback(fetchLocations, []));

  const [locationId, setLocationId] = useState<number | "">("");
  const [values, setValues] = useState<Record<WeatherKey, string>>({
    precipitation_mm: "",
    temperature_c: "",
    temperature_max_c: "",
    temperature_min_c: "",
    relative_humidity_pct: "",
    wind_speed_10m_ms: "",
  });
  const [result, setResult] = useState<RiskPredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const payload = {
        location_id: locationId === "" ? undefined : Number(locationId),
        ...(Object.fromEntries(
          WEATHER_FIELDS.map((f) => [f.key, Number(values[f.key])]),
        ) as Record<WeatherKey, number>),
      };
      setResult(await requestPrediction(payload));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Prediction failed.");
    } finally {
      setSubmitting(false);
    }
  }

  const locName = new Map(
    (locState.status === "success" ? locState.data : []).map((l) => [l.id, l.name]),
  );

  // Rank by real calibrated probability — ranking is the model's demonstrated strength.
  const ordered =
    state.status === "success"
      ? [...state.data].sort((a, b) => b.prediction_probability - a.prediction_probability)
      : [];

  const counts =
    state.status === "success"
      ? state.data.reduce(
          (acc, p) => {
            acc[normalizeRisk(p.risk_level)] += 1;
            return acc;
          },
          { low: 0, moderate: 0, high: 0, critical: 0 },
        )
      : null;

  return (
    <div>
      <div className="page-header">
        <h1>AI Flood Predictions</h1>
        <p>Model-generated flood-risk estimates for monitored locations.</p>
      </div>

      {state.status === "success" && (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
          <KpiCard label="Stored Predictions" value={state.data.length} icon="predictions" accent="blue" />
          <KpiCard label="High Risk" value={counts!.high} icon="warning" accent="critical" />
          <KpiCard label="Moderate Risk" value={counts!.moderate} icon="warning" accent="gold" />
          <KpiCard label="Low Risk" value={counts!.low} icon="predictions" accent="green" />
        </div>
      )}

      <div className="grid grid-auto" style={{ marginBottom: "1rem" }}>
        <form className="card" onSubmit={onSubmit}>
          <h3>Run a prediction</h3>
          <p className="text-muted" style={{ marginTop: 0 }}>
            Score a weather observation against the trained model (7-day horizon). All six values
            are required — missing weather is never filled in with an assumed number.
          </p>

          <div className="field">
            <label htmlFor="pred-location">Location</label>
            <select
              id="pred-location"
              required
              value={locationId}
              onChange={(e) => setLocationId(e.target.value === "" ? "" : Number(e.target.value))}
            >
              <option value="">Select a location…</option>
              {locState.status === "success" &&
                locState.data.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
            </select>
          </div>

          {WEATHER_FIELDS.map((f) => (
            <div className="field" key={f.key}>
              <label htmlFor={`pred-${f.key}`}>{f.label}</label>
              <input
                id={`pred-${f.key}`}
                type="number"
                step={f.step}
                required
                value={values[f.key]}
                onChange={(e) => setValues((v) => ({ ...v, [f.key]: e.target.value }))}
              />
            </div>
          ))}

          {error && <ErrorState title="Could not generate a prediction" detail={error} />}

          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button className="btn btn-primary" type="submit" disabled={submitting}>
              {submitting ? "Scoring…" : "Estimate Risk"}
            </button>
          </div>
        </form>

        {result && (
          <div className="card">
            <h3>Risk estimate — {result.location}</h3>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", margin: "0.4rem 0 0.8rem" }}>
              <RiskBadge level={normalizeRisk(result.risk_level)} />
              <span className="text-secondary">
                {(result.risk_probability_calibrated * 100).toFixed(2)}% calibrated
              </span>
            </div>

            <table>
              <tbody>
                <tr>
                  <td className="text-muted">Horizon</td>
                  <td>Next {result.prediction_horizon_days} days</td>
                </tr>
                <tr>
                  <td className="text-muted">Raw model score</td>
                  <td>{result.risk_probability_raw.toFixed(4)}</td>
                </tr>
                <tr>
                  <td className="text-muted">Above alert threshold</td>
                  <td>
                    <span className="status-badge">
                      <span
                        className={`status-dot ${result.would_alert_at_threshold ? "degraded" : "operational"}`}
                      />
                      {result.would_alert_at_threshold ? "Yes" : "No"} (≥ {result.decision_threshold})
                    </span>
                  </td>
                </tr>
                <tr>
                  <td className="text-muted">Model</td>
                  <td>{result.model_version}</td>
                </tr>
              </tbody>
            </table>

            <h3 style={{ marginBottom: "0.4rem" }}>Contributing factors</h3>
            <table>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Contribution</th>
                  <th>Direction</th>
                </tr>
              </thead>
              <tbody>
                {result.explanation.map((c) => (
                  <tr key={c.feature}>
                    <td>{c.feature}</td>
                    <td>{c.contribution.toFixed(4)}</td>
                    <td className="text-secondary">{c.direction}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <ul className="text-muted" style={{ fontSize: "0.8rem", paddingLeft: "1.1rem", marginBottom: 0 }}>
              {result.caveats.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {state.status === "loading" && <LoadingState label="Loading predictions" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState
          title="No stored predictions yet"
          detail="Predictions are only stored once scheduled inference runs against ingested weather. Use “Run a prediction” above to score an observation now — nothing on this page is fabricated."
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
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {ordered.map((p) => (
                <tr key={p.id}>
                  <td>{locName.get(p.location_id) ?? `Location ${p.location_id}`}</td>
                  <td><RiskBadge level={normalizeRisk(p.risk_level)} /></td>
                  <td>{(p.prediction_probability * 100).toFixed(3)}%</td>
                  <td>{p.predicted_at}</td>
                  <td className="text-muted">flood_risk_lr_v1</td>
                  <td><Link className="btn btn-secondary" to={`/predictions/${p.id}`}>View</Link></td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="record-cards">
            {ordered.map((p) => (
              <div className="record-card" key={p.id}>
                <strong>{locName.get(p.location_id) ?? `Location ${p.location_id}`}</strong>
                <div style={{ margin: "0.3rem 0" }}>
                  <RiskBadge level={normalizeRisk(p.risk_level)} /> — {(p.prediction_probability * 100).toFixed(3)}%
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
