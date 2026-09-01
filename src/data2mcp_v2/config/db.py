from dataclasses import dataclass, field
from enum import Enum

from data2mcp_v2.base_config import BaseConfig

from .llm import EmbeddingConfig

__all__ = [
    "SQLDBConfig",
    "KGConfig",
    "VectorConfig",
    "ESConfig",
    "DataFrameConfig",
    "DBType",
]


class DBType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    NEO4J = "neo4j"
    ELASTICSEARCH = "elasticsearch"
    FAISS = "faiss"
    CSV = "csv"
    JSON = "json"


DB_GROUPS = {
    "SQL": [DBType.MYSQL, DBType.POSTGRESQL, DBType.SQLITE],
    "KG": [DBType.NEO4J],
    "TEXT": [DBType.ELASTICSEARCH],
    "DATAFRAME": [DBType.CSV, DBType.JSON],
}


@dataclass
class BaseDBConfig(BaseConfig):
    type: DBType = None

    def __post_init__(self):
        object.__setattr__(self, "type", DBType(self.type))


@dataclass
class SQLDBConfig(BaseDBConfig):
    host: str = None
    port: int = None
    user: str = None
    password: str = None
    db_name: str = None
    # For SQLite
    file_path: str = None

    def __post_init__(self):
        if self.type == DBType.SQLITE and not self.file_path:
            raise ValueError("file_path must be set for SQLite databases.")
        elif self.type in {DBType.MYSQL, DBType.POSTGRESQL} and not all(
            [self.host, self.port, self.user, self.password, self.db_name]
        ):
            raise ValueError(
                f"host, port, user, password and db_name must be set for {self.type} databases."
            )


@dataclass
class KGConfig(BaseDBConfig):
    host: str = None
    port: int = None
    user: str = None
    password: str = None


@dataclass
class VectorConfig(BaseDBConfig):
    # data path
    data_path: str = None
    # vector store path
    save_path: str = None
    # vector index name
    index_name: str = "index"
    allow_dangerous_deserialization: bool = False
    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    # loader kwords
    loader_kwargs: dict = None
    splitter_kwargs: dict = None



@dataclass
class ESConfig(BaseDBConfig):
    host: str = None
    port: int = None
    user: str = None
    password: str = None
    index_name: str = None


@dataclass
class DataFrameConfig(BaseDBConfig):
    save_path: str = None
