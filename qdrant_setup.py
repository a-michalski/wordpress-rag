"""
Qdrant collection setup with named vectors (dense, ColBERT, sparse).
Optimized for M1 Mac with binary quantization and on-disk storage.
"""
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    SparseVectorParams,
    SparseIndexParams,
    MultiVectorConfig,
    MultiVectorComparator,
    QuantizationConfig,
    BinaryQuantization,
    BinaryQuantizationConfig,
    OptimizersConfigDiff,
)

import config


def create_qdrant_client() -> QdrantClient:
    """Create Qdrant client - cloud or local."""
    if config.QDRANT_URL:
        # Remote Qdrant Cloud
        client = QdrantClient(
            url=config.QDRANT_URL,
            api_key=config.QDRANT_API_KEY
        )
        print(f"Connected to Qdrant Cloud: {config.QDRANT_URL[:50]}...")
    else:
        # Local disk storage
        client = QdrantClient(path=str(config.QDRANT_STORAGE_PATH))
        print(f"Using local Qdrant storage at {config.QDRANT_STORAGE_PATH}")
    return client


def initialize_collection(
    client: QdrantClient = None,
    collection_name: str = None,
    recreate: bool = False,
) -> QdrantClient:
    """
    Initialize Qdrant collection with named vectors configuration.
    
    Architecture:
    - Dense vector: 768 dim (nomic-embed) with binary quantization
    - ColBERT: 96 dim multivector with MaxSim comparator
    - Sparse: BM25 for keyword matching
    
    Memory optimization:
    - Binary quantization for dense vectors (32x compression)
    - On-disk storage for original vectors
    - Quantized vectors kept in RAM for fast search
    
    Args:
        client: QdrantClient instance (creates new if None)
        collection_name: Name of collection to create
        recreate: If True, delete existing collection
        
    Returns:
        QdrantClient instance
    """
    if client is None:
        client = create_qdrant_client()
    
    if collection_name is None:
        collection_name = config.QDRANT_COLLECTION_NAME
    
    # Check if collection exists
    collections = client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)
    
    if collection_exists:
        if recreate:
            print(f"Deleting existing collection: {collection_name}")
            client.delete_collection(collection_name)
        else:
            print(f"Collection '{collection_name}' already exists. Use recreate=True to delete.")
            return client
    
    print(f"\nCreating collection: {collection_name}")
    print(f"Configuration:")
    print(f"  - Dense vectors: {config.DENSE_VECTOR_SIZE} dim, {config.DENSE_DISTANCE_METRIC} distance")
    print(f"  - ColBERT vectors: {config.COLBERT_VECTOR_SIZE} dim (multivector), {config.COLBERT_DISTANCE_METRIC} distance")
    print(f"  - Sparse vectors: BM25")
    print(f"  - Binary quantization: {config.ENABLE_BINARY_QUANTIZATION}")
    print(f"  - On-disk storage: dense={config.DENSE_VECTORS_ON_DISK}, colbert={config.COLBERT_VECTORS_ON_DISK}")
    
    # Configure dense vectors with optional binary quantization
    dense_quantization = None
    if config.ENABLE_BINARY_QUANTIZATION:
        dense_quantization = BinaryQuantization(
            binary=BinaryQuantizationConfig(
                always_ram=config.QUANTIZATION_ALWAYS_RAM,
            )
        )
    
    dense_params = VectorParams(
        size=config.DENSE_VECTOR_SIZE,
        distance=Distance.COSINE if config.DENSE_DISTANCE_METRIC == "Cosine" else Distance.DOT,
        on_disk=config.DENSE_VECTORS_ON_DISK,
        quantization_config=dense_quantization,
    )
    
    # Configure ColBERT multivector (late interaction) - no quantization for precision
    colbert_params = VectorParams(
        size=config.COLBERT_VECTOR_SIZE,
        distance=Distance.COSINE if config.COLBERT_DISTANCE_METRIC == "Cosine" else Distance.DOT,
        on_disk=config.COLBERT_VECTORS_ON_DISK,
        multivector_config=MultiVectorConfig(
            comparator=MultiVectorComparator.MAX_SIM,  # MaxSim scoring for ColBERT
        ),
    )
    
    # Configure sparse vectors (BM25)
    sparse_params = SparseVectorParams(
        index=SparseIndexParams(
            on_disk=False,  # Keep sparse index in RAM for speed
        )
    )
    
    # Create collection with named vectors
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": dense_params,
            "colbert": colbert_params,
        },
        sparse_vectors_config={
            "sparse": sparse_params,
        },
        optimizers_config=OptimizersConfigDiff(
            indexing_threshold=0,  # Start indexing immediately for better search performance
        ),
    )
    
    print(f"Collection '{collection_name}' created successfully")
    
    if config.ENABLE_BINARY_QUANTIZATION:
        print("Binary quantization enabled for dense vectors")
        print("  - Memory savings: ~32x compression")
        print("  - Quantized vectors: in RAM")
        print("  - Original vectors: on disk")
    
    # Create payload indexes for filtering
    print("\nCreating payload indexes for efficient filtering...")
    
    # Index for document_id (grouping)
    client.create_payload_index(
        collection_name=collection_name,
        field_name="document_id",
        field_schema="keyword",
    )
    
    # Index for tags (filtering)
    client.create_payload_index(
        collection_name=collection_name,
        field_name="tags",
        field_schema="keyword",
    )
    
    # Index for categories (filtering)
    client.create_payload_index(
        collection_name=collection_name,
        field_name="categories",
        field_schema="keyword",
    )
    
    # Index for publication_date (range filtering)
    client.create_payload_index(
        collection_name=collection_name,
        field_name="publication_date",
        field_schema="datetime",
    )
    
    # Index for section_type (filtering)
    client.create_payload_index(
        collection_name=collection_name,
        field_name="section_type",
        field_schema="keyword",
    )
    
    print("Payload indexes created")
    
    print(f"\n✓ Collection '{collection_name}' is ready for ingestion")
    
    return client


def get_collection_info(client: QdrantClient = None, collection_name: str = None):
    """
    Get information about the collection.
    
    Args:
        client: QdrantClient instance
        collection_name: Name of collection
    """
    if client is None:
        client = create_qdrant_client()
    
    if collection_name is None:
        collection_name = config.QDRANT_COLLECTION_NAME
    
    try:
        info = client.get_collection(collection_name)
        print(f"\n=== Collection Info: {collection_name} ===")
        print(f"Status: {info.status}")
        print(f"Points count: {info.points_count}")
        print(f"Vectors:")
        for vector_name, vector_config in info.config.params.vectors.items():
            print(f"  - {vector_name}: {vector_config.size} dim, {vector_config.distance}")
            if hasattr(vector_config, 'multivector_config') and vector_config.multivector_config:
                print(f"    Multivector: {vector_config.multivector_config.comparator}")
        
        if info.config.params.sparse_vectors:
            print(f"Sparse vectors: {list(info.config.params.sparse_vectors.keys())}")
        
        if info.config.quantization_config:
            print(f"Quantization: enabled")
        
    except Exception as e:
        print(f"Error getting collection info: {e}")


if __name__ == "__main__":
    # Test collection creation
    print("=== Qdrant Collection Setup ===\n")
    
    client = initialize_collection(recreate=True)
    
    # Show collection info
    get_collection_info(client)
    
    print("\n✓ Qdrant setup complete!")
