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

  const cheatSheet = [
    {
      id: "V0",
      title: "Baseline vanilla judge",
      model: experiments.judge_model,
      benchmark: "LLMBar-Adversarial · 100 held-out items · order-swap on",
      method: "Single generic LLM-as-a-judge prompt with no rubric, no teacher, and no learning loop.",
      result: "81.0% agreement · baseline reference",
    },
    {
      id: "V1",
      title: "Structured rubric",
      model: experiments.judge_model,
      benchmark: "LLMBar-Adversarial · same 100-item test set",
      method: "Hand-written judging policy with explicit bias guards, criteria extraction, and stronger correctness checks.",
      result: "85.5% agreement · +4.5pp over baseline",
    },
    {
      id: "V2",
      title: "Continual self-critique",
      model: experiments.judge_model,
      benchmark: "40 disjoint dev items → same 100-item test set",
      method: "The judge learns from its own errors on a small dev stream by appending task-general lessons to its policy.",
      result: "86.0% agreement · +5.0pp over baseline · 98.0% position-consistency",
    },
    {
      id: "V4",
      title: "Judge-jury preference track",
      model: `${experiments.judge_model} + juror personas`,
      benchmark: "Separate subjective benchmarks: creative writing and tweet preference",
      method: "A central judge models shared quality signals while juror agents try to model individual user taste and disagreement.",
      result: "Mixed result: creative few-shot jurors reached 65.0% vs 63.3% B0; tweet jurors reached +0.46 mean Spearman, but personalization was limited.",
    },
    {
      id: "V5",
      title: "Teacher-driven learning",
      model: `${experiments.judge_model} + GPT teacher`,
      benchmark: "40 disjoint dev items → same 100-item test set",
      method: "A cross-family GPT teacher critiques mistakes and writes lessons plus examples that are added back into the judge context.",
      result: "86.5% final · 88.5% peak · +7.5pp peak over baseline",
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Variant Comparison"
        subtitle="Real artifact-backed results on the shared LLMBar-Adversarial benchmark. Every variant below uses the same Gemini judge unless noted."
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard
          label="Baseline"
          value={pct(baseline.agreement, 1)}
          hint={baseline.label}
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

      <div className="panel panel-pad">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <h3 className="text-base font-semibold text-fog-100">Variant cheat sheet</h3>
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
              <div className="mt-3 rounded-lg border border-ink-600/60 bg-ink-800/45 px-3 py-2">
                <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">Result</div>
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
            Colored bars show agreement with human labels. Gray bars show order robustness, which is where V2 stands out even more than on raw accuracy.
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
            This is the direct baseline-vs-variant view: V1 gives the fastest static prompt gain, V2 improves robustness most, and V5 reaches the best peak once early-stopped.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Database size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Experimental setup</h3>
          </div>
          <div className="space-y-4 text-sm leading-6 text-fog-300">
            <div>
              <div className="label">Test set</div>
              <p className="mt-1">{experiments.test_set}</p>
            </div>
            <div>
              <div className="label">Learning set</div>
              <p className="mt-1">{experiments.train_set}</p>
            </div>
            <div>
              <div className="label">What "learning" means here</div>
              <p className="mt-1">{experiments.training_means}</p>
            </div>
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Sparkles size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Per-variant setup</h3>
          </div>
          <div className="grid gap-3">
            {experiments.variants.map((variant) => (
              <article key={variant.id} className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="accent">{variant.id}</Badge>
                  <span className="text-sm font-semibold text-fog-100">{variant.label}</span>
                  {variant.teacher_model && <Badge tone="neutral">teacher: {variant.teacher_model}</Badge>}
                  {variant.learns ? <Badge tone="good">learns</Badge> : <Badge tone="neutral">static</Badge>}
                </div>
                <p className="mt-3 text-sm leading-6 text-fog-300">{variant.method}</p>
                <div className="mt-3 grid gap-2 md:grid-cols-2">
                  <SetupRow label="Judge model" value={experiments.judge_model} />
                  <SetupRow label="Teacher" value={variant.teacher_model ?? "none"} />
                  <SetupRow label="Train data" value={variant.trains_on} />
                  <SetupRow label="Eval set" value="LLMBar-Adversarial test 100" />
                  <SetupRow label="Learning mode" value={variant.learns ? "context updates" : "static policy"} />
                  <SetupRow label="Order swap" value="enabled" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="chip">agreement {pct(variant.agreement, 1)}</span>
                  <span className="chip">pos-consistency {pct(variant.pos_consistency, 1)}</span>
                  {variant.peak && <span className="chip">peak {pct(variant.peak, 1)}</span>}
                  {variant.cost_usd !== null && <span className="chip">~${variant.cost_usd.toFixed(2)}</span>}
                </div>
                <p className="mt-3 text-xs leading-5 text-fog-500">{variant.note}</p>
              </article>
            ))}
          </div>
        </div>
      </div>
    </div>
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
