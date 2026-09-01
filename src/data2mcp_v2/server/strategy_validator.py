"""
策略验证器 - 检测LLM是否真正遵循了选定的检索策略

用于分析工具调用模式，判断实际执行是否符合策略预期
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolCallEvent:
    """工具调用事件"""
    tool_name: str
    timestamp: int  # 调用顺序索引
    is_parallel: bool  # 是否与其他工具并行


@dataclass
class StrategyValidationReport:
    """策略验证报告"""
    strategy_key: str
    strategy_name: str
    compliance_score: float  # 0-1，遵循度评分
    total_tool_calls: int
    parallel_calls: int
    sequential_calls: int
    distinct_tools: int
    tool_call_pattern: str  # 描述调用模式
    compliance_details: list[str]  # 详细的合规性检查结果
    violations: list[str]  # 违反策略的行为


class StrategyValidator:
    """策略验证器"""

    def __init__(self, strategy_key: str):
        self.strategy_key = strategy_key
        self.tool_calls: list[ToolCallEvent] = []

    def record_tool_call(self, tool_name: str, timestamp: int, is_parallel: bool = False):
        """记录一次工具调用"""
        self.tool_calls.append(ToolCallEvent(tool_name, timestamp, is_parallel))

    def analyze_pattern(self) -> StrategyValidationReport:
        """分析工具调用模式，生成验证报告"""
        if not self.tool_calls:
            return self._empty_report()

        # 基础统计
        total_calls = len(self.tool_calls)
        parallel_calls = sum(1 for call in self.tool_calls if call.is_parallel)
        sequential_calls = total_calls - parallel_calls
        distinct_tools = len(set(call.tool_name for call in self.tool_calls))

        # 分析调用模式
        pattern = self._describe_pattern()

        # 策略特定验证
        if self.strategy_key == "structured":
            report = self._validate_structured()
        elif self.strategy_key == "virtual":
            report = self._validate_virtual()
        elif self.strategy_key == "nominal":
            report = self._validate_nominal()
        elif self.strategy_key == "starbursting":
            report = self._validate_starbursting()
        else:
            report = self._generic_report()

        # 填充基础统计信息
        report.total_tool_calls = total_calls
        report.parallel_calls = parallel_calls
        report.sequential_calls = sequential_calls
        report.distinct_tools = distinct_tools
        report.tool_call_pattern = pattern

        return report

    def _describe_pattern(self) -> str:
        """描述工具调用模式"""
        if not self.tool_calls:
            return "No tool calls"

        # 检测模式
        is_batch_start = (
            len(self.tool_calls) >= 3 and
            all(call.is_parallel for call in self.tool_calls[:3])
        )

        if is_batch_start:
            return "Batch parallel → Sequential"

        # 检测交替模式
        parallel_count = sum(1 for call in self.tool_calls if call.is_parallel)
        if parallel_count == 0:
            return "Pure sequential"
        elif parallel_count == len(self.tool_calls):
            return "Pure parallel"
        else:
            return "Mixed parallel/sequential"

    def _validate_structured(self) -> StrategyValidationReport:
        """验证Structured Brainstorming策略"""
        compliance_details = []
        violations = []
        score = 1.0

        # 要求1：应该有并行调用
        parallel_ratio = (
            sum(1 for call in self.tool_calls if call.is_parallel) / len(self.tool_calls)
            if self.tool_calls else 0
        )

        if parallel_ratio >= 0.5:
            compliance_details.append("✅ High parallel call ratio (>50%)")
        elif parallel_ratio >= 0.3:
            compliance_details.append("⚠️ Moderate parallel calls (30-50%)")
            score -= 0.2
        else:
            violations.append("❌ Expected parallel queries, found mostly sequential")
            score -= 0.4

        # 要求2：应该查询多个不同工具
        distinct_tools = len(set(call.tool_name for call in self.tool_calls if call.tool_name != "end_with_message"))
        if distinct_tools >= 3:
            compliance_details.append(f"✅ Queried {distinct_tools} different tools (good coverage)")
        elif distinct_tools >= 2:
            compliance_details.append(f"⚠️ Queried {distinct_tools} tools (limited coverage)")
            score -= 0.2
        else:
            violations.append(f"❌ Only queried {distinct_tools} tool (poor coverage)")
            score -= 0.3

        # 要求3：不应该有早期过滤（通过调用次数判断）
        if len(self.tool_calls) >= 5:
            compliance_details.append("✅ Multiple rounds of queries (thorough exploration)")
        else:
            violations.append("⚠️ Few tool calls - may indicate early filtering")
            score -= 0.1

        return StrategyValidationReport(
            strategy_key="structured",
            strategy_name="Structured Brainstorming",
            compliance_score=max(0.0, min(1.0, score)),
            total_tool_calls=0,  # 会被填充
            parallel_calls=0,
            sequential_calls=0,
            distinct_tools=0,
            tool_call_pattern="",
            compliance_details=compliance_details,
            violations=violations
        )

    def _validate_virtual(self) -> StrategyValidationReport:
        """验证Virtual Brainstorming策略"""
        compliance_details = []
        violations = []
        score = 1.0

        # 要求1：应该是迭代式的（主要是串行）
        sequential_ratio = (
            sum(1 for call in self.tool_calls if not call.is_parallel) / len(self.tool_calls)
            if self.tool_calls else 0
        )

        if sequential_ratio >= 0.7:
            compliance_details.append("✅ Mainly sequential calls (iterative pattern)")
        elif sequential_ratio >= 0.5:
            compliance_details.append("⚠️ Mixed pattern (less iterative than expected)")
            score -= 0.2
        else:
            violations.append("❌ Expected iterative queries, found mostly parallel")
            score -= 0.4

        # 要求2：应该有多轮反思（通过调用间隔判断）
        if len(self.tool_calls) >= 4:
            compliance_details.append("✅ Multiple query rounds (sustained exploration)")
        else:
            violations.append("⚠️ Few rounds - may lack deep reflection")
            score -= 0.2

        # 要求3：工具可能重复（深入同一数据源）
        tool_names = [call.tool_name for call in self.tool_calls if call.tool_name != "end_with_message"]
        unique_tools = len(set(tool_names))
        if len(tool_names) > unique_tools:
            compliance_details.append("✅ Re-queried tools (deep dive into sources)")
        else:
            compliance_details.append("⚠️ No tool re-queries (may lack depth)")
            score -= 0.1

        return StrategyValidationReport(
            strategy_key="virtual",
            strategy_name="Virtual Brainstorming",
            compliance_score=max(0.0, min(1.0, score)),
            total_tool_calls=0,
            parallel_calls=0,
            sequential_calls=0,
            distinct_tools=0,
            tool_call_pattern="",
            compliance_details=compliance_details,
            violations=violations
        )

    def _validate_nominal(self) -> StrategyValidationReport:
        """验证Nominal Group策略"""
        compliance_details = []
        violations = []
        score = 1.0

        # 要求1：独立查询（每个工具只查一次）
        tool_names = [call.tool_name for call in self.tool_calls if call.tool_name != "end_with_message"]
        unique_tools = len(set(tool_names))

        if len(tool_names) == unique_tools:
            compliance_details.append("✅ Each tool queried independently (no cross-contamination)")
        else:
            violations.append("⚠️ Some tools re-queried (may indicate contamination)")
            score -= 0.2

        # 要求2：应该查询多个工具
        if unique_tools >= 3:
            compliance_details.append(f"✅ Queried {unique_tools} independent sources")
        elif unique_tools >= 2:
            compliance_details.append(f"⚠️ Limited sources ({unique_tools} tools)")
            score -= 0.2
        else:
            violations.append("❌ Too few sources for ranking")
            score -= 0.4

        return StrategyValidationReport(
            strategy_key="nominal",
            strategy_name="Nominal Group",
            compliance_score=max(0.0, min(1.0, score)),
            total_tool_calls=0,
            parallel_calls=0,
            sequential_calls=0,
            distinct_tools=0,
            tool_call_pattern="",
            compliance_details=compliance_details,
            violations=violations
        )

    def _validate_starbursting(self) -> StrategyValidationReport:
        """验证Starbursting (5W1H)策略"""
        compliance_details = []
        violations = []
        score = 1.0

        # 要求1：应该有多次查询（对应6个维度）
        non_end_calls = [call for call in self.tool_calls if call.tool_name != "end_with_message"]

        if len(non_end_calls) >= 6:
            compliance_details.append("✅ 6+ queries (likely covered all 5W1H dimensions)")
        elif len(non_end_calls) >= 4:
            compliance_details.append("⚠️ 4-5 queries (may have missed some dimensions)")
            score -= 0.2
        else:
            violations.append("❌ Too few queries for 5W1H decomposition")
            score -= 0.4

        # 要求2：可能查询不同工具（不同维度可能需要不同数据源）
        distinct_tools = len(set(call.tool_name for call in non_end_calls))
        if distinct_tools >= 2:
            compliance_details.append(f"✅ Used {distinct_tools} different tools (dimension-specific)")
        else:
            compliance_details.append("⚠️ Only one tool used (may lack dimension diversity)")
            score -= 0.1

        return StrategyValidationReport(
            strategy_key="starbursting",
            strategy_name="Starbursting (5W1H)",
            compliance_score=max(0.0, min(1.0, score)),
            total_tool_calls=0,
            parallel_calls=0,
            sequential_calls=0,
            distinct_tools=0,
            tool_call_pattern="",
            compliance_details=compliance_details,
            violations=violations
        )

    def _generic_report(self) -> StrategyValidationReport:
        """通用报告（未知策略）"""
        return StrategyValidationReport(
            strategy_key=self.strategy_key,
            strategy_name="Unknown Strategy",
            compliance_score=1.0,
            total_tool_calls=0,
            parallel_calls=0,
            sequential_calls=0,
            distinct_tools=0,
            tool_call_pattern="",
            compliance_details=["Strategy validation not implemented"],
            violations=[]
        )

    def _empty_report(self) -> StrategyValidationReport:
        """空报告（无工具调用）"""
        return StrategyValidationReport(
            strategy_key=self.strategy_key,
            strategy_name="N/A",
            compliance_score=0.0,
            total_tool_calls=0,
            parallel_calls=0,
            sequential_calls=0,
            distinct_tools=0,
            tool_call_pattern="No tool calls",
            compliance_details=[],
            violations=["No tool calls were made"]
        )


def format_validation_report(report: StrategyValidationReport) -> str:
    """格式化验证报告为可读文本"""
    lines = [
        "=" * 60,
        f"📊 Strategy Validation Report: {report.strategy_name}",
        "=" * 60,
        f"Compliance Score: {report.compliance_score:.1%} {'✅' if report.compliance_score >= 0.7 else '⚠️' if report.compliance_score >= 0.5 else '❌'}",
        "",
        "Execution Statistics:",
        f"  • Total tool calls: {report.total_tool_calls}",
        f"  • Parallel calls: {report.parallel_calls}",
        f"  • Sequential calls: {report.sequential_calls}",
        f"  • Distinct tools: {report.distinct_tools}",
        f"  • Call pattern: {report.tool_call_pattern}",
        "",
    ]

    if report.compliance_details:
        lines.append("Compliance Checks:")
        for detail in report.compliance_details:
            lines.append(f"  {detail}")
        lines.append("")

    if report.violations:
        lines.append("Violations:")
        for violation in report.violations:
            lines.append(f"  {violation}")
        lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)
