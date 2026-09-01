from typing import Any

from langchain_community.retrievers import ElasticSearchBM25Retriever
from langchain_core.callbacks import (
    CallbackManagerForRetrieverRun,
)
from langchain_core.documents import Document


class CustomElasticBM25Retriever(ElasticSearchBM25Retriever):
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    client: Any
    """Elasticsearch client."""
    index_name: str
    """Name of the index to use in Elasticsearch."""
    k: int = 10
    """Number of hits to retrieve."""

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        query_dict = {"query": {"match": {"content": query}}, "size": self.k}
        res = self.client.search(index=self.index_name, body=query_dict)

        docs = []
        for r in res["hits"]["hits"]:
            docs.append(Document(page_content=r["_source"]["content"]))
        return docs
