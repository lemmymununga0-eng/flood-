import { useCallback, useState } from "react";
import { fetchLocations, ingestWeather } from "../services/api";
import { useFetch } from "../hooks/useFetch";
import type { WeatherIngestResult } from "../types";

export default function WeatherPanel() {
  const [locState] = useFetch(useCallback(fetchLocations, []));
  const [ingestState, setIngestState] = useState<
    | { status: "idle" }
    | { status: "loading" }
    | { status: "done"; result: WeatherIngestResult }
    | { status: "error"; message: string }
  >({ status: "idle" });

  const runIngest = (locationId: number) => {
    setIngestState({ status: "loading" });
    ingestWeather(locationId)
      .then((result) => setIngestState({ status: "done", result }))
      .catch((err: unknown) =>
        setIngestState({
          status: "error",
          message: err instanceof Error ? err.message : "Unknown error",
        }),
      );
  };

  return (
    <section className="panel">
      <h2>Weather data ingestion</h2>
      <p className="hint">
        Attempts a real request to NASA POWER for a monitored location. This
        environment's network policy blocks that request — the result below is the
        actual honest outcome, not a simulated one.
      </p>
      {locState.status === "success" && locState.data.length > 0 && (
        <div className="button-row">
          {locState.data.map((loc) => (
            <button key={loc.id} onClick={() => runIngest(loc.id)}>
              Fetch weather for {loc.name}
            </button>
          ))}
        </div>
      )}
      {ingestState.status === "loading" && <p className="hint">Requesting NASA POWER…</p>}
      {ingestState.status === "error" && (
        <div className="error-box">
          <p>Ingestion request failed at the network layer.</p>
          <p className="hint">{ingestState.message}</p>
        </div>
      )}
      {ingestState.status === "done" && (
        <div className={ingestState.result.status === "success" ? "success-box" : "error-box"}>
          <p>
            Status: <strong>{ingestState.result.status}</strong> —{" "}
            {ingestState.result.observations_stored} observation(s) stored
          </p>
          {ingestState.result.error_detail && (
            <p className="hint">{ingestState.result.error_detail}</p>
          )}
          <p className="hint">Requested: {ingestState.result.source_url_attempted}</p>
        </div>
      )}
    </section>
  );
}
