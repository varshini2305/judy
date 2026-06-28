"""Plot a continual-learning run's held-out learning curve to a PNG.

Reads ``curve.json`` (list of {after, agreement}) from a run dir and renders
agreement vs. examples seen, annotating the peak and overlaying reference lines
for prior variants. Reusable for any continual run (V2, V5, ...).

Run: python scripts/plot_learning_curve.py [RUN_DIR]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

REFERENCES = {"V0 vanilla": 0.81, "V1 rubric": 0.855, "V2 self-critique": 0.86}


def plot(run_dir: Path) -> Path:
    curve = json.loads((run_dir / "curve.json").read_text())
    # dedupe consecutive duplicate x (the final checkpoint repeats the last x)
    pts: list[tuple[int, float]] = []
    for p in curve:
        if not pts or pts[-1][0] != p["after"]:
            pts.append((p["after"], p["agreement"]))
    xs = [x for x, _ in pts]
    ys = [y * 100 for _, y in pts]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(xs, ys, "-o", color="#2563eb", lw=2.5, ms=7, label="V5 teacher-driven", zorder=3)

    # peak annotation
    peak_i = max(range(len(ys)), key=lambda i: ys[i])
    ax.annotate(f"peak {ys[peak_i]:.1f}%",
                (xs[peak_i], ys[peak_i]), textcoords="offset points", xytext=(0, 12),
                ha="center", color="#16a34a", fontweight="bold")
    ax.scatter([xs[peak_i]], [ys[peak_i]], color="#16a34a", s=90, zorder=4)
    # final annotation
    ax.annotate(f"final {ys[-1]:.1f}%", (xs[-1], ys[-1]),
                textcoords="offset points", xytext=(6, -16), color="#dc2626")

    for name, val in REFERENCES.items():
        ax.axhline(val * 100, ls="--", lw=1, color="#9ca3af", alpha=0.8)
        ax.text(xs[-1], val * 100 + 0.1, f" {name} {val*100:.1f}%", color="#6b7280", fontsize=8, va="bottom", ha="right")

    ax.set_xlabel("training examples seen (continual critique)")
    ax.set_ylabel("held-out agreement (%)")
    ax.set_title("Judge performance as it learns from the continual critique agent")
    ax.grid(True, alpha=0.25)
    ax.set_ylim(min(ys + [80]) - 2, max(ys) + 3)
    fig.tight_layout()

    out = run_dir / "learning_curve.png"
    fig.savefig(out, dpi=150)
    return out


def main() -> None:
    run_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runs/v5-20260628-154637")
    out = plot(run_dir)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
