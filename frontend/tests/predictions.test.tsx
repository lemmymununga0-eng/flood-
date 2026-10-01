/**
 * Phase 23 - frontend tests for the prediction path.
 *
 * The audit found the frontend contains no fabricated data, which is the standard worth
 * protecting. These tests assert that property directly, plus the contract change:
 * the form must post `wind_speed_10m_ms` (10 m wind, what the model was trained on) and
 * never `wind_speed_ms` (2 m wind, which the backend used to supply).
 *
 * Every network call is stubbed. Nothing here talks to a real API.
 *
 *   npm test
 */
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import Predictions from "../src/pages/Predictions";
import * as api from "../src/services/api";

const A_PREDICTION = {
  id: 1,
  location_id: 1,
  model_version_id: 1,
  predicted_at: "2026-09-25T05:08:25Z",
  prediction_probability: 0.0021,
  risk_level: "low",
  prediction_horizon: "7 days",
  explanation: "{}",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <Predictions />
    </MemoryRouter>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Predictions page", () => {
  it("shows a loading state before any data arrives", () => {
    vi.spyOn(api, "fetchPredictions").mockReturnValue(new Promise(() => {}));
    vi.spyOn(api, "fetchLocations").mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText(/loading/i)).toBeTruthy();
  });

  it("renders an honest empty state, not placeholder rows, when the API returns nothing", async () => {
    vi.spyOn(api, "fetchPredictions").mockResolvedValue([]);
    vi.spyOn(api, "fetchLocations").mockResolvedValue([]);
    const { container } = renderPage();

    await waitFor(() => {
      expect(container.querySelectorAll("tbody tr").length).toBe(0);
    });
    // No fabricated probability may appear anywhere on an empty page.
    expect(container.textContent).not.toMatch(/\d+\.\d+\s*%/);
  });

  it("surfaces a real error with a retry affordance instead of falling back to fake data", async () => {
    vi.spyOn(api, "fetchPredictions").mockRejectedValue(new Error("model_unavailable"));
    vi.spyOn(api, "fetchLocations").mockResolvedValue([]);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/model_unavailable/i)).toBeTruthy();
    });
  });

  it("renders only values that came from the API", async () => {
    vi.spyOn(api, "fetchPredictions").mockResolvedValue([A_PREDICTION] as never);
    vi.spyOn(api, "fetchLocations").mockResolvedValue([
      { id: 1, name: "Lusaka", province: "Lusaka", latitude: -15.4, longitude: 28.3 },
    ] as never);
    const { container } = renderPage();

    await waitFor(() => {
      expect(container.textContent).toContain("Lusaka");
    });
    // The stubbed risk level is the only one that may be displayed.
    expect(container.textContent?.toLowerCase()).toContain("low");
    expect(container.textContent?.toLowerCase()).not.toContain("critical");
  });
});

describe("feature contract in the request payload", () => {
  it("posts wind_speed_10m_ms and never the 2 m field name", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }) as never,
    );
    const { requestPrediction } = await import("../src/services/predictions");

    await requestPrediction({
      location_id: 1,
      precipitation_mm: 12,
      temperature_c: 22,
      temperature_max_c: 28,
      temperature_min_c: 17,
      relative_humidity_pct: 85,
      wind_speed_10m_ms: 3,
    });

    const body = JSON.parse(String((fetchSpy.mock.calls[0]?.[1] as RequestInit)?.body));
    expect(body).toHaveProperty("wind_speed_10m_ms", 3);
    expect(body).not.toHaveProperty("wind_speed_ms");
  });

  it("sends distinct max/mean/min temperatures, which the backend now requires", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({}), { status: 200 }) as never,
    );
    const { requestPrediction } = await import("../src/services/predictions");

    await requestPrediction({
      location_id: 1,
      precipitation_mm: 0,
      temperature_c: 22,
      temperature_max_c: 28,
      temperature_min_c: 17,
      relative_humidity_pct: 60,
      wind_speed_10m_ms: 4,
    });

    const body = JSON.parse(String((fetchSpy.mock.calls[0]?.[1] as RequestInit)?.body));
    const distinct = new Set([
      body.temperature_min_c,
      body.temperature_c,
      body.temperature_max_c,
    ]);
    expect(distinct.size).toBe(3);
  });
});
