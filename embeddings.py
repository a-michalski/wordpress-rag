"""
Embedding wrappers for FastEmbed models.
Supports dense (nomic), ColBERT (late interaction), and sparse (BM25) embeddings.
"""
from typing import List, Union, Dict
import numpy as np

from fastembed import TextEmbedding, LateInteractionTextEmbedding, SparseTextEmbedding

import config


class DenseEmbedder:
    """Dense vector embeddings using FastEmbed."""
    
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = config.DENSE_MODEL_NAME
        
        print(f"Loading dense embedding model: {model_name}")
        self.model = TextEmbedding(model_name=model_name)
        self.model_name = model_name
        print(f"Dense model loaded: {model_name}")
    
    def embed(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Generate dense embeddings for text(s).
        
        Args:
            texts: Single text string or list of texts
            
        Returns:
            Single embedding array or list of embedding arrays
        """
        single_text = isinstance(texts, str)
        if single_text:
            texts = [texts]
        
        # FastEmbed returns generator, convert to list
        embeddings = list(self.model.embed(texts))
        
        return embeddings[0] if single_text else embeddings
    
    def embed_batch(self, texts: List[str], batch_size: int = None) -> List[np.ndarray]:
        """
        Generate embeddings in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding arrays
        """
        if batch_size is None:
            batch_size = config.EMBEDDING_BATCH_SIZE
        
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = list(self.model.embed(batch))
            all_embeddings.extend(embeddings)
        
        return all_embeddings


class ColBERTEmbedder:
    """ColBERT late interaction embeddings using FastEmbed."""
    
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = config.COLBERT_MODEL_NAME
        
        print(f"Loading ColBERT model: {model_name}")
        self.model = LateInteractionTextEmbedding(model_name=model_name)
        self.model_name = model_name
        print(f"ColBERT model loaded: {model_name}")
    
    def embed(self, texts: Union[str, List[str]]) -> Union[List[np.ndarray], List[List[np.ndarray]]]:
        """
        Generate ColBERT embeddings for text(s).
        
        ColBERT returns multiple vectors per text (one per token).
        
        Args:
            texts: Single text string or list of texts
            
        Returns:
            List of token embeddings for single text, or list of lists for multiple texts
        """
        single_text = isinstance(texts, str)
        if single_text:
            texts = [texts]
        
        # FastEmbed returns generator of lists (one list per text)
        embeddings = list(self.model.embed(texts))
        
        return embeddings[0] if single_text else embeddings
    
    def embed_batch(self, texts: List[str], batch_size: int = None) -> List[List[np.ndarray]]:
        """
        Generate ColBERT embeddings in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of token embedding lists (one per text)
        """
        if batch_size is None:
            batch_size = config.EMBEDDING_BATCH_SIZE
        
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            embeddings = list(self.model.embed(batch))
            all_embeddings.extend(embeddings)
        
        return all_embeddings


class SparseEmbedder:
    """Sparse BM25 embeddings using FastEmbed."""
    
    def __init__(self, model_name: str = None):
        if model_name is None:
            model_name = config.SPARSE_MODEL_NAME
        
        print(f"Loading sparse embedding model: {model_name}")
        self.model = SparseTextEmbedding(model_name=model_name)
        self.model_name = model_name
        print(f"Sparse model loaded: {model_name}")
    
    def embed(self, texts: Union[str, List[str]]) -> Union[Dict, List[Dict]]:
        """
        Generate sparse embeddings for text(s).
        
        Args:
            texts: Single text string or list of texts
            
        Returns:
            Sparse embedding dict(s) with 'indices' and 'values'
        """
        single_text = isinstance(texts, str)
        if single_text:
            texts = [texts]
        
        # FastEmbed returns generator of sparse dicts
        embeddings = []
        for embedding in self.model.embed(texts):
            # Convert to format expected by Qdrant
            sparse_dict = {
                'indices': embedding.indices.tolist(),
                'values': embedding.values.tolist()
            }
            embeddings.append(sparse_dict)
        
        return embeddings[0] if single_text else embeddings
    
    def embed_batch(self, texts: List[str], batch_size: int = None) -> List[Dict]:
        """
        Generate sparse embeddings in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of sparse embedding dicts
        """
        if batch_size is None:
            batch_size = config.EMBEDDING_BATCH_SIZE
        
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for embedding in self.model.embed(batch):
                sparse_dict = {
                    'indices': embedding.indices.tolist(),
                    'values': embedding.values.tolist()
                }
                all_embeddings.append(sparse_dict)
        
        return all_embeddings


class HybridEmbedder:
    """
    Unified interface for generating all three embedding types.
    Optimized for batch processing.
    """
    
    def __init__(self):
        print("Initializing hybrid embedder with all models...")
        self.dense = DenseEmbedder()
        self.colbert = ColBERTEmbedder()
        self.sparse = SparseEmbedder()
        print("All embedding models loaded")
    
    def embed_all(self, texts: Union[str, List[str]]) -> Dict[str, Union[np.ndarray, List, Dict]]:
        """
        Generate all three embedding types for text(s).
        
        Args:
            texts: Single text or list of texts
            
        Returns:
            Dictionary with 'dense', 'colbert', and 'sparse' embeddings
        """
        return {
            'dense': self.dense.embed(texts),
            'colbert': self.colbert.embed(texts),
            'sparse': self.sparse.embed(texts),
        }
    
    def embed_batch_all(self, texts: List[str], batch_size: int = None) -> List[Dict[str, Union[np.ndarray, List, Dict]]]:
        """
        Generate all three embedding types for a batch of texts.
        
        Args:
            texts: List of texts
            batch_size: Batch size for processing
            
        Returns:
            List of dicts, each containing 'dense', 'colbert', and 'sparse' embeddings
        """
        dense_embeddings = self.dense.embed_batch(texts, batch_size)
        colbert_embeddings = self.colbert.embed_batch(texts, batch_size)
        sparse_embeddings = self.sparse.embed_batch(texts, batch_size)
        
        # Combine into list of dicts
        results = []
        for i in range(len(texts)):
            results.append({
                'dense': dense_embeddings[i],
                'colbert': colbert_embeddings[i],
                'sparse': sparse_embeddings[i],
            })
        
        return results


if __name__ == "__main__":
    # Test embeddings
    print("\n=== Testing Embedding Models ===\n")
    
    test_texts = [
        "To jest przykładowy tekst w języku polskim o sztucznej inteligencji.",
        "Drugie zdanie testowe o produktach cyfrowych i UX design.",
    ]
    
    # Test dense embeddings
    print("Testing dense embeddings...")
    dense = DenseEmbedder()
    dense_emb = dense.embed(test_texts[0])
    print(f"Dense embedding shape: {dense_emb.shape}")
    print(f"Dense embedding preview: {dense_emb[:5]}")
    
    # Test ColBERT embeddings
    print("\nTesting ColBERT embeddings...")
    colbert = ColBERTEmbedder()
    colbert_emb = colbert.embed(test_texts[0])
    print(f"ColBERT tokens: {len(colbert_emb)}")
    print(f"ColBERT token vector shape: {colbert_emb[0].shape}")
    
    # Test sparse embeddings
    print("\nTesting sparse embeddings...")
    sparse = SparseEmbedder()
    sparse_emb = sparse.embed(test_texts[0])
    print(f"Sparse non-zero elements: {len(sparse_emb['indices'])}")
    print(f"Sparse indices preview: {sparse_emb['indices'][:10]}")
    print(f"Sparse values preview: {sparse_emb['values'][:10]}")
    
    # Test hybrid embedder
    print("\nTesting hybrid embedder...")
    hybrid = HybridEmbedder()
    all_emb = hybrid.embed_all(test_texts[0])
    print(f"Generated embeddings: {list(all_emb.keys())}")
    
    print("\nAll embedding models working correctly! ✓")
