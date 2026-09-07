import { useCallback } from "react";
import { Link, useParams } from "react-router-dom";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchFloodEvents } from "../services/api";

export default function HistoricalEventDetail() {
  const { id } = useParams();
  const [state, retry] = useFetch(useCallback(fetchFloodEvents, []));

  if (state.status === "loading") return <LoadingState label="Loading event" />;
  if (state.status === "error") return <ErrorState detail={state.message} onRetry={retry} />;

  const event = state.data.find((e) => String(e.id) === id);
  if (!event) {
    return (
      <EmptyState
        title="Event not found"
        detail="This event id doesn't exist in the current flood-event log."
        action={
          <Link className="btn" to="/historical-events">
            Back to events
          </Link>
        }
      />
    );
  }

  return (
    <div>
      <Link to="/historical-events" className="text-muted">
        ← Back to events
      </Link>
      <div className="page-header" style={{ marginTop: "0.5rem" }}>
        <h1>{event.event_id}</h1>
        <p>
          {event.start_date}
          {event.end_date ? ` – ${event.end_date}` : ""} · {event.provinces}
        </p>
      </div>
      <div className="grid grid-auto">
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Reported impact</h3>
          <p className="text-secondary">{event.impact_note}</p>
          {event.deaths != null && <p className="text-secondary">Deaths reported: {event.deaths}</p>}
          <h3>Districts</h3>
          <p className="text-secondary">{event.districts || "Not specified in source"}</p>
          <h3>Rivers</h3>
          <p className="text-secondary">{event.rivers || "Not specified in source"}</p>
        </div>
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Provenance</h3>
          <p className="text-secondary">
            <a href={event.source_url} target="_blank" rel="noreferrer">
              {event.source_name}
            </a>
          </p>
          <h3>Confidence notes</h3>
          <p className="text-secondary">{event.confidence_notes}</p>
        </div>
      </div>
    </div>
  );
}
