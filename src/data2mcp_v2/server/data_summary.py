from __future__ import annotations

import json
from datetime import datetime
import math
from pathlib import Path
from typing import Any


from data2mcp_v2.config.db import DBType
from data2mcp_v2.config.db_agent import (
    DataFrameAgentConfig,
    KGAgentConfig,
    RAGAgentConfig,
    SQLAgentConfig,
)
from data2mcp_v2.config.config import Data2McpConfig

MAX_SAMPLE_ROWS = 5
MAX_SAMPLE_CHARS = 1000
MAX_TEXT_BYTES = 200_000
MAX_SIZE_FOR_ROW_COUNT = 50 * 1024 * 1024
MAX_SIZE_FOR_JSON_ARRAY = 10 * 1024 * 1024


def _human_size(size_bytes: int | None) -> str:
    if size_bytes is None:
        return "unknown"
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024**3:
        return f"{size_bytes / 1024**2:.1f} MB"
    return f"{size_bytes / 1024**3:.1f} GB"


def _safe_stat(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        return {"exists": True, "size_bytes": stat.st_size}
    except FileNotFoundError:
        return {"exists": False, "size_bytes": None, "error": "file not found"}
    except Exception as exc:  # pragma: no cover - defensive
        return {"exists": False, "size_bytes": None, "error": str(exc)}


def _read_text_sample(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {}
    try:
        with path.open("rb") as f:
            data = f.read(MAX_TEXT_BYTES)
        text = data.decode("utf-8", errors="ignore")
        info["sample_text"] = text[:MAX_SAMPLE_CHARS]
        info["char_count"] = len(text)
        info["line_count"] = text.count("\n") + 1 if text else 0
        info["word_count"] = len(text.split())
    except Exception as exc:
        info["error"] = str(exc)
    return info


def _count_lines(path: Path) -> int | None:
    try:
        with path.open("rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def _summarize_dataframe(path: Path, data_type: DBType) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path),
        "data_type": data_type.value if isinstance(data_type, DBType) else str(data_type),
    }
    stat_info = _safe_stat(path)
    summary.update(stat_info)
    summary["size_human"] = _human_size(stat_info.get("size_bytes"))

    if not stat_info.get("exists"):
        return summary

    file_size = stat_info.get("size_bytes") or 0
    row_count = None
    if file_size and file_size <= MAX_SIZE_FOR_ROW_COUNT:
        total_lines = _count_lines(path)
        if total_lines is not None:
            row_count = max(total_lines - 1, 0)

    summary["row_count"] = row_count

    try:
        try:
            import pandas as pd
        except Exception as exc:
            summary["error"] = f"pandas_not_available: {exc}"
            return summary

        if data_type == DBType.CSV:
            df = pd.read_csv(path, nrows=100)
        else:
            try:
                df = pd.read_json(path, lines=True, nrows=100)
            except ValueError:
                df = pd.read_json(path)
        summary["columns"] = list(df.columns)
        summary["sample_rows"] = _sanitize_for_json(
            df.head(MAX_SAMPLE_ROWS).to_dict(orient="records")
        )
    except Exception as exc:
        summary["error"] = f"preview_failed: {exc}"
    return summary


def _sanitize_for_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, list):
        return [_sanitize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_for_json(val) for key, val in value.items()}
    return value


def _summarize_json_array(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"record_count": None}
    try:
        if path.stat().st_size > MAX_SIZE_FOR_JSON_ARRAY:
            return {"record_count": None, "note": "json array too large for full count"}
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"record_count": len(data)}
    except Exception:
        return {"record_count": None}
    return {"record_count": None}


def _summarize_rag(path: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {"path": str(path)}
    stat_info = _safe_stat(path)
    summary.update(stat_info)
    summary["size_human"] = _human_size(stat_info.get("size_bytes"))

    if not stat_info.get("exists"):
        return summary

    if path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file()]
        total_size = sum(p.stat().st_size for p in files)
        summary["file_count"] = len(files)
        summary["total_size_bytes"] = total_size
        summary["total_size_human"] = _human_size(total_size)
        return summary

    summary.update(_read_text_sample(path))
    return summary


def _summarize_sql(agent: SQLAgentConfig) -> dict[str, Any]:
    db = agent.db_config
    data: dict[str, Any] = {
        "db_type": db.type.value if isinstance(db.type, DBType) else str(db.type),
        "host": db.host,
        "port": db.port,
        "db_name": db.db_name,
    }
    if db.type == DBType.SQLITE:
        path = Path(db.file_path or "")
        data["file_path"] = str(path)
        stat_info = _safe_stat(path)
        data.update(stat_info)
        data["size_human"] = _human_size(stat_info.get("size_bytes"))
    return data


def _summarize_kg(agent: KGAgentConfig) -> dict[str, Any]:
    db = agent.db_config
    return {
        "db_type": db.type.value if isinstance(db.type, DBType) else str(db.type),
        "host": db.host,
        "port": db.port,
        "user": db.user,
    }


def build_data_summary(config: Data2McpConfig) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    for agent in config.agents.agent_configs:
        agent_type = agent.type.value if hasattr(agent.type, "value") else str(agent.type)
        source: dict[str, Any] = {
            "name": agent.tool_name,
            "description": agent.tool_description,
            "agent_type": agent_type,
        }
        try:
            if isinstance(agent, DataFrameAgentConfig):
                db = agent.db_config
                source.update(_summarize_dataframe(Path(db.save_path or ""), db.type))
                if db.type == DBType.JSON:
                    source.update(_summarize_json_array(Path(db.save_path or "")))
            elif isinstance(agent, RAGAgentConfig):
                db = agent.db_config
                source.update(_summarize_rag(Path(db.data_path or "")))
                source["vector_store"] = db.save_path
                source["index_name"] = db.index_name
            elif isinstance(agent, SQLAgentConfig):
                source.update(_summarize_sql(agent))
            elif isinstance(agent, KGAgentConfig):
                source.update(_summarize_kg(agent))
            else:
                source["note"] = "unsupported agent type"
        except Exception as exc:
            source["error"] = f"summary_failed: {exc}"

        sources.append(source)

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source_count": len(sources),
        "sources": sources,
    }

