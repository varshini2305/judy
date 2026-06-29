import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AlertTriangle, Cpu, FlaskConical, TrendingDown } from "lucide-react";
import type { SftEvalData, SftEvalRun, SftTrendPoint } from "../types";
import { Badge, MetricCard, SectionTitle, pct } from "./ui";

function formatDelta(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}pp`;
}

export default function TuningTrack({
  sftRuns,
  sftTrend,
}: {
  sftRuns: SftEvalRun[];
  sftTrend: SftTrendPoint[];
}) {
  const completed = sftRuns.filter((run) => run.status === "completed" && run.eval);
  const primary = completed.find((run) => run.sampleSize === 20)?.eval ?? completed[0]?.eval;

  if (!primary) {
    return (
      <div className="flex flex-col gap-6">
        <SectionTitle
          title="Weight-Update Track"
          subtitle="This page isolates the supervised fine-tuning story: what was tuned, how it was tested, and whether changing weights helped more than the untuned baseline."
        />
        <div className="panel panel-pad">
          <p className="text-sm leading-6 text-fog-300">No completed SFT evaluation artifacts are loaded yet.</p>
        </div>
      </div>
    );
  }

  const base = primary.variants.find((variant) => variant.label === "base") ?? primary.variants[0];
  const tuned20 = primary.variants.find((variant) => variant.label === "tuned") ?? primary.variants[1];
  const mostRecent = completed[completed.length - 1];
  const mostRecentEval = mostRecent.eval as SftEvalData;
  const mostRecentTuned =
    mostRecentEval.variants.find((variant) => variant.label === "tuned") ?? mostRecentEval.variants[1];
  const latestTrendPoint = [...sftTrend]
    .filter((point) => point.tunedAgreement !== null)
    .sort((a, b) => b.sampleSize - a.sampleSize)[0];
  const trend40 = sftTrend.find((point) => point.sampleSize === 40);

  const subsetData = Object.entries(base.per_subset).map(([subset, metrics]) => ({
    subset,
    base: +(metrics.agreement * 100).toFixed(1),
    tuned: +((tuned20.per_subset[subset]?.agreement ?? 0) * 100).toFixed(1),
  }));

  const trendData = sftTrend.map((point) => ({
    sampleSize: point.sampleSize,
    agreement: point.tunedAgreement,
    baseAgreement: point.baseAgreement,
    consistency: point.tunedPositionConsistency,
    baseConsistency: point.basePositionConsistency,
    status: point.status,
    label: point.label,
    agreementDeltaPp: point.agreementDeltaPp,
    positionConsistencyDeltaPp: point.positionConsistencyDeltaPp,
  }));

  const hasPositiveTrend = sftTrend
    .filter((point) => point.agreementDeltaPp !== null)
    .every((point) => (point.agreementDeltaPp ?? 0) > 0);

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Weight-Update Track"
        subtitle="This page isolates the supervised fine-tuning story: how many training examples were used, how performance changed, and whether scaling SFT is moving in a clearly useful direction."
      />

      <div className="grid gap-4 lg:grid-cols-5">
        <MetricCard
          label="Baseline"
          value={pct(base.overall.agreement, 1)}
          hint="held-out synthetic objective test"
        />
        <MetricCard
          label="SFT-20"
          value={pct(tuned20.overall.agreement, 1)}
          delta={tuned20.overall.agreement - base.overall.agreement}
          hint="first tuned checkpoint"
        />
        {trend40 && trend40.tunedAgreement !== null && (
          <MetricCard
            label={trend40.label}
            value={`${trend40.tunedAgreement.toFixed(1)}%`}
            delta={trend40.agreementDeltaPp !== null ? trend40.agreementDeltaPp / 100 : undefined}
            hint="40-example checkpoint"
          />
        )}
        <MetricCard
          label={latestTrendPoint?.label ?? mostRecent.label}
          value={latestTrendPoint ? `${latestTrendPoint.tunedAgreement?.toFixed(1)}%` : pct(mostRecentTuned.overall.agreement, 1)}
          delta={latestTrendPoint ? (latestTrendPoint.tunedAgreement! - latestTrendPoint.baseAgreement) / 100 : (mostRecentTuned.overall.agreement - base.overall.agreement)}
          hint="latest completed tuned checkpoint"
        />
        <MetricCard
          label="Current read"
          value={hasPositiveTrend ? "trend up" : "no clear upward trend"}
          hint={hasPositiveTrend ? "larger SFT checkpoints are improving together" : "completed checkpoints still regress vs base"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <NarrativeCard
          title="1. What this chart means"
          body="Each point shows the tuned judge on the same held-out test set after increasing the number of SFT training cases."
        />
        <NarrativeCard
          title="2. What users should look for"
          body="A promising tuning direction should move upward together: more samples should improve agreement without hurting answer-order robustness."
        />
        <NarrativeCard
          title="3. Current takeaway"
          body="The completed SFT checkpoints do not yet show a clean one-direction improvement trend, so scaling further is still a hypothesis rather than a proven bet."
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <TrendingDown size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Performance vs SFT sample size</h3>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            <Badge tone="neutral">same base judge: Gemini 3.5 Flash</Badge>
            <Badge tone="neutral">same held-out test set: 100 objective cases</Badge>
            <Badge tone="neutral">20 / 40 / 60 checkpoints plotted</Badge>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData} margin={{ top: 8, right: 20, left: -16, bottom: 8 }}>
                <CartesianGrid stroke="#1f2632" vertical={false} />
                <XAxis
                  dataKey="sampleSize"
                  stroke="#8b96a8"
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                  tickFormatter={(value) => `${value} samples`}
                />
                <YAxis
                  stroke="#8b96a8"
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                  domain={[90, 100]}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip
                  contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                  formatter={(value, name) => {
                    if (value == null) return ["pending", String(name)];
                    return [`${value}%`, String(name)];
                  }}
                  labelFormatter={(value) => `SFT train size: ${value}`}
                />
                <Line
                  type="monotone"
                  dataKey="baseAgreement"
                  stroke="#94a3b8"
                  strokeDasharray="5 5"
                  strokeWidth={2}
                  dot={false}
                  name="Untuned baseline"
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="agreement"
                  stroke="#60a5fa"
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: "#60a5fa" }}
                  activeDot={{ r: 6 }}
                  name="Tuned agreement"
                  connectNulls={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-sm leading-6 text-fog-300">
            This is the easiest read of the tuning story: if SFT is helping, the blue line should climb as sample size grows. Right now, it drops from <span className="font-medium text-fog-100">92.0%</span> at SFT-20 to <span className="font-medium text-fog-100">91.0%</span> at SFT-40, then partially recovers to <span className="font-medium text-fog-100">91.5%</span> at SFT-60. That is a visible trend, but not a clean upward one, because all completed checkpoints remain below the untuned base.
          </p>
        </div>

        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Cpu size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Completed checkpoints</h3>
          </div>
          <div className="space-y-3">
            {sftTrend.map((point) => {
              const run = completed.find((item) => item.sampleSize === point.sampleSize);
              const tuned = run?.eval?.variants.find((variant) => variant.label === "tuned") ?? run?.eval?.variants[1];
              return (
                <div key={point.sampleSize} className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-sm font-semibold text-fog-100">{point.label}</div>
                    <Badge tone={point.agreementDeltaPp !== null && point.agreementDeltaPp >= 0 ? "good" : "bad"}>
                      {point.agreementDeltaPp !== null ? formatDelta(point.agreementDeltaPp) : "pending"}
                    </Badge>
                  </div>
                  <p className="text-sm leading-6 text-fog-300">
                    Tuned agreement: <span className="font-medium text-fog-100">{point.tunedAgreement !== null ? `${point.tunedAgreement.toFixed(1)}%` : (tuned ? pct(tuned.overall.agreement, 1) : "n/a")}</span>
                    {" · "}
                    position-consistency: <span className="font-medium text-fog-100">{point.tunedPositionConsistency !== null ? `${point.tunedPositionConsistency.toFixed(1)}%` : (tuned ? pct(tuned.overall.position_consistency, 1) : "n/a")}</span>
                  </p>
                  {point.notes && <p className="mt-2 text-xs leading-5 text-fog-500">{point.notes}</p>}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <FlaskConical size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Where SFT helps or hurts</h3>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={subsetData} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
                <CartesianGrid stroke="#1f2632" vertical={false} />
                <XAxis dataKey="subset" stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={11} interval={0} angle={-18} textAnchor="end" height={72} />
                <YAxis stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} domain={[70, 100]} tickFormatter={(value) => `${value}%`} />
                <Tooltip
                  contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                  formatter={(value: number, name: string) => [`${value}%`, name]}
                />
                <Bar dataKey="base" fill="#60a5fa" radius={[6, 6, 0, 0]} />
                <Bar dataKey="tuned" fill="#f59e0b" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs leading-5 text-fog-500">
            On the first tuned checkpoint, the main regression came from numeric-constraint cases. That is why the tuning track cannot be judged by one average number alone.
          </p>
        </div>

        <div className="grid gap-4">
          <div className="panel panel-pad">
            <div className="mb-3 flex items-center gap-2">
              <AlertTriangle size={16} className="text-accent" />
              <h3 className="text-base font-semibold text-fog-100">Plain-English read</h3>
            </div>
            <ul className="space-y-2 text-sm leading-6 text-fog-300">
              <li>The tuning lane is real and end-to-end functional: dataset export, cloud tuning, and held-out evaluation are all wired.</li>
              <li>But the completed checkpoints do not yet beat the untuned base judge on this benchmark.</li>
              <li>That means users should treat bigger SFT runs as experiments to validate, not as an automatically improving curve.</li>
            </ul>
          </div>

          <div className="panel panel-pad">
            <div className="mb-3 text-base font-semibold text-fog-100">What would count as encouraging</div>
            <p className="text-sm leading-6 text-fog-300">
              A convincing positive tuning trend would show both lines moving in the right direction as sample size grows: higher held-out agreement and stable answer-order robustness. Until that happens, context-learning remains the stronger result family in Judy.
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <NarrativeCard
          title="How users should use this page"
          body="Use the trend chart first. If the direction is clearly improving with more data, tuning may be worth scaling. If the curve is flat or negative, it is safer to invest in context-learning or change the tuning setup before spending more examples."
        />
        <NarrativeCard
          title="Why this matters"
          body="Most teams want to know whether evaluator tuning is actually paying off before they scale. This page makes that decision easier by showing the sample-size trend directly instead of hiding it inside one isolated run."
        />
      </div>
    </div>
  );
}

function NarrativeCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">{title}</div>
      <p className="text-sm leading-6 text-fog-300">{body}</p>
    </div>
  );
}
