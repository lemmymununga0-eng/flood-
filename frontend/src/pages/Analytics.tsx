import { useCallback } from "react";
import { Link } from "react-router-dom";
import KpiCard from "../components/ui/KpiCard";
import RiskBadge from "../components/ui/RiskBadge";
import { ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchFloodEvents, fetchLocations, fetchModels, fetchPredictions } from "../services/api";

const RISK_KEYS = ["low", "moderate", "high", "critical"] as const;
type RiskKey = (typeof RISK_KEYS)[number];
function normalizeRisk(r: string): RiskKey {
  const lower = r.toLowerCase();
  return (RISK_KEYS as readonly string[]).includes(lower) ? (lower as RiskKey) : "moderate";
}

function Bar({ label, value, max, tone, display }: {
  label: string; value: number; max: number; tone?: string; display?: string;
}) {
  const pct = max > 0 ? Math.max(2, (value / max) * 100) : 0;
  return (
    <div className="bar-row">
      <span>{label}</span>
      <span className="bar-track">
        <span className={`bar-fill ${tone ?? ""}`} style={{ width: `${pct}%` }} />
      </span>
      <span className="bar-value">{display ?? value}</span>
    </div>
  );
}

export default function Analytics() {
  const [predState, retryPred] = useFetch(useCallback(fetchPredictions, []));
  const [eventsState] = useFetch(useCallback(fetchFloodEvents, []));
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const [modelState] = useFetch(useCallback(fetchModels, []));

  const loading = predState.status === "loading" || eventsState.status === "loading";
  const preds = predState.status === "success" ? predState.data : [];
  const events = eventsState.status === "success" ? eventsState.data : [];
  const locations = locState.status === "success" ? locState.data : [];

  const locName = new Map(locations.map((l) => [l.id, l.name]));

  // --- Real current risk ranking (the model's demonstrated strength is ranking) ---
  const ranked = [...preds]
    .sort((a, b) => b.prediction_probability - a.prediction_probability)
    .slice(0, 8);
  const maxProb = ranked.length ? ranked[0].prediction_probability : 0;

  // --- Real risk-level distribution ---
  const dist = preds.reduce(
    (acc, p) => { acc[normalizeRisk(p.risk_level)] += 1; return acc; },
    { low: 0, moderate: 0, high: 0, critical: 0 } as Record<RiskKey, number>,
  );

  // --- Real historical events by province ---
  const byProvince = new Map<string, number>();
  for (const e of events) {
    for (const p of (e.provinces ?? "").split(",").map((s) => s.trim()).filter(Boolean)) {
      byProvince.set(p, (byProvince.get(p) ?? 0) + 1);
    }
  }
  const provinceRows = [...byProvince.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  const maxProvince = provinceRows.length ? provinceRows[0][1] : 0;

  // --- Real coverage by coordinate confidence ---
  const byConfidence = new Map<string, number>();
  for (const l of locations) {
    const key = (l.coordinate_confidence || "unspecified").split(",")[0].trim();
    byConfidence.set(key, (byConfidence.get(key) ?? 0) + 1);
  }
  const confRows = [...byConfidence.entries()].sort((a, b) => b[1] - a[1]);
  const maxConf = confRows.length ? confRows[0][1] : 0;

  const model = modelState.status === "success" ? modelState.data[0] : undefined;
  let metrics: any = null;
  try { metrics = model ? JSON.parse(model.metrics_json) : null; } catch { metrics = null; }

  return (
    <div>
      <div className="page-header">
        <h1>Flood Risk Analytics</h1>
        <p>
          Current model risk ranking, historical event distribution, and measured model
          performance — all computed from real records, never illustrative figures.
        </p>
      </div>

      {loading && <LoadingState label="Loading analytics" />}
      {predState.status === "error" && (
        <ErrorState detail={predState.message} onRetry={retryPred} />
      )}

      {predState.status === "success" && (
        <>
          <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
            <KpiCard label="Locations Scored" value={preds.length} icon="predictions" accent="blue" />
            <KpiCard label="Elevated Risk" value={dist.high + dist.critical}
                     note="High or critical band" icon="warning" accent="critical" />
            <KpiCard label="Moderate Risk" value={dist.moderate} icon="warning" accent="gold" />
            <KpiCard label="Events on Record" value={events.length}
                     note="Media/DesInventar-derived" icon="historical-events" accent="green" />
          </div>

          <div className="grid grid-auto">
            <div className="card">
              <h3>Highest current risk</h3>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                Locations ranked by the model's calibrated probability of flooding within
                7 days. Ranking is what this model does well (test ROC-AUC 0.777); the
                absolute percentages are small because flooding is genuinely rare.
              </p>
              {ranked.length === 0 ? (
                <p className="text-secondary">No predictions stored yet.</p>
              ) : (
                ranked.map((p) => (
                  <Bar
                    key={p.id}
                    label={locName.get(p.location_id) ?? `Location ${p.location_id}`}
                    value={p.prediction_probability}
                    max={maxProb}
                    tone={normalizeRisk(p.risk_level)}
                    display={`${(p.prediction_probability * 100).toFixed(3)}%`}
                  />
                ))
              )}
            </div>

            <div className="card">
              <h3>Current risk distribution</h3>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                How the {preds.length} scored locations fall across the risk bands right now.
              </p>
              {RISK_KEYS.map((k) => (
                <Bar key={k} label={k[0].toUpperCase() + k.slice(1)} value={dist[k]}
                     max={Math.max(...Object.values(dist), 1)} tone={k} />
              ))}
              <div style={{ marginTop: "0.8rem" }}>
                <Link className="btn btn-secondary" to="/predictions">Score an observation</Link>
              </div>
            </div>

            <div className="card">
              <h3>Historical events by province</h3>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                Real recorded flood events ({events.length} on file). Counts reflect
                reporting, not validated incidence — under-reporting is likely.
              </p>
              {provinceRows.length === 0 ? (
                <p className="text-secondary">No event records loaded.</p>
              ) : (
                provinceRows.map(([prov, n]) => (
                  <Bar key={prov} label={prov} value={n} max={maxProvince} tone="gold" />
                ))
              )}
            </div>

            <div className="card">
              <h3>Location coordinate confidence</h3>
              <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                Provenance of the {locations.length} monitored coordinates. Verified
                entries were resolved against the OpenStreetMap Nominatim geocoder.
              </p>
              {confRows.map(([k, n]) => (
                <Bar key={k} label={k} value={n} max={maxConf}
                     tone={k.startsWith("VERIFIED") ? "low" : undefined} />
              ))}
            </div>

            {metrics?.test && (
              <div className="card">
                <h3>Measured model performance</h3>
                <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                  From a chronological held-out test split ({model?.version}). Reported
                  exactly as measured, including the weaknesses.
                </p>
                <div className="stat-row">
                  <span className="stat-label">ROC-AUC (ranking quality)</span>
                  <span className="stat-value">{metrics.test.roc_auc}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Recall (real events caught)</span>
                  <span className="stat-value">
                    {metrics.test.recall} ({metrics.test.true_positives}/
                    {metrics.test.true_positives + metrics.test.false_negatives})
                  </span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Precision</span>
                  <span className="stat-value">{metrics.test.precision}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">PR-AUC</span>
                  <span className="stat-value">{metrics.test.pr_auc}</span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Positive prevalence</span>
                  <span className="stat-value">
                    {(metrics.test.positive_prevalence * 100).toFixed(3)}%
                  </span>
                </div>
                <div className="stat-row">
                  <span className="stat-label">Calibration (Brier)</span>
                  <span className="stat-value">
                    {metrics.calibration?.brier_raw} → {metrics.calibration?.brier_calibrated}
                  </span>
                </div>
                <p className="text-muted" style={{ fontSize: "0.78rem", marginBottom: 0 }}>
                  Low precision is real and disclosed: flooding occurs on ~0.04% of
                  location-days, so most alerts at this threshold are false alarms. This
                  is a research-grade risk signal, not an operational warning service.
                </p>
              </div>
            )}

            {metrics?.model_comparison && (
              <div className="card" style={{ gridColumn: "1 / -1" }}>
                <h3>Model comparison</h3>
                <p className="text-muted" style={{ marginTop: 0, fontSize: "0.82rem" }}>
                  Every model trained on the identical chronological split and weather-only
                  feature set, evaluated on the same held-out future test period. Note that
                  the selected model has the <em>lowest</em> accuracy — accuracy is the wrong
                  headline metric when the positive class is ~0.04% of days.
                </p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th>
                        <th>F1</th><th>ROC-AUC</th><th>Events caught</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.model_comparison.map((m: any) => (
                        <tr key={m.model}>
                          <td>
                            <strong>{m.model}</strong>
                            {m.selected && (
                              <span className="status-badge" style={{ marginLeft: "0.4rem" }}>
                                <span className="status-dot operational" />selected
                              </span>
                            )}
                          </td>
                          <td>{m.accuracy.toFixed(3)}</td>
                          <td>{m.precision.toFixed(4)}</td>
                          <td>{m.recall.toFixed(3)}</td>
                          <td>{m.f1.toFixed(4)}</td>
                          <td><strong>{m.roc_auc.toFixed(3)}</strong></td>
                          <td>{m.tp}/{m.tp + m.fn}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {metrics.models_not_trained?.map((m: any) => (
                  <p className="text-muted" style={{ fontSize: "0.78rem", marginBottom: 0 }} key={m.model}>
                    <strong>{m.model}:</strong> {m.reason}
                  </p>
                ))}
              </div>
            )}

            <div className="card">
              <h3>Seasonality</h3>
              <p className="text-secondary" style={{ marginTop: 0 }}>
                Rainfall and risk trend charts over time are not shown here yet. The
                stored observations currently cover only the last few days per location,
                which is too short a window to plot a meaningful seasonal trend —
                drawing one would misrepresent the data.
              </p>
              <p className="text-muted" style={{ fontSize: "0.8rem", marginBottom: 0 }}>
                Populated by continued scheduled ingestion. <RiskBadge level="low" /> bands
                shown elsewhere on this page use the same model output.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
