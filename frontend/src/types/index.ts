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

export interface WeatherIngestResult {
  status: "success" | "failed";
  location_id: number;
  source_url_attempted: string;
  observations_stored: number;
  error_detail: string | null;
}
