import { useEffect, useState } from "react";
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

// Renders the held-out learning curve for a continual-learning run (V2/V5/...).
// Reads real run data emitted by the pipeline into /public/runs/. Self-contained:
// drop <LearningCurve /> into a tab and it lists runs + charts the selected one.

interface RunData {
  run_id: string;
  variant: string;
  description: string;
  benchmark: string;
  judge_model: string;
  teacher_model?: string;
  curve: { after: number; agreement: number }[];
  references: Record<string, number>;
  peak: number;
  final: number;
  cost_usd: number;
}

interface IndexEntry {
  run_id: string;
  variant: string;
  final: number;
  peak: number;
}

const REF_COLORS = ["#9ca3af", "#a78bfa", "#fbbf24", "#34d399"];

export default function LearningCurve() {
  const [index, setIndex] = useState<IndexEntry[]>([]);
  const [runId, setRunId] = useState<string | null>(null);
  const [data, setData] = useState<RunData | null>(null);

  useEffect(() => {
    fetch("/curves/index.json")
      .then((r) => r.json())
      .then((idx: IndexEntry[]) => {
        setIndex(idx);
        if (idx[0]) setRunId(idx[0].run_id);
      })
      .catch(() => setIndex([]));
  }, []);

  useEffect(() => {
    if (!runId) return;
    fetch(`/curves/${runId}.json`)
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, [runId]);

  if (!index.length)
    return (
      <div className="panel panel-pad text-sm text-fog-400">
        No runs yet — run a continual variant (e.g. <code className="font-mono">scripts/run_v5.py</code>) to chart its learning curve here.
      </div>
    );

  // dedupe consecutive duplicate x (final checkpoint repeats the last point)
  const pts: { x: number; y: number }[] = [];
  (data?.curve ?? []).forEach((p) => {
    if (!pts.length || pts[pts.length - 1].x !== p.after)
      pts.push({ x: p.after, y: +(p.agreement * 100).toFixed(1) });
  });
  const peakPct = data ? +(data.peak * 100).toFixed(1) : 0;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-fog-100">{data?.variant ?? "Learning curve"}</h2>
          <p className="mt-0.5 max-w-2xl text-sm text-fog-400">{data?.description}</p>
        </div>
        <select
          value={runId ?? ""}
          onChange={(e) => setRunId(e.target.value)}
          className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-1.5 text-sm text-fog-200"
        >
          {index.map((r) => (
            <option key={r.run_id} value={r.run_id}>
              {r.variant} · {r.run_id}
            </option>
          ))}
        </select>
      </div>

      {data && (
        <>
          <div className="flex flex-wrap gap-2 text-xs">
            <span className="chip">judge: {data.judge_model}</span>
            {data.teacher_model && <span className="chip">teacher: {data.teacher_model}</span>}
            <span className="chip">{data.benchmark}</span>
            <span className="chip">peak {peakPct}%</span>
            <span className="chip">final {(data.final * 100).toFixed(1)}%</span>
            <span className="chip">~${data.cost_usd.toFixed(2)}</span>
          </div>

          <div className="panel panel-pad">
            <span className="label">Held-out agreement as the judge learns</span>
            <div className="mt-3 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={pts} margin={{ top: 12, right: 80, bottom: 4, left: -8 }}>
                  <CartesianGrid stroke="#1f2632" vertical={false} />
                  <XAxis
                    dataKey="x"
                    stroke="#8b96a8"
                    tickLine={false}
                    axisLine={false}
                    fontSize={12}
                    label={{ value: "training examples seen", position: "insideBottom", offset: -2, fill: "#8b96a8", fontSize: 11 }}
                  />
                  <YAxis
                    stroke="#8b96a8"
                    tickLine={false}
                    axisLine={false}
                    fontSize={12}
                    domain={["dataMin-2", "dataMax+2"]}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <Tooltip
                    contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                    labelFormatter={(v) => `after ${v} examples`}
                    formatter={(val: number) => [`${val}%`, "agreement"]}
                  />
                  {Object.entries(data.references).map(([name, val], i) => (
                    <ReferenceLine
                      key={name}
                      y={+(val * 100).toFixed(1)}
                      stroke={REF_COLORS[i % REF_COLORS.length]}
                      strokeDasharray="4 4"
                      strokeOpacity={0.7}
                      label={{ value: `${name} ${(val * 100).toFixed(0)}%`, position: "right", fill: "#6b7280", fontSize: 10 }}
                    />
                  ))}
                  <Line
                    type="monotone"
                    dataKey="y"
                    stroke="#7c9cff"
                    strokeWidth={2.5}
                    dot={{ r: 4, fill: "#7c9cff" }}
                    activeDot={{ r: 6 }}
                    isAnimationActive
                    animationDuration={900}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-2 text-xs text-fog-500">
              The curve reveals dynamics a before/after number hides — e.g. peaking then drifting as later
              lessons over-correct (early-stopping at the peak is best).
            </p>
          </div>
        </>
      )}
    </div>
  );
}
