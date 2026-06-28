import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Play, RotateCcw, Sparkles } from "lucide-react";
import type { RunBundle } from "../types";
import { Badge, MetricCard, SectionTitle, pct } from "./ui";

export default function ControlRoom({ run }: { run: RunBundle }) {
  const a = run.results.anchored;
  const u = run.results.unanchored;
  const baseline = a.history[0];
  const final = a.history[a.history.length - 1];

  const chartData = a.history.map((m, i) => ({
    iter: i,
    Anchored: +(m.agreement * 100).toFixed(1),
    Unanchored: +(u.history[i]?.agreement * 100).toFixed(1),
  }));

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Control Room"
        subtitle="Held-out agreement as Judy rewrites her own policy. Anchored learning uses ground truth; unanchored uses only self-consistency."
      />

      {/* Hero chart */}
      <div className="panel panel-pad">
        <div className="mb-3 flex items-center justify-between">
          <span className="label">Held-out agreement vs. iteration</span>
          <div className="flex items-center gap-3 text-xs">
            <LegendDot className="bg-good" label="Anchored" />
            <LegendDot className="bg-fog-400" label="Unanchored" dashed />
          </div>
        </div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 4, left: -12 }}>
              <CartesianGrid stroke="#1f2632" vertical={false} />
              <XAxis
                dataKey="iter"
                stroke="#8b96a8"
                tickLine={false}
                axisLine={false}
                fontSize={12}
                tickFormatter={(v) => (v === 0 ? "baseline" : `iter ${v}`)}
              />
              <YAxis
                stroke="#8b96a8"
                tickLine={false}
                axisLine={false}
                fontSize={12}
                domain={[50, 95]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f1219",
                  border: "1px solid #1f2632",
                  borderRadius: 10,
                  fontSize: 12,
                }}
                labelFormatter={(v) => (v === 0 ? "baseline" : `iteration ${v}`)}
                formatter={(val: number) => [`${val}%`, ""]}
              />
              <ReferenceLine y={chartData[0].Anchored} stroke="#2a3340" strokeDasharray="3 3" />
              <Line
                type="monotone"
                dataKey="Anchored"
                stroke="#34d399"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#34d399" }}
                activeDot={{ r: 5 }}
                isAnimationActive
                animationDuration={900}
              />
              <Line
                type="monotone"
                dataKey="Unanchored"
                stroke="#8b96a8"
                strokeWidth={2}
                strokeDasharray="5 4"
                dot={{ r: 2.5, fill: "#8b96a8" }}
                isAnimationActive
                animationDuration={900}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard
          label="Agreement (anchored)"
          value={pct(final.agreement, 0)}
          delta={final.agreement - baseline.agreement}
          hint={`baseline ${pct(baseline.agreement, 0)}`}
        />
        <MetricCard
          label="Position-consistent agreement"
          value={pct(final.position_consistent_agreement, 0)}
          delta={
            (final.position_consistent_agreement ?? 0) -
            (baseline.position_consistent_agreement ?? 0)
          }
          hint="correct under both A/B orders"
        />
        <MetricCard
          label="Score-spread"
          value={final.score_spread.toFixed(2)}
          hint="stdev of margin — watch for collapse"
        />
        <MetricCard
          label="Errors on held-out"
          value={`${final.n_errors}`}
          delta={(baseline.n_errors - final.n_errors) / Math.max(1, baseline.n_errors)}
          hint={`of ${final.n_records} judgments`}
        />
      </div>

      {/* Run controls */}
      <div className="panel panel-pad flex flex-wrap items-center gap-3">
        <button className="btn btn-accent">
          <Play size={15} /> Run baseline
        </button>
        <button className="btn">
          <Sparkles size={15} /> Run 4 iterations
        </button>
        <button className="btn">
          <RotateCcw size={15} /> Reset policy
        </button>
        <div className="ml-auto flex items-center gap-2">
          <Badge tone="neutral">order-swap: held-out only</Badge>
          <Badge tone="neutral">dataset: judy_v1 ({run.n_dev}+{run.n_heldout})</Badge>
        </div>
      </div>

      {/* Status strip */}
      <div className="panel panel-pad flex items-center gap-3 font-mono text-xs text-fog-300">
        <span className="h-2 w-2 animate-pulse rounded-full bg-good" />
        <span>mock run · {run.run_id}</span>
        <span className="text-fog-500">·</span>
        <span>unseen held-out types: {run.unseen_heldout_types.join(", ")}</span>
        <span className="ml-auto text-fog-500">idle — connect the API to run live</span>
      </div>
    </div>
  );
}

function LegendDot({ className, label, dashed }: { className: string; label: string; dashed?: boolean }) {
  return (
    <span className="flex items-center gap-1.5 text-fog-300">
      <span
        className={`inline-block h-0.5 w-4 ${className} ${dashed ? "opacity-70" : ""}`}
        style={dashed ? { backgroundImage: "repeating-linear-gradient(90deg,currentColor 0 4px,transparent 4px 7px)" } : undefined}
      />
      {label}
    </span>
  );
}
