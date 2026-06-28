import { useState } from "react";
import { Gavel, Home, LayoutDashboard, ListTree, Scale, Wand2 } from "lucide-react";
import ControlRoom from "./components/ControlRoom";
import SkillEvolution from "./components/SkillEvolution";
import ItemInspector from "./components/ItemInspector";
import TryJudy from "./components/TryJudy";
import LandingPage from "./components/LandingPage";
import { MOCK_RUN } from "./mock/run";
import { Badge } from "./components/ui";

const TABS = [
  { id: "home", label: "Overview", icon: Home },
  { id: "control", label: "Control Room", icon: LayoutDashboard },
  { id: "skill", label: "Skill Evolution", icon: ListTree },
  { id: "items", label: "Item Inspector", icon: Scale },
  { id: "try", label: "Try Judy", icon: Wand2 },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("home");
  const run = MOCK_RUN;

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-6">
      {/* Header */}
      <header className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent/15 text-accent">
            <Gavel size={18} />
          </span>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-fog-100">Judy</h1>
            <p className="text-xs text-fog-400">a self-improving LLM-as-a-judge</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="accent">Gemini 3.5 Flash</Badge>
          <Badge tone="neutral">mock run</Badge>
        </div>
      </header>

      {/* Nav */}
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

      {/* Content */}
      <main className="flex-1">
        {tab === "home" && (
          <LandingPage
            onOpenControlRoom={() => setTab("control")}
            onOpenTryJudy={() => setTab("try")}
          />
        )}
        {tab === "control" && <ControlRoom run={run} />}
        {tab === "skill" && <SkillEvolution run={run} />}
        {tab === "items" && <ItemInspector run={run} />}
        {tab === "try" && <TryJudy />}
      </main>

      <footer className="mt-10 border-t border-ink-600/50 pt-4 text-center text-xs text-fog-500">
        Judy · iteration 1 · pairwise + pointwise judging · self-improvement via policy rewriting
      </footer>
    </div>
  );
}
