from __future__ import annotations

import hashlib
import logging
import math
import re

import httpx

from inkdesk_server.core.config import Settings


logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.provider = settings.resolved_embedding_provider

    @property
    def embedding_configured(self) -> bool:
        if self.provider.profile == "deterministic":
            return True
        return bool(self.provider.api_key)

    @property
    def retrieval_mode(self) -> str:
        return "hybrid" if self.embedding_configured else "lexical_fallback"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self.embedding_configured:
            return [[] for _ in texts]
        if self.provider.profile == "deterministic":
            return [self._deterministic_embedding(text) for text in texts]

        payload = {"model": self.provider.model, "input": texts}
        headers = {"Authorization": f"Bearer {self.provider.api_key}"} if self.provider.api_key else {}
        try:
            with httpx.Client(
                base_url=self.provider.base_url or "https://api.openai.com/v1",
                timeout=(self.settings.agent_connect_timeout_seconds, self.settings.agent_read_timeout_seconds),
            ) as client:
                response = client.post("/embeddings", json=payload, headers=headers)
                response.raise_for_status()
                data = response.json().get("data", [])
                embeddings = [item.get("embedding", []) for item in data]
                if len(embeddings) == len(texts):
                    return [self._normalize_embedding(vector) for vector in embeddings]
        except Exception:
            logger.exception("Embedding provider failed; falling back to deterministic embeddings.")
        return [self._deterministic_embedding(text) for text in texts]

    def cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        return max(-1.0, min(1.0, sum(a * b for a, b in zip(left, right))))

    def _normalize_embedding(self, values: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in values))
        if norm <= 0:
            return [0.0 for _ in values]
        return [value / norm for value in values]

    def _deterministic_embedding(self, text: str) -> list[float]:
        tokens = re.findall(r"[\w\u4e00-\u9fff]+", (text or "").lower())
        dimensions = 32
        vector = [0.0 for _ in range(dimensions)]
        if not tokens:
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % dimensions
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            vector[index] += sign * (1.0 + min(len(token), 12) / 12.0)
        return self._normalize_embedding(vector)
