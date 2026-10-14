import { authedRequest, getJson } from "./http";

// Every measurement is nullable: null means "not measured", never zero.
export const MEASUREMENT_KEYS = [
  "reservoir_level_m",
  "storage_m3",
  "storage_pct",
  "inflow_m3s",
  "outflow_m3s",
  "spillway_m3s",
  "turbine_m3s",
  "downstream_level_m",
  "downstream_discharge_m3s",
  "rainfall_observed_mm",
  "rainfall_forecast_mm",
] as const;
export type MeasurementKey = (typeof MEASUREMENT_KEYS)[number];

export type DataKind = "live" | "historical" | "manual_import" | "synthetic_test";

export type DamObservation = {
  observed_at: string;
  source_published_at: string | null;
  retrieved_at: string;
  data_kind: DataKind;
  provider: string;
  source_reference: string;
  quality_flag: string;
} & Record<MeasurementKey, number | null>;

export interface Dam {
  slug: string;
  name: string;
  river_system: string | null;
  district: string | null;
  province: string | null;
  latitude: number | null;
  longitude: number | null;
  coordinate_source: string | null;
  capacity_m3: number | null;
  capacity_source: string | null;
  data_provider: string | null;
  data_status: "no_data" | "historical_only" | "manual_import" | "live";
  last_successful_update: string | null;
  notes: string;
  verification_required: boolean;
  freshness: "no_data" | "fresh" | "stale";
  latest: DamObservation | null;
}

export interface ReleaseNotice {
  published_at: string;
  effective_from: string | null;
  effective_to: string | null;
  description: string;
  source_reference: string;
  issuing_body: string;
}

export interface DamDetail {
  dam: Dam;
  observations: DamObservation[];
  release_notices: ReleaseNotice[];
  units: Record<MeasurementKey, string>;
}

export interface DamAssessment {
  experimental: true;
  status: "insufficient_data" | "monitoring" | "elevated_concern" | "official_release_notice";
  message: string;
  data_freshness: string;
  latest_observation_at: string | null;
  disclaimer: string;
  reason?: string;
  signals: { signal: string; evaluable: boolean; triggered: boolean; detail: string }[];
  notices?: { published_at: string; description: string; source_reference: string }[];
}

export const fetchDams = () => getJson<Dam[]>("/dams");
export const fetchDam = (slug: string) => getJson<DamDetail>(`/dams/${encodeURIComponent(slug)}`);
export const fetchDamAssessment = (slug: string) =>
  getJson<DamAssessment>(`/dams/${encodeURIComponent(slug)}/assessment`);

// ---- seven-day outlook -------------------------------------------------------------------

export interface OutlookDay {
  day_number: number;
  date: string;
  weekday: string;
  label: string;
  in_prediction_window: boolean;
  window_risk_level: string | null;
  daily_flood_prediction: null;
  weather_forecast: null;
  weather_forecast_status: string;
}

export interface Outlook {
  timezone: string;
  day_1_convention: string;
  generated_at: string;
  today_local: string;
  status: "no_prediction" | "window_outside_outlook" | "partial" | "complete";
  stale: boolean;
  days: OutlookDay[];
  window_prediction: {
    scope: "window";
    description: string;
    risk_level: string;
    probability_calibrated: number;
    window_start: string;
    window_end: string;
    observation_date: string | null;
    model_version: string | null;
    predicted_at: string | null;
  } | null;
  notes: string[];
}

export const fetchOutlook = (locationId: number) =>
  getJson<Outlook>(`/forecast/outlook?location_id=${locationId}`);

// ADMIN / ANALYST / OPERATOR. Fetches real NASA POWER weather and scores it with the unchanged model.
export const refreshOutlook = (locationId: number) =>
  authedRequest<Outlook>(`/forecast/outlook/refresh?location_id=${locationId}`, { method: "POST" });
