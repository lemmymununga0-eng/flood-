import { useEffect, useState } from "react";
import { fetchLocations } from "../services/api";
import { canManageAlerts, useAuth } from "../context/AuthContext";
import { fetchOutlook, refreshOutlook, type Outlook } from "../services/dams";
import type { Location } from "../types";
import RiskBadge from "./ui/RiskBadge";
import { EmptyState, ErrorState, LoadingState } from "./ui/States";

type RiskKey = "low" | "moderate" | "high" | "critical";
const norm = (r: string): RiskKey => {
  const l = r.toLowerCase();
  return (["low", "moderate", "high", "critical"].includes(l) ? l : "moderate") as RiskKey;
};

const STATUS_TEXT: Record<Outlook["status"], string> = {
  no_prediction: "No stored prediction exists for this location, so no risk is shown for these dates.",
  window_outside_outlook: "The latest stored prediction covers dates outside this outlook, so it is not applied to any day below.",
  partial: "The latest stored prediction covers only part of this outlook. Days outside its window show no risk.",
  complete: "The latest stored prediction's window covers all seven days.",
};

function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-GB", { timeZone: "Africa/Lusaka", dateStyle: "medium", timeStyle: "short" }) + " (Lusaka)";
}

export default function ForecastOutlook() {
  const { user } = useAuth();
  const [locations, setLocations] = useState<Location[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [locationId, setLocationId] = useState<number | "">("");
  const [state, setState] = useState<
    { status: "idle" } | { status: "loading" } | { status: "error"; message: string } | { status: "ok"; data: Outlook }
  >({ status: "idle" });

  useEffect(() => {
    fetchLocations().then(setLocations).catch(() => setLocations([]));
  }, []);

  function load(id: number) {
    setState({ status: "loading" });
    fetchOutlook(id)
      .then((data) => setState({ status: "ok", data }))
      .catch((e: unknown) => setState({ status: "error", message: e instanceof Error ? e.message : "Failed" }));
  }

  function refresh(id: number) {
    setRefreshing(true);
    setRefreshError(null);
    refreshOutlook(id)
      .then((data) => setState({ status: "ok", data }))
      .catch((e: unknown) => setRefreshError(e instanceof Error ? e.message : "Refresh failed"))
      .finally(() => setRefreshing(false));
  }

  return (
    <section className="card" style={{ marginBottom: "1rem" }} aria-labelledby="outlook-h">
      <h3 id="outlook-h">Seven-day outlook</h3>
      <p className="text-muted" style={{ marginTop: 0 }}>
        Seven consecutive dates in Zambia time (Africa/Lusaka). The model produces one risk estimate for a
        whole 7-day window, not a separate prediction per day, and no weather-forecast provider is
        connected — so per-day values are shown as unavailable rather than invented.
      </p>

      <div className="field" style={{ maxWidth: 320 }}>
        <label htmlFor="outlook-location">Location</label>
        <select
          id="outlook-location"
          value={locationId}
          onChange={(e) => {
            const v = e.target.value === "" ? "" : Number(e.target.value);
            setLocationId(v);
            if (v !== "") load(v);
            else setState({ status: "idle" });
          }}
        >
          <option value="">Select a location…</option>
          {locations.map((l) => (
            <option key={l.id} value={l.id}>{l.name}</option>
          ))}
        </select>
      </div>

      {state.status === "idle" && <EmptyState title="Choose a location to see its dated outlook" />}
      {state.status === "loading" && <LoadingState label="Loading outlook" />}
      {state.status === "error" && (
        <ErrorState title="Could not load the outlook" detail={state.message}
          onRetry={locationId !== "" ? () => load(locationId) : undefined} />
      )}

      {state.status === "ok" && (
        <>
          <p className="text-secondary" style={{ fontSize: "0.85rem" }}>
            Generated {fmtDateTime(state.data.generated_at)} · {state.data.day_1_convention}
          </p>
          {canManageAlerts(user) && locationId !== "" && (
            <div style={{ margin: "0.5rem 0" }}>
              <button className="btn btn-secondary" disabled={refreshing} onClick={() => refresh(locationId)}>
                {refreshing ? "Fetching weather and scoring…" : "Refresh from latest weather"}
              </button>
              <span className="text-muted" style={{ fontSize: "0.78rem", marginLeft: "0.5rem" }}>
                Fetches real NASA POWER weather (about 3 days behind) and scores it with the existing model.
              </span>
              {refreshError && <ErrorState title="Refresh failed" detail={refreshError} />}
            </div>
          )}
          {state.data.stale && (
            <div className="error-state" role="status">
              <strong>Stale data.</strong> The stored prediction was computed from weather more than 3 days
              old (or its window has already passed).
            </div>
          )}
          <p className="text-muted" style={{ fontSize: "0.85rem" }}>{STATUS_TEXT[state.data.status]}</p>

          <div className="grid grid-auto" style={{ marginBottom: "1rem" }}>
            {state.data.days.map((d) => (
              <div className="card" key={d.date} aria-label={d.label}>
                <div className="text-muted" style={{ fontSize: "0.75rem" }}>Day {d.day_number}</div>
                <strong>{d.weekday}</strong>
                <div>{new Date(d.date + "T12:00:00Z").toLocaleDateString("en-GB", { timeZone: "UTC", day: "numeric", month: "long", year: "numeric" })}</div>
                <div style={{ margin: "0.5rem 0 0.25rem" }}>
                  {d.window_risk_level ? (
                    <>
                      <RiskBadge level={norm(d.window_risk_level)} />
                      <div className="text-muted" style={{ fontSize: "0.72rem" }}>
                        window-level estimate (not specific to this day)
                      </div>
                    </>
                  ) : (
                    <span className="text-muted">No model risk for this date</span>
                  )}
                </div>
                <div className="text-muted" style={{ fontSize: "0.72rem" }}>
                  Weather forecast: unavailable (no provider connected)
                </div>
              </div>
            ))}
          </div>

          {state.data.window_prediction && (
            <table>
              <tbody>
                <tr><td className="text-muted">Type</td><td>Model-derived flood-risk estimate for the whole window (not a weather forecast)</td></tr>
                <tr><td className="text-muted">Window</td><td>{state.data.window_prediction.window_start} to {state.data.window_prediction.window_end}</td></tr>
                <tr><td className="text-muted">Risk</td><td><RiskBadge level={norm(state.data.window_prediction.risk_level)} /> ({(state.data.window_prediction.probability_calibrated * 100).toFixed(3)}% calibrated; relative, not an absolute chance)</td></tr>
                <tr><td className="text-muted">Computed from weather of</td><td>{state.data.window_prediction.observation_date ?? "unknown"}</td></tr>
                <tr><td className="text-muted">Model</td><td>{state.data.window_prediction.model_version ?? "unknown"}</td></tr>
              </tbody>
            </table>
          )}
          <ul className="text-muted" style={{ fontSize: "0.8rem", paddingLeft: "1.1rem" }}>
            {state.data.notes.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </>
      )}
    </section>
  );
}
