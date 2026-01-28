"""
Main CLI interface for WordPress RAG system.
Commands: ingest, search, query (with filters)
"""
import argparse
import sys
from typing import Optional, List

import config
from ingest import ingest_wordpress_data
from search import search
from agent import search_with_agent
from qdrant_setup import get_collection_info, create_qdrant_client


def cmd_ingest(args):
    """Run document ingestion pipeline."""
    print("\n" + "="*70)
    print("Starting WordPress Document Ingestion")
    print("="*70)
    print(f"XML file: {args.xml_path or config.WORDPRESS_XML_PATH}")
    print(f"Recreate collection: {args.recreate}")
    print()
    
    stats = ingest_wordpress_data(
        xml_path=args.xml_path,
        recreate_collection=args.recreate,
    )
    
    if stats["success"]:
        print("\n" + "="*70)
        print("✓ INGESTION COMPLETE")
        print("="*70)
        print(f"Articles parsed: {stats['articles_parsed']}")
        print(f"Chunks created: {stats['chunks_created']}")
        print(f"Points uploaded: {stats['points_uploaded']}")
        print(f"Collection: {stats['collection_name']}")
    else:
        print(f"\n✗ Ingestion failed: {stats.get('error', 'Unknown error')}")
        sys.exit(1)


def cmd_search(args):
    """Run simple semantic search."""
    print("\n" + "="*70)
    print("Semantic Search")
    print("="*70)
    print(f"Query: {args.query}")
    print(f"Top-k: {args.top_k}")
    print()
    
    results = search(
        query=args.query,
        top_k=args.top_k,
    )
    
    if not results:
        print("No results found.")
        return
    
    print(f"\n{'='*70}")
    print(f"Found {len(results)} results")
    print('='*70)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   URL: {result.url}")
        print(f"   Section: {result.section_type}")
        print(f"   Author: {result.author}")
        print(f"   Date: {result.publication_date}")
        
        if result.categories:
            print(f"   Categories: {', '.join(result.categories)}")
        
        if result.tags:
            print(f"   Tags: {', '.join(result.tags[:5])}" + (" ..." if len(result.tags) > 5 else ""))
        
        print(f"\n   {result.text[:300]}...")
        print()


def cmd_query(args):
    """Run search with agent filters."""
    print("\n" + "="*70)
    print("Agent-Based Search with Filters")
    print("="*70)
    print(f"Query: {args.query}")
    print(f"Top-k: {args.top_k}")
    
    # Show active filters
    filters_active = False
    if args.tags:
        print(f"Tags filter: {', '.join(args.tags)}")
        filters_active = True
    if args.categories:
        print(f"Categories filter: {', '.join(args.categories)}")
        filters_active = True
    if args.start_date:
        print(f"Start date: {args.start_date}")
        filters_active = True
    if args.end_date:
        print(f"End date: {args.end_date}")
        filters_active = True
    if args.section_types:
        print(f"Section types: {', '.join(args.section_types)}")
        filters_active = True
    
    if not filters_active:
        print("No filters applied")
    
    print()
    
    results = search_with_agent(
        query=args.query,
        top_k=args.top_k,
        tags=args.tags,
        categories=args.categories,
        start_date=args.start_date,
        end_date=args.end_date,
        section_types=args.section_types,
    )
    
    if not results:
        print("No results found.")
        return
    
    print(f"\n{'='*70}")
    print(f"Found {len(results)} results")
    print('='*70)
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   URL: {result.url}")
        print(f"   Section: {result.section_type}")
        print(f"   Date: {result.publication_date}")
        
        if result.categories:
            print(f"   Categories: {', '.join(result.categories)}")
        
        if result.tags and len(result.tags) > 0:
            print(f"   Tags: {', '.join(result.tags[:5])}" + (" ..." if len(result.tags) > 5 else ""))
        
        print(f"\n   {result.text[:300]}...")
        print()


def cmd_info(args):
    """Show collection information."""
    print("\n" + "="*70)
    print("Collection Information")
    print("="*70)
    
    client = create_qdrant_client()
    get_collection_info(client, args.collection)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="WordPress RAG System - CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Ingest WordPress XML data
  python main.py ingest --recreate
  
  # Simple semantic search
  python main.py search "Jak używać agentów AI?"
  
  # Search with filters
  python main.py query "Product management" --tags AI --categories Produkt
  
  # Search by date range
  python main.py query "UX design" --start-date 2025-01-01
  
  # Search for specific section types
  python main.py query "Workflow" --section-types checklist tldr
  
  # Show collection info
  python main.py info
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest WordPress XML data')
    ingest_parser.add_argument(
        '--xml-path',
        type=str,
        default=None,
        help=f'Path to WordPress XML file (default: {config.WORDPRESS_XML_PATH})'
    )
    ingest_parser.add_argument(
        '--recreate',
        action='store_true',
        help='Recreate collection (delete existing data)'
    )
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Simple semantic search')
    search_parser.add_argument('query', type=str, help='Search query')
    search_parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='Number of results to return (default: 10)'
    )
    
    # Query command (with filters)
    query_parser = subparsers.add_parser('query', help='Search with filters')
    query_parser.add_argument('query', type=str, help='Search query')
    query_parser.add_argument(
        '--top-k',
        type=int,
        default=10,
        help='Number of results to return (default: 10)'
    )
    query_parser.add_argument(
        '--tags',
        nargs='+',
        help='Filter by tags (space-separated)'
    )
    query_parser.add_argument(
        '--categories',
        nargs='+',
        help='Filter by categories (space-separated)'
    )
    query_parser.add_argument(
        '--start-date',
        type=str,
        help='Filter by start date (ISO format: YYYY-MM-DD)'
    )
    query_parser.add_argument(
        '--end-date',
        type=str,
        help='Filter by end date (ISO format: YYYY-MM-DD)'
    )
    query_parser.add_argument(
        '--section-types',
        nargs='+',
        choices=['tldr', 'checklist', 'key_insight', 'content', 'source_attribution'],
        help='Filter by section types'
    )
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show collection information')
    info_parser.add_argument(
        '--collection',
        type=str,
        default=None,
        help=f'Collection name (default: {config.QDRANT_COLLECTION_NAME})'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'ingest':
        cmd_ingest(args)
    elif args.command == 'search':
        cmd_search(args)
    elif args.command == 'query':
        cmd_query(args)
    elif args.command == 'info':
        cmd_info(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
