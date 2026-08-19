"""Minimal hybrid-memory assistant used by ``bonus/demo.py``.

The class intentionally keeps the profile adapter small. Replace it with a
Feast FeatureStore in production; the vector-memory contract stays the same.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import QdrantClient, models

from app.embeddings import Embedder


@dataclass
class FeatureStoreAdapter:
    profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    activity: dict[str, list[str]] = field(default_factory=dict)

    def profile(self, user_id: str) -> dict[str, Any]:
        return self.profiles.get(user_id, {
            "preferred_language": "vi", "reading_speed_wpm": 220,
            "topic_affinity": "cloud", "active_hours": "20:00-23:00",
        })

    def record_query(self, user_id: str, query: str) -> None:
        recent = self.activity.setdefault(user_id, [])
        recent.append(query)
        del recent[:-20]

    def recent(self, user_id: str) -> dict[str, Any]:
        queries = self.activity.get(user_id, [])
        topics = ("cloud", "security", "ai_ml", "database", "devops")
        counts = {t: sum(t in q.lower() for q in queries) for t in topics}
        return {
            "queries_last_hour": len(queries),
            "distinct_topics_24h": sum(v > 0 for v in counts.values()),
            "top_recent_topic": max(counts, key=counts.get) if queries else "-",
        }


class HybridMemoryAgent:
    COLLECTION = "bonus_episodic_memory"

    def __init__(self, client: QdrantClient | None = None,
                 embedder: Embedder | None = None,
                 feature_store: FeatureStoreAdapter | None = None) -> None:
        self.client = client or QdrantClient(":memory:")
        # Bonus memory is local by default; the key is reserved for final
        # generation. Opt into a different embedding backend explicitly.
        self.embedder = embedder or Embedder(
            backend=os.getenv("BONUS_EMBEDDING_BACKEND", "fastembed"),
        )
        self.features = feature_store or FeatureStoreAdapter()
        if self.COLLECTION in {c.name for c in self.client.get_collections().collections}:
            self.client.delete_collection(self.COLLECTION)
        self.client.create_collection(
            collection_name=self.COLLECTION,
            vectors_config=models.VectorParams(
                size=self.embedder.dim, distance=models.Distance.COSINE,
            ),
        )
        self._next_id = 0

    def _embed(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self.embedder.embed(texts)]

    @staticmethod
    def _chunks(text: str, words: int = 120, overlap: int = 15) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        result: list[str] = []
        for paragraph in paragraphs or [text.strip()]:
            tokens = paragraph.split()
            for start in range(0, len(tokens), max(1, words - overlap)):
                chunk = " ".join(tokens[start:start + words]).strip()
                if chunk:
                    result.append(chunk)
        return result

    def remember(self, text: str, user_id: str = "u_001") -> None:
        chunks = self._chunks(text)
        vectors = self._embed(chunks)
        self.client.upsert(
            collection_name=self.COLLECTION,
            points=[models.PointStruct(
                id=self._next_id + i, vector=vector,
                payload={"user_id": user_id, "text": chunk},
            ) for i, (chunk, vector) in enumerate(zip(chunks, vectors))],
        )
        self._next_id += len(chunks)

    def recall(self, query: str, user_id: str = "u_001", top_k: int = 3) -> str:
        self.features.record_query(user_id, query)
        profile = self.features.profile(user_id)
        activity = self.features.recent(user_id)
        qv = self._embed([query])[0]
        result = self.client.query_points(
            collection_name=self.COLLECTION, query=qv, limit=top_k,
            query_filter=models.Filter(must=[models.FieldCondition(
                key="user_id", match=models.MatchValue(value=user_id),
            )]),
        )
        memories = [p.payload["text"] for p in result.points]
        memory_text = "\n".join(f"- {text}" for text in memories) or "- (no matching memory)"
        return (
            f"User profile: language={profile['preferred_language']}; "
            f"reading_speed={profile['reading_speed_wpm']} wpm; "
            f"topic_affinity={profile['topic_affinity']}; "
            f"active_hours={profile['active_hours']}\n"
            f"Recent activity: {activity['queries_last_hour']} queries in this session; "
            f"{activity['distinct_topics_24h']} distinct topics; "
            f"top_recent_topic={activity['top_recent_topic']}\n"
            f"Top episodic memories for {query!r}:\n{memory_text}"
        )

    def answer(self, query: str, user_id: str = "u_001") -> str:
        context = self.recall(query, user_id)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return context
        from openai import OpenAI
        response = OpenAI(api_key=api_key).responses.create(
            model=os.getenv("BONUS_MODEL", "gpt-4o-mini"),
            instructions=("You are a concise Vietnamese personal assistant. "
                          "Use only the supplied memory context; say when it is insufficient. "
                          "Do not reveal internal metadata or another user's memory."),
            input=f"Memory context:\n{context}\n\nUser question: {query}",
        )
        return response.output_text
