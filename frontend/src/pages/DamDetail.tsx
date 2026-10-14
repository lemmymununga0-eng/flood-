import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { LineChart } from "../components/ui/Charts";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchDam, fetchDamAssessment, type MeasurementKey } from "../services/dams";
import { KIND_LABEL, whenLabel } from "./Dams";

const CHARTS: { key: MeasurementKey; title: string; unit: string; group: string }[] = [
  { key: "reservoir_level_m", title: "Reservoir level", unit: "m", group: "Reservoir" },
  { key: "storage_pct", title: "Storage", unit: "%", group: "Reservoir" },
  { key: "storage_m3", title: "Storage volume", unit: "m³", group: "Reservoir" },
  { key: "inflow_m3s", title: "Inflow", unit: "m³/s", group: "Flows" },
  { key: "outflow_m3s", title: "Outflow / release", unit: "m³/s", group: "Flows" },
  { key: "spillway_m3s", title: "Spillway discharge", unit: "m³/s", group: "Flows" },
  { key: "turbine_m3s", title: "Turbine discharge", unit: "m³/s", group: "Flows" },
  { key: "downstream_level_m", title: "Downstream river level", unit: "m", group: "Downstream" },
  { key: "downstream_discharge_m3s", title: "Downstream river discharge", unit: "m³/s", group: "Downstream" },
  { key: "rainfall_observed_mm", title: "Observed rainfall", unit: "mm", group: "Rainfall" },
  { key: "rainfall_forecast_mm", title: "Rainfall FORECAST (not an observation)", unit: "mm", group: "Rainfall" },
];

const STATUS_TEXT: Record<string, string> = {
  insufficient_data: "Insufficient data",
  monitoring: "Monitoring",
  elevated_concern: "Elevated concern based on documented conditions",
  official_release_notice: "Official release notice available",
};

export default function DamDetail() {
  const { slug = "" } = useParams();
  const [state, retry] = useFetch(useCallback(() => fetchDam(slug), [slug]));
  const [assess] = useFetch(useCallback(() => fetchDamAssessment(slug), [slug]));

  if (state.status === "loading") return <LoadingState label="Loading dam" />;
  if (state.status === "error") return <ErrorState detail={state.message} onRetry={retry} />;
  const { dam, observations, release_notices } = state.data;
  const kinds = [...new Set(observations.map((o) => o.data_kind))];

  return (
    <div>
      <Link to="/dams">← All dams</Link>
      <div className="page-header">
        <h1>{dam.name}</h1>
        <p>{dam.river_system ?? "River system unverified"} river system · data status: {dam.data_status.replace("_", " ")}</p>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Registry</h3>
        <table><tbody>
          <tr><td className="text-muted">District / province</td><td>{dam.district ?? "unverified"} / {dam.province ?? "unverified"}</td></tr>
          <tr><td className="text-muted">Coordinates</td><td>{dam.latitude !== null ? `${dam.latitude}, ${dam.longitude} (${dam.coordinate_source})` : "unverified — verification required"}</td></tr>
          <tr><td className="text-muted">Documented capacity</td><td>{dam.capacity_m3 !== null ? `${dam.capacity_m3} m³ (${dam.capacity_source})` : "unverified — storage % cannot be derived"}</td></tr>
          <tr><td className="text-muted">Data provider</td><td>{dam.data_provider ?? "none established"}</td></tr>
          <tr><td className="text-muted">Last successful update</td><td>{whenLabel(dam.last_successful_update)}</td></tr>
          <tr><td className="text-muted">Latest observation</td><td>{whenLabel(dam.latest?.observed_at ?? null)}{dam.freshness === "stale" && " — STALE"}</td></tr>
          <tr><td className="text-muted">Data labels present</td><td>{kinds.length ? kinds.map((k) => KIND_LABEL[k]).join(", ") : "no observations"}</td></tr>
        </tbody></table>
        <p className="text-muted" style={{ fontSize: "0.8rem", marginBottom: 0 }}>{dam.notes}</p>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Experimental dam-related assessment</h3>
        {assess.status === "success" ? (
          <>
            <p><strong>{STATUS_TEXT[assess.data.status]}</strong></p>
            <p>{assess.data.message}</p>
            {assess.data.signals.length > 0 && (
              <ul className="text-muted" style={{ fontSize: "0.85rem" }}>
                {assess.data.signals.map((s) => (
                  <li key={s.signal}>{s.signal}: {s.evaluable ? (s.triggered ? "present" : "not present") : "not evaluable"} — {s.detail}</li>
                ))}
              </ul>
            )}
            {assess.data.notices?.map((n) => (
              <p key={n.source_reference}>Official notice ({whenLabel(n.published_at)}): {n.description} <span className="text-muted">[{n.source_reference}]</span></p>
            ))}
            <p className="text-muted" style={{ fontSize: "0.78rem", marginBottom: 0 }}>{assess.data.disclaimer}</p>
          </>
        ) : assess.status === "error" ? <ErrorState detail={assess.message} /> : <LoadingState label="Loading assessment" />}
      </div>

      {observations.length === 0 ? (
        <EmptyState title="No observations recorded"
          detail="No verified data has been imported for this dam. Charts are only drawn for measurements that exist." />
      ) : (
        <div className="grid grid-auto" style={{ marginBottom: "1rem" }}>
          {CHARTS.map((c) => {
            const pts = observations
              .filter((o) => o[c.key] !== null)
              .map((o) => ({ label: o.observed_at.slice(0, 10), value: o[c.key] as number }));
            if (pts.length === 0) return null;
            return (
              <div className="card" key={c.key}>
                <h3>{c.title}</h3>
                <LineChart points={pts} unit={c.unit}
                  tone={c.key === "rainfall_forecast_mm" ? "var(--risk-moderate)" : undefined} />
                <p className="text-muted" style={{ fontSize: "0.75rem", marginBottom: 0 }}>
                  {pts.length} observation{pts.length === 1 ? "" : "s"} · {c.group}
                  {c.key === "rainfall_forecast_mm" && " · forecast values, not measurements"}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h3>Official release announcements</h3>
        {release_notices.length === 0 ? <p className="text-muted">None recorded.</p> : (
          <ul>{release_notices.map((n) => (
            <li key={n.source_reference + n.published_at}>
              {whenLabel(n.published_at)} — {n.issuing_body}: {n.description} <span className="text-muted">[{n.source_reference}]</span>
            </li>))}
          </ul>
        )}
      </div>

      {observations.length > 0 && (
        <div className="table-wrap">
          <h3>Observation provenance (latest 20)</h3>
          <table>
            <thead><tr><th>Observed</th><th>Label</th><th>Provider</th><th>Source</th><th>Quality</th><th>Stored</th></tr></thead>
            <tbody>
              {[...observations].reverse().slice(0, 20).map((o) => (
                <tr key={o.observed_at + o.provider}>
                  <td>{whenLabel(o.observed_at)}</td><td>{KIND_LABEL[o.data_kind]}</td><td>{o.provider}</td>
                  <td>{o.source_reference}</td><td>{o.quality_flag}</td><td>{whenLabel(o.retrieved_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
