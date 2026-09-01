from dataclasses import dataclass

from data2mcp_v2.base_config import BaseConfig

__all__ = ["LLMConfig", "EmbeddingConfig"]


@dataclass
class LLMConfig(BaseConfig):
    model: str = "gpt-4-turbo"
    temperature: float = 0.0
    max_tokens: int | None = None
    timeout_seconds: int = 60
    max_retries: int = 3
    base_url: str | None = None
    api_key: str | None = None


@dataclass
class EmbeddingConfig(BaseConfig):
    model: str = "text-embedding-3-large"
    base_url: str | None = None
    api_key: str | None = None
    dimensions: int | None = None
    encoding_format: str = "base64"  # "base64" or "float"
    chunk_size: int = 1000
