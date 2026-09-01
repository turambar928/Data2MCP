import logging
from pathlib import Path

from langchain_community.document_loaders.text import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import MarkdownTextSplitter, TextSplitter

from data2mcp_v2.config import DBType, EmbeddingConfig, VectorConfig

logger = logging.getLogger(__name__)


def init_vector_store(vector_config: VectorConfig):
    db_type: DBType = vector_config.type
    if db_type == DBType.FAISS:
        embedding_config: EmbeddingConfig = vector_config.embedding_config
        embedding_model = OpenAIEmbeddings(
            model=embedding_config.model,
            base_url=embedding_config.base_url,
            api_key=embedding_config.api_key,
            show_progress_bar=True,
            chunk_size=embedding_config.chunk_size,
        )
        vector_store = FAISS.load_local(
            vector_config.save_path,
            embedding_model,
            index_name=vector_config.index_name,
            allow_dangerous_deserialization=vector_config.allow_dangerous_deserialization,
        )
    else:
        raise ValueError(f"Unsupported vector store type: {db_type}")
    return vector_store


def init_vector_store_with_docs(docs: list[Document], vector_config: VectorConfig):
    db_type: DBType = vector_config.type
    if db_type == DBType.FAISS:
        embedding_config: EmbeddingConfig = vector_config.embedding_config
        embedding_model = OpenAIEmbeddings(
            model=embedding_config.model,
            base_url=embedding_config.base_url,
            api_key=embedding_config.api_key,
            show_progress_bar=True,
            dimensions=embedding_config.dimensions,
            model_kwargs={"encoding_format": embedding_config.encoding_format},
            check_embedding_ctx_length=False,
            chunk_size=embedding_config.chunk_size,
        )
        vector_store = FAISS.from_documents(documents=docs, embedding=embedding_model)
        vector_store.save_local(
            vector_config.save_path, index_name=vector_config.index_name
        )
        logger.info(
            f"Vector store saved at {Path(vector_config.save_path) / f'{vector_config.index_name}.faiss'}"
        )
    else:
        raise ValueError(f"Unsupported vector store type: {db_type}")
    return vector_store


def indexing_loop(
    loaders: list[BaseLoader],
    splitter: TextSplitter,
    vector_config: VectorConfig,
):
    """Index documents from the loader into the vector store in batches."""
    vector_store_path = (
        Path(vector_config.save_path) / f"{vector_config.index_name}.faiss"
    )
    if vector_store_path.is_file():
        logger.info(
            f"Vector store already exists at {vector_store_path}, loading it directly."
        )
        return init_vector_store(vector_config)
    else:
        logger.info("Vector store does not exist, indexing documents.")
        all_docs: list[Document] = []
        for loader in loaders:
            all_docs += loader.load()
        split_docs: list[Document] = splitter.split_documents(all_docs)
        vector_store = init_vector_store_with_docs(split_docs, vector_config)
    return vector_store


def indexing_data(vector_config: VectorConfig) -> VectorStore:
    data_path = Path(vector_config.data_path)
    if not data_path.is_file():
        raise ValueError(f"Data path is not a file: {data_path}")
    ext = data_path.suffix.lower()
    if ext in [".txt", ".md", ".markdown"]:
        loader_cls = TextLoader
    if ext in [".md", ".markdown"]:
        splitter_cls = MarkdownTextSplitter
    return indexing_loop(
        loaders=[loader_cls(file_path=data_path, **vector_config.loader_kwargs)],
        splitter=splitter_cls(**vector_config.splitter_kwargs),
        vector_config=vector_config,
    )
