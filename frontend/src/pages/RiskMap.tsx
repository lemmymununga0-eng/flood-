import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState, LoadingState } from "../components/ui/States";
import RiskBadge from "../components/ui/RiskBadge";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations, fetchPredictions } from "../services/api";
import type { Location, Prediction } from "../types";

const RISK_KEYS = ["low", "moderate", "high", "critical"] as const;
type RiskKey = (typeof RISK_KEYS)[number];
function normalizeRisk(r: string): RiskKey {
  const lower = r.toLowerCase();
  return (RISK_KEYS as readonly string[]).includes(lower) ? (lower as RiskKey) : "moderate";
}

// Matches the approved risk tokens. Leaflet needs literal colours, so these are kept
// in sync with tokens.css deliberately rather than read from CSS at runtime.
const RISK_COLOR: Record<RiskKey, string> = {
  low: "#2f9e6e",
  moderate: "#e0a32e",
  high: "#e2703a",
  critical: "#d24b4b",
};

export default function RiskMap() {
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const [predState] = useFetch(useCallback(fetchPredictions, []));
  const mapEl = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const [selected, setSelected] = useState<Location | null>(null);

  const ready = locState.status === "success" && predState.status === "success";

  // Latest prediction per location (predictions arrive newest-first).
  const latestByLocation = new Map<number, Prediction>();
  if (predState.status === "success") {
    for (const p of predState.data) {
      if (!latestByLocation.has(p.location_id)) latestByLocation.set(p.location_id, p);
    }
  }

  const counts = { low: 0, moderate: 0, high: 0, critical: 0 } as Record<RiskKey, number>;
  latestByLocation.forEach((p) => { counts[normalizeRisk(p.risk_level)] += 1; });

  useEffect(() => {
    if (!ready || !mapEl.current || mapRef.current) return;

    const map = L.map(mapEl.current, { scrollWheelZoom: false }).setView([-14.0, 28.5], 6);
    mapRef.current = map;

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(map);

    (locState.status === "success" ? locState.data : []).forEach((loc) => {
      const pred = latestByLocation.get(loc.id);
      const risk = pred ? normalizeRisk(pred.risk_level) : null;
      const color = risk ? RISK_COLOR[risk] : "#7d8da1"; // grey = genuinely unscored

      L.circleMarker([loc.latitude, loc.longitude], {
        radius: risk === "critical" || risk === "high" ? 11 : 8,
        color: "#ffffff",
        fillColor: color,
        fillOpacity: 0.9,
        weight: 2,
      })
        .addTo(map)
        .bindTooltip(
          pred
            ? `${loc.name} — ${risk} (${(pred.prediction_probability * 100).toFixed(3)}%)`
            : `${loc.name} — not scored`,
        )
        .on("click", () => setSelected(loc));
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [ready]);

  const selectedPred = selected ? latestByLocation.get(selected.id) : undefined;
  const scored = latestByLocation.size;
  const unscored =
    (locState.status === "success" ? locState.data.length : 0) - scored;

  return (
    <div>
      <div className="page-header">
        <h1>Risk Map</h1>
        <p>
          Every monitored location plotted at its verified coordinates and coloured by
          its most recent model risk level. Grey markers are locations with no stored
          prediction — shown honestly rather than coloured by assumption.
        </p>
      </div>

      {(locState.status === "loading" || predState.status === "loading") && (
        <LoadingState label="Loading map" />
      )}
      {locState.status === "error" && <ErrorState detail={locState.message} />}

      <div className="map-layout">
        <div className="map-side-panel">
          <div className="card">
            <h3 style={{ marginTop: 0 }}>Risk level</h3>
            {RISK_KEYS.slice().reverse().map((k) => (
              <div className="stat-row" key={k} style={{ padding: "0.3rem 0" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                  <span style={{
                    width: 11, height: 11, borderRadius: "50%",
                    background: RISK_COLOR[k], display: "inline-block",
                    border: "2px solid #fff", boxShadow: "0 0 0 1px var(--border)",
                  }} />
                  {k[0].toUpperCase() + k.slice(1)}
                </span>
                <span className="stat-value">{counts[k]}</span>
              </div>
            ))}
            <div className="stat-row" style={{ padding: "0.3rem 0" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                <span style={{
                  width: 11, height: 11, borderRadius: "50%", background: "#7d8da1",
                  display: "inline-block", border: "2px solid #fff",
                  boxShadow: "0 0 0 1px var(--border)",
                }} />
                Not scored
              </span>
              <span className="stat-value">{unscored > 0 ? unscored : 0}</span>
            </div>
            <p className="text-muted" style={{ marginBottom: 0, fontSize: "0.78rem" }}>
              {scored} of {locState.status === "success" ? locState.data.length : "—"}{" "}
              locations have a stored prediction.
            </p>
          </div>

          {selected ? (
            <div className="card">
              <h3 style={{ marginTop: 0 }}>{selected.name}</h3>
              <p className="text-secondary" style={{ margin: "0 0 0.3rem" }}>
                {selected.province}
              </p>
              <p className="text-muted" style={{ margin: "0 0 0.7rem", fontSize: "0.8rem" }}>
                {selected.latitude.toFixed(4)}, {selected.longitude.toFixed(4)}
              </p>

              {selectedPred ? (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
                    <RiskBadge level={normalizeRisk(selectedPred.risk_level)} />
                    <strong style={{ fontSize: "1.25rem" }}>
                      {(selectedPred.prediction_probability * 100).toFixed(3)}%
                    </strong>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">Horizon</span>
                    <span className="stat-value">{selectedPred.prediction_horizon}</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">Coordinate source</span>
                    <span className="stat-value" style={{ fontSize: "0.78rem" }}>
                      {selected.coordinate_confidence}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.7rem", flexWrap: "wrap" }}>
                    <Link className="btn btn-primary" to={`/predictions/${selectedPred.id}`}>
                      Prediction detail
                    </Link>
                    <Link className="btn btn-secondary" to={`/locations/${selected.id}`}>
                      Location
                    </Link>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-secondary" style={{ margin: "0 0 0.7rem" }}>
                    No stored prediction for this location yet.
                  </p>
                  <Link className="btn btn-secondary" to={`/locations/${selected.id}`}>
                    View location
                  </Link>
                </>
              )}
            </div>
          ) : (
            <div className="card">
              <h3 style={{ marginTop: 0 }}>Location info</h3>
              <p className="text-secondary" style={{ marginBottom: 0 }}>
                Select a marker on the map to see its current risk level, probability and
                coordinate provenance.
              </p>
            </div>
          )}
        </div>

        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <div ref={mapEl} style={{ height: 620, width: "100%" }} />
        </div>
      </div>
    </div>
  );
}
