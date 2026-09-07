import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useCallback, useEffect, useRef } from "react";
import { ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations } from "../services/api";

export default function RiskMap() {
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const mapEl = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    if (locState.status !== "success" || !mapEl.current || mapRef.current) return;

    const map = L.map(mapEl.current, { scrollWheelZoom: false }).setView([-14.0, 28.5], 6);
    mapRef.current = map;

    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18,
    }).addTo(map);

    locState.data.forEach((loc) => {
      L.circleMarker([loc.latitude, loc.longitude], {
        radius: 9,
        color: "#1e5a7a",
        fillColor: "#2e8b68",
        fillOpacity: 0.85,
        weight: 2,
      })
        .addTo(map)
        .bindPopup(
          `<strong>${loc.name}</strong><br/>${loc.province}<br/><span style="color:#666">No risk prediction available (no model trained yet)</span><br/><a href="/locations/${loc.id}">View location →</a>`,
        );
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [locState]);

  return (
    <div>
      <div className="page-header">
        <h1>Risk Map</h1>
        <p>
          Monitored locations only — no colored risk overlay yet, since no flood-risk
          model has been trained (see Predictions and AI Model). This is not a bug: an
          overlay here would have to be invented.
        </p>
      </div>

      {locState.status === "loading" && <LoadingState label="Loading map" />}
      {locState.status === "error" && <ErrorState detail={locState.message} />}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div ref={mapEl} style={{ height: 480, width: "100%" }} />
      </div>

      <div className="card" style={{ marginTop: "1rem" }}>
        <h3 style={{ marginTop: 0 }}>Legend</h3>
        <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
          <span className="risk-badge low">Low</span>
          <span className="risk-badge moderate">Moderate</span>
          <span className="risk-badge high">High</span>
          <span className="risk-badge critical">Critical</span>
        </div>
        <p className="text-muted" style={{ marginBottom: 0 }}>
          Risk colors are defined but not currently applied to any location — no
          predictions exist to color by.
        </p>
      </div>
    </div>
  );
}
