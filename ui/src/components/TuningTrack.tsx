import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Cpu, FlaskConical, LoaderCircle } from "lucide-react";
import type { SftEvalData } from "../types";
import { Badge, MetricCard, SectionTitle, pct } from "./ui";

const BAR_COLORS = ["#60a5fa", "#f59e0b"];

function formatDelta(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}pp`;
}

export default function TuningTrack({ sft }: { sft: SftEvalData }) {
  const base = sft.variants.find((variant) => variant.label === "base") ?? sft.variants[0];
  const tuned = sft.variants.find((variant) => variant.label === "tuned") ?? sft.variants[1];

  const headline = [
    { label: "base", agreement: +(base.overall.agreement * 100).toFixed(1) },
    { label: "tuned", agreement: +(tuned.overall.agreement * 100).toFixed(1) },
  ];

  const subsetData = Object.entries(base.per_subset).map(([subset, metrics]) => ({
    subset,
    base: +(metrics.agreement * 100).toFixed(1),
    tuned: +((tuned.per_subset[subset]?.agreement ?? 0) * 100).toFixed(1),
  }));

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Weight-Update Track"
        subtitle="This is the supervised fine-tuning lane. Unlike V0/V1/V2/V5, this track changes weights instead of only changing the judging context."
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard
          label="SFT-20 base"
          value={pct(base.overall.agreement, 1)}
          hint="synthetic objective held-out"
        />
        <MetricCard
          label="SFT-20 tuned"
          value={pct(tuned.overall.agreement, 1)}
          delta={(tuned.overall.agreement - base.overall.agreement)}
          hint="same held-out set"
        />
        <MetricCard
          label="Consistency delta"
          value={formatDelta(sft.delta.position_consistency_pp)}
          hint="tuned minus base"
        />
        <MetricCard
          label="Current read"
          value="not yet better"
          hint="20-sample tuned judge regressed slightly"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Cpu size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Completed run: 20-sample SFT</h3>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            <Badge tone="neutral">judge family: Gemini 3.5 Flash</Badge>
            <Badge tone="neutral">policy mode: {sft.policy}</Badge>
            <Badge tone="neutral">dataset: 100 synthetic objective test items</Badge>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={headline} margin={{ top: 8, right: 20, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#1f2632" vertical={false} />
                <XAxis dataKey="label" stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} domain={[85, 100]} tickFormatter={(value) => `${value}%`} />
                <Tooltip
                  contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                  formatter={(value: number) => [`${value}%`, "agreement"]}
                />
                <Bar dataKey="agreement" radius={[6, 6, 0, 0]}>
                  {headline.map((entry, index) => (
                    <Cell key={entry.label} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-sm leading-6 text-fog-300">
            The first completed weight-update experiment does not beat the base judge yet: agreement moved from {pct(base.overall.agreement, 1)} to {pct(tuned.overall.agreement, 1)}, and position-consistency dropped by {formatDelta(sft.delta.position_consistency_pp)}.
          </p>
        </div>

        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <FlaskConical size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Where tuning helps or hurts</h3>
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
            The tuned judge improved a little on factual QA, but gave back more on numeric-constraint cases. That is why the overall result is still below the untuned baseline.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="panel panel-pad">
          <div className="mb-3 flex items-center gap-2">
            <LoaderCircle size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">SFT-40 status</h3>
          </div>
          <p className="text-sm leading-6 text-fog-300">
            The 40-sample checkpoint bundle is prepared in the repo, but I do not see a completed evaluation artifact yet. The UI now reflects that honestly as pending rather than pretending the result exists.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone="neutral">checkpoint bundle prepared</Badge>
            <Badge tone="neutral">upload + request stub present</Badge>
            <Badge tone="accent">evaluation pending</Badge>
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-3 text-base font-semibold text-fog-100">Read on the tuning track</div>
          <ul className="space-y-2 text-sm leading-6 text-fog-300">
            <li>The weight-update lane is real, but it has not yet cleared the context-only baseline.</li>
            <li>The 20-sample SFT run is useful because it proves the evaluation path works end to end.</li>
            <li>The next meaningful checkpoint is whether larger tuned checkpoints beat the base judge without sacrificing order robustness.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
