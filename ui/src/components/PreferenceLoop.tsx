import { useEffect, useState } from "react";
import { RefreshCcw, Scale, Server, Sparkles } from "lucide-react";
import { Badge, MetricCard, SectionTitle } from "./ui";

interface PreferencePair {
  index: number;
  answer_a: string;
  answer_b: string;
  task_type: string;
  remaining: number;
  done?: boolean;
}

interface PreferenceState {
  inferred_preference: string;
  confidence: number;
  weights: Record<string, number>;
  n_feedback: number;
}

interface PreferenceFeedbackResult {
  you_chose: "A" | "B";
  judy_predicted: "A" | "B";
  was_correct: boolean;
  inferred_preference: string;
  confidence: number;
  n_feedback: number;
}

export default function PreferenceLoop() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [pair, setPair] = useState<PreferencePair | null>(null);
  const [state, setState] = useState<PreferenceState | null>(null);
  const [lastResult, setLastResult] = useState<PreferenceFeedbackResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void initialize();
  }, []);

  async function initialize() {
    setBusy(true);
    setError(null);
    try {
      const [healthResponse, stateResponse, nextResponse] = await Promise.all([
        fetch("/api/health"),
        fetch("/api/preference/state"),
        fetch("/api/preference/next"),
      ]);

      if (!healthResponse.ok || !stateResponse.ok || !nextResponse.ok) {
        throw new Error("Preference backend is not reachable from this UI.");
      }

      const [, stateJson, nextJson] = await Promise.all([
        healthResponse.json(),
        stateResponse.json() as Promise<PreferenceState>,
        nextResponse.json() as Promise<PreferencePair>,
      ]);

      setConnected(true);
      setState(stateJson);
      setPair(nextJson.done ? null : nextJson);
    } catch (loadError) {
      setConnected(false);
      setError(loadError instanceof Error ? loadError.message : "Unknown backend error");
    } finally {
      setBusy(false);
    }
  }

  async function submitChoice(chosen: "A" | "B") {
    if (!pair) return;
    setBusy(true);
    setError(null);
    try {
      const feedbackResponse = await fetch("/api/preference/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ index: pair.index, chosen }),
      });
      if (!feedbackResponse.ok) {
        throw new Error("Failed to record preference feedback.");
      }

      const feedbackJson = (await feedbackResponse.json()) as PreferenceFeedbackResult;
      const [stateResponse, nextResponse] = await Promise.all([
        fetch("/api/preference/state"),
        fetch("/api/preference/next"),
      ]);
      if (!stateResponse.ok || !nextResponse.ok) {
        throw new Error("Saved feedback, but failed to refresh the preference loop.");
      }

      const [stateJson, nextJson] = await Promise.all([
        stateResponse.json() as Promise<PreferenceState>,
        nextResponse.json() as Promise<PreferencePair>,
      ]);

      setLastResult(feedbackJson);
      setState(stateJson);
      setPair(nextJson.done ? null : nextJson);
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
      const resetResponse = await fetch("/api/preference/reset", { method: "POST" });
      if (!resetResponse.ok) {
        throw new Error("Failed to reset preference session.");
      }
      setLastResult(null);
      await initialize();
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unknown reset error");
      setBusy(false);
    }
  }

  const weightEntries = Object.entries(state?.weights ?? {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Preference Loop"
        subtitle="A separate, backend-backed tab for user preference learning. Judy serves answer pairs, observes your picks, and updates its evaluator profile continuously within the session."
      />

      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard
          label="Backend"
          value={connected === null ? "..." : connected ? "live" : "offline"}
          hint={connected ? "FastAPI preference loop connected" : "requires /api backend"}
        />
        <MetricCard
          label="Feedback received"
          value={`${state?.n_feedback ?? 0}`}
          hint="pairwise choices in this session"
        />
        <MetricCard
          label="Top preference"
          value={state?.inferred_preference ?? "—"}
          hint="current inferred hypothesis"
        />
        <MetricCard
          label="Confidence"
          value={state ? `${Math.round(state.confidence * 100)}%` : "—"}
          hint="strength of current preference read"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="panel panel-pad">
          <div className="mb-4 flex items-center gap-2">
            <Scale size={16} className="text-accent" />
            <h3 className="text-base font-semibold text-fog-100">Rate the next pair</h3>
          </div>

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

              <div className="grid gap-4 md:grid-cols-2">
                <ChoiceCard
                  side="A"
                  text={pair.answer_a}
                  disabled={busy}
                  onChoose={() => void submitChoice("A")}
                />
                <ChoiceCard
                  side="B"
                  text={pair.answer_b}
                  disabled={busy}
                  onChoose={() => void submitChoice("B")}
                />
              </div>
            </>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <div className="panel panel-pad">
            <div className="mb-4 flex items-center gap-2">
              <Sparkles size={16} className="text-accent" />
              <h3 className="text-base font-semibold text-fog-100">What Judy has learned so far</h3>
            </div>
            <div className="space-y-3">
              <div>
                <div className="label">Current hypothesis</div>
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
              <h3 className="text-base font-semibold text-fog-100">Loop feedback</h3>
            </div>
            {lastResult ? (
              <div className="space-y-3 text-sm leading-6 text-fog-300">
                <p>
                  You chose <span className="font-medium text-fog-100">{lastResult.you_chose}</span>. Judy predicted{" "}
                  <span className="font-medium text-fog-100">{lastResult.judy_predicted}</span>.
                </p>
                <div className="flex flex-wrap gap-2">
                  <Badge tone={lastResult.was_correct ? "good" : "bad"}>
                    {lastResult.was_correct ? "prediction matched" : "prediction missed"}
                  </Badge>
                  <Badge tone="neutral">confidence {Math.round(lastResult.confidence * 100)}%</Badge>
                </div>
              </div>
            ) : (
              <p className="text-sm leading-6 text-fog-300">
                Submit a few pairwise choices and this panel will show whether Judy is starting to predict your
                preferences correctly.
              </p>
            )}
            <button onClick={() => void resetLoop()} disabled={busy} className="btn mt-4">
              <RefreshCcw size={15} /> Reset session
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChoiceCard({
  side,
  text,
  onChoose,
  disabled,
}: {
  side: "A" | "B";
  text: string;
  onChoose: () => void;
  disabled: boolean;
}) {
  return (
    <div className="rounded-xl border border-ink-600/70 bg-ink-900/35 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="label">Answer {side}</span>
        <button onClick={onChoose} disabled={disabled} className="btn btn-accent">
          Choose {side}
        </button>
      </div>
      <p className="whitespace-pre-line text-sm leading-6 text-fog-200">{text}</p>
    </div>
  );
}
