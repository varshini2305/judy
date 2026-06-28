import { useState } from "react";
import { Gavel, Loader2, Sparkles } from "lucide-react";
import { Badge, SectionTitle } from "./ui";

type JudgeMode = "pairwise" | "pointwise";

interface PairwiseResult {
  verdict: "A" | "B";
  margin: number;
  rationale: string;
  criteria: { name: string; winner: "A" | "B" | "tie" }[];
}
interface PointwiseResult {
  verdict: "pass" | "fail";
  score: number;
  rationale: string;
  criteria: { name: string; met: boolean }[];
}

// Mock judging until the live API is wired. Shapes match the planned backend.
const MOCK_PAIRWISE: PairwiseResult = {
  verdict: "B",
  margin: 4,
  rationale: "B obeys the exact three-bullet, no-preamble format; A adds prohibited preamble.",
  criteria: [
    { name: "exactly three bullets", winner: "B" },
    { name: "no preamble", winner: "B" },
    { name: "factual accuracy", winner: "tie" },
  ],
};
const MOCK_POINTWISE: PointwiseResult = {
  verdict: "fail",
  score: 2,
  rationale: "Correct unit but omits the required calculation step.",
  criteria: [
    { name: "uses km not miles", met: true },
    { name: "shows one calculation step", met: false },
    { name: "rounded to one decimal", met: true },
  ],
};

export default function TryJudy() {
  const [mode, setMode] = useState<JudgeMode>("pairwise");
  const [busy, setBusy] = useState(false);
  const [pair, setPair] = useState<PairwiseResult | null>(null);
  const [point, setPoint] = useState<PointwiseResult | null>(null);

  function judge() {
    setBusy(true);
    setTimeout(() => {
      if (mode === "pairwise") setPair(MOCK_PAIRWISE);
      else setPoint(MOCK_POINTWISE);
      setBusy(false);
    }, 650);
  }

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Try Judy"
        subtitle="Judge live, with Judy's current policy. Compare two answers, or evaluate one on its own merits."
      />

      <div className="flex items-center gap-2">
        {(["pairwise", "pointwise"] as JudgeMode[]).map((m) => (
          <button key={m} onClick={() => setMode(m)} className={`btn ${mode === m ? "btn-accent" : ""}`}>
            {m === "pairwise" ? "Compare two (pairwise)" : "Evaluate one (pointwise)"}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Inputs */}
        <div className="panel panel-pad flex flex-col gap-3">
          <Input label="System prompt" placeholder="Reply as exactly three bullet points. No preamble." rows={3} />
          <Input label="Question" placeholder="Give three tips for better sleep." rows={2} />
          {mode === "pairwise" ? (
            <>
              <Input label="Answer A" placeholder="Sure! Here are some great tips: ..." rows={3} />
              <Input label="Answer B" placeholder="- Keep a schedule\n- Avoid screens\n- Limit caffeine" rows={3} />
            </>
          ) : (
            <Input label="Answer" placeholder="3.2 miles is about 5.1 kilometers." rows={4} />
          )}
          <div className="mt-1 flex items-center gap-2">
            <button onClick={judge} disabled={busy} className="btn btn-accent">
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Gavel size={15} />}
              {busy ? "Judging…" : "Judge"}
            </button>
            <button disabled className="btn group relative" title="Coming in v2">
              <Sparkles size={15} /> Ground with Antigravity →
              <span className="absolute -top-7 left-1/2 hidden -translate-x-1/2 rounded bg-ink-700 px-2 py-1 text-xs text-fog-300 group-hover:block">
                coming in v2
              </span>
            </button>
          </div>
        </div>

        {/* Verdict */}
        <div className="panel panel-pad">
          <span className="label">Verdict</span>
          {mode === "pairwise" ? (
            pair ? <PairwiseView r={pair} /> : <Empty />
          ) : point ? (
            <PointwiseView r={point} />
          ) : (
            <Empty />
          )}
        </div>
      </div>
    </div>
  );
}

function Empty() {
  return <p className="mt-6 text-center text-sm text-fog-500">Run a judgment to see Judy's verdict.</p>;
}

function PairwiseView({ r }: { r: PairwiseResult }) {
  return (
    <div className="mt-3 flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <span className="font-mono text-3xl font-semibold text-fog-100">{r.verdict}</span>
        <Badge tone="accent">margin {r.margin}/5</Badge>
      </div>
      <p className="text-sm text-fog-200">{r.rationale}</p>
      <div className="flex flex-col gap-1.5">
        {r.criteria.map((c, i) => (
          <div key={i} className="flex items-center justify-between rounded-md bg-ink-700/50 px-3 py-1.5 text-sm">
            <span className="text-fog-300">{c.name}</span>
            <Badge tone={c.winner === "tie" ? "neutral" : "accent"}>{c.winner}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function PointwiseView({ r }: { r: PointwiseResult }) {
  return (
    <div className="mt-3 flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Badge tone={r.verdict === "pass" ? "good" : "bad"}>{r.verdict.toUpperCase()}</Badge>
        <span className="font-mono text-2xl font-semibold text-fog-100">{r.score}/5</span>
      </div>
      <p className="text-sm text-fog-200">{r.rationale}</p>
      <div className="flex flex-col gap-1.5">
        {r.criteria.map((c, i) => (
          <div key={i} className="flex items-center justify-between rounded-md bg-ink-700/50 px-3 py-1.5 text-sm">
            <span className="text-fog-300">{c.name}</span>
            <Badge tone={c.met ? "good" : "bad"}>{c.met ? "met" : "unmet"}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}

function Input({ label, placeholder, rows }: { label: string; placeholder: string; rows: number }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="label">{label}</span>
      <textarea
        rows={rows}
        placeholder={placeholder}
        className="resize-none rounded-lg border border-ink-600 bg-ink-900/60 px-3 py-2 text-sm text-fog-100 placeholder:text-fog-500 focus:border-accent/50 focus:outline-none"
      />
    </label>
  );
}
