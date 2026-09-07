export default function About() {
  return (
    <div>
      <div className="page-header">
        <h1>About FloodShield Zambia</h1>
      </div>
      <div className="card" style={{ maxWidth: 760 }}>
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
        <h3>Current limitations</h3>
        <ul className="text-secondary">
          <li>No model has been trained yet — all prediction/analytics screens are honestly empty.</li>
          <li>The historical flood-event log (11 events) is media-derived, not a primary government dataset.</li>
          <li>Live weather ingestion is blocked in this development environment.</li>
          <li>No authentication, alerts delivery (SMS/email), or citizen-report backend exists yet.</li>
        </ul>
        <p className="text-muted">See docs/LIMITATIONS.md in the project repository for the full list.</p>
      </div>
    </div>
  );
}
