from dataclasses import dataclass, field

from data2mcp_v2.base_config import BaseConfig

from .llm import LLMConfig

__all__ = ["EvaluationConfig"]


@dataclass
class EvaluationConfig(BaseConfig):
    llm: LLMConfig = field(default_factory=LLMConfig)
