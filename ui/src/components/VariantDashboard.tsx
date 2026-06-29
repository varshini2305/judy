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
import { BarChart3, Database, Gauge, Sparkles } from "lucide-react";
import type { ExperimentData } from "../types";
import { Badge, MetricCard, SectionTitle, pct } from "./ui";

const COLORS = ["#64748b", "#60a5fa", "#34d399", "#f59e0b"];

export default function VariantDashboard({ experiments }: { experiments: ExperimentData }) {
  const baseline = experiments.variants.find((variant) => variant.id === "V0") ?? experiments.variants[0];
  const bestFinal = experiments.variants.reduce((best, variant) =>
    variant.agreement > best.agreement ? variant : best,
  experiments.variants[0]);
  const bestPeak = experiments.variants.reduce((best, variant) =>
    (variant.peak ?? variant.agreement) > (best.peak ?? best.agreement) ? variant : best,
  experiments.variants[0]);

  const comparisonData = experiments.variants.map((variant) => ({
    id: variant.id,
    label: variant.id,
    agreement: +(variant.agreement * 100).toFixed(1),
    positionConsistency: +(variant.pos_consistency * 100).toFixed(1),
    peak: +(((variant.peak ?? variant.agreement) * 100).toFixed(1)),
  }));

  const deltaData = experiments.variants
    .filter((variant) => variant.id !== baseline.id)
    .map((variant) => ({
      id: variant.id,
      agreementDelta: +(((variant.agreement - baseline.agreement) * 100).toFixed(1)),
      consistencyDelta: +(((variant.pos_consistency - baseline.pos_consistency) * 100).toFixed(1)),
    }));
  const storyOrder = ["V0", "V1", "V2", "V4", "V5"] as const;
  // Real measured numbers per variant, so every card reports BOTH metrics.
  const variantById = Object.fromEntries(experiments.variants.map((variant) => [variant.id, variant]));

  const cheatSheet = [
    {
      id: "V0",
      title: "Baseline vanilla judge",
      model: experiments.judge_model,
      benchmark: "LLMBar-Adversarial · 100 held-out items · order-swap on",
      method: "Single generic LLM-as-a-judge prompt with no rubric, no teacher, and no learning loop.",
      result: "Baseline reference every other variant is measured against.",
    },
    {
      id: "V1",
      title: "Structured rubric",
      model: experiments.judge_model,
      benchmark: "LLMBar-Adversarial · same 100-item test set",
      method: "Hand-written judging policy with explicit bias guards, criteria extraction, and stronger correctness checks.",
      result: "+4.5pp agreement over baseline, concentrated on the hard adversarial subsets.",
    },
    {
      id: "V2",
      title: "Continual self-critique",
      model: experiments.judge_model,
      benchmark: "40 disjoint dev items → same 100-item test set",
      method: "The judge learns from its own errors on a small dev stream by appending task-general lessons to its policy.",
      result: "+5.0pp over baseline; its biggest gain is robustness (position-consistency).",
    },
    {
      id: "V4",
      title: "Judge-jury preference track",
      model: `${experiments.judge_model} + juror personas`,
      benchmark: "Separate subjective benchmarks: creative writing and tweet preference",
      method: "A central judge models shared quality signals while juror agents try to learn where user taste differs. This is most useful when evaluation is subjective and two users can reasonably prefer different answers.",
      result: "Headline gains were small, but the direction is still promising: the jurors picked up some real user-specific signal. That matters because preference learning and literature on human-feedback modeling both suggest that personalized evaluators can help when subjectivity and user bias make one global judge inconsistent.",
    },
    {
      id: "V5",
      title: "Teacher-driven learning",
      model: `${experiments.judge_model} + GPT teacher`,
      benchmark: "40 disjoint dev items → same 100-item test set",
      method: "A cross-family GPT teacher critiques mistakes and writes lessons plus examples that are added back into the judge context.",
      result: "+7.5pp at peak — the best of any variant — before drifting to its final value.",
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Variant Comparison"
        subtitle="Read this page as a method story: start from the baseline judge, then see what each improvement layer adds, and finally compare all variants on one shared benchmark."
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard
          label="Baseline"
          value={pct(baseline.agreement, 1)}
          hint={`${baseline.label} · ${pct(baseline.pos_consistency, 1)} position-consistency`}
        />
        <MetricCard
          label="Best final"
          value={pct(bestFinal.agreement, 1)}
          delta={bestFinal.agreement - baseline.agreement}
          hint={`${bestFinal.id} ${bestFinal.label}`}
        />
        <MetricCard
          label="Best peak"
          value={pct(bestPeak.peak ?? bestPeak.agreement, 1)}
          delta={(bestPeak.peak ?? bestPeak.agreement) - baseline.agreement}
          hint={`${bestPeak.id} peak during learning`}
        />
        <MetricCard
          label="Best robustness"
          value={pct(Math.max(...experiments.variants.map((variant) => variant.pos_consistency)), 1)}
          hint="position-consistency under answer order swap"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Database size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Shared experiment frame</h3>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <SetupRow label="Benchmark" value={experiments.benchmark} />
            <SetupRow label="Judge model" value={experiments.judge_model} />
            <SetupRow label="Learning set" value={experiments.train_set} />
            <SetupRow label="Held-out test" value={experiments.test_set} />
          </div>
          <p className="mt-4 text-sm leading-6 text-fog-300">
            Most variants stay comparable because they keep the same judge family and the same held-out adversarial test set. The main variable is the method used to improve the evaluator.
          </p>
        </div>

        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Gauge size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">How the variants build on each other</h3>
          </div>
          <div className="grid gap-3">
            {storyOrder.map((id) => {
              const variant = cheatSheet.find((item) => item.id === id);
              if (!variant) return null;
              return (
                <StoryStep
                  key={variant.id}
                  id={variant.id}
                  title={variant.title}
                  method={variant.method}
                  result={variant.result}
                />
              );
            })}
          </div>
        </div>
      </div>

      <div className="panel panel-pad">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <h3 className="text-base font-semibold text-fog-100">Variant reference</h3>
        </div>
        <div className="grid gap-3 lg:grid-cols-2">
          {cheatSheet.map((variant) => (
            <article key={variant.id} className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="accent">{variant.id}</Badge>
                <span className="text-sm font-semibold text-fog-100">{variant.title}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-fog-300">{variant.method}</p>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                <SetupRow label="Model" value={variant.model} />
                <SetupRow label="Benchmark" value={variant.benchmark} />
              </div>
              {variantById[variant.id] ? (
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <SetupRow
                    label="Agreement"
                    value={`${pct(variantById[variant.id].agreement, 1)}${
                      variantById[variant.id].peak ? ` · peak ${pct(variantById[variant.id].peak, 1)}` : ""
                    }`}
                  />
                  <SetupRow
                    label="Position-consistency"
                    value={pct(variantById[variant.id].pos_consistency, 1)}
                  />
                </div>
              ) : (
                <div className="mt-3">
                  <SetupRow
                    label="Metrics"
                    value="Separate subjective benchmark — not on the shared agreement/consistency scale"
                  />
                </div>
              )}
              <div className="mt-3 rounded-lg border border-ink-600/60 bg-ink-800/45 px-3 py-2">
                <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">Takeaway</div>
                <div className="mt-1 text-sm text-fog-200">{variant.result}</div>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <BarChart3 size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">All variants on one benchmark</h3>
          </div>
          <div className="mb-4 flex flex-wrap gap-2">
            <Badge tone="neutral">{experiments.benchmark}</Badge>
            <Badge tone="neutral">{experiments.judge_model}</Badge>
            <Badge tone="neutral">order-swap on</Badge>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparisonData} margin={{ top: 8, right: 20, left: -20, bottom: 0 }} barGap={10}>
                <CartesianGrid stroke="#1f2632" vertical={false} />
                <XAxis dataKey="label" stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} domain={[75, 100]} tickFormatter={(value) => `${value}%`} />
                <Tooltip
                  contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                  formatter={(value: number, name: string) => [`${value}%`, name === "agreement" ? "agreement" : name === "peak" ? "peak" : "position-consistency"]}
                />
                <Bar dataKey="agreement" radius={[6, 6, 0, 0]}>
                  {comparisonData.map((entry, index) => (
                    <Cell key={entry.id} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
                <Bar dataKey="positionConsistency" radius={[6, 6, 0, 0]} fill="#8b96a8" fillOpacity={0.55} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs leading-5 text-fog-500">
            Colored bars show agreement with human labels. Gray bars show order robustness. This is the quickest visual check for whether a variant improved both accuracy and stability.
          </p>
        </div>

        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Gauge size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Pairwise lift over baseline</h3>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={deltaData} layout="vertical" margin={{ top: 8, right: 20, left: 0, bottom: 0 }} barGap={10}>
                <CartesianGrid stroke="#1f2632" horizontal={false} />
                <XAxis type="number" stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} tickFormatter={(value) => `${value}pp`} />
                <YAxis type="category" dataKey="id" stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} width={36} />
                <Tooltip
                  contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                  formatter={(value: number, name: string) => [`${value > 0 ? "+" : ""}${value}pp`, name === "agreementDelta" ? "agreement" : "position-consistency"]}
                />
                <Bar dataKey="agreementDelta" fill="#34d399" radius={[0, 6, 6, 0]} />
                <Bar dataKey="consistencyDelta" fill="#7c9cff" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs leading-5 text-fog-500">
            This is the baseline-vs-variant view in percentage points. It makes clear which methods provide immediate lift, which improve robustness, and which only help transiently at peak.
          </p>
        </div>
      </div>
    </div>
  );
}

function StoryStep({
  id,
  title,
  method,
  result,
}: {
  id: string;
  title: string;
  method: string;
  result: string;
}) {
  return (
    <article className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent">{id}</Badge>
        <span className="text-sm font-semibold text-fog-100">{title}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-fog-300">{method}</p>
      <div className="mt-3 rounded-lg border border-ink-600/60 bg-ink-800/45 px-3 py-2 text-sm text-fog-200">
        {result}
      </div>
    </article>
  );
}

function SetupRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-600/60 bg-ink-800/45 px-3 py-2">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-1 text-sm text-fog-200">{value}</div>
    </div>
  );
}
