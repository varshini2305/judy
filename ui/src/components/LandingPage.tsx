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
    title: "Judge the actual task, not just the vibe",
    body:
      "Judy evaluates answers against the real system prompt, question, constraints, and formatting requirements. The goal is not generic answer ranking. The goal is spec-aware evaluation.",
  },
  {
    icon: Sparkles,
    title: "Improve through policy rewriting first",
    body:
      "The current system improves by rewriting the judging policy after analyzing failures. That keeps the method legible, cheap to iterate on, and easier to audit than jumping directly to weight updates.",
  },
  {
    icon: Shield,
    title: "Separate real improvement from self-delusion",
    body:
      "Judy compares anchored learning against unanchored self-critique. If a judge only agrees with itself more, that is not enough. The system is built to show when self-improvement is real and when it is just drift.",
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

const WHAT_WORKED = [
  "Policy rewriting is a fast, legible way to improve a judge without retraining.",
  "Held-out evaluation and benchmark grounding keep the narrative honest.",
  "The judge is weakest where fluent wrong answers disguise failure, which is exactly the useful pressure point.",
];

const WHAT_DIDNT = [
  "A single baseline number is misleading when easy subsets are saturated.",
  "Pure self-critique without an external anchor is not trustworthy enough to be the whole story.",
  "The UI shipped before the live API, so the product story outran the real data wiring.",
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
              Judy is building a judge that can learn from its failures, not just score answers once.
            </h1>
            <p className="mt-4 max-w-4xl text-base leading-7 text-fog-300 md:text-lg">
              The project starts from a simple question: can an LLM-as-a-judge become
              more reliable if it evaluates its own mistakes, rewrites how it judges,
              and proves the gains on held-out tasks and external benchmarks? The long-term
              vision is a judge-and-jury system where multiple evaluators bring different
              perspectives instead of trusting a single model opinion.
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-4">
            <Stat label="Core demo" value="anchored vs. unanchored learning" />
            <Stat label="Current baseline" value="88.6% on a 35-item RewardBench sample" />
            <Stat label="Important caveat" value="hard subsets still fall to chance" />
            <Stat label="Execution mode" value="policy rewrite first, tuning next" />
          </div>

          <div className="grid gap-3 md:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-2xl border border-ink-600/70 bg-ink-900/45 p-4">
              <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">
                Why this matters
              </div>
              <p className="text-sm leading-6 text-fog-300">
                Many judge systems look strong on average while failing exactly on the
                cases that matter most: adversarial, safety-sensitive, or spec-heavy
                prompts where fluency hides wrongness. Judy is trying to push the frontier
                from “a model that scores” toward “a system that learns how to evaluate.”
              </p>
            </div>
            <div className="rounded-2xl border border-ink-600/70 bg-ink-900/45 p-4">
              <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">
                Where the product is today
              </div>
              <p className="text-sm leading-6 text-fog-300">
                The UI is currently a product shell on mock data. The evaluation method,
                benchmark framing, and judge-improvement strategy are real; the remaining
                gap is live backend connectivity and final benchmark-backed claims.
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
              body="Turn LLM-as-a-judge from a static evaluator into a learning system. The long-term destination is a judge-and-jury architecture where multiple evaluators can disagree, challenge each other, and reduce the bias of any one model."
            />
            <NarrativeBlock
              title="Execution"
              body="Start at the cheapest and most legible point on the improvement spectrum: context engineering, explicit evaluation policy, held-out measurement, and benchmark comparisons. Use that as the reference point before moving into weight updates, grounding, and multi-judge systems."
            />
            <NarrativeBlock
              title="What's next"
              body="Short-term work includes live API wiring, stronger bias probes, benchmark depth on hard subsets, Gemini tuning baselines, and selective grounding on uncertain items. The roadmap is intentionally changing fast as implementation reality catches up to the vision."
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
              detail="RewardBench 35-item sample with Gemini 3.5 Flash and order-swap enabled."
            />
            <SignalCard
              label="Why that is not enough"
              value="easy subsets saturate"
              detail="Several subsets hit 100%, which hides the actual room for improvement."
            />
            <SignalCard
              label="Useful pressure point"
              value="50% on llmbar-adver-neighbor"
              detail="Adversarial fluent-but-wrong cases are where the baseline breaks and where Judy needs to get stronger."
            />
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
            <h2 className="text-lg font-semibold text-fog-100">What did not work yet</h2>
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
