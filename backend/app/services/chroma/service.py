from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path


class ChromaService:
    def __init__(self, path: Path):
        self.path = path
        self._collection = None

    def collection(self):
        if self._collection is None:
            import chromadb

            client = chromadb.PersistentClient(path=str(self.path))
            self._collection = client.get_or_create_collection(
                "tax_knowledge"
            )
        return self._collection

    def remember(self, identifier: str, text: str, metadata: dict) -> None:
        if not text.strip():
            return
        self.collection().upsert(
            ids=[identifier],
            documents=[text],
            metadatas=[metadata],
            embeddings=[self._local_embedding(text)],
        )

    @staticmethod
    def _local_embedding(text: str, dimensions: int = 128) -> list[float]:
        vector = [0.0] * dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % dimensions
            vector[index] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
