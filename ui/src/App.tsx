import { useEffect, useState } from "react";
import {
  FlaskConical,
  Gavel,
  Home,
  LayoutDashboard,
  LineChart,
} from "lucide-react";
import LandingPage from "./components/LandingPage";
import LearningCurve from "./components/LearningCurve";
import VariantDashboard from "./components/VariantDashboard";
import TuningTrack from "./components/TuningTrack";
import { Badge } from "./components/ui";
import type { ExperimentData, SftEvalData } from "./types";

const TABS = [
  { id: "home", label: "Overview", icon: Home },
  { id: "variants", label: "Variants", icon: LayoutDashboard },
  { id: "curve", label: "Learning Curve", icon: LineChart },
  { id: "tuning", label: "Tuning", icon: FlaskConical },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("home");
  const [experiments, setExperiments] = useState<ExperimentData | null>(null);
  const [sft, setSft] = useState<SftEvalData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [experimentsResponse, sftResponse] = await Promise.all([
          fetch("/experiments.json"),
          fetch("/sft/judy_sft_v20_eval.json"),
        ]);

        if (!experimentsResponse.ok || !sftResponse.ok) {
          throw new Error("Failed to load UI experiment artifacts.");
        }

        const [experimentsJson, sftJson] = await Promise.all([
          experimentsResponse.json() as Promise<ExperimentData>,
          sftResponse.json() as Promise<SftEvalData>,
        ]);

        if (!cancelled) {
          setExperiments(experimentsJson);
          setSft(sftJson);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown loading error");
        }
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
  }, []);

  const ready = experiments && sft;

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-6">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <Gavel size={18} />
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-fog-100">Judy</h1>
            <p className="text-xs text-fog-400">self-learning system of judge and juries</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Badge tone="accent">Gemini 3.5 Flash</Badge>
          <Badge tone="neutral">real benchmark artifacts</Badge>
          <Badge tone="neutral">Railway UI</Badge>
        </div>
      </header>

      <nav className="mb-8 flex gap-1 rounded-xl border border-ink-600/70 bg-ink-800/60 p-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
              tab === id ? "bg-ink-600 text-fog-100" : "text-fog-400 hover:text-fog-200"
            }`}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </nav>

      <main className="flex-1">
        {!ready ? (
          <div className="panel panel-pad">
            <h2 className="text-lg font-semibold text-fog-100">{error ? "Data load failed" : "Loading results"}</h2>
            <p className="mt-2 text-sm leading-6 text-fog-300">
              {error
                ? error
                : "Fetching the latest experiment artifacts packaged with this UI so the dashboard reflects real runs instead of static placeholders."}
            </p>
          </div>
        ) : (
          <>
            {tab === "home" && (
              <LandingPage
                experiments={experiments}
                sft={sft}
                onOpenVariants={() => setTab("variants")}
                onOpenCurve={() => setTab("curve")}
                onOpenTuning={() => setTab("tuning")}
              />
            )}
            {tab === "variants" && <VariantDashboard experiments={experiments} />}
            {tab === "curve" && <LearningCurve />}
            {tab === "tuning" && <TuningTrack sft={sft} />}
          </>
        )}
      </main>

      <footer className="mt-10 border-t border-ink-600/50 pt-4 text-center text-xs text-fog-500">
        Judy · benchmarked judge improvement · context learning + tuning track + jury direction
      </footer>
    </div>
  );
}
