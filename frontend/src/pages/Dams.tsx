import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useCallback, useEffect, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchDams, type Dam } from "../services/dams";

export const KIND_LABEL: Record<string, string> = {
  live: "Live",
  historical: "Historical",
  manual_import: "Manually imported",
  synthetic_test: "SYNTHETIC TEST DATA",
};

export function fmt(v: number | null | undefined, unit: string, digits = 2): string {
  return v === null || v === undefined ? "not reported" : `${v.toFixed(digits)} ${unit}`;
}

export function whenLabel(iso: string | null): string {
  return iso
    ? new Date(iso).toLocaleString("en-GB", { timeZone: "Africa/Lusaka", dateStyle: "medium", timeStyle: "short" }) + " (Lusaka)"
    : "none";
}

function DamMap({ dams }: { dams: Dam[] }) {
  const el = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const located = dams.filter((d) => d.latitude !== null && d.longitude !== null);
  useEffect(() => {
    if (!el.current || located.length === 0) return;
    const map = L.map(el.current, { scrollWheelZoom: false }).setView([-15.5, 28], 6);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(map);
    located.forEach((d) =>
      L.circleMarker([d.latitude!, d.longitude!], { radius: 8, color: "#fff", fillColor: "#2b6cb0", fillOpacity: 0.9, weight: 2 })
        .addTo(map)
        .bindTooltip(d.name)
        .on("click", () => navigate(`/dams/${d.slug}`)),
    );
    return () => { map.remove(); };
  }, [located.length]);
  if (located.length === 0) {
    return (
      <p className="text-muted">
        Map unavailable: no dam has a verified coordinate yet. Markers are only drawn from verified
        coordinates, never estimated.
      </p>
    );
  }
  return <div ref={el} style={{ height: 320, borderRadius: 8, marginBottom: "1rem" }} />;
}

export default function Dams() {
  const [state, retry] = useFetch(useCallback(fetchDams, []));
  return (
    <div>
      <div className="page-header">
        <h1>Dam and Reservoir Monitoring</h1>
        <p>
          Research module, separate from the flood-prediction model. Values appear only where an
          authoritative record has been imported; missing measurements are shown as “not reported”,
          never as zero. No live official feed is currently connected.
        </p>
      </div>
      {state.status === "loading" && <LoadingState label="Loading dams" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && <EmptyState title="No dams registered" />}
      {state.status === "success" && state.data.length > 0 && (
        <>
          <DamMap dams={state.data} />
          <div className="grid grid-auto">
            {state.data.map((d) => (
              <Link key={d.slug} to={`/dams/${d.slug}`} className="card card-link">
                <h3>{d.name}</h3>
                <p className="text-muted" style={{ margin: 0 }}>{d.river_system ?? "River system unverified"} river system</p>
                <table><tbody>
                  <tr><td className="text-muted">Data status</td><td>{d.data_status.replace("_", " ")}</td></tr>
                  <tr><td className="text-muted">Latest observation</td><td>{whenLabel(d.latest?.observed_at ?? null)}
                    {d.freshness === "stale" && " — STALE"}</td></tr>
                  <tr><td className="text-muted">Reservoir level</td><td>{fmt(d.latest?.reservoir_level_m, "m")}</td></tr>
                  <tr><td className="text-muted">Storage</td><td>{d.latest?.storage_pct != null ? fmt(d.latest.storage_pct, "%", 1) : "not reported"}</td></tr>
                  <tr><td className="text-muted">Inflow</td><td>{fmt(d.latest?.inflow_m3s, "m³/s", 1)}</td></tr>
                  <tr><td className="text-muted">Outflow</td><td>{fmt(d.latest?.outflow_m3s, "m³/s", 1)}</td></tr>
                </tbody></table>
                {d.latest && <p className="text-muted" style={{ fontSize: "0.75rem" }}>{KIND_LABEL[d.latest.data_kind]} · {d.latest.provider}</p>}
                {d.verification_required && (
                  <p className="text-muted" style={{ fontSize: "0.75rem", marginBottom: 0 }}>
                    Location, capacity and provider require verification.
                  </p>
                )}
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
