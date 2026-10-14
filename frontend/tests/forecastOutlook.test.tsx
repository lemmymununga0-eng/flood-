/** Seven-day outlook: every card is dated, and nothing per-day is invented. Network stubbed. */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import ForecastOutlook from "../src/components/ForecastOutlook";
import * as api from "../src/services/api";
import * as dams from "../src/services/dams";

const auth = vi.hoisted(() => ({ user: null as null | { role: string } }));
vi.mock("../src/context/AuthContext", async (orig) => ({
  ...(await orig<typeof import("../src/context/AuthContext")>()),
  useAuth: () => ({ user: auth.user }),
}));

const WEEKDAYS = ["Thursday", "Friday", "Saturday", "Sunday", "Monday", "Tuesday", "Wednesday"];
const days = WEEKDAYS.map((weekday, i) => ({
  day_number: i + 1,
  date: `2026-10-${15 + i}`,
  weekday,
  label: `Day ${i + 1}`,
  in_prediction_window: i < 3,
  window_risk_level: i < 3 ? "HIGH" : null,
  daily_flood_prediction: null,
  weather_forecast: null,
  weather_forecast_status: "unavailable_no_provider",
}));
const outlook = {
  timezone: "Africa/Lusaka",
  day_1_convention: "Day 1 is tomorrow (Africa/Lusaka).",
  generated_at: "2026-10-14T10:00:00+00:00",
  today_local: "2026-10-14",
  status: "partial" as const,
  stale: false,
  days,
  window_prediction: null,
  notes: [],
};

afterEach(() => {
  vi.restoreAllMocks();
  auth.user = null;
});

describe("ForecastOutlook", () => {
  it("renders seven dated cards and marks window-level risk only where it applies", async () => {
    vi.spyOn(api, "fetchLocations").mockResolvedValue([
      { id: 1, name: "Lusaka", province: "Lusaka", latitude: 0, longitude: 0, coordinate_confidence: "", evidence_note: "", evidence_source_url: "" },
    ]);
    vi.spyOn(dams, "fetchOutlook").mockResolvedValue(outlook);
    render(<ForecastOutlook />);
    fireEvent.change(await screen.findByLabelText("Location"), { target: { value: "1" } });
    await waitFor(() => expect(screen.getAllByText(/^Day \d$/)).toHaveLength(7));
    expect(screen.getByText("15 October 2026")).toBeTruthy();
    expect(screen.getByText("21 October 2026")).toBeTruthy();
    expect(screen.getAllByText(/window-level estimate/)).toHaveLength(3);
    expect(screen.getAllByText(/No model risk for this date/)).toHaveLength(4);
    expect(screen.getAllByText(/Weather forecast: unavailable/)).toHaveLength(7);
  });

  it("shows an error state rather than fallback values when the request fails", async () => {
    vi.spyOn(api, "fetchLocations").mockResolvedValue([
      { id: 1, name: "Lusaka", province: "Lusaka", latitude: 0, longitude: 0, coordinate_confidence: "", evidence_note: "", evidence_source_url: "" },
    ]);
    vi.spyOn(dams, "fetchOutlook").mockRejectedValue(new Error("boom"));
    render(<ForecastOutlook />);
    fireEvent.change(await screen.findByLabelText("Location"), { target: { value: "1" } });
    expect(await screen.findByText("Could not load the outlook")).toBeTruthy();
    expect(screen.queryByText(/^Day \d$/)).toBeNull();
  });

  it("offers the refresh action only to privileged roles, and shows the refreshed result", async () => {
    const loc = { id: 1, name: "Lusaka", province: "Lusaka", latitude: 0, longitude: 0, coordinate_confidence: "", evidence_note: "", evidence_source_url: "" };
    vi.spyOn(api, "fetchLocations").mockResolvedValue([loc]);
    vi.spyOn(dams, "fetchOutlook").mockResolvedValue({ ...outlook, status: "no_prediction" });
    const refreshed = vi.spyOn(dams, "refreshOutlook").mockResolvedValue({ ...outlook, status: "partial" });

    const first = render(<ForecastOutlook />);
    fireEvent.change(await screen.findByLabelText("Location"), { target: { value: "1" } });
    await screen.findAllByText(/^Day \d$/);
    expect(screen.queryByText("Refresh from latest weather")).toBeNull();
    first.unmount();

    auth.user = { role: "ANALYST" };
    render(<ForecastOutlook />);
    fireEvent.change(await screen.findByLabelText("Location"), { target: { value: "1" } });
    fireEvent.click(await screen.findByText("Refresh from latest weather"));
    await waitFor(() => expect(refreshed).toHaveBeenCalledWith(1));
    expect(await screen.findAllByText(/window-level estimate/)).toHaveLength(3);
  });
});
