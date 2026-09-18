import { useCallback } from "react";
import { Link } from "react-router-dom";
import KpiCard from "../components/ui/KpiCard";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchFloodEvents } from "../services/api";

export default function HistoricalEvents() {
  const [state, retry] = useFetch(useCallback(fetchFloodEvents, []));

  const summary =
    state.status === "success" && state.data.length > 0
      ? (() => {
          const provinces = new Set<string>();
          state.data.forEach((ev) => ev.provinces.split(",").forEach((p) => provinces.add(p.trim())));
          const dates = state.data.map((ev) => ev.start_date).sort();
          return { provinceCount: provinces.size, earliest: dates[0], latest: dates[dates.length - 1] };
        })()
      : null;

  return (
    <div>
      <div className="page-header">
        <h1>Historical Flood Events</h1>
        <p>
          Reported events compiled from public sources — not a validated ground-truth
          label. Every row cites where it came from.
        </p>
      </div>

      {summary && (
        <div className="kpi-grid" style={{ marginBottom: "1rem" }}>
          <KpiCard label="Total Events" value={state.status === "success" ? state.data.length : 0} icon="historical-events" accent="blue" />
          <KpiCard label="Provinces Affected" value={summary.provinceCount} icon="geo" accent="gold" />
          <KpiCard label="Date Range" value={`${summary.earliest} – ${summary.latest}`} icon="historical-events" accent="green" />
        </div>
      )}

      {state.status === "loading" && <LoadingState label="Loading historical events" />}
      {state.status === "error" && <ErrorState detail={state.message} onRetry={retry} />}
      {state.status === "success" && state.data.length === 0 && (
        <EmptyState title="No historical events recorded" />
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
                <th>Confidence</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((ev) => (
                <tr key={ev.id}>
                  <td>
                    <Link to={`/historical-events/${ev.id}`}>{ev.event_id}</Link>
                  </td>
                  <td>{ev.start_date}</td>
                  <td>{ev.provinces}</td>
                  <td>{ev.impact_note}</td>
                  <td className="text-muted">{ev.confidence_notes.slice(0, 40)}…</td>
                  <td>
                    <a href={ev.source_url} target="_blank" rel="noreferrer">
                      {ev.source_name.slice(0, 24)}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="record-cards">
            {state.data.map((ev) => (
              <Link
                to={`/historical-events/${ev.id}`}
                key={ev.id}
                className="record-card"
                style={{ display: "block", color: "inherit", textDecoration: "none" }}
              >
                <strong>{ev.event_id}</strong>
                <div className="text-secondary">{ev.start_date} — {ev.provinces}</div>
                <div className="text-secondary">{ev.impact_note}</div>
                <div className="text-muted">{ev.source_name}</div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
