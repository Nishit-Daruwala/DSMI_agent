import os
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

class VectorStore:
    def __init__(self, collection_name: str = "research_embeddings"):
        self.collection_name = collection_name
        
        # Initialize the embedding model first (MiniLM-L6-v2 is fast and good)
        self.embedding_model_name = 'all-MiniLM-L6-v2'
        self.encoder = SentenceTransformer(self.embedding_model_name)
        
        # Dimensions for all-MiniLM-L6-v2 is 384
        self.vector_size = self.encoder.get_sentence_embedding_dimension()
        
        # Try to connect to Qdrant Cloud
        connected = False
        if QDRANT_URL and QDRANT_API_KEY:
            try:
                # Clean URL (remove trailing slashes)
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
                print("Using local in-memory Qdrant client.")
            except Exception as local_err:
                print(f"CRITICAL: Failed to initialize local memory Qdrant: {local_err}")
                self.client = None

    def _ensure_collection_exists(self):
        """Creates the Qdrant collection if it doesn't already exist."""
        if not self.client:
            return
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            print(f"Creating Qdrant collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
            
    def embed_text(self, text: str) -> List[float]:
        """Convert text into a vector embedding."""
        try:
            if not text:
                return [0.0] * self.vector_size
            return self.encoder.encode(text).tolist()
        except Exception as e:
            print(f"WARNING: Embedding generation failed: {e}")
            return [0.0] * self.vector_size

    def store_research(self, session_id: str, content: str, metadata: Dict[str, Any] = None):
        """
        Store a piece of research content in the vector DB.
        """
        if not self.client or not content:
            return
            
        try:
            vector = self.embed_text(content)
            point_id = str(uuid.uuid4())
            
            payload = {"session_id": session_id, "content": content}
            if metadata:
                payload.update(metadata)
                
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload
                    )
                ]
            )
            print(f"Stored 1 embedding for session {session_id}")
        except Exception as e:
            print(f"WARNING: Failed to store research in Qdrant: {e}")

    def semantic_search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find past research related to the new query.
        """
        if not self.client:
            return []
            
        try:
            vector = self.embed_text(query)
            
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                score_threshold=0.60 # Only return fairly relevant results
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
        """
        Help deduplication by finding sources with identical/nearly-identical content.
        """
        if not self.client:
            return []
            
        try:
            vector = self.embed_text(text)
            
            # Score > 0.95 means it's incredibly similar (likely the same source re-scraped)
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                score_threshold=0.95
            )
            
            return [point.payload for point in search_result.points]
        except Exception as e:
            print(f"WARNING: Qdrant similarity search failed: {e}")
            return []
            
    def delete_session(self, session_id: str):
        """Clean up vectors for a single session if needed."""
        if not self.client:
            return
            
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="session_id",
                            match=MatchValue(value=session_id)
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"WARNING: Failed to delete session from Qdrant: {e}")
