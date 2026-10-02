import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";

export default function Landing() {
  // The page wrapper and header now come from PublicLayout, so every public page
  // shares one header and none can be reached without a way back.
  return (
    <>
      <section className="hero-split">
        <div className="hero">
          <div className="demo-banner">Demonstration Environment — early development build, not a deployed public service.</div>
          <h1>
            Predict Risk. Act Earlier. <span className="accent">Protect Communities.</span>
          </h1>
          <p>
            Flood Prediction System ZM transforms weather and environmental data into
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
        </div>
        <div className="hero-visual" aria-hidden="true">
          <svg viewBox="0 0 400 320" preserveAspectRatio="xMidYMid slice">
            <defs>
              <linearGradient id="contour1" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="var(--brand-blue)" />
                <stop offset="100%" stopColor="var(--brand-green)" />
              </linearGradient>
            </defs>
            <g fill="none" strokeWidth="1.5" opacity="0.55">
              <path d="M-20 60 Q100 20 200 60 T420 60" stroke="var(--brand-blue)" />
              <path d="M-20 100 Q100 60 200 100 T420 100" stroke="var(--brand-blue)" />
              <path d="M-20 140 Q100 100 200 140 T420 140" stroke="url(#contour1)" />
              <path d="M-20 180 Q100 140 200 180 T420 180" stroke="var(--brand-green)" />
              <path d="M-20 220 Q100 180 200 220 T420 220" stroke="var(--brand-green)" />
              <path d="M-20 260 Q100 220 200 260 T420 260" stroke="var(--brand-gold-2)" />
            </g>
            <g fill="var(--brand-gold-2)" opacity="0.9">
              <circle cx="150" cy="150" r="4" />
              <circle cx="230" cy="190" r="4" />
              <circle cx="190" cy="230" r="4" />
            </g>
          </svg>
        </div>
      </section>

      <section className="page-content" style={{ maxWidth: 960 }}>
        <div className="grid grid-auto">
          <div className="card">
            <div className="icon-chip">
              <Icon name="data" />
            </div>
            <h3>Real-time Monitoring</h3>
            <p className="text-secondary">
              Meteorological observations from documented sources, ingested and
              validated before they reach any model.
            </p>
          </div>
          <div className="card">
            <div className="icon-chip">
              <Icon name="ai-model" />
            </div>
            <h3>AI-Powered Predictions</h3>
            <p className="text-secondary">
              Baseline and time-series models compared honestly on held-out data — no
              model is assumed best in advance. None trained yet in this build.
            </p>
          </div>
          <div className="card">
            <div className="icon-chip">
              <Icon name="warning" />
            </div>
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
    </>
  );
}
