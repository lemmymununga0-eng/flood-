import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import { fetchLocations, ingestWeather } from "../services/api";
import type { WeatherIngestResult } from "../types";

export default function LocationDetail() {
  const { id } = useParams();
  const [state, retry] = useFetch(useCallback(fetchLocations, []));
  const [ingest, setIngest] = useState<
    | { status: "idle" }
    | { status: "loading" }
    | { status: "done"; result: WeatherIngestResult }
    | { status: "error"; message: string }
  >({ status: "idle" });

  if (state.status === "loading") return <LoadingState label="Loading location" />;
  if (state.status === "error") return <ErrorState detail={state.message} onRetry={retry} />;

  const location = state.data.find((l) => String(l.id) === id);
  if (!location) {
    return (
      <EmptyState
        title="Location not found"
        action={
          <Link className="btn" to="/risk-map">
            Back to map
          </Link>
        }
      />
    );
  }

  const runIngest = () => {
    setIngest({ status: "loading" });
    ingestWeather(location.id)
      .then((result) => setIngest({ status: "done", result }))
      .catch((err: unknown) =>
        setIngest({ status: "error", message: err instanceof Error ? err.message : "Unknown error" }),
      );
  };

  return (
    <div>
      <div className="page-header">
        <h1>{location.name}</h1>
        <p>
          {location.province} · {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)} (
          {location.coordinate_confidence})
        </p>
      </div>

      <div className="grid grid-auto">
        <div className="card">
          <div className="icon-chip">
            <Icon name="predictions" />
          </div>
          <h3 style={{ marginTop: 0 }}>Current flood risk</h3>
          <EmptyState
            title="No prediction available"
            detail="No model has been trained yet — see AI Model."
          />
        </div>

        <div className="card">
          <div className="icon-chip">
            <Icon name="data" />
          </div>
          <h3 style={{ marginTop: 0 }}>Weather</h3>
          <p className="text-secondary">
            Attempts a real NASA POWER request. In this environment it is expected to
            fail (egress policy + robots.txt) — the result below is the actual outcome.
          </p>
          <button className="btn btn-primary" onClick={runIngest} disabled={ingest.status === "loading"}>
            {ingest.status === "loading" ? "Requesting…" : "Fetch weather data"}
          </button>
          {ingest.status === "error" && <ErrorState detail={ingest.message} />}
          {ingest.status === "done" && (
            <div className={ingest.result.status === "success" ? "empty-state" : "error-state"} style={{ marginTop: "0.75rem" }}>
              <p style={{ margin: 0 }}>
                Status: <strong>{ingest.result.status}</strong> — {ingest.result.observations_stored} observation(s)
              </p>
              {ingest.result.error_detail && (
                <p className="text-muted" style={{ wordBreak: "break-word" }}>{ingest.result.error_detail}</p>
              )}
            </div>
          )}
        </div>

        <div className="card">
          <div className="icon-chip">
            <Icon name="geo" />
          </div>
          <h3 style={{ marginTop: 0 }}>Evidence for this location</h3>
          <p className="text-secondary">{location.evidence_note}</p>
          <a href={location.evidence_source_url} target="_blank" rel="noreferrer">
            source
          </a>
        </div>
      </div>
    </div>
  );
}
