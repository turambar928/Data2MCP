from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from data2mcp_v2.base_config import BaseConfig

from .db import DataFrameConfig, KGConfig, SQLDBConfig, VectorConfig
from .llm import LLMConfig
from .tool import ToolConfig

__all__ = [
    "AgentConfig",
    "SQLAgentConfig",
    "KGAgentConfig",
    "RAGAgentConfig",
    "DataFrameAgentConfig",
]


class AgentType(str, Enum):
    SQL_AGENT = "sql_agent"
    KG_AGENT = "kg_agent"
    RAG_Agent = "rag_agent"
    DataFrame_Agent = "dataframe_agent"


@dataclass
class BaseAgent(ToolConfig):
    type: AgentType = None

    def __post_init__(self):
        object.__setattr__(self, "type", AgentType(self.type))


@dataclass
class SQLAgentConfig(BaseAgent):
    agent_type: Literal["tool-calling", "zero-shot-react-description"] = "tool-calling"
    db_config: SQLDBConfig = field(default_factory=SQLDBConfig)
    llm_config: LLMConfig = field(default_factory=LLMConfig)


@dataclass
class KGAgentConfig(BaseAgent):
    allow_dangerous_requests: bool = False
    db_config: KGConfig = field(default_factory=KGConfig)
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    validate_cypher: bool = False


@dataclass
class RAGAgentConfig(BaseAgent):
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    db_config: VectorConfig = field(default_factory=VectorConfig)
    search_type: Literal["similarity", "mmr", "similarity_score_threshold"] = (
        "similarity"
    )
    top_k: int = 5
    # Minimum relevance threshold for similarity_score_threshold
    score_threshold: float = 0.8
    # Amount of documents to pass to MMR algorithm
    fetch_k: int = 20
    # Diversity of results returned by MMR
    lambda_mult: float = 0.5



@dataclass
class DataFrameAgentConfig(BaseAgent):
    db_config: DataFrameConfig = field(default_factory=DataFrameConfig)
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    agent_type: Literal["tool-calling", "zero-shot-react-description"] = "tool-calling"
    allow_dangerous_code: bool = False
    verbose: bool = False
    max_iterations: int = 15
    include_df_in_prompt: bool = True
    number_of_head_rows: int = 5
    engine: Literal["pandas", "modin"] = "pandas"


@dataclass
class AgentConfig(BaseConfig):
    agent_configs: list[BaseAgent] = field(default_factory=list)
    default_llm_config: LLMConfig = field(default_factory=LLMConfig)
