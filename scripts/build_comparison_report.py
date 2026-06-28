"""Build a per-item comparison report of two judge variants ($0 — uses saved records).

Joins the benchmark sample (questions + correct/incorrect answers) with the
per-item judgment records each variant logged, then renders an HTML table + CSV
sorted so the items where the improved judge CHANGED the outcome (fixed / broke)
come first — each with both judges' verdicts and rationales, so you can see where
and why the improved judge differs.

Run: python scripts/build_comparison_report.py
"""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "judy/data/datasets/llmbar_adversarial_100.jsonl"
RUNS = ROOT / "runs"
V0_FILE = RUNS / "records_V0-baseline-vanilla.jsonl"
V1_FILE = RUNS / "records_V1-structured-rubric.jsonl"
HTML_OUT = RUNS / "comparison_report.html"
CSV_OUT = RUNS / "comparison_report.csv"

# verdict "A" = picked the correct (chosen) answer; "B" = picked the distractor.
CATEGORIES = {
    ("wrong", "right"): ("fixed", "#10391f"),    # V1 fixed a V0 mistake
    ("right", "wrong"): ("broke", "#3d1620"),     # V1 broke a V0 success
    ("wrong", "wrong"): ("both-wrong", "#332a12"),
    ("right", "right"): ("both-right", "#161b25"),
}
ORDER = {"fixed": 0, "broke": 1, "both-wrong": 2, "both-right": 3}


def _load_records(path: Path) -> dict[str, dict]:
    """item_id -> the canonical (swap=False) judgment record."""
    out: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r["swap"]:
            out[r["item_id"]] = r
    return out


def _load_sample() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for line in SAMPLE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["id"]] = row
    return out


def build_rows() -> list[dict]:
    items, v0, v1 = _load_sample(), _load_records(V0_FILE), _load_records(V1_FILE)
    rows = []
    for item_id, item in items.items():
        a, b = v0.get(item_id), v1.get(item_id)
        if not a or not b:
            continue
        s0 = "right" if a["correct"] else "wrong"
        s1 = "right" if b["correct"] else "wrong"
        cat, color = CATEGORIES[(s0, s1)]
        rows.append({
            "item_id": item_id,
            "subset": item["subset"],
            "question": item["question"],
            "correct_answer": item["chosen"],
            "distractor": item["rejected"],
            "v0_correct": a["correct"], "v0_rationale": a["rationale"],
            "v1_correct": b["correct"], "v1_rationale": b["rationale"],
            "category": cat, "_color": color,
        })
    rows.sort(key=lambda r: ORDER[r["category"]])
    return rows


def _esc(s: str, n: int = 600) -> str:
    s = s if len(s) <= n else s[:n] + "…"
    return html.escape(s)


def render_html(rows: list[dict]) -> str:
    counts = {c: sum(1 for r in rows if r["category"] == c) for c in ORDER}
    summary = " · ".join(f"{c}: {counts[c]}" for c in ORDER)
    cells = []
    for r in rows:
        v0 = "✓" if r["v0_correct"] else "✗"
        v1 = "✓" if r["v1_correct"] else "✗"
        cells.append(f"""
        <tr style="background:{r['_color']}">
          <td><span class="cat">{r['category']}</span><br><span class="sub">{html.escape(r['subset'])}</span></td>
          <td class="q">{_esc(r['question'], 400)}</td>
          <td class="ans"><b>correct:</b> {_esc(r['correct_answer'], 300)}<br><b class="dim">distractor:</b> <span class="dim">{_esc(r['distractor'], 300)}</span></td>
          <td class="v {'ok' if r['v0_correct'] else 'no'}">{v0}<div class="rat">{_esc(r['v0_rationale'], 220)}</div></td>
          <td class="v {'ok' if r['v1_correct'] else 'no'}">{v1}<div class="rat">{_esc(r['v1_rationale'], 220)}</div></td>
        </tr>""")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Judge comparison</title>
<style>
 body{{background:#0a0c10;color:#d4dae3;font:14px/1.5 system-ui,sans-serif;margin:24px}}
 h1{{font-size:18px}} .summary{{color:#8b96a8;margin-bottom:16px}}
 table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #1f2632;padding:10px;vertical-align:top;text-align:left}}
 th{{position:sticky;top:0;background:#0f1219;font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:#8b96a8}}
 .cat{{font-weight:600}} .sub{{color:#8b96a8;font-size:12px}} .q{{max-width:280px}} .ans{{max-width:360px;font-size:13px}}
 .dim{{color:#8b96a8}} .v{{text-align:center;font-size:18px;width:220px}} .v.ok{{color:#34d399}} .v.no{{color:#fb7185}}
 .rat{{font-size:12px;color:#aab4c4;text-align:left;margin-top:6px}}
</style></head><body>
<h1>Judge comparison — V0 baseline-vanilla vs V1 structured-rubric (100 adversarial LLMBar items)</h1>
<div class="summary">{summary} &nbsp;|&nbsp; ✓ = picked the correct answer. Rows sorted: fixed (V1 wins) → broke (V1 regressions) → both-wrong → both-right.</div>
<table><thead><tr><th>Category · subset</th><th>Question</th><th>Answers</th><th>V0</th><th>V1</th></tr></thead>
<tbody>{''.join(cells)}</tbody></table></body></html>"""


def main() -> None:
    rows = build_rows()
    HTML_OUT.write_text(render_html(rows), encoding="utf-8")
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "subset", "category", "v0_correct", "v1_correct",
                    "question", "v0_rationale", "v1_rationale"])
        for r in rows:
            w.writerow([r["item_id"], r["subset"], r["category"], r["v0_correct"],
                        r["v1_correct"], r["question"], r["v0_rationale"], r["v1_rationale"]])
    counts = {c: sum(1 for r in rows if r["category"] == c) for c in ORDER}
    print("Per-item comparison:", " · ".join(f"{c}={counts[c]}" for c in ORDER))
    print(f"HTML -> {HTML_OUT}")
    print(f"CSV  -> {CSV_OUT}")


if __name__ == "__main__":
    main()
