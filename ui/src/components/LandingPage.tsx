import {
  ArrowRight,
  Compass,
  Database,
  Scale,
  Sparkles,
  Target,
} from "lucide-react";
import type { ExperimentData, SftEvalData } from "../types";
import { Badge } from "./ui";

type Props = {
  experiments: ExperimentData;
  sft: SftEvalData;
  onOpenVariants: () => void;
  onOpenCurve: () => void;
  onOpenTuning: () => void;
};

export default function LandingPage({
  experiments,
  sft,
  onOpenVariants,
  onOpenCurve,
  onOpenTuning,
}: Props) {
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
              <span className="block text-fog-300">Self-learning system of Judge and Juries.</span>
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-fog-300 md:text-lg">
              Judy treats evaluation as a system, not a single prompt. The judge defines the rubric and decision process. Jurors contribute independent perspectives. The goal is a clearer, more reliable evaluator that can be tested, improved, and eventually deliberated rather than trusted blindly.
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
            <QuickPoint
              title="Vision"
              body="Move from a static LLM judge to a learning evaluator that can revise its policy, compare methods, and eventually combine judge and jury signals."
            />
            <QuickPoint
              title="What is real here"
              body="This UI now shows artifact-backed results for V0, V1, V2, and V5 on LLMBar-Adversarial: a 100-item held-out test set with order-swap enabled, plus the first completed SFT evaluation."
            />
            <QuickPoint
              title="Why it matters"
              body="Many judges look good on easy averages and fail on adversarial or tightly constrained cases. Judy focuses on those failure modes directly."
            />
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
            <h2 className="text-lg font-semibold text-fog-100">How Judy works</h2>
          </div>
          <div className="grid gap-4">
            <NarrativeBlock
              title="1. Start with a judge"
              body="Gemini 3.5 Flash is the shared judge across the main benchmark variants. That keeps the model fixed so differences come from the method, not from swapping models."
            />
            <NarrativeBlock
              title="2. Change the evaluation method"
              body="V1 improves the judging policy by hand. V2 learns from self-critique on disjoint dev data. V5 adds a cross-family GPT teacher that writes better lessons when the judge gets an item wrong."
            />
            <NarrativeBlock
              title="3. Measure what changed"
              body="Each variant is tested on the same adversarial benchmark with answer-order swaps, replayable run artifacts, and comparable metrics. That makes the improvements inspectable instead of anecdotal."
            />
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Target size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">What the current results say</h2>
          </div>
          <div className="space-y-4">
            <MiniBlock
              title="Worked"
              body="A better starting policy helped immediately. Continual learning improved robustness. Cross-family teaching produced the strongest peak result."
            />
            <MiniBlock
              title="Limitations"
              body="Hand-written rubrics do not generalize everywhere. More learning can drift if it is not stopped well. The first 20-sample SFT run did not beat the untuned judge."
            />
            <MiniBlock
              title="Next"
              body={`The next step is to validate whether larger tuned checkpoints, stronger stopping rules, or more diverse jurors can improve beyond the current ${((bestPeak.peak ?? bestPeak.agreement) * 100).toFixed(1)}% peak.`}
            />
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="panel panel-pad">
          <div className="mb-3 flex items-center gap-2 text-lg font-semibold text-fog-100">
            <Database size={16} className="text-accent" />
            <span>Model and benchmark setup</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge tone="neutral">{experiments.judge_model}</Badge>
            <Badge tone="neutral">GPT teacher in V5: gpt-5.4-nano</Badge>
            <Badge tone="neutral">{experiments.benchmark}</Badge>
            <Badge tone="neutral">SFT eval: synthetic objective test set</Badge>
          </div>
          <p className="mt-4 text-sm leading-6 text-fog-300">
            The main comparison is grounded in one shared adversarial benchmark so every variant is directly comparable. The tuning page is separate because it changes model weights and is evaluated on a different held-out synthetic objective test set.
          </p>
        </div>

        <div className="panel panel-pad">
          <div className="mb-3 text-lg font-semibold text-fog-100">Why this is more than a prompt demo</div>
          <p className="text-sm leading-6 text-fog-300">
            Judy is trying multiple improvement paths under one evaluation frame: policy design, self-critique, teacher-guided learning, and supervised tuning. The important part is not claiming that every method works. It is making the gains, regressions, and tradeoffs visible enough to guide the next iteration.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge tone="neutral">SFT-20: {(sft.variants[0].overall.agreement * 100).toFixed(1)}% → {(sft.variants[1].overall.agreement * 100).toFixed(1)}%</Badge>
            <Badge tone="neutral">V5 peak: {((bestPeak.peak ?? bestPeak.agreement) * 100).toFixed(1)}%</Badge>
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

function NarrativeBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">{title}</div>
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
