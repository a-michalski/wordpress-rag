"""RAG Search API with ColBERT Reranking for Hetzner CX23"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict

# Add parent directory to path to import local modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from search import HybridSearchEngine, SearchResult as SearchResultClass
from qdrant_setup import create_qdrant_client
import config

app = FastAPI(
    title="RAG Search API with ColBERT",
    description="Hybrid search with dense recall + ColBERT reranking",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine (singleton)
search_engine = None


def get_search_engine():
    """Get or create search engine instance"""
    global search_engine
    if search_engine is None:
        client = create_qdrant_client()
        search_engine = HybridSearchEngine(client=client)
    return search_engine


# Request/Response models
class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 10
    filters: Optional[Dict] = None
    include_full_article: Optional[bool] = False

    class Config:
        schema_extra = {
            "example": {
                "query": "Jak używać agentów AI w developmencie?",
                "top_k": 10,
                "include_full_article": False,
                "filters": {
                    "tags": ["AI", "development"],
                    "categories": ["Technologia"],
                    "section_type": ["content", "key_insight"]
                }
            }
        }


class SearchResultModel(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    url: str
    text: str
    score: float
    section_type: str
    author: Optional[str] = None
    publication_date: Optional[str] = None
    categories: List[str] = []
    tags: List[str] = []
    full_article: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultModel]
    total: int
    config: Dict


# Endpoints
@app.get("/")
def root():
    return {
        "status": "online",
        "service": "RAG Search API",
        "features": [
            "Dense vector search (nomic-embed-text-v1.5)",
            "ColBERT reranking (MaxSim scoring)",
            "Sparse BM25 vectors",
            "Two-stage hybrid search",
            "Grouping by document"
        ],
        "endpoints": {
            "/search": "POST - Hybrid search with ColBERT reranking",
            "/health": "GET - Health check",
            "/stats": "GET - Collection statistics",
            "/docs": "GET - API documentation (Swagger)"
        }
    }


@app.get("/health")
def health():
    """Health check endpoint"""
    try:
        engine = get_search_engine()
        info = engine.client.get_collection(config.COLLECTION_NAME)

        return {
            "status": "healthy",
            "collection": config.COLLECTION_NAME,
            "points": info.points_count,
            "vectors": list(info.config.params.vectors.keys()),
            "models": {
                "dense": config.DENSE_MODEL,
                "colbert": config.COLBERT_MODEL,
                "sparse": config.SPARSE_MODEL
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/stats")
def stats():
    """Get collection statistics"""
    try:
        engine = get_search_engine()
        info = engine.client.get_collection(config.COLLECTION_NAME)

        return {
            "collection": config.COLLECTION_NAME,
            "points_count": info.points_count,
            "vectors": {
                name: {
                    "size": vec.size,
                    "distance": vec.distance
                }
                for name, vec in info.config.params.vectors.items()
            },
            "config": {
                "recall_limit": config.RECALL_LIMIT,
                "final_results": config.FINAL_RESULTS_LIMIT,
                "grouping_enabled": config.ENABLE_GROUPING,
                "group_by_field": config.GROUP_BY_FIELD if config.ENABLE_GROUPING else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """
    Hybrid search with two-stage pipeline:
    1. Dense vector recall (top 100 candidates)
    2. ColBERT reranking (MaxSim scoring, top K results)

    Supports filtering by:
    - tags: List of tags
    - categories: List of categories
    - date_range: {"start": "2024-01-01", "end": "2024-12-31"}
    - section_type: ["content", "tldr", "checklist", "key_insight"]
    """
    try:
        engine = get_search_engine()

        # Perform hybrid search with ColBERT reranking
        results = engine.search(
            query=request.query,
            top_k=request.top_k,
            filters=request.filters
        )

        # If full article requested, fetch all chunks for each document
        full_articles = {}
        if request.include_full_article:
            for r in results:
                if r.document_id not in full_articles:
                    full_articles[r.document_id] = engine.get_full_article(r.document_id)

        # Convert to response model
        search_results = [
            SearchResultModel(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                title=r.title,
                url=r.url,
                text=r.text,
                score=r.score,
                section_type=r.section_type,
                author=r.author,
                publication_date=r.publication_date,
                categories=r.categories or [],
                tags=r.tags or [],
                full_article=full_articles.get(r.document_id) if request.include_full_article else None
            )
            for r in results
        ]

        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results),
            config={
                "two_stage_search": True,
                "colbert_reranking": True,
                "recall_limit": config.RECALL_LIMIT,
                "grouping": config.ENABLE_GROUPING
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
