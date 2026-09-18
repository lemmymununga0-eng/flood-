import { Icon } from "./icons";

export default function KpiCard({
  label,
  value,
  note,
  icon,
  accent = "blue",
}: {
  label: string;
  value: React.ReactNode;
  note?: string;
  icon?: string;
  accent?: "blue" | "green" | "gold" | "critical";
}) {
  return (
    <div className="kpi-card">
      {icon && (
        <div className={`kpi-icon accent-${accent}`}>
          <Icon name={icon} />
        </div>
      )}
      <div className="kpi-body">
        <div className="kpi-label">{label}</div>
        <div className="kpi-value">{value}</div>
        {note && <div className="kpi-note">{note}</div>}
      </div>
    </div>
  );
}
