from dataclasses import dataclass
from typing import Any

import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import settings


@dataclass
class RetrievedDocument:
    page_content: str
    metadata: dict[str, Any]


class ChromaVectorStore:
    def __init__(self) -> None:
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=settings.embedding_model,
            google_api_key=settings.google_api_key,
        )
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name
        )

    def similarity_search_with_score(
        self,
        query: str,
        k: int,
    ) -> list[tuple[RetrievedDocument, float]]:
        query_embedding = self.embeddings.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        return [
            (RetrievedDocument(page_content=content or "", metadata=metadata or {}), score)
            for content, metadata, score in zip(documents, metadatas, distances)
        ]


def load_vectorstore() -> ChromaVectorStore:
    return ChromaVectorStore()


def search_schemes(profile_query: str, top_k: int) -> list[dict]:
    vectorstore = load_vectorstore()
    matches = vectorstore.similarity_search_with_score(profile_query, k=top_k)

    return [
        {
            "scheme_id": document.metadata.get("scheme_id"),
            "name": document.metadata.get("name"),
            "category": document.metadata.get("category"),
            "state": document.metadata.get("state"),
            "source_url": document.metadata.get("source_url"),
            "content": document.page_content,
            "relevance_score": score,
        }
        for document, score in matches
    ]
