"""Prepare a Gemini SFT launch bundle from a local Judy SFT dataset directory.

This script does not submit the tuning job itself. It writes:
- a resolved GCS layout for train/val/test JSONL
- shell commands to upload the bundle
- a JSON request stub you can adapt for the current Vertex / Agent Platform API

That keeps the repo-side setup deterministic while the exact cloud submission
surface can evolve independently.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_DIR = (
    REPO_ROOT / "judy" / "tuning_datasets" / "sft" / "gemini35-flash" / "judy_benchmark_v1"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Gemini SFT upload and request assets.")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--bucket-uri", required=True, help="Example: gs://judy-tuning-us")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--region", default="us-central1")
    parser.add_argument("--base-model", default="gemini-3.5-flash")
    parser.add_argument("--tuned-model-name", default="judy-judge-sft-v1")
    args = parser.parse_args()

    dataset_dir = args.dataset_dir.resolve()
    for filename in ("train.jsonl", "val.jsonl", "test.jsonl", "metadata.json"):
        path = dataset_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing required file: {path}")

    out_dir = dataset_dir / "cloud_prepare"
    out_dir.mkdir(parents=True, exist_ok=True)
    vertex_train = out_dir / "vertex_train.jsonl"
    vertex_val = out_dir / "vertex_val.jsonl"
    vertex_test = out_dir / "vertex_test.jsonl"
    _render_vertex_dataset(dataset_dir / "train.jsonl", vertex_train)
    _render_vertex_dataset(dataset_dir / "val.jsonl", vertex_val)
    _render_vertex_dataset(dataset_dir / "test.jsonl", vertex_test)

    gcs_prefix = f"{args.bucket_uri.rstrip('/')}/sft/gemini35-flash/{args.tuned_model_name}"
    request_stub = {
        "display_name": args.tuned_model_name,
        "base_model": args.base_model,
        "project_id": args.project_id,
        "region": args.region,
        "training_data": {
            "train_uri": f"{gcs_prefix}/vertex_train.jsonl",
            "validation_uri": f"{gcs_prefix}/vertex_val.jsonl",
            "test_uri": f"{gcs_prefix}/vertex_test.jsonl",
            "metadata_uri": f"{gcs_prefix}/metadata.json",
        },
        "notes": [
            "upload the local dataset bundle to the URIs above before job submission",
            "vertex_{train,val,test}.jsonl are rendered from Judy's internal rows into Gemini tuning format",
            "after tuning completes, pass the tuned model resource into scripts/eval_tuned_judge.py",
        ],
    }

    (out_dir / "request_stub.json").write_text(json.dumps(request_stub, indent=2), encoding="utf-8")

    upload_lines = [
        f"gcloud auth application-default login",
        f"gcloud config set project {args.project_id}",
        f"gcloud storage cp {vertex_train} {gcs_prefix}/vertex_train.jsonl",
        f"gcloud storage cp {vertex_val} {gcs_prefix}/vertex_val.jsonl",
        f"gcloud storage cp {vertex_test} {gcs_prefix}/vertex_test.jsonl",
        f"gcloud storage cp {dataset_dir / 'metadata.json'} {gcs_prefix}/metadata.json",
    ]
    (out_dir / "upload_commands.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n" + "\n".join(upload_lines) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote cloud prep assets to {out_dir}")
    print(json.dumps(request_stub, indent=2))


def _render_vertex_dataset(src: Path, dst: Path) -> None:
    rows = []
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rows.append(
            {
                "systemInstruction": {
                    "parts": [
                        {
                            "text": "You are a question-answering judge. Return only which answer is better: A or B."
                        }
                    ]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": row["prompt"]
                            }
                        ],
                    },
                    {
                        "role": "model",
                        "parts": [
                            {
                                "text": row["target"]
                            }
                        ],
                    },
                ],
            }
        )
    with dst.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=True) + "\n")


if __name__ == "__main__":
    main()
