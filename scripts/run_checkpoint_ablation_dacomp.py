#!/usr/bin/env python3
"""Run a DAComp checkpoint-ablation experiment for strategy injection.

Conditions:
  no_strategy         No strategy block.
  text_only           Inject the strategy full_text but disable checkpoint lookup.
  checkpoint_eval     Inject strategy full_text and run checkpoint validation post-hoc.
  checkpoint_refine   Inject strategy full_text and allow checkpoint-guided refinement.

The key contrast for the reviewer is:
  text_only vs checkpoint_refine

This isolates whether explicit checkpoints contribute beyond a plain methodology
description. The checkpoint_eval condition is useful for auditability analysis,
but it should not change the answer because max_refinement_rounds=0.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import yaml


BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data2mcp_v2.server.strategy_catalog import load_strategies  # noqa: E402


DATA_FILE = BASE_DIR / "data/benchmark/DAComp/dacomp-da/dacomp-da.jsonl"
DACOMP_DA_DIR = BASE_DIR / "data/benchmark/DAComp/dacomp-da"
DEFAULT_OUT_DIR = BASE_DIR / "output/checkpoint_ablation"
DEFAULT_API_URL = "http://localhost:2734/api/chat"

CONDITIONS = {"no_strategy", "text_only", "checkpoint_eval", "checkpoint_refine"}
CONDITION_ORDER = ["no_strategy", "text_only", "checkpoint_eval", "checkpoint_refine"]


def load_questions() -> list[dict[str, Any]]:
    items = []
    with DATA_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def load_llm_config() -> dict[str, Any]:
    cfg_file = BASE_DIR / "demo/public/config.yaml"
    cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
    llm = cfg.get("llm", {})
    if llm.get("base_url") and llm.get("model") and llm.get("api_key"):
        return llm

    default_file = BASE_DIR / "config/llm/default.yaml"
    fallback = yaml.safe_load(default_file.read_text(encoding="utf-8")) or {}
    return {
        "_target_": fallback.get("_target_", "data2mcp_v2.config.LLMConfig"),
        "model": fallback.get("model", "qwen3-235b-a22b-instruct-2507"),
        "temperature": fallback.get("temperature", 0),
        "max_tokens": fallback.get("max_tokens", 8192),
        "timeout_seconds": fallback.get("timeout_seconds", 600),
        "max_retries": fallback.get("max_retries", 3),
        "base_url": fallback.get("base_url", ""),
        "api_key": fallback.get("api_key", ""),
    }


def resolve_strategy(strategy_key: str) -> tuple[str, str]:
    if not strategy_key:
        return "", ""
    strategies = load_strategies()
    if strategy_key not in strategies:
        raise KeyError(f"Unknown strategy key {strategy_key!r}. Available examples: {list(strategies)[:10]}")
    spec = strategies[strategy_key]
    return spec.name, spec.full_text


def db_available(instance_id: str) -> bool:
    path = DACOMP_DA_DIR / instance_id / f"{instance_id}.sqlite"
    return path.exists() and path.stat().st_size > 10_000


def build_config(
    instance_id: str,
    llm_cfg: dict[str, Any],
    condition: str,
    strategy_key: str,
    strategy_text: str,
    max_refinement_rounds: int,
    refinement_threshold: float,
    min_charts_required: int,
) -> dict[str, Any]:
    db_path = str(DACOMP_DA_DIR / instance_id / f"{instance_id}.sqlite")

    if condition == "no_strategy":
        injected_strategy = ""
        active_strategy_key = ""
        rounds = 0
    elif condition == "text_only":
        injected_strategy = strategy_text
        active_strategy_key = ""  # Router treats this as manual text with no StrategySpec/checkpoints.
        rounds = 0
    elif condition == "checkpoint_eval":
        injected_strategy = strategy_text
        active_strategy_key = strategy_key
        rounds = 0
    elif condition == "checkpoint_refine":
        injected_strategy = strategy_text
        active_strategy_key = strategy_key
        rounds = max_refinement_rounds
    else:
        raise ValueError(f"Unknown condition {condition}")

    return {
        "_target_": "data2mcp_v2.config.Data2McpConfig",
        "route_type": "agentic",
        "tool_call_timeout": 600,
        "tool_call_max_length": 10000,
        "max_turns": 30,
        "min_tool_calls": 3,
        "min_charts_required": min_charts_required,
        "retrieval_strategy": injected_strategy,
        "strategy_key": active_strategy_key,
        "auto_select_strategy": False,
        "max_refinement_rounds": rounds,
        "refinement_threshold": refinement_threshold,
        "llm": llm_cfg,
        "agents": {
            "_target_": "data2mcp_v2.config.AgentConfig",
            "default_llm_config": llm_cfg,
            "agent_configs": [
                {
                    "_target_": "data2mcp_v2.config.SQLAgentConfig",
                    "tool_name": f"{instance_id}_database",
                    "tool_description": f"DAComp {instance_id} database for data analysis",
                    "type": "sql_agent",
                    "agent_type": "tool-calling",
                    "llm_config": llm_cfg,
                    "db_config": {
                        "_target_": "data2mcp_v2.config.SQLDBConfig",
                        "type": "sqlite",
                        "file_path": db_path,
                    },
                }
            ],
        },
    }


def load_existing(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding="utf-8"))
    return {row["instance_id"]: row for row in rows}


def save_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=sorted(CONDITIONS | {"all"}), default="all")
    parser.add_argument("--strategy", default="crisp_dm")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--case-list", type=Path, default=None, help="Optional newline-delimited instance ids.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--min-final-chars",
        type=int,
        default=1,
        help="When resuming, rerun existing answers shorter than this many non-space characters.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=8)
    parser.add_argument("--max-refinement-rounds", type=int, default=1)
    parser.add_argument("--refinement-threshold", type=float, default=0.7)
    parser.add_argument("--min-charts-required", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strategy_name, strategy_text = resolve_strategy(args.strategy)
    llm_cfg = load_llm_config()
    questions = load_questions()

    if args.case_list:
        wanted = {
            line.strip()
            for line in args.case_list.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        questions = [item for item in questions if item["instance_id"] in wanted]
    if args.offset:
        questions = questions[args.offset :]
    if args.limit:
        questions = questions[: args.limit]

    conditions = CONDITION_ORDER if args.condition == "all" else [args.condition]
    print(f"Strategy: {args.strategy} ({strategy_name or 'none'})")
    print(f"Conditions: {', '.join(conditions)}")
    print(f"Questions: {len(questions)}")

    for condition in conditions:
        out_file = args.out_dir / f"dacomp_{args.strategy}_{condition}.json"
        existing = load_existing(out_file) if args.resume else {}
        rows: list[dict[str, Any]] = []
        print("=" * 80)
        print(f"Condition: {condition}  output={out_file}")

        with httpx.Client(timeout=1800) as client:
            for idx, item in enumerate(questions, 1):
                instance_id = item["instance_id"]
                question = item["instruction"]
                if instance_id in existing and not str(existing[instance_id].get("final_text", "")).startswith("Error"):
                    existing_text = str(existing[instance_id].get("final_text", "")).strip()
                    if len(existing_text) >= args.min_final_chars:
                        rows.append(existing[instance_id])
                        print(f"  SKIP [{idx}/{len(questions)}] {instance_id}")
                        continue

                if not db_available(instance_id):
                    row = {
                        "instance_id": instance_id,
                        "condition": condition,
                        "strategy_key": args.strategy if condition != "no_strategy" else "",
                        "strategy_name": strategy_name if condition != "no_strategy" else "",
                        "question": question,
                        "final_text": "Error: database not available",
                        "output_compliance_score": None,
                        "skipped": True,
                    }
                    rows.append(row)
                    save_rows(out_file, rows)
                    print(f"  SKIP DB [{idx}/{len(questions)}] {instance_id}")
                    continue

                config = build_config(
                    instance_id=instance_id,
                    llm_cfg=llm_cfg,
                    condition=condition,
                    strategy_key=args.strategy,
                    strategy_text=strategy_text,
                    max_refinement_rounds=args.max_refinement_rounds,
                    refinement_threshold=args.refinement_threshold,
                    min_charts_required=args.min_charts_required,
                )
                payload = {"message": question, "config": config, "history": []}

                print(f"  RUN  [{idx}/{len(questions)}] {instance_id}")
                try:
                    resp = client.post(args.api_url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    final_text = data.get("final_text") or data.get("answer") or ""
                    row = {
                        "instance_id": instance_id,
                        "condition": condition,
                        "strategy_key": args.strategy if condition != "no_strategy" else "",
                        "strategy_name": strategy_name if condition != "no_strategy" else "",
                        "question": question,
                        "final_text": final_text,
                        "output_compliance_score": data.get("output_compliance_score"),
                        "skipped": False,
                    }
                    print(f"       ok len={len(final_text)} compliance={row['output_compliance_score']}")
                except Exception as exc:
                    row = {
                        "instance_id": instance_id,
                        "condition": condition,
                        "strategy_key": args.strategy if condition != "no_strategy" else "",
                        "strategy_name": strategy_name if condition != "no_strategy" else "",
                        "question": question,
                        "final_text": f"Error: {exc}",
                        "output_compliance_score": None,
                        "skipped": False,
                    }
                    print(f"       error {exc}")

                rows.append(row)
                save_rows(out_file, rows)
                time.sleep(args.sleep_seconds)

        # Persist skipped rows appended after the last actual run. Without this,
        # a resume pass that ends with SKIP entries can leave the output truncated.
        save_rows(out_file, rows)


if __name__ == "__main__":
    main()
