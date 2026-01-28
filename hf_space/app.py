"""RAG Search API for HuggingFace Spaces"""
import os
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from qdrant_client import QdrantClient
from fastembed import TextEmbedding

app = FastAPI(title="RAG Search API")

# Config from environment variables (set in HF Space secrets)
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION_NAME = "wordpress_articles"
EMBEDDING_MODEL = "nomic-ai/nomic-embed-text-v1.5"

# Initialize clients
qdrant = None
embedder = None


def get_qdrant():
    global qdrant
    if qdrant is None:
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return qdrant


def get_embedder():
    global embedder
    if embedder is None:
        embedder = TextEmbedding(model_name=EMBEDDING_MODEL)
    return embedder


def get_embedding(text: str) -> List[float]:
    """Get embedding using FastEmbed (local model)"""
    # Add search prefix as required by nomic model
    text_with_prefix = f"search_query: {text}"

    embedder = get_embedder()
    # FastEmbed returns generator, convert to list and get first embedding
    embeddings = list(embedder.embed([text_with_prefix]))

    if not embeddings:
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

    return embeddings[0].tolist()


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class SearchResult(BaseModel):
    text: str
    title: str
    url: str
    score: float
    section_type: Optional[str] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str


@app.get("/")
def root():
    return {"status": "RAG Search API is running", "model": EMBEDDING_MODEL}


@app.get("/health")
def health():
    try:
        client = get_qdrant()
        count = client.count(COLLECTION_NAME).count
        return {"status": "healthy", "points": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    """Search for relevant documents"""
    try:
        # Get query embedding
        query_vector = get_embedding(request.query)
        
        # Search in Qdrant
        client = get_qdrant()
        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=("dense", query_vector),
            limit=request.top_k,
            with_payload=True
        )
        
        # Format results
        search_results = []
        for hit in results:
            search_results.append(SearchResult(
                text=hit.payload.get("text", ""),
                title=hit.payload.get("title", ""),
                url=hit.payload.get("url", ""),
                score=hit.score,
                section_type=hit.payload.get("section_type")
            ))
        
        return SearchResponse(results=search_results, query=request.query)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
