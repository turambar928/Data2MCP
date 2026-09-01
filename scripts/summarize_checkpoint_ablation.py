#!/usr/bin/env python3
"""Summarize checkpoint-ablation DAComp judge outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]


def load_eval(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def pct(rows: list[dict[str, Any]], key: str) -> float:
    vals = [float(r.get(key, 0)) for r in rows]
    return mean(vals) if vals else 0.0


def max_pct(rows: list[dict[str, Any]], key: str) -> float:
    vals = []
    for row in rows:
        max_score = float(row.get("max_score") or 100)
        vals.append(float(row.get(key, 0)) / max_score * 100)
    return mean(vals) if vals else 0.0


def micro_pct(rows: list[dict[str, Any]], key: str) -> float:
    total = sum(float(row.get(key, 0)) for row in rows)
    max_total = sum(float(row.get("max_score") or 0) for row in rows)
    return total / max_total * 100 if max_total else 0.0


def condition_name(path: Path) -> str:
    stem = path.stem
    for prefix in ("dacomp_crisp_dm_", "crisp_dm_", "eval_"):
        if stem.startswith(prefix):
            return stem[len(prefix):]
    return stem


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval", nargs="+", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("output/checkpoint_ablation/summary.md"))
    args = parser.parse_args()

    evals: dict[str, list[dict[str, Any]]] = {}
    for raw_path in args.eval:
        path = raw_path if raw_path.is_absolute() else BASE_DIR / raw_path
        evals[condition_name(path)] = load_eval(path)

    lines = [
        "# Checkpoint Ablation Summary",
        "",
        "## Aggregate Scores",
        "",
        "| Condition | N | Micro Total % | Macro Total % | Completeness | Accuracy | Conclusiveness |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for cond, rows in sorted(evals.items()):
        lines.append(
            f"| {cond} | {len(rows)} | {micro_pct(rows, 'total_score'):.2f} | "
            f"{max_pct(rows, 'total_score'):.2f} | "
            f"{pct(rows, 'completeness_score'):.2f} | "
            f"{pct(rows, 'accuracy_score'):.2f} | "
            f"{pct(rows, 'conclusiveness_score'):.2f} |"
        )

    if "text_only" in evals and "checkpoint_refine" in evals:
        text_rows = {r["instance_id"]: r for r in evals["text_only"]}
        refine_rows = {r["instance_id"]: r for r in evals["checkpoint_refine"]}
        common = sorted(set(text_rows) & set(refine_rows))
        deltas = []
        improved = tied = degraded = 0
        for iid in common:
            base = float(text_rows[iid].get("total_score", 0))
            ref = float(refine_rows[iid].get("total_score", 0))
            delta = ref - base
            deltas.append(delta)
            if delta > 0:
                improved += 1
            elif delta < 0:
                degraded += 1
            else:
                tied += 1
        lines += [
            "",
            "## Paired Contrast: Checkpoint Refine - Text Only",
            "",
            f"- Common instances: {len(common)}",
            f"- Mean raw-score delta: {mean(deltas):.2f}" if deltas else "- Mean raw-score delta: N/A",
            f"- Improved / tied / degraded: {improved} / {tied} / {degraded}",
        ]

    out_path = args.out if args.out.is_absolute() else BASE_DIR / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(out_path)


if __name__ == "__main__":
    main()
