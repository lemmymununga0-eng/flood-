import { Icon } from "../components/ui/icons";

const PIPELINE_STEPS = [
  "Weather Data",
  "Validation",
  "Preprocessing",
  "Feature Engineering",
  "Model",
  "Prediction",
  "Explanation",
];

export default function About() {
  return (
    <div>
      <div className="page-header">
        <h1>About FloodShield Zambia</h1>
      </div>

      <div className="grid grid-auto" style={{ marginBottom: "1.25rem" }}>
        <div className="card">
          <div className="icon-chip">
            <Icon name="ml" />
          </div>
          <h3 style={{ margin: "0 0 0.3rem" }}>AI &amp; Machine Learning</h3>
          <p className="text-secondary" style={{ margin: 0 }}>
            Baseline and time-series models compared honestly on held-out data.
          </p>
        </div>
        <div className="card">
          <div className="icon-chip">
            <Icon name="data" />
          </div>
          <h3 style={{ margin: "0 0 0.3rem" }}>Real-time Data</h3>
          <p className="text-secondary" style={{ margin: 0 }}>
            Meteorological observations from documented, cited sources.
          </p>
        </div>
        <div className="card">
          <div className="icon-chip">
            <Icon name="geo" />
          </div>
          <h3 style={{ margin: "0 0 0.3rem" }}>Geospatial Analysis</h3>
          <p className="text-secondary" style={{ margin: 0 }}>
            Location-based monitoring across Zambian provinces and districts.
          </p>
        </div>
        <div className="card">
          <div className="icon-chip">
            <Icon name="warning" />
          </div>
          <h3 style={{ margin: "0 0 0.3rem" }}>Early Warnings</h3>
          <p className="text-secondary" style={{ margin: 0 }}>
            Dashboard-first alerting, independent of any external delivery provider.
          </p>
        </div>
      </div>

      <div className="card" style={{ maxWidth: 900 }}>
        <p className="text-secondary">
          FloodShield Zambia is an AI-powered flood prediction and early-warning
          research system for the Zambian context. It uses historical and near-real-time
          meteorological data, machine learning, and explainable AI to estimate flood
          risk and provide actionable early warnings for citizens, communities, farmers,
          disaster-management personnel, local authorities, and emergency-response
          organizations.
        </p>
        <p className="text-secondary">
          <strong>
            FloodShield predictions are risk estimates generated from available data and
            should support, not replace, professional emergency-management decisions.
          </strong>
        </p>

        <h3>Methodology pipeline</h3>
        <div className="pipeline-steps">
          {PIPELINE_STEPS.map((step, i) => (
            <span key={step} style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="pipeline-step">{step}</span>
              {i < PIPELINE_STEPS.length - 1 && <span className="pipeline-arrow">→</span>}
            </span>
          ))}
        </div>
        <p className="text-muted" style={{ marginTop: 0 }}>
          See <code>docs/ML-METHODOLOGY.md</code> for the full methodology, including open
          data-labeling questions this pipeline has not yet resolved.
        </p>

        <h3>Current limitations</h3>
        <ul className="text-secondary">
          <li>No model has been trained on valid, non-leaky real-event data yet — all prediction/analytics screens are honestly empty.</li>
          <li>The historical flood-event log (14 events) is media-derived, not a primary government dataset.</li>
          <li>Live weather ingestion (NASA POWER) works from this machine (verified 2026-09-18) but the trained models in <code>ai-engine/</code> are not yet wired into the running backend, so <code>/predictions</code> still returns real, honestly empty results.</li>
          <li>Alert delivery to external channels (SMS/email) is not configured — alerts are dashboard-only.</li>
        </ul>
        <p className="text-muted">See docs/LIMITATIONS.md in the project repository for the full list.</p>
      </div>
    </div>
  );
}
