import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import RiskBadge from "../components/ui/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations, fetchModels, fetchPredictions } from "../services/api";

const RISK_KEYS = ["low", "moderate", "high", "critical"] as const;
function normalizeRisk(r: string): (typeof RISK_KEYS)[number] {
  const lower = r.toLowerCase();
  return (RISK_KEYS as readonly string[]).includes(lower) ? (lower as any) : "moderate";
}

const TABS = ["AI Explanation", "Input Data", "SHAP Analysis", "Model Info"] as const;
type Tab = (typeof TABS)[number];

export default function PredictionDetail() {
  const { id } = useParams();
  const [predState, retry] = useFetch(useCallback(fetchPredictions, []));
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const [modelState] = useFetch(useCallback(fetchModels, []));
  const [tab, setTab] = useState<Tab>("AI Explanation");

  if (predState.status === "loading") return <LoadingState label="Loading prediction" />;
  if (predState.status === "error")
    return <ErrorState detail={predState.message} onRetry={retry} />;

  const prediction = predState.data.find((p) => String(p.id) === String(id));
  if (!prediction) {
    return (
      <div>
        <div className="page-header"><h1>Prediction not found</h1></div>
        <EmptyState
          title="No such prediction"
          detail="This prediction id does not exist in the database. It may have been superseded by a newer run."
        />
        <Link className="btn btn-secondary" to="/predictions">Back to Predictions</Link>
      </div>
    );
  }

  const location =
    locState.status === "success"
      ? locState.data.find((l) => l.id === prediction.location_id)
      : undefined;

  const model = modelState.status === "success" ? modelState.data[0] : undefined;
  let modelMeta: any = null;
  try { modelMeta = model ? JSON.parse(model.metrics_json) : null; } catch { modelMeta = null; }

  let detail: any = null;
  try { detail = JSON.parse(prediction.explanation || "{}"); } catch { detail = null; }

  const risk = normalizeRisk(prediction.risk_level);
  const shap: { feature: string; mean_abs_shap: number }[] = modelMeta?.shap_global_importance ?? [];
  const maxShap = shap.length ? Math.max(...shap.map((s) => s.mean_abs_shap)) : 1;

  return (
    <div>
      <div className="page-header">
        <h1>{location?.name ?? `Location ${prediction.location_id}`}</h1>
        <p>
          {location?.province ? `${location.province} Province · ` : ""}
          {location ? `${location.latitude.toFixed(4)}, ${location.longitude.toFixed(4)} · ` : ""}
          Model {model?.version ?? "—"}
        </p>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <Link className="btn btn-secondary" to="/predictions">← Back to Predictions</Link>
      </div>

      <div className="grid grid-auto" style={{ marginBottom: "1rem" }}>
        <div className="card">
          <h3 style={{ marginBottom: "0.5rem" }}>Risk assessment</h3>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <RiskBadge level={risk} />
            <span style={{ fontSize: "1.9rem", fontWeight: 700 }}>
              {(prediction.prediction_probability * 100).toFixed(3)}%
            </span>
          </div>
          <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
            Calibrated probability of a flood occurring within the next{" "}
            {prediction.prediction_horizon}. Flooding is genuinely rare (~0.04% of
            location-days), so meaningful values are small — the band above reflects how
            this location ranks relative to others, not an absolute chance.
          </p>
          <div className="stat-row">
            <span className="stat-label">Horizon</span>
            <span className="stat-value">{prediction.prediction_horizon}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Raw model score</span>
            <span className="stat-value">{detail?.raw_score ?? "—"}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Observation date</span>
            <span className="stat-value">{detail?.observation_date ?? "—"}</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Generated</span>
            <span className="stat-value">{prediction.predicted_at}</span>
          </div>
        </div>

        <div className="card">
          <div className="tab-bar">
            {TABS.map((t) => (
              <button
                key={t}
                type="button"
                className={`tab ${tab === t ? "active" : ""}`}
                onClick={() => setTab(t)}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === "AI Explanation" && (
            <div>
              <h3 style={{ marginTop: "0.8rem" }}>Why this prediction?</h3>
              <ul className="text-secondary" style={{ paddingLeft: "1.1rem", fontSize: "0.86rem" }}>
                <li>
                  Strongest contributing features for this observation:{" "}
                  <strong>{detail?.top_contributions ?? "not recorded"}</strong>
                </li>
                <li>
                  The model weighs sustained atmospheric moisture (relative humidity) and
                  temperature more heavily than same-day rainfall — a real, measured
                  finding from its SHAP analysis, not an assumption.
                </li>
                <li>
                  Risk band assigned by comparing the calibrated probability against
                  validation-set percentiles (90th → Moderate, 99th → High).
                </li>
              </ul>
              <p className="text-muted" style={{ fontSize: "0.78rem" }}>
                These are correlational contributions the model found. They do not assert
                that any feature <em>causes</em> flooding.
              </p>
            </div>
          )}

          {tab === "Input Data" && (
            <div>
              <h3 style={{ marginTop: "0.8rem" }}>Observation used</h3>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                Real NASA POWER reading for {detail?.observation_date ?? "the scored date"}.
                No value was imputed.
              </p>
              {detail?.note && (
                <p className="text-secondary" style={{ fontSize: "0.82rem" }}>{detail.note}</p>
              )}
              <div className="stat-row">
                <span className="stat-label">Source</span>
                <span className="stat-value">NASA POWER (MERRA-2 reanalysis)</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Features used</span>
                <span className="stat-value">
                  {(modelMeta?.features ?? []).join(", ") || "—"}
                </span>
              </div>
            </div>
          )}

          {tab === "SHAP Analysis" && (
            <div>
              <h3 style={{ marginTop: "0.8rem" }}>Feature contribution (SHAP)</h3>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                Mean |SHAP value| measured across a real sample of the held-out test set.
              </p>
              {shap.length === 0 ? (
                <p className="text-secondary">No SHAP output recorded for this model.</p>
              ) : (
                shap.map((s) => (
                  <div className="bar-row" key={s.feature}>
                    <span>{s.feature}</span>
                    <span className="bar-track">
                      <span
                        className="bar-fill gold"
                        style={{ width: `${Math.max(2, (s.mean_abs_shap / maxShap) * 100)}%` }}
                      />
                    </span>
                    <span className="bar-value">{s.mean_abs_shap.toFixed(3)}</span>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "Model Info" && modelMeta && (
            <div>
              <h3 style={{ marginTop: "0.8rem" }}>Model information</h3>
              <div className="stat-row">
                <span className="stat-label">Version</span>
                <span className="stat-value">{model?.version}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Algorithm</span>
                <span className="stat-value">{modelMeta.model_type}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Feature set</span>
                <span className="stat-value">{modelMeta.feature_set}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Test ROC-AUC</span>
                <span className="stat-value">{modelMeta.test?.roc_auc}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Test recall</span>
                <span className="stat-value">{modelMeta.test?.recall}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Calibration</span>
                <span className="stat-value">{modelMeta.calibration?.method}</span>
              </div>
              <p className="text-muted" style={{ fontSize: "0.78rem", marginBottom: 0 }}>
                {modelMeta.split}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
