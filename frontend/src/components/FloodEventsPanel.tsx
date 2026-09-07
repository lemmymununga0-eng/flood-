import { useCallback } from "react";
import { fetchFloodEvents } from "../services/api";
import { useFetch } from "../hooks/useFetch";

export default function FloodEventsPanel() {
  const [state, retry] = useFetch(useCallback(fetchFloodEvents, []));

  return (
    <section className="panel">
      <h2>Historical flood-event log</h2>
      <p className="hint">
        Reported events, not a validated ground-truth label — see the project's
        ML-METHODOLOGY.md. Each row cites its source.
      </p>
      {state.status === "loading" && <p className="hint">Loading flood events…</p>}
      {state.status === "error" && (
        <div className="error-box">
          <p>Unable to retrieve flood events.</p>
          <p className="hint">{state.message}</p>
          <button onClick={retry}>Retry</button>
        </div>
      )}
      {state.status === "success" && state.data.length === 0 && (
        <p className="hint">No flood events recorded yet.</p>
      )}
      {state.status === "success" && state.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Start</th>
                <th>Provinces</th>
                <th>Impact (as reported)</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((ev) => (
                <tr key={ev.id}>
                  <td>{ev.event_id}</td>
                  <td>{ev.start_date}</td>
                  <td>{ev.provinces}</td>
                  <td>{ev.impact_note}</td>
                  <td>
                    <a href={ev.source_url} target="_blank" rel="noreferrer">
                      {ev.source_name}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
