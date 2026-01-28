"""
Document ingestion pipeline: Parse → Chunk → Embed → Upload to Qdrant.
Handles batch processing with progress tracking.
"""
from typing import List, Optional
from tqdm import tqdm
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, SparseVector

import config
from parser import parse_wordpress_xml, Article
from chunker import chunk_articles, Chunk
from embeddings import HybridEmbedder
from qdrant_setup import create_qdrant_client, initialize_collection


class DocumentIngester:
    """
    Orchestrates the full ingestion pipeline.
    """
    
    def __init__(
        self,
        client: QdrantClient = None,
        collection_name: str = None,
    ):
        """
        Initialize ingester with Qdrant client and embedder.
        
        Args:
            client: QdrantClient instance (creates new if None)
            collection_name: Name of Qdrant collection
        """
        self.client = client if client else create_qdrant_client()
        self.collection_name = collection_name or config.QDRANT_COLLECTION_NAME
        self.embedder = HybridEmbedder()
    
    def ingest_from_xml(
        self,
        xml_path: str = None,
        batch_size: int = None,
    ) -> dict:
        """
        Full pipeline: parse XML → chunk → embed → upload.
        
        Args:
            xml_path: Path to WordPress XML file
            batch_size: Batch size for embedding and upload
            
        Returns:
            Dictionary with ingestion statistics
        """
        if batch_size is None:
            batch_size = config.UPLOAD_BATCH_SIZE
        
        # Step 1: Parse WordPress XML
        print("\n" + "="*70)
        print("STEP 1: Parsing WordPress XML")
        print("="*70)
        articles = parse_wordpress_xml(xml_path)
        
        if not articles:
            print("No articles found in XML!")
            return {"success": False, "error": "No articles found"}
        
        # Step 2: Semantic chunking
        print("\n" + "="*70)
        print("STEP 2: Semantic Chunking")
        print("="*70)
        chunks = chunk_articles(articles)
        
        # Step 3: Generate embeddings and upload
        print("\n" + "="*70)
        print("STEP 3: Embedding and Upload to Qdrant")
        print("="*70)
        points_uploaded = self._embed_and_upload_chunks(chunks, batch_size)
        
        # Summary
        stats = {
            "success": True,
            "articles_parsed": len(articles),
            "chunks_created": len(chunks),
            "points_uploaded": points_uploaded,
            "collection_name": self.collection_name,
        }
        
        print("\n" + "="*70)
        print("INGESTION COMPLETE")
        print("="*70)
        print(f"Articles parsed: {stats['articles_parsed']}")
        print(f"Chunks created: {stats['chunks_created']}")
        print(f"Points uploaded: {stats['points_uploaded']}")
        print(f"Collection: {stats['collection_name']}")
        
        return stats
    
    def _embed_and_upload_chunks(
        self,
        chunks: List[Chunk],
        batch_size: int,
    ) -> int:
        """
        Generate embeddings and upload chunks to Qdrant in batches.
        
        Args:
            chunks: List of chunks to process
            batch_size: Batch size for processing
            
        Returns:
            Number of points uploaded
        """
        total_uploaded = 0
        
        print(f"Processing {len(chunks)} chunks in batches of {batch_size}...")
        
        for i in tqdm(range(0, len(chunks), batch_size), desc="Uploading batches"):
            batch = chunks[i:i + batch_size]
            
            # Extract texts
            texts = [chunk.text for chunk in batch]
            
            # Generate all embeddings for batch
            embeddings = self.embedder.embed_batch_all(texts, batch_size=len(texts))
            
            # Convert to Qdrant points
            points = []
            for chunk, emb in zip(batch, embeddings):
                point = self._chunk_to_point(chunk, emb)
                points.append(point)
            
            # Upload batch to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            
            total_uploaded += len(points)
        
        return total_uploaded
    
    def _chunk_to_point(self, chunk: Chunk, embeddings: dict) -> PointStruct:
        """
        Convert a chunk with embeddings to a Qdrant point.
        
        Args:
            chunk: Chunk object with metadata
            embeddings: Dictionary with 'dense', 'colbert', and 'sparse' embeddings
            
        Returns:
            PointStruct ready for upload
        """
        # Create unique point ID
        point_id = str(uuid.uuid4())
        
        # Prepare payload (metadata)
        payload = {
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
            "text": chunk.text,  # Store original text for retrieval
        }
        
        # Add optional fields
        if chunk.reading_time_minutes:
            payload["reading_time_minutes"] = chunk.reading_time_minutes
        if chunk.seo_description:
            payload["seo_description"] = chunk.seo_description
        
        # Prepare vectors
        # Dense: simple array
        dense_vector = embeddings['dense'].tolist() if hasattr(embeddings['dense'], 'tolist') else embeddings['dense']
        
        # ColBERT: list of arrays (multivector)
        colbert_vectors = [
            vec.tolist() if hasattr(vec, 'tolist') else vec
            for vec in embeddings['colbert']
        ]
        
        # Sparse: convert to SparseVector format for Qdrant
        sparse_data = embeddings['sparse']
        sparse_vector = SparseVector(
            indices=sparse_data['indices'],
            values=sparse_data['values']
        )
        
        # Create point with all vector types
        point = PointStruct(
            id=point_id,
            vector={
                "dense": dense_vector,
                "colbert": colbert_vectors,
                "sparse": sparse_vector,
            },
            payload=payload,
        )
        
        return point


def ingest_wordpress_data(
    xml_path: str = None,
    recreate_collection: bool = False,
) -> dict:
    """
    Convenience function to run full ingestion pipeline.
    
    Args:
        xml_path: Path to WordPress XML file
        recreate_collection: If True, delete and recreate collection
        
    Returns:
        Dictionary with ingestion statistics
    """
    # Initialize Qdrant collection
    client = initialize_collection(recreate=recreate_collection)
    
    # Run ingestion
    ingester = DocumentIngester(client=client)
    stats = ingester.ingest_from_xml(xml_path=xml_path)
    
    return stats


if __name__ == "__main__":
    # Run ingestion pipeline
    print("\n" + "="*70)
    print("WordPress RAG System - Document Ingestion")
    print("="*70)
    
    stats = ingest_wordpress_data(
        xml_path=str(config.WORDPRESS_XML_PATH),
        recreate_collection=True,
    )
    
    if stats["success"]:
        print(f"\n✓ Ingestion successful!")
        print(f"  Articles: {stats['articles_parsed']}")
        print(f"  Chunks: {stats['chunks_created']}")
        print(f"  Points in Qdrant: {stats['points_uploaded']}")
    else:
        print(f"\n✗ Ingestion failed: {stats.get('error', 'Unknown error')}")
