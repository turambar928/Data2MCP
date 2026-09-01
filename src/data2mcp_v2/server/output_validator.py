"""
产出验证器 (Output Validator)

在 Agent 完成回答后，对最终答案进行语义评估：
- 针对每个 checkpoint（策略规定的产出锚点）逐一判断是否满足
- 汇总出合规分数和详细报告
- 对没有预定义 checkpoints 的策略，回退到 generic 评分

不依赖过程（工具调用顺序），只看最终产出内容。
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from data2mcp_v2.server.strategy_catalog import StrategySpec
from data2mcp_v2.utils.llm_api import ChatModel

logger = logging.getLogger(__name__)


# ── prompt ──────────────────────────────────────────────────────────────────

_CHECKPOINT_EVAL_PROMPT = """\
You are evaluating whether an AI agent's final answer satisfies a specific analytical checkpoint.

Strategy: {strategy_name}
Checkpoint to verify: "{checkpoint}"

Agent's final answer:
\"\"\"
{answer}
\"\"\"

Does the answer satisfy the checkpoint?
Reply with a JSON object: {{"satisfied": true/false, "reason": "one sentence"}}
Do NOT include any text outside the JSON.
""".strip()

_GENERIC_EVAL_PROMPT = """\
You are evaluating whether an AI agent's answer correctly applied a structured analytical strategy.

Strategy name: {strategy_name}
Strategy instructions given to the agent:
\"\"\"
{full_text}
\"\"\"

Agent's final answer:
\"\"\"
{answer}
\"\"\"

Evaluate the answer on three dimensions:
1. Does the answer show evidence that the strategy was applied (not just a generic response)?
2. Does the answer contain intermediate analytical artifacts expected from this strategy (e.g. hypothesis lists, comparison tables, sub-question decompositions)?
3. Is the answer structure consistent with what this strategy would produce?

Reply with a JSON object:
{{
  "score": <float 0.0-1.0>,
  "evidence": "one sentence describing what in the answer shows strategy was applied",
  "gaps": "one sentence describing what is missing or inconsistent with the strategy"
}}
Do NOT include any text outside the JSON.
""".strip()


# ── result dataclass ─────────────────────────────────────────────────────────

@dataclass
class CheckpointResult:
    checkpoint: str
    satisfied: bool
    reason: str
    eval_error: bool = False  # True when the LLM eval call itself failed


@dataclass
class OutputValidationReport:
    strategy_key: str
    strategy_name: str
    # checkpoint-based (when checkpoints exist)
    checkpoint_results: list[CheckpointResult] = field(default_factory=list)
    # generic score (always present)
    compliance_score: float = 0.0       # 0-1, higher = better
    evidence: str = ""                  # what in the answer shows strategy was applied
    gaps: str = ""                      # what is missing

    @property
    def checkpoints_passed(self) -> int:
        return sum(1 for r in self.checkpoint_results if r.satisfied and not r.eval_error)

    @property
    def checkpoints_total(self) -> int:
        # Only count checkpoints where eval actually ran (no LLM errors)
        return sum(1 for r in self.checkpoint_results if not r.eval_error)

    @property
    def checkpoints_errored(self) -> int:
        return sum(1 for r in self.checkpoint_results if r.eval_error)

    def summary_line(self) -> str:
        score_pct = f"{self.compliance_score:.0%}"
        if self.checkpoint_results:
            errored = self.checkpoints_errored
            err_note = f", {errored} eval errors" if errored else ""
            return (
                f"产出合规分数: {score_pct}  "
                f"({self.checkpoints_passed}/{self.checkpoints_total} checkpoints 通过{err_note})"
            )
        return f"产出合规分数: {score_pct}"


# ── validator ────────────────────────────────────────────────────────────────

class OutputValidator:
    """
    对 Agent 最终答案做产出验证。

    使用方式：
        validator = OutputValidator(spec, llm)
        report = validator.validate(final_answer)
    """

    def __init__(self, spec: StrategySpec, llm: ChatModel):
        self.spec = spec
        self.llm = llm

    def validate(self, answer: str) -> OutputValidationReport:
        if not answer or not answer.strip():
            return OutputValidationReport(
                strategy_key=self.spec.key,
                strategy_name=self.spec.name,
                compliance_score=0.0,
                gaps="Agent produced no answer",
            )

        report = OutputValidationReport(
            strategy_key=self.spec.key,
            strategy_name=self.spec.name,
        )

        if self.spec.checkpoints:
            report.checkpoint_results = self._eval_checkpoints(answer)
            passed = report.checkpoints_passed
            total = report.checkpoints_total   # excludes eval-error checkpoints
            # generic score (always computed)
            generic = self._eval_generic(answer)
            report.evidence = generic.get("evidence", "")
            report.gaps = generic.get("gaps", "")
            if total > 0:
                # checkpoint score = fraction passed among evaluable checkpoints, weighted 70%
                checkpoint_score = passed / total
                report.compliance_score = round(0.7 * checkpoint_score + 0.3 * generic["score"], 3)
            else:
                # All checkpoints failed to evaluate (LLM unavailable) → fall back to generic
                logger.warning("All checkpoint evals failed; falling back to generic score only")
                report.compliance_score = round(generic["score"], 3)
        else:
            # no checkpoints → use generic only
            generic = self._eval_generic(answer)
            report.compliance_score = round(generic["score"], 3)
            report.evidence = generic.get("evidence", "")
            report.gaps = generic.get("gaps", "")

        return report

    # ── internal ────────────────────────────────────────────────────────────

    def _eval_checkpoints(self, answer: str) -> list[CheckpointResult]:
        results = []
        for cp in self.spec.checkpoints:
            prompt = _CHECKPOINT_EVAL_PROMPT.format(
                strategy_name=self.spec.name,
                checkpoint=cp,
                answer=answer[:4000],   # truncate to avoid huge payloads
            )
            try:
                resp = self.llm.chat_with_retry(
                    [{"role": "user", "content": prompt}], retry=1
                )
                raw = resp.choices[0].message.content or "{}"
                data = json.loads(raw)
                satisfied = bool(data.get("satisfied", False))
                reason = data.get("reason", "")
                results.append(CheckpointResult(checkpoint=cp, satisfied=satisfied, reason=reason))
            except Exception as exc:
                logger.warning("Checkpoint eval failed for '%s': %s", cp, exc)
                # Mark eval_error=True so this checkpoint is excluded from scoring
                results.append(CheckpointResult(
                    checkpoint=cp, satisfied=False,
                    reason=f"eval error: {exc}", eval_error=True,
                ))
        return results

    def _eval_generic(self, answer: str) -> dict:
        prompt = _GENERIC_EVAL_PROMPT.format(
            strategy_name=self.spec.name,
            full_text=self.spec.full_text,
            answer=answer[:4000],
        )
        try:
            resp = self.llm.chat_with_retry(
                [{"role": "user", "content": prompt}], retry=1
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            return {
                "score": max(0.0, min(1.0, float(data.get("score", 0.5)))),
                "evidence": data.get("evidence", ""),
                "gaps": data.get("gaps", ""),
            }
        except Exception as exc:
            logger.warning("Generic eval failed: %s", exc)
            return {"score": 0.5, "evidence": "", "gaps": str(exc)}


# ── formatting ───────────────────────────────────────────────────────────────

def format_output_validation_report(report: OutputValidationReport) -> str:
    icon = "✅" if report.compliance_score >= 0.7 else "⚠️" if report.compliance_score >= 0.4 else "❌"
    lines = [
        "=" * 60,
        f"📋 产出验证报告: {report.strategy_name}",
        "=" * 60,
        f"总体合规分数: {report.compliance_score:.1%}  {icon}",
    ]

    if report.checkpoint_results:
        errored = report.checkpoints_errored
        err_note = f", {errored} eval errors" if errored else ""
        lines += ["", f"Checkpoint 验证 ({report.checkpoints_passed}/{report.checkpoints_total} 通过{err_note}):"]
        for r in report.checkpoint_results:
            if r.eval_error:
                mark = "⚠️"
            else:
                mark = "✅" if r.satisfied else "❌"
            lines.append(f"  {mark} {r.checkpoint}")
            if r.reason:
                lines.append(f"     → {r.reason}")

    if report.evidence:
        lines += ["", f"策略应用证据: {report.evidence}"]
    if report.gaps:
        lines += [f"不足之处:     {report.gaps}"]

    lines.append("=" * 60)
    return "\n".join(lines)
