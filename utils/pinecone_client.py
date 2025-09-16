import os
from typing import List, Dict, Any, Optional, Tuple
from pinecone import Pinecone
import uuid

class PineconeClient:
    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "taya-memories")

        if not self.api_key:
            print("Warning: Pinecone API key not found. Vector search features disabled.")
            self.pc = None
            self.index = None
        else:
            try:
                self.pc = Pinecone(api_key=self.api_key)

                # Check if index exists
                existing_indexes = [idx.name for idx in self.pc.list_indexes()]

                if self.index_name not in existing_indexes:
                    print(f"Pinecone index '{self.index_name}' not found. Please create it manually in the Pinecone console.")
                    print(f"Index configuration: dimension=1536, metric=cosine")
                    self.index = None
                else:
                    self.index = self.pc.Index(self.index_name)
                    print(f"Connected to Pinecone index: {self.index_name}")

            except Exception as e:
                print(f"Pinecone initialization error: {e}")
                self.pc = None
                self.index = None

    def is_available(self) -> bool:
        """Check if Pinecone is available and configured"""
        return self.index is not None

    def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """
        Upsert vectors to Pinecone
        vectors format: [{"id": "unique_id", "values": [0.1, 0.2, ...], "metadata": {...}}]
        """
        if not self.is_available():
            return False

        try:
            self.index.upsert(vectors=vectors)
            return True
        except Exception as e:
            print(f"Pinecone upsert error: {e}")
            return False

    def query_vectors(self,
                     query_vector: List[float],
                     top_k: int = 10,
                     filter: Optional[Dict] = None,
                     include_metadata: bool = True) -> List[Dict[str, Any]]:
        """
        Query similar vectors from Pinecone
        Returns list of matches with id, score, and metadata
        """
        if not self.is_available():
            return []

        try:
            response = self.index.query(
                vector=query_vector,
                top_k=top_k,
                filter=filter,
                include_metadata=include_metadata
            )

            return [
                {
                    "id": match.id,
                    "score": match.score,
                    "metadata": match.metadata if include_metadata else None
                }
                for match in response.matches
            ]
        except Exception as e:
            print(f"Pinecone query error: {e}")
            return []

    def delete_vectors(self, ids: List[str]) -> bool:
        """Delete vectors by IDs"""
        if not self.is_available():
            return False

        try:
            self.index.delete(ids=ids)
            return True
        except Exception as e:
            print(f"Pinecone delete error: {e}")
            return False

    def get_stats(self) -> Optional[Dict[str, Any]]:
        """Get index statistics"""
        if not self.is_available():
            return None

        try:
            return self.index.describe_index_stats()
        except Exception as e:
            print(f"Pinecone stats error: {e}")
            return None

    def upsert_memory(self,
                     memory_id: str,
                     embedding: List[float],
                     text: str,
                     user_id: str,
                     metadata: Optional[Dict] = None) -> bool:
        """
        Upsert a memory with embedding
        Convenience method for memory-specific operations
        """
        memory_metadata = {
            "text": text,
            "user_id": user_id,
            "type": "memory"
        }

        if metadata:
            memory_metadata.update(metadata)

        vector = {
            "id": memory_id,
            "values": embedding,
            "metadata": memory_metadata
        }

        return self.upsert_vectors([vector])

    def search_memories(self,
                       query_embedding: List[float],
                       user_id: str,
                       top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar memories for a specific user
        """
        filter_dict = {"user_id": user_id, "type": "memory"}

        return self.query_vectors(
            query_vector=query_embedding,
            top_k=top_k,
            filter=filter_dict,
            include_metadata=True
        )

# Global Pinecone client instance
pinecone_client = PineconeClient()