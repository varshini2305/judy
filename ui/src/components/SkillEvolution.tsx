import { useState } from "react";
import ReactDiffViewer from "react-diff-viewer-continued";
import { GitCommitVertical } from "lucide-react";
import type { RunBundle } from "../types";
import { Badge, SectionTitle } from "./ui";

export default function SkillEvolution({ run }: { run: RunBundle }) {
  const skills = run.results.anchored.skills;
  const edits = run.results.anchored.edits;
  const [t, setT] = useState(Math.max(1, skills.length - 1));

  const before = skills[t - 1] ?? skills[0];
  const after = skills[t] ?? skills[skills.length - 1];
  const editAtT = edits.find((e) => e.iter === t);

  // All failure modes accumulated up to and including iteration t.
  const accumulated = edits
    .filter((e) => e.iter <= t)
    .flatMap((e) => e.failure_modes.map((fm) => ({ iter: e.iter, text: fm })));

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Skill Evolution"
        subtitle="Every reflection rewrites SKILL.md. This is the visible proof Judy is rewriting herself — in plain English."
      />

      {/* Iteration selector */}
      <div className="flex flex-wrap items-center gap-2">
        {skills.slice(1).map((_, i) => {
          const iter = i + 1;
          return (
            <button
              key={iter}
              onClick={() => setT(iter)}
              className={`btn ${t === iter ? "btn-accent" : ""}`}
            >
              <GitCommitVertical size={14} /> iter {iter - 1} → {iter}
            </button>
          );
        })}
        {editAtT && (
          <Badge tone="good">
            +{editAtT.failure_modes.length} failure mode
            {editAtT.failure_modes.length === 1 ? "" : "s"}
          </Badge>
        )}
      </div>

      {/* Diff */}
      <div className="panel overflow-hidden font-mono text-[13px]">
        <ReactDiffViewer
          oldValue={before}
          newValue={after}
          splitView={false}
          useDarkTheme
          hideLineNumbers
          styles={{
            variables: {
              dark: {
                diffViewerBackground: "#0f1219",
                addedBackground: "#0f3b2e55",
                addedColor: "#bef0d8",
                removedBackground: "#3d162055",
                wordAddedBackground: "#0f3b2e",
                gutterBackground: "#0f1219",
                emptyLineBackground: "#0f1219",
                codeFoldBackground: "#161b25",
              },
            },
          }}
        />
      </div>

      {/* Accumulated failure modes */}
      <div>
        <span className="label">Known failure modes Judy has learned</span>
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {accumulated.map((fm, i) => (
            <div key={i} className="panel panel-pad flex gap-3">
              <Badge tone="accent">iter {fm.iter}</Badge>
              <p className="text-sm text-fog-200">{fm.text}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
