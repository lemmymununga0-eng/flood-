import { useCallback } from "react";
import { fetchLocations } from "../services/api";
import { useFetch } from "../hooks/useFetch";

export default function LocationsPanel() {
  const [state, retry] = useFetch(useCallback(fetchLocations, []));

  return (
    <section className="panel">
      <h2>Monitored locations</h2>
      {state.status === "loading" && <p className="hint">Loading locations…</p>}
      {state.status === "error" && (
        <div className="error-box">
          <p>Unable to retrieve locations.</p>
          <p className="hint">{state.message}</p>
          <button onClick={retry}>Retry</button>
        </div>
      )}
      {state.status === "success" && state.data.length === 0 && (
        <p className="hint">No locations configured yet.</p>
      )}
      {state.status === "success" && state.data.length > 0 && (
        <ul className="location-list">
          {state.data.map((loc) => (
            <li key={loc.id}>
              <strong>{loc.name}</strong> — {loc.province}
              <div className="hint">
                {loc.latitude.toFixed(4)}, {loc.longitude.toFixed(4)} (
                {loc.coordinate_confidence})
              </div>
              <div className="hint">{loc.evidence_note}</div>
              <a href={loc.evidence_source_url} target="_blank" rel="noreferrer">
                source
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
