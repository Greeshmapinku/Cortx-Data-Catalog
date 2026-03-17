"""Embedding generation and storage module."""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer

from cortx_catalog.models import CatalogEntry, SemanticData


class Embedder:
    """Creates and manages embeddings for semantic search."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embedder.
        
        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embeddings: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    def create_embedding_text(self, semantic: SemanticData) -> str:
        """Create text block for embedding from semantic data.
        
        Concatenates title + description + query_hints as specified in requirements.
        
        Args:
            semantic: Semantic data
            
        Returns:
            Text string for embedding
        """
        parts = [
            semantic.title,
            semantic.description,
            " ".join(semantic.query_hints),
        ]
        return " ".join(parts)
    
    def embed_entry(self, entry: CatalogEntry) -> np.ndarray:
        """Create embedding for a catalog entry.
        
        Args:
            entry: Catalog entry
            
        Returns:
            Embedding vector
        """
        text = self.create_embedding_text(entry.semantic)
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def add_entry(self, entry: CatalogEntry) -> None:
        """Add entry to embedding store.
        
        Args:
            entry: Catalog entry to add
        """
        embedding = self.embed_entry(entry)
        source_id = entry.source_id
        
        self.embeddings[source_id] = embedding
        self.metadata[source_id] = {
            "source_id": entry.source_id,
            "source_type": entry.source_type,
            "title": entry.semantic.title,
            "domain_tags": entry.semantic.domain_tags,
        }
    
    def search(
        self, query: str, top_k: int = 3
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar entries using cosine similarity.
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of (source_id, confidence_score, metadata) tuples
        """
        if not self.embeddings:
            return []
        
        # Encode query
        query_embedding = self.model.encode(query, convert_to_numpy=True)
        
        # Calculate cosine similarity with all entries
        results = []
        for source_id, embedding in self.embeddings.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            results.append((source_id, float(similarity), self.metadata.get(source_id, {})))
        
        # Sort by similarity (descending) and take top_k
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Cosine similarity score (0.0 - 1.0)
        """
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored embeddings.
        
        Returns:
            Dictionary with embedding stats
        """
        return {
            "model": self.model_name,
            "dimension": self.model.get_sentence_embedding_dimension(),
            "num_entries": len(self.embeddings),
        }
