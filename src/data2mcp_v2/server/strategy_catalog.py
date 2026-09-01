from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class StrategySpec:
    key: str
    name: str
    description: str
    full_text: str
    source: str = "builtin"  # "builtin" | filename of extraction source
    checkpoints: tuple[str, ...] = ()  # observable output anchors for compliance validation


DEFAULT_STRATEGIES: dict[str, StrategySpec] = {
    "structured": StrategySpec(
        key="structured",
        name="Structured Brainstorming",
        description="All-source parallel query without early judgment",
        full_text=(
            "Structured Brainstorming: Query all available data sources in parallel "
            "without early filtering or judgment. Maximize coverage by exploring all "
            "potential data dimensions systematically. Aggregate all results first, "
            "then organize and categorize findings - prioritizing quantity over "
            "premature quality assessment."
        ),
        checkpoints=(
            "queries multiple data sources before drawing any conclusion",
            "presents findings from at least 2 different sources or dimensions",
            "organizes results into categories or themes rather than a single narrative",
            "does not discard or filter results in early stages",
        ),
    ),
    "virtual": StrategySpec(
        key="virtual",
        name="Virtual Brainstorming",
        description="Iterative deep-dive with independent reflection",
        full_text=(
            "Virtual Brainstorming: Use iterative, phased retrieval with independent "
            "analysis between rounds. After each query, deeply reflect on results "
            "independently to guide the next step. Continue until comprehensive "
            "understanding emerges through sustained, asynchronous exploration."
        ),
        checkpoints=(
            "shows multiple rounds of querying with reflection between rounds",
            "later queries are informed by earlier query results",
            "explicitly revisits or refines earlier findings",
            "the final answer synthesizes insights across multiple iterations",
        ),
    ),
    "nominal": StrategySpec(
        key="nominal",
        name="Nominal Group",
        description="Independent queries, aggregate, then rank by priority",
        full_text=(
            "Nominal Group Technique: Query each data source independently first "
            "(avoiding cross-contamination of results). Aggregate all findings without "
            "judgment. Evaluate and rank all results by relevance and importance. "
            "Finally, select top-priority insights for synthesis."
        ),
        checkpoints=(
            "queries each data source independently before comparing results",
            "aggregates findings from all sources before making judgments",
            "ranks or prioritizes findings by relevance or importance",
            "final answer reflects a ranked or weighted synthesis",
        ),
    ),
    "starbursting": StrategySpec(
        key="starbursting",
        name="Starbursting (5W1H)",
        description="Decompose into question dimensions before querying",
        full_text=(
            "Starbursting (5W1H Analysis): Before querying data, systematically "
            "decompose the user question into multiple interrogative dimensions "
            "(Who, What, When, Where, Why, How). For each dimension, generate "
            "specific sub-questions. Query relevant data sources to answer each "
            "sub-question separately, then integrate findings into a comprehensive "
            "answer."
        ),
        checkpoints=(
            "explicitly decomposes the question into Who/What/When/Where/Why/How sub-questions",
            "answers at least 3 different interrogative dimensions",
            "each dimension is answered with specific data from queries",
            "final answer integrates findings across all dimensions",
        ),
    ),
}


def format_strategy_catalog(strategies: dict[str, StrategySpec]) -> str:
    lines = []
    for spec in strategies.values():
        lines.append(f"- {spec.key}: {spec.name}. {spec.full_text}")
    return "\n".join(lines)


def _raw_dict_to_spec(d: dict[str, Any]) -> StrategySpec | None:
    """Convert a raw dict (from JSON store) to a StrategySpec, skipping invalid entries."""
    key = d.get("key", "").strip()
    name = d.get("name", "").strip()
    full_text = d.get("full_text", "").strip()
    if not (key and name and full_text):
        return None
    return StrategySpec(
        key=key,
        name=name,
        description=d.get("description", "")[:120],
        full_text=full_text,
        source=d.get("source", "extracted"),
        checkpoints=tuple(d.get("checkpoints", [])),
    )


def load_strategies(
    store_path: str | Path | None = None,
    include_defaults: bool = True,
) -> dict[str, StrategySpec]:
    """
    Build the active strategy catalog.

    Args:
        store_path: Path to the extracted_strategies.json file.
                    Defaults to config/extracted_strategies.json relative to cwd.
        include_defaults: If True, DEFAULT_STRATEGIES are always included.
                          Extracted strategies with the same key override defaults.

    Returns:
        Merged dict of StrategySpec, keyed by strategy key.
    """
    from data2mcp_v2.server.strategy_extractor import (
        DEFAULT_STRATEGY_STORE,
        load_extracted_strategies,
    )

    catalog: dict[str, StrategySpec] = {}
    if include_defaults:
        catalog.update(DEFAULT_STRATEGIES)

    resolved = Path(store_path) if store_path else DEFAULT_STRATEGY_STORE
    raw_list = load_extracted_strategies(resolved)
    for raw in raw_list:
        spec = _raw_dict_to_spec(raw)
        if spec:
            catalog[spec.key] = spec

    return catalog
