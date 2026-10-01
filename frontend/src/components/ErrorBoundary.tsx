import React from "react";

/**
 * Catches render-time errors anywhere below it so an unhandled exception degrades to a
 * readable panel instead of a blank white page.
 *
 * Without this, any throw during render unmounts the whole tree and React leaves an
 * empty <div id="root">. The user sees nothing at all — no message, no way back — which
 * is the worst possible failure mode for an operations dashboard, because it is
 * indistinguishable from the app simply not loading.
 *
 * Error boundaries must be class components: there is no hook equivalent of
 * componentDidCatch.
 */
interface Props {
  children: React.ReactNode;
  /** Optional label so a boundary around one panel can say what failed. */
  area?: string;
}

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Keep the real error in the console for debugging. It is deliberately not shown
    // to the user beyond its message — a component stack is not useful to them and can
    // disclose internals.
    console.error("Unhandled render error", error, info.componentStack);
  }

  private reset = () => this.setState({ error: null });

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    const where = this.props.area ? ` in ${this.props.area}` : "";
    return (
      <div className="error-state" role="alert" style={{ margin: "2rem auto", maxWidth: 560 }}>
        <h3>Something went wrong{where}</h3>
        <p className="text-secondary">
          This screen failed to render. The rest of the application is unaffected — the
          error has been logged to the browser console.
        </p>
        <p className="text-muted" style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
          {error.message}
        </p>
        <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
          <button className="btn btn-primary" type="button" onClick={this.reset}>
            Try again
          </button>
          <button
            className="btn btn-secondary"
            type="button"
            onClick={() => {
              window.location.href = "/dashboard";
            }}
          >
            Back to dashboard
          </button>
        </div>
      </div>
    );
  }
}
