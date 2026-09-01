from dataclasses import dataclass, field
from enum import Enum

from data2mcp_v2.base_config import BaseConfig

from .db_agent import AgentConfig
from .llm import LLMConfig

__all__ = ["Data2McpConfig"]


class RouteType(str, Enum):
    SELECTION = "selection"
    FUSION = "fusion"
    HYBRID = "hybrid"
    AGENTIC = "agentic"


@dataclass
class Data2McpConfig(BaseConfig):
    agents: AgentConfig = field(default_factory=AgentConfig)
    route_type: RouteType = RouteType.SELECTION
    llm: LLMConfig = field(default_factory=LLMConfig)
    tool_call_timeout: int = 300
    tool_call_max_length: int = 10000
    max_turns: int = 5  # 给复杂问题更长的对话上限
    min_tool_calls: int = 0  # 至少调用若干次工具后再允许结束
    min_charts_required: int = 2  # 数据分析任务至少需要生成的图表数量
    retrieval_strategy: str = ""  # 检索策略指令文本（结构化分析技术）
    strategy_key: str = ""  # 对应 extracted_strategies.json 里的 key，用于产出验证
    auto_select_strategy: bool = False  # 后端自动选择检索策略
    auto_strategy_candidates: list[str] = field(default_factory=list)  # 可选策略key
    max_refinement_rounds: int = 0  # 产出验证不通过时最多重试几轮（0=不重试）
    refinement_threshold: float = 0.7  # 合规分数低于此值才触发重试
