"""
Memory-optimized incremental ingestion.
Saves after EACH article. Can resume from any point.
"""
from qdrant_setup import create_qdrant_client, initialize_collection
from parser import parse_wordpress_xml
from chunker import SemanticChunker
from embeddings import HybridEmbedder
from qdrant_client.models import PointStruct, SparseVector
import config
import uuid
import gc


def get_existing_document_ids(client):
    """Get all document IDs already in Qdrant."""
    existing_ids = set()
    try:
        offset = None
        while True:
            points, offset = client.scroll(
                collection_name=config.QDRANT_COLLECTION_NAME,
                limit=1000,
                offset=offset,
                with_payload=["document_id"],
                with_vectors=False,
            )
            for point in points:
                if point.payload and "document_id" in point.payload:
                    existing_ids.add(point.payload["document_id"])
            if offset is None:
                break
    except Exception:
        pass
    return existing_ids


def process_single_article(article, chunker, embedder, client):
    """Process ONE article: chunk → embed → save to Qdrant."""
    chunks = None
    texts = None
    embeddings = None
    points = None
    
    try:
        chunks = chunker.chunk_article(article)
        if not chunks:
            return 0
        
        texts = [c.text for c in chunks]
        embeddings = embedder.embed_batch_all(texts)
        
        points = []
        for chunk, emb in zip(chunks, embeddings):
            dense = emb['dense'].tolist() if hasattr(emb['dense'], 'tolist') else emb['dense']
            colbert = [v.tolist() if hasattr(v, 'tolist') else v for v in emb['colbert']]
            sparse = SparseVector(indices=emb['sparse']['indices'], values=emb['sparse']['values'])
            
            points.append(PointStruct(
                id=str(uuid.uuid4()),
                vector={"dense": dense, "colbert": colbert, "sparse": sparse},
                payload={
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "title": chunk.title,
                    "url": chunk.url,
                    "author": chunk.author,
                    "publication_date": chunk.publication_date,
                    "categories": chunk.categories,
                    "tags": chunk.tags,
                    "chunk_index": chunk.chunk_index,
                    "section_type": chunk.section_type,
                    "text": chunk.text,
                },
            ))
        
        # SAVE IMMEDIATELY to disk
        client.upsert(collection_name=config.QDRANT_COLLECTION_NAME, points=points)
        return len(points)
        
    finally:
        # Safe memory cleanup
        del chunks, texts, embeddings, points
        gc.collect()


def main():
    print("=" * 70, flush=True)
    print("INCREMENTAL INGESTION - Save after each article", flush=True)
    print("=" * 70, flush=True)
    
    # Connect to Qdrant
    client = create_qdrant_client()
    
    # Check/create collection
    try:
        info = client.get_collection(config.QDRANT_COLLECTION_NAME)
        print(f"\n✓ Collection exists: {info.points_count} points", flush=True)
    except Exception:
        print("\n⚠ Creating collection...", flush=True)
        initialize_collection(client, recreate=False)
    
    # Get existing document IDs (for resume)
    existing_ids = get_existing_document_ids(client)
    print(f"Already ingested: {len(existing_ids)} documents", flush=True)
    
    # Parse XML
    print("\nParsing WordPress XML...", flush=True)
    all_articles = parse_wordpress_xml()
    
    # Filter out already processed
    articles = [a for a in all_articles if a.document_id not in existing_ids]
    print(f"To process: {len(articles)} | Skipping: {len(existing_ids)}", flush=True)
    
    if not articles:
        print("\n✓ All articles already ingested!", flush=True)
        return
    
    # Load models ONCE
    print("\nLoading models (this takes a moment)...", flush=True)
    chunker = SemanticChunker()
    embedder = HybridEmbedder()
    print("Models ready!\n", flush=True)
    
    # Process ONE BY ONE with checkpoint after each
    total_chunks = 0
    
    for i, article in enumerate(articles):
        try:
            n = process_single_article(article, chunker, embedder, client)
            total_chunks += n
            print(f"[{i+1}/{len(articles)}] ✓ SAVED {n} chunks | {article.title[:45]}...", flush=True)
            
        except Exception as e:
            print(f"[{i+1}/{len(articles)}] ✗ ERROR: {e}", flush=True)
        
        # Extra garbage collection every 10 articles
        if (i + 1) % 10 == 0:
            gc.collect()
    
    # Final summary
    print("\n" + "=" * 70, flush=True)
    print("✓ INGESTION COMPLETE", flush=True)
    print("=" * 70, flush=True)
    
    info = client.get_collection(config.QDRANT_COLLECTION_NAME)
    print(f"Total points in Qdrant: {info.points_count}", flush=True)
    print(f"New chunks added this run: {total_chunks}", flush=True)


if __name__ == "__main__":
    main()