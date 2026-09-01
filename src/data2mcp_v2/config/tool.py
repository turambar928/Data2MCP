from dataclasses import dataclass

from data2mcp_v2.base_config import BaseConfig

__all__ = ["ToolConfig"]


@dataclass
class ToolConfig(BaseConfig):
    tool_name: str = "NotSet"
    tool_description: str = "NotSet"
