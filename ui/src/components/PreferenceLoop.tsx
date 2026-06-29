import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCcw, Scale, Server, Sparkles } from "lucide-react";
import { Badge, MetricCard, SectionTitle } from "./ui";

type FeedbackMode = "best" | "ranking" | "score";

interface PreferencePair {
  index: number;
  answer_a: string;
  answer_b: string;
  task_type: string;
  remaining: number;
  done?: boolean;
}

interface RecentEvent {
  case_id: string;
  feedback_mode: FeedbackMode;
  selected: "A" | "B" | null;
  score_a?: number | null;
  score_b?: number | null;
  confidence: number;
  summary: string;
  note: string;
  loop_ready: Record<string, unknown>;
}

interface PreferenceState {
  inferred_preference: string;
  confidence: number;
  weights: Record<string, number>;
  n_feedback: number;
  feedback_modes_seen: FeedbackMode[];
  recent_events: RecentEvent[];
}

interface PreferenceFeedbackResult {
  you_chose: "A" | "B" | null;
  judy_predicted: "A" | "B";
  was_correct: boolean;
  inferred_preference: string;
  confidence: number;
  n_feedback: number;
  feedback_mode: FeedbackMode;
  feedback_summary: string;
  loop_ready: Record<string, unknown>;
}

interface LoopReadyResponse {
  events: Array<Record<string, unknown>>;
  how_to_use: string[];
}

interface SimulationResult {
  method: "winner_only" | "weighted_feedback" | "note_aware";
  description: string;
  train_events: number;
  eval_events: number;
  baseline_accuracy: number;
  final_accuracy: number;
  delta_pp: number;
  curve: Array<{ after: number; accuracy: number }>;
  top_hypothesis: string;
  top_weight: number;
  feedback_modes: string[];
}

interface SimulationResponse {
  train_events: number;
  eval_events: number;
  results: SimulationResult[];
  best_method: string;
  best_delta_pp: number;
  summary: string;
}

async function readResponseBody(response: Response): Promise<string> {
  try {
    return await response.text();
  } catch {
    return "";
  }
}

function buildApiError(path: string, response: Response, body: string): Error {
  const contentType = response.headers.get("content-type") ?? "";
  const trimmed = body.trim();

  if (contentType.includes("text/html") || trimmed.startsWith("<!doctype") || trimmed.startsWith("<html")) {
    return new Error(
      `API route ${path} returned HTML instead of JSON (${response.status} ${response.statusText}). ` +
      "The frontend is likely serving its SPA fallback for /api, which usually means the backend proxy is not configured or not reachable."
    );
  }

  if (!response.ok) {
    const detail = trimmed ? ` Response: ${trimmed.slice(0, 200)}` : "";
    return new Error(`API route ${path} failed (${response.status} ${response.statusText}).${detail}`);
  }

  return new Error(`API route ${path} did not return valid JSON.`);
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = await readResponseBody(response);

  if (!response.ok) {
    throw buildApiError(path, response, body);
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("text/html") || body.trim().startsWith("<!doctype") || body.trim().startsWith("<html")) {
    throw buildApiError(path, response, body);
  }

  try {
    return JSON.parse(body) as T;
  } catch {
    throw buildApiError(path, response, body);
  }
}

export default function PreferenceLoop() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [pair, setPair] = useState<PreferencePair | null>(null);
  const [state, setState] = useState<PreferenceState | null>(null);
  const [lastResult, setLastResult] = useState<PreferenceFeedbackResult | null>(null);
  const [loopReady, setLoopReady] = useState<LoopReadyResponse | null>(null);
  const [simulation, setSimulation] = useState<SimulationResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<FeedbackMode>("best");
  const [rankingChoice, setRankingChoice] = useState<"A>B" | "B>A">("A>B");
  const [scoreA, setScoreA] = useState<number>(4);
  const [scoreB, setScoreB] = useState<number>(3);
  const [note, setNote] = useState("");

  useEffect(() => {
    void initialize();
  }, []);

  async function initialize() {
    setBusy(true);
    setError(null);
    try {
      const [, stateJson, nextJson, loopReadyJson] = await Promise.all([
        fetchJson<Record<string, unknown>>("/api/health"),
        fetchJson<PreferenceState>("/api/preference/state"),
        fetchJson<PreferencePair>("/api/preference/next"),
        fetchJson<LoopReadyResponse>("/api/preference/loop-ready"),
      ]);

      setConnected(true);
      setState(stateJson);
      setPair(nextJson.done ? null : nextJson);
      setLoopReady(loopReadyJson);
    } catch (loadError) {
      setConnected(false);
      setError(loadError instanceof Error ? loadError.message : "Unknown backend error");
    } finally {
      setBusy(false);
    }
  }

  async function refreshAfterFeedback(feedbackJson: PreferenceFeedbackResult) {
    const [stateJson, nextJson, loopReadyJson] = await Promise.all([
      fetchJson<PreferenceState>("/api/preference/state"),
      fetchJson<PreferencePair>("/api/preference/next"),
      fetchJson<LoopReadyResponse>("/api/preference/loop-ready"),
    ]);

    setLastResult(feedbackJson);
    setState(stateJson);
    setPair(nextJson.done ? null : nextJson);
    setLoopReady(loopReadyJson);
    setNote("");
  }

  async function submitFeedback(payload: Record<string, unknown>) {
    if (!pair) return;
    setBusy(true);
    setError(null);
    try {
      const feedbackJson = await fetchJson<PreferenceFeedbackResult>("/api/preference/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index: pair.index, note, ...payload }),
      });
      await refreshAfterFeedback(feedbackJson);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unknown feedback error");
    } finally {
      setBusy(false);
    }
  }

  async function resetLoop() {
    setBusy(true);
    setError(null);
    try {
      await fetchJson<{ ok: true }>("/api/preference/reset", { method: "POST" });
      setLastResult(null);
      setSimulation(null);
      await initialize();
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unknown reset error");
      setBusy(false);
    }
  }

  const weightEntries = Object.entries(state?.weights ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const latestLoopReady = useMemo(() => {
    const events = loopReady?.events ?? [];
    return events.length ? events[events.length - 1] : null;
  }, [loopReady]);
  const bestSimulation = useMemo(
    () =>
      simulation?.results.reduce((best, result) =>
        result.final_accuracy > best.final_accuracy ? result : best,
      simulation.results[0]),
    [simulation],
  );

  async function runSimulation() {
    setBusy(true);
    setError(null);
    try {
      let body: SimulationResponse;
      try {
        body = await fetchJson<SimulationResponse>("/api/preference/simulate-run");
      } catch (error) {
        if (error instanceof Error && error.message.includes("(400 Bad Request)")) {
          throw new Error("Need at least 4 labeled feedback events before a simulation can run.");
        }
        throw error;
      }
      setSimulation(body);
    } catch (simulationError) {
      setError(simulationError instanceof Error ? simulationError.message : "Unknown simulation error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Preference Learning"
        subtitle="This page turns user feedback into training signal. First collect preferences, then inspect what Judy inferred, and finally see how those signals can drive a recursive improvement loop."
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard
          label="Backend"
          value={connected === null ? "..." : connected ? "live" : "offline"}
          hint={connected ? "FastAPI preference-learning backend connected" : "requires /api backend"}
        />
        <MetricCard
          label="Feedback received"
          value={`${state?.n_feedback ?? 0}`}
          hint="all preference signals in this session"
        />
        <MetricCard
          label="Top preference"
          value={state?.inferred_preference ?? "—"}
          hint="current inferred hypothesis"
        />
        <MetricCard
          label="Modes seen"
          value={`${state?.feedback_modes_seen.length ?? 0}`}
          hint={(state?.feedback_modes_seen ?? []).join(", ") || "no feedback yet"}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <GuideCard
          title="1. Give feedback"
          body="Choose which answer is better, rank them, or score them independently. You can also leave a short note explaining why."
        />
        <GuideCard
          title="2. Watch Judy infer a pattern"
          body="As feedback accumulates, Judy builds a lightweight preference hypothesis and feature weights that summarize what seems to matter to the user."
        />
        <GuideCard
          title="3. Reuse it as learning signal"
          body="Those labeled events can then be replayed as training data for preference-aware evaluators and recursive self-improvement experiments."
        />
      </div>

      <div className="panel panel-pad">
        <div className="mb-4 flex items-center gap-2">
          <Sparkles size={16} className="text-accent" />
          <h3 className="text-base font-semibold text-fog-100">Replay the loop end to end</h3>
        </div>
        <p className="text-sm leading-6 text-fog-300">
          This takes collected feedback, treats part of it as learning data, and measures whether later held-out user-labeled events are predicted better after replay. It is the bridge between raw user feedback and a visible self-improvement result.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <button onClick={() => void runSimulation()} disabled={busy} className="btn btn-accent">
            <Sparkles size={15} /> Run improvement simulation
          </button>
          {simulation && (
            <>
              <Badge tone="neutral">train events: {simulation.train_events}</Badge>
              <Badge tone="neutral">eval events: {simulation.eval_events}</Badge>
              <Badge tone="good">best method: {simulation.best_method}</Badge>
            </>
          )}
        </div>

        {simulation && bestSimulation && (
          <div className="mt-5 grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="grid gap-3">
              {simulation.results.map((result) => (
                <article key={result.method} className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={result.method === simulation.best_method ? "good" : "accent"}>
                      {result.method}
                    </Badge>
                    <span className="text-sm font-semibold text-fog-100">
                      {result.method === "winner_only"
                        ? "Winner-only replay"
                        : result.method === "weighted_feedback"
                          ? "Weighted feedback replay"
                          : "Note-aware replay"}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-fog-300">{result.description}</p>
                  <div className="mt-3 grid gap-2 md:grid-cols-2">
                    <SimulationStat label="Before" value={`${Math.round(result.baseline_accuracy * 100)}%`} />
                    <SimulationStat label="After" value={`${Math.round(result.final_accuracy * 100)}%`} />
                    <SimulationStat label="Delta" value={`${result.delta_pp > 0 ? "+" : ""}${result.delta_pp}pp`} />
                    <SimulationStat label="Top learned rule" value={result.top_hypothesis} />
                  </div>
                </article>
              ))}
            </div>

            <div className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
              <div className="mb-3 text-sm font-semibold text-fog-100">Held-out improvement curve</div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={bestSimulation.curve.map((point) => ({
                      after: point.after,
                      accuracy: +(point.accuracy * 100).toFixed(1),
                    }))}
                    margin={{ top: 8, right: 16, bottom: 4, left: -8 }}
                  >
                    <CartesianGrid stroke="#1f2632" vertical={false} />
                    <XAxis dataKey="after" stroke="#8b96a8" tickLine={false} axisLine={false} fontSize={12} />
                    <YAxis
                      stroke="#8b96a8"
                      tickLine={false}
                      axisLine={false}
                      fontSize={12}
                      domain={[0, 100]}
                      tickFormatter={(value) => `${value}%`}
                    />
                    <Tooltip
                      contentStyle={{ background: "#0f1219", border: "1px solid #1f2632", borderRadius: 10, fontSize: 12 }}
                      formatter={(value: number) => [`${value}%`, "held-out accuracy"]}
                    />
                    <Line
                      type="monotone"
                      dataKey="accuracy"
                      stroke="#34d399"
                      strokeWidth={2.5}
                      dot={{ r: 3, fill: "#34d399" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-3 text-xs leading-5 text-fog-500">{simulation.summary}</p>
            </div>
          </div>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Scale size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Collect preference data</h3>
          </div>
          <p className="mb-4 text-sm leading-6 text-fog-300">
            The interaction model is simple: compare two answers, choose a feedback mode, and optionally explain your reasoning. Judy records the result as structured preference supervision.
          </p>

          {error && (
            <div className="mb-4 rounded-xl border border-bad/30 bg-bad/10 p-3 text-sm text-fog-200">
              {error}
            </div>
          )}

          {!connected && (
            <div className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4 text-sm leading-6 text-fog-300">
              This tab needs the FastAPI backend running with the UI. Locally, the Vite dev server proxies
              `/api` to `http://localhost:8000`. On static hosting, this will stay unavailable until the backend
              is deployed alongside the UI.
            </div>
          )}

          {connected && !pair && !busy && (
            <div className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4 text-sm leading-6 text-fog-300">
              This session is out of pairs. Reset the loop to start a fresh round of preference learning.
            </div>
          )}

          {connected && pair && (
            <>
              <div className="mb-4 flex flex-wrap items-center gap-2">
                <Badge tone="neutral">task: {pair.task_type}</Badge>
                <Badge tone="neutral">remaining: {pair.remaining}</Badge>
                <Badge tone="accent">session learning active</Badge>
              </div>

              <div className="mb-4 flex flex-wrap gap-2">
                {(["best", "ranking", "score"] as FeedbackMode[]).map((option) => (
                  <button
                    key={option}
                    onClick={() => setMode(option)}
                    className={`btn ${mode === option ? "btn-accent" : ""}`}
                  >
                    {option === "best" ? "Best response" : option === "ranking" ? "Rank order" : "Absolute score"}
                  </button>
                ))}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <AnswerPanel side="A" text={pair.answer_a} />
                <AnswerPanel side="B" text={pair.answer_b} />
              </div>

              <div className="mt-4 rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
                <div className="mb-3 text-sm font-medium text-fog-100">Choose a feedback mode</div>
                {mode === "best" && (
                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => void submitFeedback({ feedback_mode: "best", chosen: "A" })}
                      disabled={busy}
                      className="btn btn-accent"
                    >
                      Pick A
                    </button>
                    <button
                      onClick={() => void submitFeedback({ feedback_mode: "best", chosen: "B" })}
                      disabled={busy}
                      className="btn btn-accent"
                    >
                      Pick B
                    </button>
                  </div>
                )}

                {mode === "ranking" && (
                  <div className="space-y-3">
                    <div className="flex flex-wrap gap-3">
                      <button
                        onClick={() => setRankingChoice("A>B")}
                        className={`btn ${rankingChoice === "A>B" ? "btn-accent" : ""}`}
                      >
                        A &gt; B
                      </button>
                      <button
                        onClick={() => setRankingChoice("B>A")}
                        className={`btn ${rankingChoice === "B>A" ? "btn-accent" : ""}`}
                      >
                        B &gt; A
                      </button>
                    </div>
                    <button
                      onClick={() =>
                        void submitFeedback({
                          feedback_mode: "ranking",
                          ranking: rankingChoice === "A>B" ? ["A", "B"] : ["B", "A"],
                        })
                      }
                      disabled={busy}
                      className="btn btn-accent"
                    >
                      Submit ranking
                    </button>
                  </div>
                )}

                {mode === "score" && (
                  <div className="space-y-4">
                    <div className="grid gap-4 md:grid-cols-2">
                      <ScoreInput label="Score A" value={scoreA} onChange={setScoreA} />
                      <ScoreInput label="Score B" value={scoreB} onChange={setScoreB} />
                    </div>
                    <button
                      onClick={() => void submitFeedback({ feedback_mode: "score", score_a: scoreA, score_b: scoreB })}
                      disabled={busy}
                      className="btn btn-accent"
                    >
                      Submit scores
                    </button>
                  </div>
                )}

                <label className="mt-4 flex flex-col gap-2">
                  <span className="label">Optional note for the recursive learner</span>
                  <textarea
                    rows={3}
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="Why was one answer better? This note can later be summarized into task-general lessons."
                    className="resize-none rounded-lg border border-ink-600 bg-ink-900/60 px-3 py-2 text-sm text-fog-100 placeholder:text-fog-500 focus:border-accent/50 focus:outline-none"
                  />
                </label>
              </div>
            </>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <div className="panel panel-pad">
            <div className="mb-4 flex items-center gap-2">
              <Sparkles size={16} className="text-accent" />
              <h3 className="text-base font-semibold text-fog-100">What Judy currently infers</h3>
            </div>
            <div className="space-y-3">
              <div>
                <div className="label">Current preference hypothesis</div>
                <p className="mt-1 text-sm leading-6 text-fog-200">
                  {state?.inferred_preference ?? "No stable preference inferred yet."}
                </p>
              </div>
              <div>
                <div className="label">Feature weights</div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {weightEntries.length ? (
                    weightEntries.map(([name, value]) => (
                      <Badge key={name} tone="neutral">
                        {name}: {value > 0 ? "+" : ""}
                        {value.toFixed(2)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-fog-500">No weights yet.</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="panel panel-pad">
            <div className="mb-4 flex items-center gap-2">
              <Server size={16} className="text-accent" />
              <h3 className="text-base font-semibold text-fog-100">How feedback becomes training signal</h3>
            </div>
            {lastResult ? (
              <div className="space-y-3 text-sm leading-6 text-fog-300">
                <p>{lastResult.feedback_summary}.</p>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={lastResult.was_correct ? "good" : "bad"}>
                    {lastResult.was_correct ? "prediction matched" : "prediction missed"}
                  </Badge>
                  <Badge tone="neutral">confidence {Math.round(lastResult.confidence * 100)}%</Badge>
                  <Badge tone="neutral">mode {lastResult.feedback_mode}</Badge>
                </div>
              </div>
            ) : (
              <p className="text-sm leading-6 text-fog-300">
                Submit preference data and Judy will normalize it into loop-ready training events.
              </p>
            )}

            <div className="mt-4 rounded-xl border border-ink-600/70 bg-ink-900/35 p-3">
              <div className="label">Latest normalized event</div>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs leading-5 text-fog-300">
                {latestLoopReady ? JSON.stringify(latestLoopReady, null, 2) : "No loop-ready event yet."}
              </pre>
            </div>

            <div className="mt-4">
              <div className="label">How this feeds recursive improvement</div>
              <ul className="mt-2 space-y-2 text-sm leading-6 text-fog-300">
                {(loopReady?.how_to_use ?? []).map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </div>

            <button onClick={() => void resetLoop()} disabled={busy} className="btn mt-4">
              <RefreshCcw size={15} /> Reset session
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function GuideCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-2 text-[11px] uppercase tracking-[0.18em] text-fog-500">{title}</div>
      <p className="text-sm leading-6 text-fog-300">{body}</p>
    </div>
  );
}

function AnswerPanel({ side, text }: { side: "A" | "B"; text: string }) {
  return (
    <div className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="label">Answer {side}</span>
      </div>
      <p className="whitespace-pre-line text-sm leading-6 text-fog-200">{text}</p>
    </div>
  );
}

function SimulationStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-600/60 bg-ink-800/45 px-3 py-2">
      <div className="text-[11px] uppercase tracking-[0.18em] text-fog-500">{label}</div>
      <div className="mt-1 text-sm text-fog-200">{value}</div>
    </div>
  );
}

function ScoreInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="label">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="rounded-lg border border-ink-600 bg-ink-900/60 px-3 py-2 text-sm text-fog-100 focus:border-accent/50 focus:outline-none"
      >
        {[1, 2, 3, 4, 5].map((score) => (
          <option key={score} value={score}>
            {score}
          </option>
        ))}
      </select>
    </label>
  );
}
