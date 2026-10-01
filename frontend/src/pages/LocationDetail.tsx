import { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Icon } from "../components/ui/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { useFetch } from "../hooks/useFetch";
import RiskBadge from "../components/ui/RiskBadge";
import {
  fetchLocationObservations,
  fetchLocations,
  fetchPredictions,
  ingestWeather,
} from "../services/api";
import type { WeatherIngestResult, WeatherObservation } from "../types";

export default function LocationDetail() {
  const { id } = useParams();
  const [state, retry] = useFetch(useCallback(fetchLocations, []));
  const [predState] = useFetch(useCallback(fetchPredictions, []));
  // Stored observations for this location. Loaded by id from the route rather than
  // from the resolved location object, so the fetch does not wait on the list call.
  const [obsState, reloadObs] = useFetch(
    useCallback(() => fetchLocationObservations(Number(id)), [id]),
  );
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

  const prediction =
    predState.status === "success"
      ? predState.data.find((p) => p.location_id === location.id)
      : undefined;
  const riskLevel = ((): "low" | "moderate" | "high" | "critical" => {
    const r = (prediction?.risk_level ?? "").toLowerCase();
    return (["low", "moderate", "high", "critical"] as const).includes(r as any)
      ? (r as any)
      : "moderate";
  })();
  let predDetail: any = null;
  try { predDetail = prediction ? JSON.parse(prediction.explanation || "{}") : null; } catch { predDetail = null; }

  const runIngest = () => {
    setIngest({ status: "loading" });
    ingestWeather(location.id)
      .then((result) => {
        setIngest({ status: "done", result });
        // Newly ingested rows are useless if the panel below still shows the old set.
        reloadObs();
      })
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
          {prediction ? (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: "0.7rem", margin: "0.3rem 0 0.8rem" }}>
                <RiskBadge level={riskLevel} />
                <strong style={{ fontSize: "1.9rem" }}>
                  {(prediction.prediction_probability * 100).toFixed(3)}%
                </strong>
              </div>
              <div className="stat-row">
                <span className="stat-label">Horizon</span>
                <span className="stat-value">{prediction.prediction_horizon}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Generated</span>
                <span className="stat-value">
                  {new Date(prediction.predicted_at).toLocaleString()}
                </span>
              </div>
              {predDetail?.raw_score !== undefined && (
                <div className="stat-row">
                  <span className="stat-label">Raw model score</span>
                  <span className="stat-value">{predDetail.raw_score}</span>
                </div>
              )}
              {predDetail?.observation_date && (
                <div className="stat-row">
                  <span className="stat-label">Based on observation</span>
                  <span className="stat-value">{predDetail.observation_date}</span>
                </div>
              )}
              <Link className="btn btn-primary" to={`/predictions/${prediction.id}`}
                    style={{ marginTop: "0.8rem" }}>
                Full prediction detail
              </Link>
            </>
          ) : (
            <EmptyState
              title="No stored prediction"
              detail="This location has not been scored yet. Run one from the Predictions page."
            />
          )}
        </div>

        <div className="card">
          <div className="icon-chip">
            <Icon name="data" />
          </div>
          <h3 style={{ marginTop: 0 }}>Weather</h3>
          <p className="text-secondary">
            Runs a real NASA POWER request for the last 10 days and stores whatever it
            returns. NASA's "-999" no-data sentinel is rejected rather than stored, so a
            missing day stays missing.
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

        <div className="card" style={{ gridColumn: "1 / -1" }}>
          <div className="icon-chip">
            <Icon name="data" />
          </div>
          <h3 style={{ marginTop: 0 }}>Stored weather history</h3>
          <p className="text-secondary">
            Real NASA POWER observations held for this location, newest first. Blank
            cells are genuinely absent measurements — nothing is interpolated.
          </p>
          {obsState.status === "loading" && <LoadingState label="Loading observations" />}
          {obsState.status === "error" && (
            <ErrorState detail={obsState.message} onRetry={reloadObs} />
          )}
          {obsState.status === "success" && obsState.data.length === 0 && (
            <EmptyState
              title="No observations stored yet"
              detail="Use “Fetch weather data” above to run a real NASA POWER request for this location."
            />
          )}
          {obsState.status === "success" && obsState.data.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Rain (mm)</th>
                    <th>Temp (°C)</th>
                    <th>Max (°C)</th>
                    <th>Min (°C)</th>
                    <th>Humidity (%)</th>
                    <th>Wind 10m (m/s)</th>
                  </tr>
                </thead>
                <tbody>
                  {[...obsState.data]
                    .sort((a, b) => b.observed_date.localeCompare(a.observed_date))
                    .map((o: WeatherObservation) => (
                      <tr key={o.id}>
                        <td>{o.observed_date.slice(0, 10)}</td>
                        <td>{o.precipitation_mm ?? "—"}</td>
                        <td>{o.temperature_c ?? "—"}</td>
                        <td>{o.temperature_max_c ?? "—"}</td>
                        <td>{o.temperature_min_c ?? "—"}</td>
                        <td>{o.relative_humidity_pct ?? "—"}</td>
                        <td>{o.wind_speed_10m_ms ?? "—"}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
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
