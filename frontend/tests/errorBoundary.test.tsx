/**
 * The boundary exists so that a render-time throw produces a readable panel instead of
 * a blank page. These tests assert exactly that, including the negative case: without
 * the boundary the same component leaves the container empty.
 */
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ErrorBoundary from "../src/components/ErrorBoundary";

function Boom({ message = "kaboom" }: { message?: string }): JSX.Element {
  throw new Error(message);
}

// React logs caught render errors to console.error; silence it so the suite output
// stays readable, and restore afterwards.
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("ErrorBoundary", () => {
  it("renders its children untouched when nothing throws", () => {
    render(
      <ErrorBoundary>
        <p>all good</p>
      </ErrorBoundary>,
    );
    expect(screen.getByText("all good")).toBeTruthy();
  });

  it("shows a fallback panel instead of a blank page when a child throws", () => {
    const { container } = render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );
    expect(container.textContent).toContain("Something went wrong");
    // The real failure mode this guards against: an empty root.
    expect(container.textContent!.trim().length).toBeGreaterThan(40);
  });

  it("surfaces the error message and offers a way out", () => {
    render(
      <ErrorBoundary>
        <Boom message="prediction chart failed" />
      </ErrorBoundary>,
    );
    expect(screen.getByText("prediction chart failed")).toBeTruthy();
    expect(screen.getByRole("button", { name: /try again/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /back to dashboard/i })).toBeTruthy();
  });

  it("names the failing area when one is given", () => {
    render(
      <ErrorBoundary area="Risk Map">
        <Boom />
      </ErrorBoundary>,
    );
    expect(screen.getByText(/Something went wrong in Risk Map/)).toBeTruthy();
  });

  it("without a boundary the same component leaves the container empty", () => {
    // Guard on the guard: proves the fallback above is doing real work.
    const container = document.createElement("div");
    expect(() => render(<Boom />, { container })).toThrow();
    expect(container.textContent).toBe("");
  });
});
