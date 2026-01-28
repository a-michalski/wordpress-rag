"""
Agentic workflow with pre-search filtering.
Agent can filter by tags, dates, and section types before semantic search.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime

from qdrant_client import QdrantClient

import config
from search import HybridSearchEngine, SearchResult


class SearchAgent:
    """
    Simple agent that applies filters before executing semantic search.
    
    Tools available:
    1. filter_by_tags: Filter results to specific tags
    2. filter_by_date_range: Filter by publication date range
    3. filter_by_section_type: Filter to specific section types (tldr, checklist, etc.)
    4. semantic_search: Execute hybrid search with optional filters
    """
    
    def __init__(self, client: QdrantClient = None):
        """Initialize agent with search engine."""
        self.search_engine = HybridSearchEngine(client=client)
        self.active_filters = {}
    
    def filter_by_tags(self, tags: List[str]) -> str:
        """
        Add tag filter to active filters.
        
        Args:
            tags: List of tag names to filter by (OR logic)
            
        Returns:
            Confirmation message
        """
        self.active_filters["tags"] = tags
        return f"✓ Filtrowanie po tagach: {', '.join(tags)}"
    
    def filter_by_categories(self, categories: List[str]) -> str:
        """
        Add category filter to active filters.
        
        Args:
            categories: List of categories to filter by (OR logic)
            
        Returns:
            Confirmation message
        """
        self.active_filters["categories"] = categories
        return f"✓ Filtrowanie po kategoriach: {', '.join(categories)}"
    
    def filter_by_date_range(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        """
        Add date range filter to active filters.
        
        Args:
            start_date: Start date (ISO format: YYYY-MM-DD)
            end_date: End date (ISO format: YYYY-MM-DD)
            
        Returns:
            Confirmation message
        """
        date_range = {}
        if start_date:
            date_range["start"] = start_date
        if end_date:
            date_range["end"] = end_date
        
        self.active_filters["date_range"] = date_range
        
        msg = "✓ Filtrowanie po datach: "
        if start_date and end_date:
            msg += f"{start_date} do {end_date}"
        elif start_date:
            msg += f"od {start_date}"
        elif end_date:
            msg += f"do {end_date}"
        
        return msg
    
    def filter_by_section_type(self, section_types: List[str]) -> str:
        """
        Add section type filter to active filters.
        
        Valid types: 'tldr', 'checklist', 'key_insight', 'content', 'source_attribution'
        
        Args:
            section_types: List of section types to filter by
            
        Returns:
            Confirmation message
        """
        valid_types = ['tldr', 'checklist', 'key_insight', 'content', 'source_attribution']
        
        # Validate section types
        invalid = [t for t in section_types if t not in valid_types]
        if invalid:
            return f"✗ Nieprawidłowe typy sekcji: {', '.join(invalid)}\nDostępne: {', '.join(valid_types)}"
        
        self.active_filters["section_type"] = section_types
        return f"✓ Filtrowanie po typach sekcji: {', '.join(section_types)}"
    
    def clear_filters(self) -> str:
        """
        Clear all active filters.
        
        Returns:
            Confirmation message
        """
        self.active_filters = {}
        return "✓ Wszystkie filtry wyczyszczone"
    
    def show_active_filters(self) -> str:
        """
        Show currently active filters.
        
        Returns:
            String describing active filters
        """
        if not self.active_filters:
            return "Brak aktywnych filtrów"
        
        msg = "Aktywne filtry:\n"
        for key, value in self.active_filters.items():
            msg += f"  - {key}: {value}\n"
        
        return msg.strip()
    
    def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        use_filters: bool = True,
    ) -> List[SearchResult]:
        """
        Execute hybrid semantic search with optional filters.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            use_filters: Whether to apply active filters
            
        Returns:
            List of search results
        """
        filters = self.active_filters if use_filters else None
        
        if filters:
            print(f"Wyszukiwanie z filtrami: {filters}")
        
        results = self.search_engine.search(
            query=query,
            top_k=top_k,
            filters=filters,
        )
        
        return results
    
    def search_with_auto_filters(
        self,
        query: str,
        top_k: int = 10,
        **filter_kwargs,
    ) -> List[SearchResult]:
        """
        Search with automatic filter detection from kwargs.
        
        Args:
            query: Search query
            top_k: Number of results
            **filter_kwargs: Optional filters (tags, categories, start_date, end_date, section_types)
            
        Returns:
            List of search results
        """
        # Clear previous filters
        self.clear_filters()
        
        # Apply filters from kwargs
        if "tags" in filter_kwargs and filter_kwargs["tags"]:
            self.filter_by_tags(filter_kwargs["tags"])
        
        if "categories" in filter_kwargs and filter_kwargs["categories"]:
            self.filter_by_categories(filter_kwargs["categories"])
        
        if "start_date" in filter_kwargs or "end_date" in filter_kwargs:
            self.filter_by_date_range(
                start_date=filter_kwargs.get("start_date"),
                end_date=filter_kwargs.get("end_date"),
            )
        
        if "section_types" in filter_kwargs and filter_kwargs["section_types"]:
            self.filter_by_section_type(filter_kwargs["section_types"])
        
        # Execute search
        return self.semantic_search(query=query, top_k=top_k)


def search_with_agent(
    query: str,
    top_k: int = 10,
    tags: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    section_types: Optional[List[str]] = None,
    client: QdrantClient = None,
) -> List[SearchResult]:
    """
    Convenience function for agent-based search with filters.
    
    Args:
        query: Search query
        top_k: Number of results
        tags: Optional list of tags to filter by
        categories: Optional list of categories to filter by
        start_date: Optional start date (ISO format)
        end_date: Optional end date (ISO format)
        section_types: Optional list of section types to filter by
        client: QdrantClient instance
        
    Returns:
        List of search results
    """
    agent = SearchAgent(client=client)
    
    return agent.search_with_auto_filters(
        query=query,
        top_k=top_k,
        tags=tags,
        categories=categories,
        start_date=start_date,
        end_date=end_date,
        section_types=section_types,
    )


if __name__ == "__main__":
    # Test agent
    print("\n=== Testing Search Agent ===\n")
    
    agent = SearchAgent()
    
    # Example 1: Search with tag filter
    print("Example 1: Wyszukiwanie artykułów o AI")
    print("-" * 50)
    
    agent.filter_by_tags(["AI", "#AI"])
    print(agent.show_active_filters())
    
    results = agent.semantic_search(
        query="Jak używać agentów AI w developmencie?",
        top_k=3,
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Tags: {result.tags[:5]}")  # First 5 tags
        print(f"   Section: {result.section_type}")
    
    # Example 2: Search for checklists only
    print("\n\nExample 2: Szukanie checklistów")
    print("-" * 50)
    
    agent.clear_filters()
    agent.filter_by_section_type(["checklist", "tldr"])
    print(agent.show_active_filters())
    
    results = agent.semantic_search(
        query="Workflow dla rozwoju produktu",
        top_k=3,
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Section: {result.section_type}")
        print(f"   Preview: {result.text[:100]}...")
    
    # Example 3: Using convenience function
    print("\n\nExample 3: Wyszukiwanie z wieloma filtrami")
    print("-" * 50)
    
    results = search_with_agent(
        query="Product management best practices",
        top_k=5,
        categories=["Produkt"],
        start_date="2025-01-01",
        section_types=["content", "key_insight"],
    )
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Date: {result.publication_date}")
        print(f"   Categories: {result.categories}")
