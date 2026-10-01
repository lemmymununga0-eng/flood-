interface BrandMarkProps {
  /** Sidebar rendering stacks the name on two lines in a larger, bolder block;
   * every other surface (topbar, auth pages) uses the compact single-line form. */
  variant?: "stacked" | "inline";
  size?: number;
}

export function BrandMark({ variant = "inline", size = 30 }: BrandMarkProps) {
  const mark = (
    <span
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        borderRadius: Math.round(size * 0.28),
        background: "linear-gradient(135deg, var(--brand-blue), var(--brand-green))",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        boxShadow: "0 2px 6px color-mix(in srgb, var(--brand-blue) 35%, transparent)",
      }}
    >
      <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 24 24" fill="#ffffff" aria-hidden="true">
        <path d="M12 2.5C10.8 4.3 5 13 5 16.5a7 7 0 0 0 14 0C19 13 13.2 4.3 12 2.5Z" />
      </svg>
    </span>
  );

  if (variant === "stacked") {
    return (
      <>
        {mark}
        <span>
          FLOOD PREDICTION
          <br />
          SYSTEM ZM
        </span>
      </>
    );
  }

  return (
    <span style={{ display: "flex", alignItems: "center", gap: "0.6rem", fontWeight: 700 }}>
      {mark}
      FLOOD PREDICTION SYSTEM ZM
    </span>
  );
}

export default BrandMark;
