import type { Role } from "../constants";

export interface Location {
  id: number;
  name: string;
  province: string;
  latitude: number;
  longitude: number;
  coordinate_confidence: string;
  evidence_note: string;
  evidence_source_url: string;
}

export interface FloodEvent {
  id: number;
  event_id: string;
  start_date: string;
  end_date: string | null;
  provinces: string;
  districts: string;
  rivers: string;
  impact_note: string;
  deaths: number | null;
  source_name: string;
  source_url: string;
  confidence_notes: string;
}

export interface Prediction {
  id: number;
  location_id: number;
  model_version_id: number;
  predicted_at: string;
  prediction_probability: number;
  risk_level: string;
  prediction_horizon: string;
  explanation: string;
}

export interface RiskPredictionRequest {
  location_id?: number;
  location_name?: string;
  precipitation_mm: number;
  temperature_c: number;
  temperature_max_c: number;
  temperature_min_c: number;
  relative_humidity_pct: number;
  /** WS10M — wind at 10 m, the variable the model was trained on (not 2 m wind). */
  wind_speed_10m_ms: number;
  observation_date?: string;
}

export interface FeatureContribution {
  feature: string;
  contribution: number;
  direction: string;
}

export interface RiskPredictionResponse {
  location: string;
  latitude: number | null;
  longitude: number | null;
  prediction_horizon_days: number;
  risk_probability_raw: number;
  risk_probability_calibrated: number;
  risk_level: string;
  would_alert_at_threshold: boolean;
  decision_threshold: number;
  model_version: string;
  generated_at: string;
  observation_date: string | null;
  /** The (t, t+7] window this probability refers to, so a stored prediction can be
   * checked against what actually happened. */
  target_window_start: string | null;
  target_window_end: string | null;
  feature_contract_version: string;
  explanation: FeatureContribution[];
  caveats: string[];
}

/** Mirrors backend WeatherObservationOut. The max/min temperature and 10 m wind
 * fields are the feature-contract columns added 2026-09-26; rows ingested before that
 * migration carry null for them, which is why every numeric field is nullable here. */
export interface WeatherObservation {
  id: number;
  location_id: number;
  observed_date: string;
  precipitation_mm: number | null;
  temperature_c: number | null;
  temperature_max_c: number | null;
  temperature_min_c: number | null;
  relative_humidity_pct: number | null;
  wind_speed_10m_ms: number | null;
  /** Legacy 2 m wind, retained so historical rows are not reinterpreted. */
  wind_speed_ms: number | null;
  source: string;
  retrieved_at: string;
}

export interface WeatherIngestResult {
  status: "success" | "failed";
  location_id: number;
  source_url_attempted: string;
  observations_stored: number;
  error_detail: string | null;
}

export interface Alert {
  id: number;
  title: string;
  risk_level: string;
  location_id: number;
  message: string;
  audience: string;
  channels: string;
  status: string;
  valid_until: string | null;
  created_at: string;
}

export interface AlertCreateInput {
  title: string;
  risk_level: string;
  location_id: number;
  message: string;
  audience?: string;
  channels?: string;
  sms_recipients?: string[];
}

export interface SmsDelivery {
  to: string;
  status: "sent" | "simulated" | "failed" | "rejected";
  detail: string;
}

export interface AlertCreated extends Alert {
  sms_provider: string;
  sms_delivery: SmsDelivery[];
}

export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

export interface RegisterInput {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginInputData {
  email: string;
  password: string;
}

export interface CitizenReport {
  id: number;
  reporter_user_id: number | null;
  location_id: number | null;
  description: string;
  severity: string;
  status: "pending" | "verified" | "rejected";
  submitted_at: string;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  review_note: string;
}

export interface CitizenReportCreateInput {
  location_id?: number | null;
  description: string;
  severity?: string;
}

export interface DataSourceEntry {
  id: number;
  name: string;
  category: string;
  base_url: string;
  description: string;
  last_checked_at: string | null;
  last_check_status: "unknown" | "ok" | "failed";
  last_check_detail: string;
}

export interface ModelVersionEntry {
  id: number;
  version: string;
  model_type: string;
  training_period_start: string;
  training_period_end: string;
  metrics_json: string;
  is_active: boolean;
  registered_at: string;
}

export interface ComponentStatus {
  name: string;
  status: "operational" | "degraded" | "unavailable";
  detail: string;
  response_time_ms: number | null;
}

export interface SystemStatus {
  checked_at: string;
  components: ComponentStatus[];
}

export interface Notification {
  id: number;
  user_id: number;
  notification_type: string;
  entity_type: string;
  entity_id: number | null;
  title: string;
  message: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}

export interface SmsSubscriber {
  id: number;
  phone: string;
  name: string;
  location_id: number | null;
  active: boolean;
  created_at: string;
}

export interface SmsSubscriberInput {
  phone: string;
  name?: string;
  location_id: number | null;
}
