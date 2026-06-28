import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ItemRecord, RunBundle } from "../types";
import { Badge, SectionTitle } from "./ui";

type Filter = "all" | "errors" | "a-vs-c";

export default function ItemInspector({ run }: { run: RunBundle }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<string | null>(null);

  const items = run.items.filter((it) => {
    if (filter === "errors") return !it.correct;
    if (filter === "a-vs-c") return it.pairing === "A-vs-C";
    return true;
  });

  return (
    <div className="flex flex-col gap-6">
      <SectionTitle
        title="Item Inspector"
        subtitle="Every held-out judgment, including the cases where fluency or format tried to fool the judge."
      />

      <div className="flex items-center gap-2">
        {(["all", "errors", "a-vs-c"] as Filter[]).map((f) => (
          <button key={f} onClick={() => setFilter(f)} className={`btn ${filter === f ? "btn-accent" : ""}`}>
            {f === "all" ? "All" : f === "errors" ? "Errors only" : "A-vs-C only"}
          </button>
        ))}
        <span className="ml-auto text-sm text-fog-400">{items.length} items</span>
      </div>

      <div className="panel divide-y divide-ink-600/60">
        <div className="grid grid-cols-[1.4fr_1fr_auto_auto] gap-3 px-4 py-2.5 text-[11px] font-medium uppercase tracking-wider text-fog-400">
          <span>Task type · id</span>
          <span>Verdict</span>
          <span>Margin</span>
          <span>Result</span>
        </div>
        {items.map((it) => (
          <Row key={it.item_id} it={it} open={open === it.item_id} onToggle={() => setOpen(open === it.item_id ? null : it.item_id)} />
        ))}
      </div>
    </div>
  );
}

function Row({ it, open, onToggle }: { it: ItemRecord; open: boolean; onToggle: () => void }) {
  return (
    <div>
      <button onClick={onToggle} className="grid w-full grid-cols-[1.4fr_1fr_auto_auto] items-center gap-3 px-4 py-3 text-left hover:bg-ink-700/40">
        <span className="flex items-center gap-2 text-sm">
          {open ? <ChevronDown size={14} className="text-fog-400" /> : <ChevronRight size={14} className="text-fog-400" />}
          <span className="text-fog-100">{it.task_type}</span>
          <span className="font-mono text-xs text-fog-500">{it.pairing}</span>
        </span>
        <span><Badge tone="neutral">picked {it.verdict}</Badge></span>
        <span className="font-mono text-sm text-fog-300">{it.margin}</span>
        <span>{it.correct ? <Badge tone="good">correct</Badge> : <Badge tone="bad">wrong</Badge>}</span>
      </button>
      {open && (
        <div className="space-y-3 bg-ink-900/40 px-6 py-4 text-sm">
          <Field label="System prompt" value={it.system_prompt} mono />
          <Field label="Question" value={it.question} />
          <div className="grid gap-3 md:grid-cols-2">
            <Answer side="A" text={it.answer_a} picked={it.verdict === "A"} />
            <Answer side="B" text={it.answer_b} picked={it.verdict === "B"} />
          </div>
          <Field label="Judge rationale" value={it.rationale} />
          {it.fooled_by && (
            <Badge tone={it.correct ? "accent" : "bad"}>
              {it.correct ? "resisted" : "fooled by"} {it.fooled_by}
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <span className="label">{label}</span>
      <p className={`mt-1 text-fog-200 ${mono ? "font-mono text-[13px]" : ""}`}>{value}</p>
    </div>
  );
}

function Answer({ side, text, picked }: { side: string; text: string; picked: boolean }) {
  return (
    <div className={`rounded-lg border p-3 ${picked ? "border-accent/40 bg-accent/5" : "border-ink-600 bg-ink-800/60"}`}>
      <div className="mb-1 flex items-center justify-between">
        <span className="label">Answer {side}</span>
        {picked && <Badge tone="accent">judge picked</Badge>}
      </div>
      <p className="whitespace-pre-line text-fog-200">{text}</p>
    </div>
  );
}
