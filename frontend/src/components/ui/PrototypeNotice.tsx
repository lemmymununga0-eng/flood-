/** Persistent research-prototype disclaimer, shown wherever model risk levels are displayed. */
export default function PrototypeNotice() {
  return (
    <aside className="card" role="note" style={{ marginBottom: "1rem", borderLeft: "4px solid var(--risk-moderate)" }}>
      <strong>Research prototype — not a forecast or a warning.</strong>
      <p className="text-secondary" style={{ margin: "0.25rem 0 0", fontSize: "0.85rem" }}>
        In this project's own evaluation, no model performed better than a seasonal-climatology
        baseline, and precision at the alert threshold is very low (many false alarms per true
        alert). Risk levels are <em>relative</em> rankings from NASA POWER reanalysis weather, not
        the chance that a flood will occur. Do not use them for safety decisions; follow official
        DMMU and WARMA guidance.
      </p>
    </aside>
  );
}
