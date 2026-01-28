"""Configuration for RAG system."""
import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent
QDRANT_STORAGE_PATH = PROJECT_ROOT / "qdrant_storage"
WORDPRESS_XML_PATH = PROJECT_ROOT / "WordPress.xml"

# Qdrant Cloud Configuration
QDRANT_URL = "https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0")

# Collection
COLLECTION_NAME = "wordpress_articles"
QDRANT_COLLECTION_NAME = COLLECTION_NAME  # compatibility alias

# Embedding models (optimized for M1 Mac)
DENSE_MODEL = "nomic-ai/nomic-embed-text-v1.5"
DENSE_MODEL_NAME = DENSE_MODEL  # compatibility alias
DENSE_DIM = 768

COLBERT_MODEL = "answerdotai/answerai-colbert-small-v1"
COLBERT_MODEL_NAME = COLBERT_MODEL  # compatibility alias
COLBERT_DIM = 96

SPARSE_MODEL = "Qdrant/bm25"
SPARSE_MODEL_NAME = SPARSE_MODEL  # compatibility alias

# Chunking
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
BREAKPOINT_THRESHOLD = 85

# Search
TOP_K = 20
RERANK_TOP_K = 5
RECALL_LIMIT = 100              # how many candidates for first stage
FINAL_RESULTS_LIMIT = TOP_K     # alias
ENABLE_GROUPING = False         # group results by field
GROUP_BY_FIELD = "post_id"      # field to group by
GROUP_SIZE = 3                  # max results per group