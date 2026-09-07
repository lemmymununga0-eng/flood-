type RiskLevel = "low" | "moderate" | "high" | "critical";

const LABEL: Record<RiskLevel, string> = {
  low: "Low",
  moderate: "Moderate",
  high: "High",
  critical: "Critical",
};

export default function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={`risk-badge ${level}`}>{LABEL[level]}</span>;
}
