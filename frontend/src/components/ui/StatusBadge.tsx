type Status = "operational" | "degraded" | "unavailable" | "unknown";

const LABEL: Record<Status, string> = {
  operational: "Operational",
  degraded: "Degraded",
  unavailable: "Unavailable",
  unknown: "Unknown",
};

export default function StatusBadge({ status }: { status: Status }) {
  return (
    <span className="status-badge">
      <span className={`status-dot ${status}`} aria-hidden="true" />
      {LABEL[status]}
    </span>
  );
}
