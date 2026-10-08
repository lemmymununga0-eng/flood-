import { Link } from "react-router-dom";
import { Icon } from "../components/ui/icons";

export default function Landing() {
  // The page wrapper and header come from PublicLayout, so every public page shares one
  // header and none can be reached without a way back.
  return (
    <>
      <section className="hero-split">
        <div className="hero">
          <div className="demo-banner">
            Research prototype — not an official warning service and not for public alerts.
          </div>
          <h1>
            Predict Risk. Act Earlier. <span className="accent">Protect Communities.</span>
          </h1>
          <p>
            Flood Prediction System ZM turns decades of Zambian rainfall, soil-wetness and
            terrain data into understandable flood-risk information — and is candid about
            how much that information can currently be trusted.
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
          <svg viewBox="0 0 400 400" preserveAspectRatio="xMidYMid slice">
            <defs>
              <linearGradient id="wave-a" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="var(--brand-blue)" stopOpacity="0" />
                <stop offset="50%" stopColor="var(--brand-blue)" />
                <stop offset="100%" stopColor="var(--brand-green-2)" stopOpacity="0.9" />
              </linearGradient>
              <linearGradient id="wave-b" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="var(--brand-green-2)" stopOpacity="0" />
                <stop offset="55%" stopColor="var(--brand-green-2)" />
                <stop offset="100%" stopColor="var(--brand-gold)" stopOpacity="0.9" />
              </linearGradient>
              <radialGradient id="pulse">
                <stop offset="0%" stopColor="var(--brand-gold)" stopOpacity="0.55" />
                <stop offset="100%" stopColor="var(--brand-gold)" stopOpacity="0" />
              </radialGradient>
            </defs>
            <g fill="none" strokeLinecap="round">
              <path d="M-20 70 Q100 20 200 70 T420 70" stroke="url(#wave-a)" strokeWidth="1.4" opacity="0.5" />
              <path d="M-20 105 Q100 55 200 105 T420 105" stroke="url(#wave-a)" strokeWidth="1.4" opacity="0.65" />
              <path d="M-20 140 Q100 90 200 140 T420 140" stroke="url(#wave-a)" strokeWidth="1.6" opacity="0.8" />
              <path d="M-20 175 Q100 125 200 175 T420 175" stroke="url(#wave-b)" strokeWidth="1.8" />
              <path d="M-20 210 Q100 160 200 210 T420 210" stroke="url(#wave-b)" strokeWidth="1.6" opacity="0.85" />
              <path d="M-20 245 Q100 195 200 245 T420 245" stroke="url(#wave-b)" strokeWidth="1.4" opacity="0.6" />
            </g>
            <g>
              <circle cx="150" cy="148" r="22" fill="url(#pulse)" />
              <circle cx="258" cy="196" r="22" fill="url(#pulse)" />
              <circle cx="196" cy="228" r="22" fill="url(#pulse)" />
              <circle cx="150" cy="148" r="4" fill="var(--brand-gold)" />
              <circle cx="258" cy="196" r="4" fill="var(--brand-gold)" />
              <circle cx="196" cy="228" r="4" fill="var(--brand-gold)" />
            </g>
          </svg>

          {/* Documented facts about the data — not marketing figures. */}
          <div className="hero-facts">
            <div className="hero-fact">
              <strong>101</strong>
              districts modelled
            </div>
            <div className="hero-fact">
              <strong>1999–2026</strong>
              daily rainfall record
            </div>
            <div className="hero-fact">
              <strong>5</strong>
              forecast horizons studied
            </div>
          </div>
        </div>
      </section>

      <section className="feature-section">
        <div className="grid grid-auto">
          <div className="card">
            <div className="icon-chip">
              <Icon name="data" />
            </div>
            <h3>Documented data</h3>
            <p className="text-secondary">
              Satellite rainfall, soil wetness and terrain from cited sources, validated
              before they reach any model. Unreliable flood dates are set aside, never
              guessed.
            </p>
          </div>
          <div className="card">
            <div className="icon-chip">
              <Icon name="ai-model" />
            </div>
            <h3>Honest model evaluation</h3>
            <p className="text-secondary">
              Models are tested against seasonal and rainfall baselines on years they have
              never seen — and the result is reported whichever way it falls.
            </p>
          </div>
          <div className="card">
            <div className="icon-chip">
              <Icon name="warning" />
            </div>
            <h3>Decision support, not alarms</h3>
            <p className="text-secondary">
              Risk estimates come with their limits attached. This is research software to
              inform judgement, not an automated warning service.
            </p>
          </div>
        </div>
      </section>

      <footer className="public-footer">
        Model-estimated flood risk is decision-support only, not an official warning.
      </footer>
    </>
  );
}
