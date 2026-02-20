"""
Semantic chunking with section type detection for WordPress articles.
Uses LlamaIndex SemanticSplitterNodeParser to preserve thought continuity.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass

from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.schema import Document, TextNode
from llama_index.embeddings.fastembed import FastEmbedEmbedding

import config
from parser import Article


@dataclass
class Chunk:
    """A chunk of text with metadata."""
    chunk_id: str  # document_id + chunk_index
    text: str

    # Source document metadata
    document_id: str
    slug: str
    title: str
    url: str
    author: str
    publication_date: str
    categories: List[str]
    tags: List[str]
    
    # Chunk-specific metadata
    chunk_index: int
    section_type: str  # 'content', 'tldr', 'checklist', 'key_insight', 'source_attribution'
    
    # Optional fields
    reading_time_minutes: Optional[int] = None
    seo_description: Optional[str] = None


class SemanticChunker:
    """
    Semantic chunker that preserves thought continuity and identifies section types.
    Optimized for Polish technical content.
    """
    
    def __init__(self):
        """Initialize semantic chunker with embedding model."""
        
        # Initialize FastEmbed for semantic similarity computation
        # Using same model as dense vectors for consistency
        print(f"Initializing semantic chunker with {config.DENSE_MODEL_NAME}...")
        
        self.embed_model = FastEmbedEmbedding(
            model_name=config.DENSE_MODEL_NAME
        )
        
        # Initialize LlamaIndex semantic splitter
        self.splitter = SemanticSplitterNodeParser(
            embed_model=self.embed_model,
            breakpoint_percentile_threshold=config.BREAKPOINT_PERCENTILE_THRESHOLD,
            buffer_size=config.BUFFER_SIZE,
        )
        
        print("Semantic chunker initialized")
    
    def chunk_article(self, article: Article) -> List[Chunk]:
        """
        Chunk a single article using semantic splitting.
        
        Args:
            article: Parsed WordPress article
            
        Returns:
            List of chunks with metadata and section type detection
        """
        
        # Skip empty articles
        if not article.content_markdown or len(article.content_markdown.strip()) < 50:
            print(f"Warning: Skipping article {article.document_id} - content too short")
            return []
        
        try:
            # Convert article to LlamaIndex Document
            document = Document(
                text=article.content_markdown,
                metadata={
                    "document_id": article.document_id,
                    "title": article.title,
                    "url": article.url,
                    "author": article.author,
                    "publication_date": article.publication_date.isoformat(),
                    "categories": article.categories,
                    "tags": article.tags,
                    "reading_time_minutes": article.reading_time_minutes,
                    "seo_description": article.seo_description,
                },
                excluded_llm_metadata_keys=["document_id"],  # Don't include in LLM context
                excluded_embed_metadata_keys=["document_id"],  # Don't include in embeddings
            )
            
            # Split into semantic chunks
            nodes = self.splitter.get_nodes_from_documents([document])
            
        except Exception as e:
            print(f"Warning: Error chunking article {article.document_id}: {e}")
            return []
        
        # Convert nodes to Chunk objects with section type detection
        chunks = []
        for idx, node in enumerate(nodes):
            section_type = self._detect_section_type(
                node.text,
                article.section_markers,
                node.start_char_idx
            )
            
            chunk = Chunk(
                chunk_id=f"{article.document_id}_{idx}",
                text=node.text,
                document_id=article.document_id,
                slug=article.slug,
                title=article.title,
                url=article.url,
                author=article.author,
                publication_date=article.publication_date.isoformat(),
                categories=article.categories,
                tags=article.tags,
                chunk_index=idx,
                section_type=section_type,
                reading_time_minutes=article.reading_time_minutes,
                seo_description=article.seo_description,
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def chunk_articles(self, articles: List[Article]) -> List[Chunk]:
        """
        Chunk multiple articles.
        
        Args:
            articles: List of parsed WordPress articles
            
        Returns:
            Flat list of all chunks from all articles
        """
        all_chunks = []
        
        print(f"Chunking {len(articles)} articles...")
        for i, article in enumerate(articles):
            if (i + 1) % 10 == 0:
                print(f"Chunked {i + 1}/{len(articles)} articles...")
            
            chunks = self.chunk_article(article)
            all_chunks.extend(chunks)
        
        print(f"Created {len(all_chunks)} total chunks from {len(articles)} articles")
        return all_chunks
    
    def _detect_section_type(
        self,
        chunk_text: str,
        section_markers: Dict[str, List[int]],
        chunk_start_pos: Optional[int]
    ) -> str:
        """
        Detect the section type of a chunk based on its content and position.
        
        Args:
            chunk_text: The text content of the chunk
            section_markers: Dictionary mapping section types to character positions
            chunk_start_pos: Starting character position of chunk in original document
            
        Returns:
            Section type string: 'tldr', 'checklist', 'key_insight', 'source_attribution', or 'content'
        """
        
        chunk_text_lower = chunk_text.lower()
        
        # Check for explicit markers in chunk text
        if 'tl;dr' in chunk_text_lower or 'tl.dr' in chunk_text_lower:
            return 'tldr'
        
        if '✅' in chunk_text or 'checklist' in chunk_text_lower:
            return 'checklist'
        
        if 'kluczowy insight' in chunk_text_lower or 'key insight' in chunk_text_lower:
            return 'key_insight'
        
        if 'źródło:' in chunk_text_lower or 'ten wpis jest częścią' in chunk_text_lower:
            return 'source_attribution'
        
        # If chunk position is available, check proximity to section markers
        if chunk_start_pos is not None:
            # Define proximity threshold (100 characters)
            proximity_threshold = 100
            
            for section_type, positions in section_markers.items():
                for pos in positions:
                    if abs(chunk_start_pos - pos) < proximity_threshold:
                        return section_type
        
        # Default to content type
        return 'content'


def chunk_articles(articles: List[Article]) -> List[Chunk]:
    """Convenience function to chunk articles with semantic splitter."""
    chunker = SemanticChunker()
    return chunker.chunk_articles(articles)


if __name__ == "__main__":
    # Test chunking
    from parser import parse_wordpress_xml
    
    print("Parsing WordPress XML...")
    articles = parse_wordpress_xml()
    
    if articles:
        print(f"\nTesting chunking on first article...")
        chunker = SemanticChunker()
        chunks = chunker.chunk_article(articles[0])
        
        print(f"\n=== Chunking Results ===")
        print(f"Article: {articles[0].title}")
        print(f"Original length: {len(articles[0].content_markdown)} chars")
        print(f"Number of chunks: {len(chunks)}")
        
        # Show section type distribution
        section_types = {}
        for chunk in chunks:
            section_types[chunk.section_type] = section_types.get(chunk.section_type, 0) + 1
        
        print(f"\nSection type distribution:")
        for section_type, count in sorted(section_types.items()):
            print(f"  {section_type}: {count} chunks")
        
        # Show first chunk
        print(f"\n=== First Chunk ===")
        print(f"ID: {chunks[0].chunk_id}")
        print(f"Section type: {chunks[0].section_type}")
        print(f"Text length: {len(chunks[0].text)} chars")
        print(f"Text preview:\n{chunks[0].text[:300]}...")
