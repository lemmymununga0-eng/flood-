import StatusBadge from "../components/ui/StatusBadge";

const SOURCES = [
  {
    name: "NASA POWER",
    type: "Meteorological (historical, daily)",
    parameters: "Precipitation, temperature, humidity, wind",
    coverage: "Zambia (point-based, per monitored location)",
    status: "unavailable" as const,
    detail:
      "Endpoint/parameters confirmed from NASA's own docs, but live requests from this development environment are blocked (egress policy + robots.txt) — see docs/DATA-SOURCES.md.",
  },
  {
    name: "CHIRPS",
    type: "Rainfall (satellite + station blend)",
    parameters: "Precipitation",
    coverage: "Not yet evaluated for Zambia",
    status: "unavailable" as const,
    detail: "Candidate only — not integrated. Access method not yet investigated.",
  },
  {
    name: "DMMU / WARMA situation reports",
    type: "Flood ground-truth (narrative)",
    parameters: "Event dates, locations, impact",
    coverage: "National (as reported)",
    status: "degraded" as const,
    detail:
      "Used to compile ai-engine/data/external/zambia_flood_events_log.csv (11 events). DMMU's own site was unreachable when checked — cross-referencing is incomplete.",
  },
];

export default function DataSources() {
  return (
    <div>
      <div className="page-header">
        <h1>Data Sources</h1>
        <p>Configured and candidate data sources for this project.</p>
      </div>
      <div className="grid grid-auto">
        {SOURCES.map((s) => (
          <div className="card" key={s.name}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <h3 style={{ margin: 0 }}>{s.name}</h3>
              <StatusBadge status={s.status} />
            </div>
            <p className="text-secondary">{s.type}</p>
            <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
              Parameters: {s.parameters}
            </p>
            <p className="text-muted" style={{ marginBottom: "0.3rem" }}>
              Coverage: {s.coverage}
            </p>
            <p className="text-muted" style={{ marginBottom: 0 }}>
              {s.detail}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
