import clsx from "clsx";
import type { ReactNode } from "react";

export function pct(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined) return "—";
  return `${(x * 100).toFixed(digits)}%`;
}

export function MetricCard({
  label,
  value,
  delta,
  hint,
}: {
  label: string;
  value: string;
  delta?: number; // signed fractional change vs baseline
  hint?: string;
}) {
  const up = delta !== undefined && delta > 0.0005;
  const down = delta !== undefined && delta < -0.0005;
  return (
    <div className="panel panel-pad flex flex-col gap-1">
      <span className="label">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-2xl font-semibold text-fog-100">{value}</span>
        {delta !== undefined && (delta !== 0) && (
          <span
            className={clsx(
              "font-mono text-xs font-medium",
              up && "text-good",
              down && "text-bad"
            )}
          >
            {up ? "▲" : "▼"} {pct(Math.abs(delta), 0)}
          </span>
        )}
      </div>
      {hint && <span className="text-xs text-fog-400">{hint}</span>}
    </div>
  );
}

export function Badge({
  tone = "neutral",
  children,
}: {
  tone?: "good" | "bad" | "accent" | "neutral";
  children: ReactNode;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium",
        tone === "good" && "bg-good/15 text-good",
        tone === "bad" && "bg-bad/15 text-bad",
        tone === "accent" && "bg-accent/15 text-accent",
        tone === "neutral" && "border border-ink-600 bg-ink-700/60 text-fog-300"
      )}
    >
      {children}
    </span>
  );
}

export function SectionTitle({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="mb-4">
      <h2 className="text-lg font-semibold text-fog-100">{title}</h2>
      {subtitle && <p className="mt-0.5 text-sm text-fog-400">{subtitle}</p>}
    </div>
  );
}
