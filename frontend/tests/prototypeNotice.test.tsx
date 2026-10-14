/** Every page that shows model risk levels carries the research-prototype notice (audit F-17). */
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import Dashboard from "../src/pages/Dashboard";
import Predictions from "../src/pages/Predictions";
import RiskMap from "../src/pages/RiskMap";

vi.mock("../src/context/AuthContext", async (orig) => ({
  ...(await orig<typeof import("../src/context/AuthContext")>()),
  useAuth: () => ({ user: null }),
}));
vi.mock("leaflet", () => {
  const chain: any = new Proxy(() => chain, { get: () => chain, apply: () => chain });
  return { default: chain };
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PrototypeNotice", () => {
  for (const [name, Page] of [["Dashboard", Dashboard], ["Predictions", Predictions], ["Risk Map", RiskMap]] as const) {
    it(`is shown on ${name} even while data is loading`, () => {
      vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
      render(<MemoryRouter><Page /></MemoryRouter>);
      expect(screen.getByText(/Research prototype — not a forecast or a warning/)).toBeTruthy();
    });
  }
});
