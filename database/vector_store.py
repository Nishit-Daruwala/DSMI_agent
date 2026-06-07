import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


def _embed_via_openai(texts: List[str]) -> List[List[float]]:
    """
    Use OpenAI's text-embedding-3-small model (1536 dims) via a lightweight
    HTTP call. This avoids loading the ~400 MB sentence-transformers + PyTorch
    stack and keeps memory well under Render's 512 MB free-tier limit.
    """
    import requests as _req

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for embeddings")

    resp = _req.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"input": texts, "model": "text-embedding-3-small"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()["data"]
    # Return vectors in the same order as input
    return [item["embedding"] for item in sorted(data, key=lambda x: x["index"])]


class VectorStore:
    # text-embedding-3-small produces 1536-dimensional vectors
    VECTOR_SIZE = 1536

    def __init__(self, collection_name: str = "research_embeddings"):
        self.collection_name = collection_name
        self.vector_size = self.VECTOR_SIZE

        # Try to connect to Qdrant Cloud
        connected = False
        if QDRANT_URL and QDRANT_API_KEY:
            try:
                clean_url = QDRANT_URL.strip().rstrip('/')
                self.client = QdrantClient(url=clean_url, api_key=QDRANT_API_KEY)
                self._ensure_collection_exists()
                print(f"Successfully connected to Qdrant Cloud at {clean_url}")
                connected = True
            except Exception as e:
                print(f"WARNING: Qdrant Cloud connection failed ({e}). Falling back to in-memory Qdrant.")

        if not connected:
            try:
                self.client = QdrantClient(":memory:")
                self._ensure_collection_exists()
                print("Using in-memory Qdrant (data will not persist across restarts)")
            except Exception as e:
                print(f"WARNING: Could not initialize any Qdrant client: {e}")
                self.client = None

    # ── helpers ────────────────────────────────────────────────
    def _ensure_collection_exists(self):
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            print(f"Created Qdrant collection '{self.collection_name}' ({self.vector_size}d)")

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string via OpenAI API."""
        return _embed_via_openai([text])[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in one API call."""
        return _embed_via_openai(texts)

    # ── public API (unchanged signatures) ─────────────────────
    def store_research(self, session_id: str, query: str, sources: List[Dict],
                       report: str, quality_score: float) -> bool:
        if not self.client:
            return False
        try:
            texts_to_embed = [query, report[:2000]]
            vectors = self.embed_texts(texts_to_embed)

            points = [
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[0],
                    payload={
                        "session_id": session_id,
                        "type": "query",
                        "content": query,
                        "quality_score": quality_score,
                        "source_count": len(sources),
                    },
                ),
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vectors[1],
                    payload={
                        "session_id": session_id,
                        "type": "report",
                        "content": report[:2000],
                        "quality_score": quality_score,
                    },
                ),
            ]

            for src in sources[:5]:
                src_text = f"{src.get('title', '')} {src.get('snippet', '')}"
                if src_text.strip():
                    vec = self.embed_text(src_text)
                    points.append(
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vec,
                            payload={
                                "session_id": session_id,
                                "type": "source",
                                "url": src.get("url", ""),
                                "title": src.get("title", ""),
                                "content": src.get("snippet", ""),
                            },
                        )
                    )

            self.client.upsert(collection_name=self.collection_name, points=points)
            print(f"Stored {len(points)} vectors for session {session_id}")
            return True
        except Exception as e:
            print(f"WARNING: Vector storage failed: {e}")
            return False

    def find_related_research(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            vector = self.embed_text(query)
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                score_threshold=0.60,
            )
            results = []
            for scored_point in search_result.points:
                res = scored_point.payload
                res["similarity_score"] = scored_point.score
                results.append(res)
            return results
        except Exception as e:
            print(f"WARNING: Qdrant semantic search failed: {e}")
            return []

    def find_similar_sources(self, text: str, limit: int = 1) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            vector = self.embed_text(text)
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                score_threshold=0.95,
            )
            return [
                {**sp.payload, "similarity_score": sp.score}
                for sp in search_result.points
            ]
        except Exception as e:
            print(f"WARNING: Similarity search failed: {e}")
            return []

    def get_collection_stats(self) -> Dict[str, Any]:
        if not self.client:
            return {"status": "not_connected"}
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "collection": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": str(info.status),
            }
        except Exception as e:
            return {"status": "error", "detail": str(e)}
