from __future__ import annotations

import json
import logging
from typing import Iterable

from data2mcp_v2.server.data_summary import build_data_summary
from data2mcp_v2.server.strategy_catalog import (
    DEFAULT_STRATEGIES,
    StrategySpec,
    format_strategy_catalog,
)
from data2mcp_v2.utils.llm_api import ChatModel
from data2mcp_v2.config.config import Data2McpConfig

logger = logging.getLogger(__name__)


AUTO_STRATEGY_SYSTEM_PROMPT = """\
You are selecting the best retrieval strategy for an agent.
Choose exactly ONE strategy key from the provided list.
Return ONLY a JSON object with keys:
- "strategy": one of the provided keys
- "reason": a short justification in 1-2 sentences
Do not include any extra text outside the JSON.
""".strip()


def _format_data_summary(summary: dict) -> str:
    sources = summary.get("sources") if isinstance(summary, dict) else None
    if not sources:
        return "Data Summary: No data sources available."

    lines = []
    for idx, source in enumerate(sources, start=1):
        name = source.get("name") or f"source_{idx}"
        agent_type = source.get("agent_type") or "unknown"
        data_type = source.get("data_type") or source.get("db_type") or "unknown"
        size = source.get("size_human") or source.get("total_size_human") or "unknown"
        row_count = source.get("row_count")
        columns = source.get("columns")
        extra = []
        if row_count is not None:
            extra.append(f"rows={row_count}")
        if isinstance(columns, list) and columns:
            extra.append("columns=" + ", ".join(columns[:10]))
        extra_text = "; " + "; ".join(extra) if extra else ""
        lines.append(f"- {name} ({agent_type}): type={data_type}; size={size}{extra_text}")

    return "Data Summary:\n" + "\n".join(lines)


def _extract_strategy_key(text: str, candidates: Iterable[str]) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    for key in candidates:
        if key.lower() in lowered:
            return key
    return None


def select_retrieval_strategy(
    query: str,
    config: Data2McpConfig,
    chat: ChatModel,
    candidates: dict[str, StrategySpec] | None = None,
) -> tuple[str, str]:
    strategies = candidates or DEFAULT_STRATEGIES
    if not strategies:
        return "", "no_candidates"

    summary = build_data_summary(config)
    summary_text = _format_data_summary(summary)
    strategy_catalog = format_strategy_catalog(strategies)
    candidate_keys = list(strategies.keys())

    user_prompt = "\n".join(
        [
            f"User Question: {query}",
            summary_text,
            "",
            "Available strategies:",
            strategy_catalog,
            "",
            "Return JSON only.",
        ]
    )

    messages = [
        {"role": "system", "content": AUTO_STRATEGY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        completion = chat.chat_with_retry(messages, retry=1)
        content = completion.choices[0].message.content or ""
        try:
            data = json.loads(content)
            key = data.get("strategy")
        except Exception:
            key = _extract_strategy_key(content, candidate_keys)
        if key not in strategies:
            key = candidate_keys[0]
        spec = strategies[key]
        return key, spec.full_text
    except Exception as exc:
        logger.warning("auto strategy selection failed: %s", exc)
        fallback_key = candidate_keys[0]
        return fallback_key, strategies[fallback_key].full_text

