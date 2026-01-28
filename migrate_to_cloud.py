"""Migrate local Qdrant data to Qdrant Cloud."""
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, SparseVectorParams, 
    BinaryQuantization, BinaryQuantizationConfig,
    PointStruct
)
import config

BATCH_SIZE = 20  # Small batches due to ColBERT multivector size

def record_to_point(record):
    """Convert Record to PointStruct for upsert."""
    return PointStruct(
        id=record.id,
        payload=record.payload,
        vector=record.vector
    )

def main():
    print("=" * 60)
    print("MIGRATION: Local → Qdrant Cloud")
    print("=" * 60)
    
    # Connect to local
    local = QdrantClient(path=str(config.QDRANT_STORAGE_PATH))
    local_count = local.count(config.COLLECTION_NAME).count
    print(f"Local points: {local_count}")
    
    # Connect to cloud
    cloud = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY)
    print(f"Connected to cloud: {config.QDRANT_URL[:50]}...")
    
    # Check if collection exists on cloud
    collections = [c.name for c in cloud.get_collections().collections]
    
    if config.COLLECTION_NAME in collections:
        cloud_count = cloud.count(config.COLLECTION_NAME).count
        print(f"Cloud collection exists: {cloud_count} points")
        if cloud_count >= local_count:
            print("Cloud already has all data. Nothing to migrate.")
            return
        response = input("Delete cloud collection and re-migrate? (y/n): ")
        if response.lower() != 'y':
            return
        cloud.delete_collection(config.COLLECTION_NAME)
        print("Deleted cloud collection")
    
    # Create collection on cloud
    print("\nCreating collection on cloud...")
    cloud.create_collection(
        collection_name=config.COLLECTION_NAME,
        vectors_config={
            "dense": VectorParams(
                size=config.DENSE_DIM,
                distance=Distance.COSINE,
                on_disk=True,
                quantization_config=BinaryQuantization(
                    binary=BinaryQuantizationConfig(always_ram=True)
                )
            ),
            "colbert": VectorParams(
                size=config.COLBERT_DIM,
                distance=Distance.COSINE,
                multivector_config={"comparator": "max_sim"},
                on_disk=True
            ),
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams(modifier="idf")
        }
    )
    print("Collection created!")
    
    # Migrate data in batches
    print(f"\nMigrating {local_count} points in batches of {BATCH_SIZE}...")
    
    offset = None
    migrated = 0
    
    while True:
        # Scroll local data
        results, offset = local.scroll(
            collection_name=config.COLLECTION_NAME,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )
        
        if not results:
            break
        
        # Convert Record -> PointStruct
        points = [record_to_point(r) for r in results]
        
        # Upsert to cloud
        cloud.upsert(
            collection_name=config.COLLECTION_NAME,
            points=points
        )
        
        migrated += len(points)
        print(f"  Migrated: {migrated}/{local_count}", flush=True)
        
        if offset is None:
            break
    
    # Verify
    cloud_count = cloud.count(config.COLLECTION_NAME).count
    print("\n" + "=" * 60)
    print(f"✓ MIGRATION COMPLETE")
    print(f"  Cloud points: {cloud_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()