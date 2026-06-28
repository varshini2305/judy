import {
  ArrowRight,
  Compass,
  Database,
  Scale,
  Sparkles,
  Target,
} from "lucide-react";
import type { ExperimentData, SftEvalRun } from "../types";
import { Badge } from "./ui";

type Props = {
  experiments: ExperimentData;
  sftRuns: SftEvalRun[];
  onOpenVariants: () => void;
  onOpenCurve: () => void;
  onOpenTuning: () => void;
};

export default function LandingPage({
  experiments,
  sftRuns,
  onOpenVariants,
  onOpenCurve,
  onOpenTuning,
}: Props) {
  const firstSft = sftRuns.find((run) => run.sampleSize === 20)?.eval ?? sftRuns[0]?.eval;
  const baseline = experiments.variants.find((variant) => variant.id === "V0") ?? experiments.variants[0];
  const bestFinal = experiments.variants.reduce((best, variant) =>
    variant.agreement > best.agreement ? variant : best,
  experiments.variants[0]);
  const bestPeak = experiments.variants.reduce((best, variant) =>
    (variant.peak ?? variant.agreement) > (best.peak ?? best.agreement) ? variant : best,
  experiments.variants[0]);
  const bestConsistency = experiments.variants.reduce((best, variant) =>
    variant.pos_consistency > best.pos_consistency ? variant : best,
  experiments.variants[0]);
  const valueProps = [
    {
      title: "Evaluate answers more reliably",
      body: "Use a judge with an explicit rubric and bias checks instead of relying on a vague single-prompt verdict.",
    },
    {
      title: "Compare improvement methods",
      body: "See which changes help most: better policy design, self-critique, teacher guidance, or weight updates.",
    },
    {
      title: "Inspect real experimental evidence",
      body: "Every page is tied to benchmark artifacts, held-out tests, and variant-by-variant comparisons rather than demo-only claims.",
    },
  ];
  const appPath = [
    {
      step: "Start here",
      title: "Understand the system",
      body: "The overview explains what Judy is for, what has been tested, and what the current best results actually mean.",
    },
    {
      step: "Then open Variants",
      title: "Read the method story",
      body: "The variants page shows what changes from V0 to V5, what each variant learns from, and how much lift each one adds.",
    },
    {
      step: "Then inspect learning and tuning",
      title: "Check how improvement happens",
      body: "The learning-curve and tuning pages separate context-learning from weight updates so gains and regressions stay interpretable.",
    },
  ];

  return (
    <div className="flex flex-col gap-8">
      <section className="relative overflow-hidden rounded-[30px] border border-ink-600/70 bg-ink-800/90 px-6 py-8 shadow-[0_35px_90px_rgba(0,0,0,0.3)] md:px-8 md:py-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(52,211,153,0.14),transparent_28%),radial-gradient(circle_at_top_right,rgba(124,156,255,0.18),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent)]" />
        <div className="relative flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">Judy</Badge>
            <Badge tone="neutral">self-learning judge and jury system</Badge>
            <Badge tone="neutral">artifact-backed results</Badge>
          </div>

          <div className="max-w-5xl">
            <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-fog-100 md:text-5xl">
              <span className="font-bold italic text-fog-100">Judy</span>
              <span className="block whitespace-nowrap text-3xl text-fog-300 md:text-4xl">
                Self-learning system of Judge and Juries.
              </span>
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-fog-300 md:text-lg">
              Judy treats evaluation as a system, not a single prompt. It combines a judge, optional jurors, and multiple improvement tracks so evaluation can be benchmarked, compared, and improved rather than trusted blindly.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <Stat
              label="Baseline"
              value={`${(baseline.agreement * 100).toFixed(1)}%`}
              detail="V0 on LLMBar-Adversarial, 100 test items, order-swap on"
            />
            <Stat
              label="Best final"
              value={`${(bestFinal.agreement * 100).toFixed(1)}%`}
              detail={`${bestFinal.id} on the same 100-item adversarial test set`}
            />
            <Stat label="Best peak" value={`${((bestPeak.peak ?? bestPeak.agreement) * 100).toFixed(1)}%`} detail="teacher-driven with early stopping" />
            <Stat label="Best robustness" value={`${(bestConsistency.pos_consistency * 100).toFixed(1)}%`} detail={`${bestConsistency.id} under answer-order swap`} />
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            {valueProps.map((item) => (
              <QuickPoint key={item.title} title={item.title} body={item.body} />
            ))}
          </div>

          <div className="flex flex-wrap gap-3">
            <button onClick={onOpenVariants} className="btn btn-accent">
              View variants <ArrowRight size={15} />
            </button>
            <button onClick={onOpenCurve} className="btn">
              Inspect learning curve <Scale size={15} />
            </button>
            <button onClick={onOpenTuning} className="btn">
              Check tuning track <Sparkles size={15} />
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Compass size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">How to read this app</h2>
          </div>
          <div className="grid gap-4">
            {appPath.map((item) => (
              <NarrativeBlock key={item.title} title={item.step} heading={item.title} body={item.body} />
            ))}
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Target size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">What the current results say</h2>
          </div>
          <div className="space-y-4">
            <MiniBlock
              title="What already works"
              body="A stronger rubric improved the judge immediately. Continual self-critique improved robustness. Cross-family teaching produced the strongest peak result so far."
            />
            <MiniBlock
              title="What is still weak"
              body="Hand-written policies do not generalize everywhere. More learning can drift if it is not stopped well. The first 20-sample SFT run did not beat the untuned judge."
            />
            <MiniBlock
              title="What comes next"
              body={`The next test is whether larger tuned checkpoints, stronger stopping rules, or more diverse jurors can improve beyond the current ${((bestPeak.peak ?? bestPeak.agreement) * 100).toFixed(1)}% peak.`}
            />
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="panel panel-pad">
          <div className="mb-3 flex items-center gap-2 text-lg font-semibold text-fog-100">
            <Database size={16} className="text-accent" />
            <span>Experiment frame</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <SetupBox label="Shared judge" value={experiments.judge_model} />
            <SetupBox label="Main benchmark" value={experiments.benchmark} />
            <SetupBox label="Teacher in V5" value="gpt-5.4-nano" />
            <SetupBox label="Weight-update eval" value="synthetic held-out objective test set" />
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-3 text-lg font-semibold text-fog-100">Core takeaway</div>
          <p className="text-sm leading-6 text-fog-300">
            Judy is useful because it makes improvement methods legible. Policy design, self-critique, teacher-guided learning, and supervised tuning are all tested under a visible evaluation frame, so users can see what helped, what regressed, and what to try next.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <CompactResult
              label="Best context-learning result"
              value={`${((bestPeak.peak ?? bestPeak.agreement) * 100).toFixed(1)}% peak`}
              detail="teacher-driven learning"
            />
            <CompactResult
              label="First weight-update result"
              value={firstSft ? `${(firstSft.variants[0].overall.agreement * 100).toFixed(1)}% → ${(firstSft.variants[1].overall.agreement * 100).toFixed(1)}%` : "pending"}
              detail="20-sample SFT"
            />
          </div>
        </div>
      </section>
    </div>
  );
}

function QuickPoint({ title, body }: { title: string; body: string }) {
  return (
    <article className="rounded-2xl border border-ink-600/70 bg-ink-900/45 p-4">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">{title}</div>
      <p className="text-sm leading-6 text-fog-300">{body}</p>
    </article>
  );
}

function NarrativeBlock({ title, heading, body }: { title: string; heading: string; body: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">{title}</div>
      <div className="mb-2 text-sm font-semibold text-fog-100">{heading}</div>
      <p className="text-sm leading-6 text-fog-300">{body}</p>
    </div>
  );
}

function MiniBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">{title}</div>
      <p className="text-sm leading-6 text-fog-300">{body}</p>
    </div>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/40 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-fog-100">{value}</div>
      <div className="mt-1 text-sm text-fog-400">{detail}</div>
    </div>
  );
}

function SetupBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-2 text-sm leading-6 text-fog-200">{value}</div>
    </div>
  );
}

function CompactResult({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-2 text-lg font-semibold text-fog-100">{value}</div>
      <div className="mt-1 text-sm text-fog-400">{detail}</div>
    </div>
  );
}
