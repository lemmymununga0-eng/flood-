/**
 * Inline SVG charts. Deliberately dependency-free — no charting library is installed,
 * and every colour comes from the approved design tokens so these read as part of the
 * same product. Both components render only the data they are given; neither invents,
 * smooths, or extrapolates a value.
 */

const RISK_VAR: Record<string, string> = {
  low: "var(--risk-low)",
  moderate: "var(--risk-moderate)",
  high: "var(--risk-high)",
  critical: "var(--risk-critical)",
};

export interface DonutSlice {
  label: string;
  value: number;
  tone?: string;
}

export function Donut({ slices, size = 168, centerLabel, centerValue }: {
  slices: DonutSlice[];
  size?: number;
  centerLabel?: string;
  centerValue?: string;
}) {
  const total = slices.reduce((s, x) => s + x.value, 0);
  const r = size / 2 - 14;
  const c = 2 * Math.PI * r;
  let offset = 0;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
      <svg width={size} height={size} role="img" aria-label="Risk distribution">
        <g transform={`translate(${size / 2},${size / 2}) rotate(-90)`}>
          <circle r={r} fill="none" stroke="var(--surface-highest)" strokeWidth={16} />
          {total > 0 &&
            slices.map((s) => {
              const frac = s.value / total;
              const dash = frac * c;
              const el = (
                <circle
                  key={s.label}
                  r={r}
                  fill="none"
                  stroke={RISK_VAR[s.tone ?? ""] ?? "var(--brand-blue)"}
                  strokeWidth={16}
                  strokeDasharray={`${dash} ${c - dash}`}
                  strokeDashoffset={-offset}
                />
              );
              offset += dash;
              return el;
            })}
        </g>
        {(centerValue || centerLabel) && (
          <g>
            <text
              x="50%" y="47%" textAnchor="middle"
              style={{ fontSize: "1.35rem", fontWeight: 700, fill: "var(--text-primary)" }}
            >
              {centerValue}
            </text>
            <text
              x="50%" y="62%" textAnchor="middle"
              style={{ fontSize: "0.68rem", fill: "var(--text-muted)" }}
            >
              {centerLabel}
            </text>
          </g>
        )}
      </svg>

      <div style={{ minWidth: 130 }}>
        {slices.map((s) => (
          <div className="stat-row" key={s.label} style={{ padding: "0.25rem 0" }}>
            <span className="stat-label" style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span
                style={{
                  width: 9, height: 9, borderRadius: "50%",
                  background: RISK_VAR[s.tone ?? ""] ?? "var(--brand-blue)",
                  display: "inline-block",
                }}
              />
              {s.label}
            </span>
            <span className="stat-value">
              {s.value}
              {total > 0 && (
                <span className="text-muted"> ({((s.value / total) * 100).toFixed(0)}%)</span>
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export interface LinePoint {
  label: string;
  value: number;
}

export function LineChart({ points, height = 150, unit = "", tone = "var(--brand-blue)" }: {
  points: LinePoint[];
  height?: number;
  unit?: string;
  tone?: string;
}) {
  if (points.length === 0) {
    return <p className="text-secondary">No observations stored for this period.</p>;
  }

  const w = 520;
  const padL = 40;
  const padB = 24;
  const padT = 10;
  const max = Math.max(...points.map((p) => p.value), 0.001);
  const innerW = w - padL - 10;
  const innerH = height - padB - padT;
  const x = (i: number) =>
    padL + (points.length === 1 ? innerW / 2 : (i / (points.length - 1)) * innerW);
  const y = (v: number) => padT + innerH - (v / max) * innerH;

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p.value)}`).join(" ");
  const area = `${path} L${x(points.length - 1)},${padT + innerH} L${x(0)},${padT + innerH} Z`;

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${height}`} role="img" aria-label="Trend">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line
            x1={padL} x2={w - 10}
            y1={padT + innerH - f * innerH} y2={padT + innerH - f * innerH}
            stroke="var(--border)" strokeWidth={1}
          />
          <text
            x={padL - 6} y={padT + innerH - f * innerH + 3} textAnchor="end"
            style={{ fontSize: "0.6rem", fill: "var(--text-muted)" }}
          >
            {(max * f).toFixed(1)}
          </text>
        </g>
      ))}
      <path d={area} fill={tone} opacity={0.12} />
      <path d={path} fill="none" stroke={tone} strokeWidth={2} strokeLinejoin="round" />
      {points.map((p, i) => (
        <circle key={p.label} cx={x(i)} cy={y(p.value)} r={2.5} fill={tone} />
      ))}
      {points.map((p, i) =>
        i % Math.ceil(points.length / 6) === 0 ? (
          <text
            key={`t-${p.label}`} x={x(i)} y={height - 6} textAnchor="middle"
            style={{ fontSize: "0.6rem", fill: "var(--text-muted)" }}
          >
            {p.label.slice(5)}
          </text>
        ) : null,
      )}
      <text
        x={w - 10} y={padT} textAnchor="end"
        style={{ fontSize: "0.62rem", fill: "var(--text-muted)" }}
      >
        {unit}
      </text>
    </svg>
  );
}
