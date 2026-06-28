import {
  AlertTriangle,
  ArrowRight,
  Compass,
  Gavel,
  Layers3,
  LineChart,
  Scale,
  Shield,
  Sparkles,
  Target,
} from "lucide-react";
import { Badge } from "./ui";

type Props = {
  onOpenControlRoom: () => void;
  onOpenTryJudy: () => void;
};

const EXECUTION_PILLARS = [
  {
    icon: Gavel,
    title: "Judge the task, not the vibe",
    body:
      "Judy evaluates answers against the actual prompt, constraints, and format requirements. It is built for spec-aware evaluation, not generic answer ranking.",
  },
  {
    icon: Sparkles,
    title: "Improve the evaluator itself",
    body:
      "The first improvement loop is policy rewriting: Judy studies failures, updates how it judges, and tests whether those changes really generalize.",
  },
  {
    icon: Shield,
    title: "Separate learning from drift",
    body:
      "Anchored learning is measured against external signal. Unanchored self-critique is tracked as a contrast arm. More self-consistency alone does not count as progress.",
  },
] as const;

const CHALLENGES = [
  {
    name: "Fluency bias",
    problem: "A polished answer can still be wrong or spec-violating.",
    response: "Judy emphasizes correctness and constraint compliance before stylistic smoothness.",
  },
  {
    name: "Position bias",
    problem: "Judges often change verdicts when answer order changes.",
    response: "Order-swap checks are part of the evaluation protocol and tracked in the metrics.",
  },
  {
    name: "Benchmark saturation",
    problem: "Easy subsets make a baseline look stronger than it really is.",
    response: "Judy focuses attention on adversarial and hard subsets where there is actual headroom.",
  },
  {
    name: "Circular self-improvement",
    problem: "A judge can look more consistent without becoming more correct.",
    response: "Anchored vs. unanchored comparisons make that failure mode visible instead of hiding it.",
  },
] as const;

const IDEAS = [
  {
    title: "Built now",
    items: [
      "Self-rewriting judge policy with held-out evaluation",
      "Pairwise judging as the headline mode",
      "Pointwise judging as a second capability",
      "RewardBench and JudgeBench baseline tracks",
    ],
  },
  {
    title: "Exploring next",
    items: [
      "Weight-update baselines with Gemini tuning",
      "Bias probes for position, verbosity, formatting, and identity",
      "Selective grounding on uncertain or claim-heavy items",
      "Preference-learning and personalized evaluation",
    ],
  },
  {
    title: "Frontier direction",
    items: [
      "Judge-and-jury deliberation with diverse evaluators",
      "Reliability-weighted aggregation across judges",
      "Experience sharing between juror agents",
      "Recursive self-improvement beyond prompt-only methods",
    ],
  },
] as const;

const METHODS_TRIED = [
  {
    title: "Vanilla judge baseline",
    body:
      "One generic prompt, one verdict, no rubric, no memory, no structured bias checks.",
  },
  {
    title: "Policy rewriting loop",
    body:
      "The current core method: inspect failures, rewrite the judge policy, then re-run held-out evaluation.",
  },
  {
    title: "Unanchored self-critique",
    body:
      "A contrast arm that reflects only on the judge's own outputs. Useful for exposing drift, but not strong enough to stand as proof.",
  },
  {
    title: "Weight-update track",
    body:
      "A parallel path with Gemini tuning to test whether modest model updates beat or complement policy-only improvement.",
  },
] as const;

const PROOF_POINTS = [
  "Can Judy beat a vanilla LLM-as-a-judge on hard subsets, not just on easy averages?",
  "Can policy updates improve held-out performance instead of only increasing internal consistency?",
  "Can the system reduce common judge failures like fluency bias and position bias in a measurable way?",
  "Can future methods like tuning, grounding, and jury-style deliberation outperform the prompt-only baseline cleanly?",
];

const WHAT_WORKED = [
  "Policy rewriting is fast, legible, and cheap to iterate on.",
  "Held-out evaluation and benchmark grounding keep the story honest.",
  "The weakest cases are also the most useful ones: fluent wrong answers, adversarial prompts, and strict spec-following tasks.",
];

const WHAT_DIDNT = [
  "A single average benchmark number hides where the judge is actually weak.",
  "Pure self-critique without an anchor is too easy to mistake for learning.",
  "The UI story moved faster than the live backend integration.",
];

export default function LandingPage({ onOpenControlRoom, onOpenTryJudy }: Props) {
  return (
    <div className="flex flex-col gap-8">
      <section className="relative overflow-hidden rounded-[30px] border border-ink-600/70 bg-ink-800/90 px-6 py-8 shadow-[0_35px_90px_rgba(0,0,0,0.3)] md:px-8 md:py-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(52,211,153,0.14),transparent_28%),radial-gradient(circle_at_top_right,rgba(124,156,255,0.18),transparent_32%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent)]" />
        <div className="relative flex flex-col gap-6">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="accent">Judy</Badge>
            <Badge tone="neutral">LLM-as-a-judge</Badge>
            <Badge tone="neutral">recursive self-improvement</Badge>
            <Badge tone="neutral">mock UI, real backend next</Badge>
          </div>

          <div className="max-w-5xl">
            <h1 className="max-w-4xl text-4xl font-semibold tracking-tight text-fog-100 md:text-5xl">
              Judy is a self-learning system of judges and juries.
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-fog-300 md:text-lg">
              A self-improving evaluation system built to learn from failures, benchmark
              its progress, and grow from a single judge into structured deliberation.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <Stat label="Core demo" value="anchored vs. unanchored learning" />
            <Stat label="Current baseline" value="88.6% on a 35-item RewardBench sample" />
            <Stat label="Important caveat" value="hard subsets still fall to chance" />
            <Stat label="Execution mode" value="policy rewrite now, tuning next" />
          </div>

          <div className="grid gap-3 md:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-ink-600/70 bg-ink-900/45 p-4">
              <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">
                Why this matters
              </div>
              <p className="text-sm leading-6 text-fog-300">
                Many judge systems look good on averages and break on the cases that matter:
                adversarial prompts, safety-sensitive tasks, and strict instruction-following
                settings where polished answers can still be wrong. Judy is trying to move the
                frontier from one-off scoring to evaluator improvement.
              </p>
            </div>
            <div className="rounded-2xl border border-ink-600/70 bg-ink-900/45 p-4">
              <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">
                Where the product is today
              </div>
              <p className="text-sm leading-6 text-fog-300">
                The evaluation logic and benchmark framing are real. The current gap is that
                the UI still carries mock-backed product scaffolding while the live backend and
                direct run artifacts are being wired in.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button onClick={onOpenControlRoom} className="btn btn-accent">
              Open the system view <ArrowRight size={15} />
            </button>
            <button onClick={onOpenTryJudy} className="btn">
              Try the judge <Scale size={15} />
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {EXECUTION_PILLARS.map(({ icon: Icon, title, body }) => (
          <article key={title} className="panel panel-pad flex flex-col gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/12 text-accent">
              <Icon size={18} />
            </span>
            <h2 className="text-lg font-semibold text-fog-100">{title}</h2>
            <p className="text-sm leading-6 text-fog-300">{body}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Compass size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">Vision, execution, and what is next</h2>
          </div>
          <div className="grid gap-4">
            <NarrativeBlock
              title="Vision"
              body="Turn LLM-as-a-judge from a static evaluator into a learning system. The destination is a judge-and-jury architecture where multiple evaluators can disagree, challenge each other, and reduce the bias of any single model."
            />
            <NarrativeBlock
              title="Implementation"
              body="Start with the cheapest, clearest improvement loop: explicit judge policy, held-out measurement, and benchmark comparison. Use that as the reference point before moving into tuning, grounding, and multi-judge systems."
            />
            <NarrativeBlock
              title="What's next"
              body="Next comes live API wiring, stronger bias probes, deeper hard-subset benchmarking, Gemini tuning baselines, and selective grounding on uncertain items. The roadmap is moving quickly because the system is still actively taking shape."
            />
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <LineChart size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">Latest baseline story</h2>
          </div>
          <div className="flex flex-col gap-3">
            <SignalCard
              label="Headline number"
              value="88.6% agreement"
              detail="RewardBench 35-item sample, Gemini 3.5 Flash, with order-swap enabled."
            />
            <SignalCard
              label="Why that is not enough"
              value="easy subsets saturate"
              detail="Several subsets hit 100%, which makes the average look stronger than the real challenge."
            />
            <SignalCard
              label="Useful pressure point"
              value="50% on llmbar-adver-neighbor"
              detail="Adversarial fluent-but-wrong cases are where the baseline breaks and where Judy has real room to improve."
            />
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Layers3 size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">Methods tried and being explored</h2>
          </div>
          <div className="grid gap-3">
            {METHODS_TRIED.map((method) => (
              <NarrativeBlock key={method.title} title={method.title} body={method.body} />
            ))}
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Target size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">What Judy is trying to prove</h2>
          </div>
          <div className="flex flex-col gap-3">
            {PROOF_POINTS.map((item) => (
              <Bullet key={item} text={item} tone="good" />
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <AlertTriangle size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">Common judge failures and Judy's response</h2>
          </div>
          <div className="flex flex-col gap-3">
            {CHALLENGES.map((challenge) => (
              <div key={challenge.name} className="rounded-xl border border-ink-600/60 bg-ink-900/35 p-4">
                <div className="mb-1 text-sm font-semibold text-fog-100">{challenge.name}</div>
                <p className="text-sm leading-6 text-fog-400">
                  <span className="text-fog-300">Limitation:</span> {challenge.problem}
                </p>
                <p className="mt-2 text-sm leading-6 text-fog-400">
                  <span className="text-fog-300">Judy response:</span> {challenge.response}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-5 flex items-center gap-2">
            <Layers3 size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">Ideas in play across the stack</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {IDEAS.map((group) => (
              <div key={group.title} className="rounded-xl border border-ink-600/60 bg-ink-900/35 p-4">
                <div className="mb-3 text-sm font-semibold text-fog-100">{group.title}</div>
                <div className="flex flex-col gap-2">
                  {group.items.map((item) => (
                    <div key={item} className="text-sm leading-6 text-fog-300">
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Target size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">What worked</h2>
          </div>
          <div className="flex flex-col gap-3">
            {WHAT_WORKED.map((item) => (
              <Bullet key={item} text={item} tone="good" />
            ))}
          </div>
        </div>

        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Shield size={16} className="text-accent" />
            <h2 className="text-lg font-semibold text-fog-100">What is still weak or incomplete</h2>
          </div>
          <div className="flex flex-col gap-3">
            {WHAT_DIDNT.map((item) => (
              <Bullet key={item} text={item} tone="warn" />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/45 px-4 py-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-2 text-sm font-semibold leading-6 text-fog-100">{value}</div>
    </div>
  );
}

function NarrativeBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-ink-600/60 bg-ink-900/35 p-4">
      <div className="mb-1 text-sm font-semibold text-fog-100">{title}</div>
      <p className="text-sm leading-6 text-fog-300">{body}</p>
    </div>
  );
}

function SignalCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="rounded-xl border border-ink-600/60 bg-ink-900/35 p-4">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-2 text-sm font-semibold text-fog-100">{value}</div>
      <p className="mt-2 text-sm leading-6 text-fog-300">{detail}</p>
    </div>
  );
}

function Bullet({ text, tone }: { text: string; tone: "good" | "warn" }) {
  return (
    <div className="rounded-xl border border-ink-600/60 bg-ink-900/35 px-4 py-3 text-sm leading-6 text-fog-300">
      <span className={tone === "good" ? "text-good" : "text-accent"}>● </span>
      {text}
    </div>
  );
}
