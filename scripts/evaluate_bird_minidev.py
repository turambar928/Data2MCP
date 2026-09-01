#!/usr/bin/env python3
"""Evaluate Data2MCP strategy injection on BIRD Mini-Dev.

Expected BIRD layout, using the official Mini-Dev/dev style:

  data/benchmark/BIRD/minidev/
    mini_dev_data/
      mini_dev_sqlite.json
      dev_databases/
      <db_id>/<db_id>.sqlite

The script is intentionally self-contained so it can run a small diagnostic
subset first:

  PYTHONPATH=src python3 scripts/evaluate_bird_minidev.py \
    --bird-root data/benchmark/BIRD/minidev \
    --questions mini_dev_sqlite.json \
    --strategy auto \
    --limit 20
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from data2mcp_v2.config import (
    AgentConfig,
    Data2McpConfig,
    LLMConfig,
    SQLAgentConfig,
    SQLDBConfig,
)
from data2mcp_v2.server.router import Router
from data2mcp_v2.server.strategy_catalog import load_strategies
from data2mcp_v2.utils.tools import function2tool


STRATEGY_ALIASES = {
    "none": "",
    "auto": "auto",
    "crisp_dm": "crisp_dm",
    "ach": "analysis_of_competing_hypotheses",
    "starbursting": "starbursting",
    "structured": "structured",
}


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}")
    return data


def get_question(item: dict[str, Any]) -> str:
    return str(item.get("question") or item.get("Question") or "").strip()


def get_gold_sql(item: dict[str, Any]) -> str:
    return str(item.get("SQL") or item.get("sql") or item.get("query") or "").strip()


def get_db_id(item: dict[str, Any]) -> str:
    return str(item.get("db_id") or item.get("db") or item.get("database_id") or "").strip()


def find_db_path(bird_root: Path, db_id: str) -> Path:
    candidates = [
        bird_root / "mini_dev_data" / "dev_databases" / db_id / f"{db_id}.sqlite",
        bird_root / "MINIDEV" / "dev_databases" / db_id / f"{db_id}.sqlite",
        bird_root / "minidev" / "MINIDEV" / "dev_databases" / db_id / f"{db_id}.sqlite",
        bird_root / "dev_databases" / db_id / f"{db_id}.sqlite",
        bird_root / "databases" / db_id / f"{db_id}.sqlite",
        bird_root / "database" / db_id / f"{db_id}.sqlite",
        bird_root / db_id / f"{db_id}.sqlite",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = list(bird_root.glob(f"**/{db_id}.sqlite"))
    if matches:
        return matches[0]
    raise FileNotFoundError(f"Could not find SQLite DB for db_id={db_id} under {bird_root}")


def sqlite_schema(db_path: Path, max_columns: int = 80) -> str:
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        lines = []
        for table in tables:
            cols = conn.execute(f"PRAGMA table_info({quote_ident(table)})").fetchall()
            rendered = []
            for _, name, typ, notnull, default, pk in cols[:max_columns]:
                markers = []
                if pk:
                    markers.append("PK")
                if notnull:
                    markers.append("NOT NULL")
                marker = f" [{' '.join(markers)}]" if markers else ""
                rendered.append(f"{name} {typ}{marker}".strip())
            suffix = "" if len(cols) <= max_columns else f", ... ({len(cols) - max_columns} more columns)"
            lines.append(f"- {table}({', '.join(rendered)}{suffix})")
        return "\n".join(lines)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def execute_sql(db_path: Path, sql: str, max_rows: int = 200) -> dict[str, Any]:
    if not sql.strip():
        return {"ok": False, "error": "empty SQL", "rows": []}
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=30) as conn:
            conn.execute("PRAGMA query_only = ON")
            cur = conn.execute(sql)
            rows = cur.fetchmany(max_rows + 1)
            columns = [desc[0] for desc in cur.description or []]
            truncated = len(rows) > max_rows
            rows = rows[:max_rows]
            return {
                "ok": True,
                "columns": columns,
                "rows": rows,
                "truncated": truncated,
            }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "rows": []}


def normalize_cell(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    try:
        number = float(text)
        if number.is_integer():
            return int(number)
        return round(number, 6)
    except ValueError:
        return re.sub(r"\s+", " ", text).lower()


def normalize_rows(rows: list[Any]) -> list[tuple[Any, ...]]:
    normalized = []
    for row in rows:
        if not isinstance(row, (list, tuple)):
            row = (row,)
        normalized.append(tuple(normalize_cell(cell) for cell in row))
    return sorted(normalized, key=lambda r: json.dumps(r, sort_keys=True, ensure_ascii=False))


def execution_match(db_path: Path, predicted_sql: str, gold_sql: str) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    pred = execute_sql(db_path, predicted_sql, max_rows=1000)
    gold = execute_sql(db_path, gold_sql, max_rows=1000)
    if not pred.get("ok") or not gold.get("ok"):
        return False, pred, gold
    return normalize_rows(pred.get("rows", [])) == normalize_rows(gold.get("rows", [])), pred, gold


def extract_json_object(text: str) -> dict[str, Any] | None:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    return None


def extract_sql(text: str) -> str:
    obj = extract_json_object(text)
    if obj:
        for key in ("sql", "predicted_sql", "query"):
            if obj.get(key):
                return str(obj[key]).strip()
    fenced = re.search(r"```sql\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    match = re.search(r"(SELECT\b.*?)(?:;|\Z)", text, flags=re.DOTALL | re.IGNORECASE)
    return (match.group(1).strip() + ";") if match else ""


def build_config(args: argparse.Namespace, db_path: Path, strategy_text: str, strategy_key: str) -> Data2McpConfig:
    llm = LLMConfig(
        model=args.model,
        base_url=args.base_url or os.getenv("OPENAI_BASE_URL"),
        api_key=args.api_key or os.getenv("OPENAI_API_KEY"),
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
    )
    sql_agent = SQLAgentConfig(
        type="sql_agent",
        tool_name="bird_sql_agent",
        tool_description=(
            "Answer natural-language questions by inspecting and querying the current BIRD SQLite database. "
            "Use this for schema exploration and sanity checks."
        ),
        db_config=SQLDBConfig(type="sqlite", file_path=str(db_path)),
        llm_config=llm,
    )
    return Data2McpConfig(
        agents=AgentConfig(agent_configs=[sql_agent], default_llm_config=llm),
        route_type="agentic",
        llm=llm,
        max_turns=args.max_turns,
        min_tool_calls=args.min_tool_calls,
        tool_call_timeout=args.tool_timeout,
        tool_call_max_length=args.tool_max_length,
        min_charts_required=args.min_charts_required,
        retrieval_strategy=strategy_text,
        strategy_key="" if args.disable_strategy_validation else strategy_key,
        auto_select_strategy=args.strategy == "auto",
        max_refinement_rounds=0,
    )


def resolve_strategy(strategy: str) -> tuple[str, str]:
    if strategy not in STRATEGY_ALIASES:
        raise ValueError(f"Unknown strategy {strategy}. Choose from {sorted(STRATEGY_ALIASES)}")
    key = STRATEGY_ALIASES[strategy]
    if not key or key == "auto":
        return key, key
    strategies = load_strategies()
    if key not in strategies:
        raise KeyError(f"Strategy key {key!r} not found in active catalog")
    return key, strategies[key].full_text


def attach_direct_sql_tool(router: Router, db_path: Path) -> None:
    async def execute_sql_tool(sql: str) -> str:
        """
        Execute a read-only SQLite SQL query against the current BIRD database.

        Args:
            sql: A SELECT/WITH query. Never use INSERT/UPDATE/DELETE/DDL.

        Returns:
            JSON with ok, columns, rows, and error fields.
        """
        lowered = sql.strip().lower()
        if not (lowered.startswith("select") or lowered.startswith("with")):
            return json.dumps({"ok": False, "error": "Only SELECT/WITH queries are allowed."}, ensure_ascii=False)
        result = execute_sql(db_path, sql, max_rows=100)
        return json.dumps(result, ensure_ascii=False, default=str)

    router.tools.insert(
        0,
        function2tool(
            execute_sql_tool,
            "execute_sql",
            "Execute an explicit read-only SQLite SELECT/WITH query on the current BIRD database and return JSON rows.",
            {},
        ),
    )


def build_prompt(item: dict[str, Any], schema: str) -> str:
    question = get_question(item)
    evidence = str(item.get("evidence") or item.get("external_knowledge") or "").strip()
    evidence_block = f"\nExternal evidence/hint:\n{evidence}\n" if evidence else ""
    return f"""You are solving a BIRD text-to-SQL task.

Database schema:
{schema}
{evidence_block}
Question:
{question}

Instructions:
- Generate one SQLite-compatible SQL query that answers the question.
- Use `execute_sql` to test the SQL before finalizing.
- Prefer exact values from the database over assumptions.
- End with valid JSON only, with this schema:
  {{"sql": "...", "answer": "...", "rationale": "brief evidence summary"}}
"""


async def evaluate_one(args: argparse.Namespace, item: dict[str, Any], index: int) -> dict[str, Any]:
    db_id = get_db_id(item)
    db_path = find_db_path(args.bird_root, db_id)
    strategy_key, strategy_text = resolve_strategy(args.strategy)
    config = build_config(args, db_path, strategy_text, strategy_key if strategy_key != "auto" else "")
    router = Router(config)
    attach_direct_sql_tool(router, db_path)
    prompt = build_prompt(item, sqlite_schema(db_path))

    started = time.time()
    final_text, messages = await router.route(prompt)
    elapsed = time.time() - started

    predicted_sql = extract_sql(final_text)
    gold_sql = get_gold_sql(item)
    match, pred_exec, gold_exec = execution_match(db_path, predicted_sql, gold_sql)
    tool_calls = [
        call
        for msg in messages
        for call in (msg.get("tool_calls") or [])
        if isinstance(msg, dict)
    ]
    return {
        "index": index,
        "db_id": db_id,
        "question": get_question(item),
        "evidence": item.get("evidence", ""),
        "gold_sql": gold_sql,
        "predicted_sql": predicted_sql,
        "execution_match": match,
        "pred_execution_ok": bool(pred_exec.get("ok")),
        "pred_execution_error": pred_exec.get("error", ""),
        "gold_execution_ok": bool(gold_exec.get("ok")),
        "strategy": args.strategy,
        "strategy_used": getattr(router, "strategy_used", ""),
        "output_compliance_score": getattr(router, "output_compliance_score", None),
        "tool_call_count": len(tool_calls),
        "elapsed_seconds": round(elapsed, 3),
        "final_text": final_text,
    }


def write_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def resolve_questions_path(bird_root: Path, questions: str) -> Path:
    requested = bird_root / questions
    if requested.exists():
        return requested
    candidates = [
        bird_root / "mini_dev_sqlite.json",
        bird_root / "mini_dev_data" / "mini_dev_sqlite.json",
        bird_root / "MINIDEV" / "mini_dev_sqlite.json",
        bird_root / "minidev" / "MINIDEV" / "mini_dev_sqlite.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Could not find questions file. Tried {requested} and standard Mini-Dev layouts under {bird_root}"
    )


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    correct = sum(1 for row in rows if row["execution_match"])
    exec_ok = sum(1 for row in rows if row["pred_execution_ok"])
    return {
        "total": total,
        "execution_accuracy": correct / total if total else 0.0,
        "execution_success_rate": exec_ok / total if total else 0.0,
        "avg_tool_calls": sum(row["tool_call_count"] for row in rows) / total if total else 0.0,
        "avg_elapsed_seconds": sum(row["elapsed_seconds"] for row in rows) / total if total else 0.0,
    }


async def main_async(args: argparse.Namespace) -> None:
    questions_path = resolve_questions_path(args.bird_root, args.questions)
    items = load_json(questions_path)
    if args.offset:
        items = items[args.offset :]
    if args.limit:
        items = items[: args.limit]

    output_path = args.output_dir / f"bird_minidev_{args.strategy}.jsonl"
    summary_path = args.output_dir / f"bird_minidev_{args.strategy}_summary.json"
    if output_path.exists() and not args.resume:
        output_path.unlink()

    done = 0
    rows: list[dict[str, Any]] = []
    if args.resume and output_path.exists():
        with output_path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                rows.append(row)
        done = len(rows)

    for local_index, item in enumerate(items[done:], start=done):
        try:
            row = await evaluate_one(args, item, args.offset + local_index)
        except Exception as exc:
            row = {
                "index": args.offset + local_index,
                "db_id": get_db_id(item),
                "question": get_question(item),
                "gold_sql": get_gold_sql(item),
                "strategy": args.strategy,
                "execution_match": False,
                "pred_execution_ok": False,
                "error": str(exc),
            }
        rows.append(row)
        write_jsonl(output_path, row)
        current = summarize(rows)
        print(
            f"[{len(rows)}/{len(items)}] db={row.get('db_id')} "
            f"ok={row.get('execution_match')} acc={current['execution_accuracy']:.3f}"
        )
        if args.sleep_seconds > 0 and len(rows) < len(items):
            time.sleep(args.sleep_seconds)

    summary = summarize(rows)
    summary["args"] = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items() if k != "api_key"}
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bird-root", type=Path, default=Path("data/benchmark/BIRD/minidev"))
    parser.add_argument("--questions", default="mini_dev_data/mini_dev_sqlite.json")
    parser.add_argument("--output-dir", type=Path, default=Path("output/bird_minidev"))
    parser.add_argument("--strategy", choices=sorted(STRATEGY_ALIASES), default="none")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-5"))
    parser.add_argument("--base-url", default=os.getenv("OPENAI_BASE_URL"))
    parser.add_argument("--api-key", default=os.getenv("OPENAI_API_KEY"))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=8192)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-turns", type=int, default=8)
    parser.add_argument("--min-tool-calls", type=int, default=1)
    parser.add_argument("--tool-timeout", type=int, default=300)
    parser.add_argument("--tool-max-length", type=int, default=12000)
    parser.add_argument("--min-charts-required", type=int, default=0)
    parser.add_argument(
        "--disable-strategy-validation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Disable post-hoc strategy validation LLM calls. Recommended for BIRD to avoid extra API traffic.",
    )
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
