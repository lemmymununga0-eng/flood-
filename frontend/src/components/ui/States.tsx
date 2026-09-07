export function LoadingState({ label }: { label: string }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <div className="skeleton" style={{ height: 14, width: "60%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 14, width: "85%", marginBottom: 8 }} />
      <div className="skeleton" style={{ height: 14, width: "40%" }} />
      <span style={{ position: "absolute", left: -9999 }}>{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {detail && <p className="text-secondary">{detail}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Unable to load data",
  detail,
  onRetry,
}: {
  title?: string;
  detail?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="error-state">
      <h3>{title}</h3>
      {detail && <p className="text-secondary">{detail}</p>}
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}
