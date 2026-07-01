"""Diagnostic: evaluate base vs SFT-tuned judge IN THE FORMAT THE MODEL WAS TRAINED ON.

The standard eval (`scripts/eval_tuned_judge.py`) scores the tuned model with
`build_user_prompt` + the SKILL.md policy + JSON output. But the SFT model was
trained on `build_sft_prompt` with a BARE-LETTER target and no policy. That
train/serve skew makes the standard eval an unfair test of what SFT actually
learned.

This script evals in the **training format**: `build_sft_prompt` → plain-text
generation → parse the first A/B letter. Run it alongside the JSON eval to tell
apart "SFT learned something the JSON eval hid" from "SFT genuinely didn't help".

No retraining needed. Requires the tuned model to be reachable (Vertex endpoint +
local gcloud ADC) — run it on the machine where you tuned.

Run:
  PYTHONPATH=. python scripts/eval_sft_format.py \
    --tuned-model projects/<p>/locations/us-central1/endpoints/<id>
"""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from judy.config import CONFIG
from judy.eval.synthetic import load_synthetic_objective_items
from judy.judge.schema import JudgeRecord
from judy.metrics.metrics import compute_metrics
from judy.tuning.export import build_sft_prompt

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover
    genai = None

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = REPO_ROOT / "judy/data/datasets/judy_benchmark_objective_test_100_full.jsonl"
_ENDPOINT_RE = re.compile(r"^projects/(?P<project>[^/]+)/locations/(?P<location>[^/]+)/endpoints/")
_LETTER_RE = re.compile(r"\b([AB])\b")


def _make_client(model: str, *, vertex_project: str | None = None, vertex_location: str | None = None):
    """Vertex client for a tuned endpoint (or base-via-Vertex), else API-key Gemini."""
    m = _ENDPOINT_RE.match(model)
    if m:
        return genai.Client(vertexai=True, project=m.group("project"), location=m.group("location"))
    if vertex_project and vertex_location:  # route the base model through Vertex (ADC, no API key)
        return genai.Client(vertexai=True, project=vertex_project, location=vertex_location)
    return genai.Client(api_key=CONFIG.gemini_api_key)


def _parse_letter(text: str) -> str:
    """Pull the verdict letter from a bare-letter completion; default 'A'."""
    m = _LETTER_RE.search((text or "").upper())
    if m:
        return m.group(1)
    for ch in (text or "").upper():
        if ch in ("A", "B"):
            return ch
    return "A"


def _judge_one(client, model: str, item, swap: bool) -> JudgeRecord:
    a_idx, b_idx = (1, 0) if swap else (0, 1)
    prompt = build_sft_prompt(
        item.system_prompt, item.question,
        item.candidates[a_idx].text, item.candidates[b_idx].text,
    )
    resp = client.models.generate_content(
        model=model, contents=prompt,
        config=genai_types.GenerateContentConfig(temperature=0.0),  # plain text, no JSON, no policy
    )
    presented = _parse_letter(resp.text or "")
    canonical = presented if not swap else ("B" if presented == "A" else "A")
    return JudgeRecord(item_id=item.id, task_type=item.task_type, swap=swap,
                       verdict=canonical, margin=3, rationale="", correct=item.is_correct(canonical))


def _eval_model(label: str, model: str, items, *, workers: int,
                vertex_project: str | None = None, vertex_location: str | None = None) -> dict:
    client = _make_client(model, vertex_project=vertex_project, vertex_location=vertex_location)
    tasks = [(item, swap) for item in items for swap in (False, True)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(lambda t: _judge_one(client, model, t[0], t[1]), tasks))
    m = compute_metrics(records)
    print(f"[{label}] {model}")
    print(f"  agreement {m.agreement:.1%} | position-consistency "
          f"{(m.position_consistency or 0):.1%} | pos-consistent agreement "
          f"{(m.position_consistent_agreement or 0):.1%}")
    return {"label": label, "model": model, "overall": m.model_dump()}


def main() -> None:
    if genai is None:
        raise SystemExit("google-genai not installed.")
    p = argparse.ArgumentParser(description="Eval base vs tuned judge in the SFT (bare-letter) format.")
    p.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    p.add_argument("--base-model", default=CONFIG.model)
    p.add_argument("--tuned-model", help="Vertex endpoint resource; omit to eval base only.")
    p.add_argument("--limit", type=int, help="evaluate only the first N items (smoke test)")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--skip-base", action="store_true", help="eval only the tuned model")
    p.add_argument("--base-via-vertex", action="store_true",
                   help="route the base model through Vertex ADC (no Gemini API key needed)")
    p.add_argument("--out", type=Path, default=CONFIG.runs_dir / "sft_format_eval.json")
    args = p.parse_args()

    items = load_synthetic_objective_items(args.dataset)
    if args.limit:
        items = items[: args.limit]
    print(f"=== SFT-format eval (build_sft_prompt + bare letter) on {len(items)} items ===")

    # Infer Vertex project/location from the tuned endpoint so base can also use ADC.
    ep = _ENDPOINT_RE.match(args.tuned_model or "")
    vproj = ep.group("project") if (ep and args.base_via_vertex) else None
    vloc = ep.group("location") if (ep and args.base_via_vertex) else None

    variants = []
    if not args.skip_base:
        variants.append(_eval_model("base", args.base_model, items, workers=args.workers,
                                    vertex_project=vproj, vertex_location=vloc))
    if args.tuned_model:
        variants.append(_eval_model("tuned", args.tuned_model, items, workers=args.workers))
    if len(variants) == 2:
        b, t = variants[0]["overall"], variants[1]["overall"]
        print(f"[delta tuned-base] agreement {(t['agreement']-b['agreement'])*100:+.1f} pp")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"dataset": str(args.dataset), "format": "sft_bare_letter",
                                    "variants": variants}, indent=2), encoding="utf-8")
    print(f"Saved -> {args.out}")


if __name__ == "__main__":
    main()
