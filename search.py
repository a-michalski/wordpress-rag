"""
Two-stage hybrid search with ColBERT reranking.
Stage 1: Dense recall with diversity (group_by document_id)
Stage 2: ColBERT MaxSim reranking for precision
"""
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
import numpy as np

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Range,
    DatetimeRange,
    ScoredPoint,
)

import config
from embeddings import HybridEmbedder
from qdrant_setup import create_qdrant_client


@dataclass
class SearchResult:
    """Search result with metadata."""
    chunk_id: str
    document_id: str
    title: str
    url: str
    text: str
    score: float
    section_type: str
    
    # Optional metadata
    author: Optional[str] = None
    publication_date: Optional[str] = None
    categories: List[str] = None
    tags: List[str] = None
    chunk_index: Optional[int] = None


class HybridSearchEngine:
    """
    Two-stage hybrid search engine with ColBERT reranking.
    
    Stage 1: Dense vector search with diversity (group_by document_id)
    Stage 2: ColBERT late interaction reranking (MaxSim scoring)
    """
    
    def __init__(
        self,
        client: QdrantClient = None,
        collection_name: str = None,
    ):
        """
        Initialize search engine.
        
        Args:
            client: QdrantClient instance
            collection_name: Name of collection to search
        """
        self.client = client if client else create_qdrant_client()
        self.collection_name = collection_name or config.QDRANT_COLLECTION_NAME
        self.embedder = HybridEmbedder()
    
    def search(
        self,
        query: str,
        top_k: int = None,
        filters: Optional[Dict] = None,
    ) -> List[SearchResult]:
        """
        Two-stage hybrid search with reranking.
        
        Args:
            query: Search query text
            top_k: Number of final results (after reranking)
            filters: Optional filters dict with 'tags', 'categories', 'date_range', 'section_type'
            
        Returns:
            List of search results, ranked by relevance
        """
        if top_k is None:
            top_k = config.FINAL_RESULTS_LIMIT
        
        # Stage 1: Dense recall with diversity
        print(f"Stage 1: Dense recall (top {config.RECALL_LIMIT} candidates)...")
        candidates = self._dense_recall(
            query=query,
            limit=config.RECALL_LIMIT,
            filters=filters,
        )
        
        if not candidates:
            print("No candidates found in dense recall")
            return []
        
        print(f"Found {len(candidates)} candidates")
        
        # Stage 2: ColBERT reranking
        print(f"Stage 2: ColBERT reranking (MaxSim scoring)...")
        reranked_results = self._colbert_rerank(
            query=query,
            candidates=candidates,
            top_k=top_k,
        )
        
        print(f"Returning top {len(reranked_results)} results")
        return reranked_results
    
    def _dense_recall(
        self,
        query: str,
        limit: int,
        filters: Optional[Dict] = None,
    ) -> List[ScoredPoint]:
        """
        Stage 1: Dense vector search with diversity.
        
        Args:
            query: Search query
            limit: Number of candidates to retrieve
            filters: Optional filters
            
        Returns:
            List of candidate points
        """
        # Generate dense embedding for query
        query_embedding = self.embedder.dense.embed(query)
        
        # Build Qdrant filter
        qdrant_filter = self._build_filter(filters) if filters else None
        
        # Add grouping if enabled - use search_groups API
        if config.ENABLE_GROUPING:
            # Use search_groups for diversity (max 1 result per document)
            results = self.client.search_groups(
                collection_name=self.collection_name,
                query_vector=("dense", query_embedding.tolist()),
                group_by=config.GROUP_BY_FIELD,
                group_size=config.GROUP_SIZE,
                limit=limit,  # Number of groups
                query_filter=qdrant_filter,
                with_payload=True,
            )
            
            # Flatten groups to points
            candidates = []
            for group in results.groups:
                candidates.extend(group.hits)
        else:
            # Standard search without grouping
            candidates = self.client.search(
                collection_name=self.collection_name,
                query_vector=("dense", query_embedding.tolist()),
                limit=limit,
                query_filter=qdrant_filter,
                with_payload=True,
            )
        
        return candidates
    
    def _colbert_rerank(
        self,
        query: str,
        candidates: List[ScoredPoint],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Stage 2: Rerank candidates using ColBERT MaxSim scoring.
        
        Args:
            query: Search query
            candidates: Candidate points from dense recall
            top_k: Number of results to return
            
        Returns:
            Reranked search results
        """
        if not candidates:
            return []
        
        # Generate ColBERT query embeddings (multiple vectors per query)
        query_vectors = self.embedder.colbert.embed(query)
        query_vectors = np.array(query_vectors)  # Shape: (num_query_tokens, embedding_dim)
        
        # Batch retrieve all ColBERT vectors at once (much faster than one-by-one)
        candidate_ids = [c.id for c in candidates]
        points_with_vectors = self.client.retrieve(
            collection_name=self.collection_name,
            ids=candidate_ids,
            with_vectors=["colbert"],  # Only fetch ColBERT vectors
            with_payload=False,  # Already have payload from search
        )
        
        # Create mapping from id to ColBERT vectors
        id_to_vectors = {}
        for point in points_with_vectors:
            vectors = point.vector.get("colbert", []) if point.vector else []
            id_to_vectors[point.id] = np.array(vectors) if vectors else None
        
        # Compute MaxSim score for each candidate
        scored_candidates = []
        
        for candidate in candidates:
            doc_vectors = id_to_vectors.get(candidate.id)
            
            if doc_vectors is None or len(doc_vectors) == 0:
                # Fallback to dense score if ColBERT vectors not available
                score = candidate.score
            else:
                # Compute MaxSim score
                score = self._compute_maxsim(query_vectors, doc_vectors)
            
            scored_candidates.append((candidate, score))
        
        # Sort by ColBERT score
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Convert top-k to SearchResult objects
        results = []
        for candidate, score in scored_candidates[:top_k]:
            result = self._point_to_result(candidate, score)
            results.append(result)
        
        return results
    
    def _compute_maxsim(
        self,
        query_vectors: np.ndarray,
        doc_vectors: np.ndarray,
    ) -> float:
        """
        Compute MaxSim score between query and document ColBERT vectors.
        
        MaxSim: For each query token, find max similarity with any doc token,
        then sum across all query tokens.
        
        Args:
            query_vectors: Query token embeddings (num_query_tokens, dim)
            doc_vectors: Document token embeddings (num_doc_tokens, dim)
            
        Returns:
            MaxSim score (higher is better)
        """
        # Compute cosine similarity matrix: (num_query_tokens, num_doc_tokens)
        # Normalize vectors
        query_norm = query_vectors / (np.linalg.norm(query_vectors, axis=1, keepdims=True) + 1e-8)
        doc_norm = doc_vectors / (np.linalg.norm(doc_vectors, axis=1, keepdims=True) + 1e-8)
        
        # Compute similarity matrix
        sim_matrix = np.dot(query_norm, doc_norm.T)
        
        # MaxSim: max over doc tokens, then sum over query tokens
        max_sims = np.max(sim_matrix, axis=1)
        maxsim_score = np.sum(max_sims)
        
        return float(maxsim_score)
    
    def _build_filter(self, filters: Dict) -> Filter:
        """
        Build Qdrant filter from filter dictionary.
        
        Supported filters:
        - tags: List of tags (any match)
        - categories: List of categories (any match)
        - date_range: Dict with 'start' and/or 'end' dates
        - section_type: String or list of section types
        
        Args:
            filters: Dictionary with filter criteria
            
        Returns:
            Qdrant Filter object
        """
        conditions = []
        
        # Tag filter
        if "tags" in filters and filters["tags"]:
            tags = filters["tags"] if isinstance(filters["tags"], list) else [filters["tags"]]
            conditions.append(
                FieldCondition(
                    key="tags",
                    match=MatchAny(any=tags)
                )
            )
        
        # Category filter
        if "categories" in filters and filters["categories"]:
            categories = filters["categories"] if isinstance(filters["categories"], list) else [filters["categories"]]
            conditions.append(
                FieldCondition(
                    key="categories",
                    match=MatchAny(any=categories)
                )
            )
        
        # Date range filter
        if "date_range" in filters and filters["date_range"]:
            date_filter = filters["date_range"]
            conditions.append(
                FieldCondition(
                    key="publication_date",
                    range=DatetimeRange(
                        gte=date_filter.get("start"),
                        lte=date_filter.get("end"),
                    )
                )
            )
        
        # Section type filter
        if "section_type" in filters and filters["section_type"]:
            section_types = filters["section_type"] if isinstance(filters["section_type"], list) else [filters["section_type"]]
            if len(section_types) == 1:
                conditions.append(
                    FieldCondition(
                        key="section_type",
                        match=MatchValue(value=section_types[0])
                    )
                )
            else:
                conditions.append(
                    FieldCondition(
                        key="section_type",
                        match=MatchAny(any=section_types)
                    )
                )
        
        return Filter(must=conditions) if conditions else None
    
    def _point_to_result(self, point: ScoredPoint, score: float = None) -> SearchResult:
        """Convert Qdrant point to SearchResult."""
        payload = point.payload

        return SearchResult(
            chunk_id=payload.get("chunk_id", ""),
            document_id=payload.get("document_id", ""),
            title=payload.get("title", ""),
            url=payload.get("url", ""),
            text=payload.get("text", ""),
            score=score if score is not None else point.score,
            section_type=payload.get("section_type", "content"),
            author=payload.get("author"),
            publication_date=payload.get("publication_date"),
            categories=payload.get("categories", []),
            tags=payload.get("tags", []),
            chunk_index=payload.get("chunk_index"),
        )

    def get_full_article(self, document_id: str) -> str:
        """
        Retrieve and assemble full article from all chunks.

        Args:
            document_id: ID of the document to retrieve

        Returns:
            Full article text assembled from all chunks
        """
        # Scroll through all points with matching document_id
        chunks = []
        offset = None

        while True:
            results, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            chunks.extend(results)

            if offset is None:
                break

        # Sort by chunk_index if available
        chunks_with_index = [(p.payload.get("chunk_index", 999), p.payload.get("text", "")) for p in chunks]
        chunks_with_index.sort(key=lambda x: x[0])

        # Join all chunk texts
        full_text = "\n\n".join(text for _, text in chunks_with_index if text)

        return full_text


def search(
    query: str,
    top_k: int = 10,
    filters: Optional[Dict] = None,
    client: QdrantClient = None,
) -> List[SearchResult]:
    """
    Convenience function for hybrid search.
    
    Args:
        query: Search query
        top_k: Number of results
        filters: Optional filters (tags, categories, date_range, section_type)
        client: QdrantClient instance
        
    Returns:
        List of search results
    """
    engine = HybridSearchEngine(client=client)
    return engine.search(query=query, top_k=top_k, filters=filters)


if __name__ == "__main__":
    # Test search
    print("\n=== Testing Hybrid Search ===\n")
    
    test_query = "Jak używać agentów AI w developmencie?"
    
    print(f"Query: {test_query}\n")
    
    results = search(
        query=test_query,
        top_k=5,
    )
    
    print(f"\n=== Search Results ===\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Section: {result.section_type}")
        print(f"   URL: {result.url}")
        print(f"   Preview: {result.text[:150]}...")
        print()
