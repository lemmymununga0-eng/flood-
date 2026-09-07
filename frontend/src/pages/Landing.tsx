import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="public-page">
      <header className="public-topbar">
        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 700 }}>
          <span
            aria-hidden="true"
            style={{
              width: 28,
              height: 28,
              borderRadius: 7,
              background: "linear-gradient(135deg, var(--brand-blue), var(--brand-green))",
            }}
          />
          FLOODSHIELD ZAMBIA
        </div>
        <nav style={{ display: "flex", gap: "0.75rem" }}>
          <Link className="btn btn-secondary" to="/about">
            How It Works
          </Link>
          <Link className="btn btn-secondary" to="/risk-map">
            Public Risk Map
          </Link>
          <Link className="btn btn-primary" to="/login">
            Sign In
          </Link>
        </nav>
      </header>

      <section className="hero">
        <div className="demo-banner">Demonstration Environment — early development build, not a deployed public service.</div>
        <h1>
          Predict Risk. Act Earlier. <span className="accent">Protect Communities.</span>
        </h1>
        <p>
          FloodShield Zambia transforms weather and environmental data into
          understandable flood-risk intelligence and early-warning information for
          disaster management, local authorities, researchers, and communities across
          Zambia.
        </p>
        <div className="hero-actions">
          <Link className="btn btn-primary" to="/dashboard">
            Explore Flood Risk
          </Link>
          <Link className="btn btn-secondary" to="/about">
            How It Works
          </Link>
        </div>
      </section>

      <section className="page-content" style={{ maxWidth: 960 }}>
        <div className="grid grid-auto">
          <div className="card">
            <h3>Real-time Monitoring</h3>
            <p className="text-secondary">
              Meteorological observations from documented sources, ingested and
              validated before they reach any model.
            </p>
          </div>
          <div className="card">
            <h3>AI-Powered Predictions</h3>
            <p className="text-secondary">
              Baseline and time-series models compared honestly on held-out data — no
              model is assumed best in advance. None trained yet in this build.
            </p>
          </div>
          <div className="card">
            <h3>Early Warnings</h3>
            <p className="text-secondary">
              Dashboard-first alerting, isolated from any external delivery provider so
              a provider outage never blocks prediction serving.
            </p>
          </div>
        </div>
      </section>

      <footer style={{ padding: "1.5rem", color: "var(--text-muted)", fontSize: "0.8rem" }}>
        Model-estimated flood risk is decision-support only, not an official warning.
      </footer>
    </div>
  );
}
