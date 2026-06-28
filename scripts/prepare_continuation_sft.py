"""Prepare an incremental SFT bundle for continuation tuning.

This takes two cumulative checkpoint exports, e.g. 60-case and 100-case train
bundles, and derives only the *new* training rows that appear in the larger
bundle after the smaller one. Validation and test splits are copied from the
larger bundle so evaluation stays aligned with the existing held-out set.

It also emits cloud-prep assets via ``scripts/run_gemini_sft.py`` so the new
bundle is ready for upload / submission.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PREV = REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash" / "judy_objective_checkpoint_60"
DEFAULT_FULL = REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash" / "judy_objective_checkpoint_100"
DEFAULT_OUT = REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash" / "judy_objective_continue_60_to_100"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a continuation SFT bundle from cumulative checkpoint exports.")
    parser.add_argument("--previous-dir", type=Path, default=DEFAULT_PREV)
    parser.add_argument("--full-dir", type=Path, default=DEFAULT_FULL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--bucket-uri", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--base-model", default="gemini-3.5-flash")
    parser.add_argument("--custom-base-model", required=True, help="Tuned model resource to continue from.")
    parser.add_argument("--tuned-model-name", default="judy-judge-sft-v100-cont-from-v60")
    args = parser.parse_args()

    prev_dir = args.previous_dir.resolve()
    full_dir = args.full_dir.resolve()
    out_dir = args.out_dir.resolve()

    prev_train = _load_lines(prev_dir / "train.jsonl")
    full_train = _load_lines(full_dir / "train.jsonl")
    if len(full_train) < len(prev_train):
        raise ValueError("full train bundle is smaller than previous bundle")
    if full_train[: len(prev_train)] != prev_train:
        raise ValueError(
            "full train bundle does not start with the previous bundle rows; cannot safely derive continuation tail"
        )

    tail_train = full_train[len(prev_train) :]
    if not tail_train:
        raise ValueError("no new train rows found between previous and full bundles")

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_lines(out_dir / "train.jsonl", tail_train)
    _copy(full_dir / "val.jsonl", out_dir / "val.jsonl")
    _copy(full_dir / "test.jsonl", out_dir / "test.jsonl")

    prev_meta = json.loads((prev_dir / "metadata.json").read_text(encoding="utf-8"))
    full_meta = json.loads((full_dir / "metadata.json").read_text(encoding="utf-8"))
    out_meta = {
        "base_model": args.base_model,
        "custom_base_model": args.custom_base_model,
        "task": full_meta.get("task"),
        "source": "judy_synthetic_objective_continuation",
        "previous_bundle": str(prev_dir),
        "full_bundle": str(full_dir),
        "continuation_range": {
            "from_checkpoint_size": prev_meta.get("checkpoint_size"),
            "to_checkpoint_size": full_meta.get("checkpoint_size"),
        },
        "counts": {
            "previous_train_rows": len(prev_train),
            "full_train_rows": len(full_train),
            "continuation_train_rows": len(tail_train),
            "continuation_train_cases": len(tail_train) // 2,
            "val_rows": _count_lines(out_dir / "val.jsonl"),
            "test_rows": _count_lines(out_dir / "test.jsonl"),
        },
        "notes": [
            "train.jsonl contains only the new rows that appear after the previous cumulative checkpoint",
            "val/test are copied from the larger checkpoint bundle to keep evaluation aligned",
            "prepared for continuation tuning from a previously tuned model resource",
            "local gcloud CLI on 2026-06-28 rejected --custom-base-model even though help text mentions it; direct API submission may be required",
        ],
    }
    (out_dir / "metadata.json").write_text(json.dumps(out_meta, indent=2), encoding="utf-8")

    cmd = [
        str((REPO_ROOT / ".venv" / "bin" / "python").resolve()),
        str((REPO_ROOT / "scripts" / "run_gemini_sft.py").resolve()),
        "--dataset-dir",
        str(out_dir),
        "--bucket-uri",
        args.bucket_uri,
        "--project-id",
        args.project_id,
        "--region",
        args.region,
        "--base-model",
        args.base_model,
        "--custom-base-model",
        args.custom_base_model,
        "--tuned-model-name",
        args.tuned_model_name,
    ]
    subprocess.run(cmd, check=True)

    print(json.dumps(out_meta, indent=2))
    print(f"\nPrepared continuation bundle -> {out_dir}")


def _load_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy(src: Path, dst: Path) -> None:
    dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def _count_lines(path: Path) -> int:
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


if __name__ == "__main__":
    main()
