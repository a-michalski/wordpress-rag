"""
WordPress WXR XML parser with HTML to Markdown conversion.
Extracts metadata and identifies special section types (TL;DR, checklists, key insights).
"""
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import re
from html import unescape

from bs4 import BeautifulSoup
from markdownify import markdownify as md
from dateutil import parser as date_parser

import config


@dataclass
class Article:
    """Parsed WordPress article with metadata and content."""
    
    # Core identifiers
    document_id: str  # wp:post_id
    title: str
    url: str  # permalink
    slug: str  # wp:post_name
    
    # Author and dates
    author: str  # dc:creator
    publication_date: datetime  # wp:post_date
    modified_date: datetime  # wp:post_modified
    
    # Taxonomy
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    # Content (both HTML and Markdown)
    content_html: str = ""
    content_markdown: str = ""
    excerpt: str = ""
    
    # SEO metadata (from Yoast)
    reading_time_minutes: Optional[int] = None
    seo_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    
    # Extracted special sections
    tldr: Optional[str] = None
    key_insights: Optional[str] = None
    checklists: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    
    # Section type markers for chunking
    section_markers: Dict[str, List[int]] = field(default_factory=dict)  # {section_type: [char_positions]}


class WordPressParser:
    """Parse WordPress WXR export and convert to structured articles."""
    
    def __init__(self, xml_path: str):
        self.xml_path = xml_path
        self.namespaces = config.WXR_NAMESPACES
    
    def parse(self) -> List[Article]:
        """Parse WordPress XML and return list of articles."""
        print(f"Parsing WordPress XML from {self.xml_path}...")
        
        tree = ET.parse(self.xml_path)
        root = tree.getroot()
        
        articles = []
        items = root.findall('.//item')
        
        print(f"Found {len(items)} total items in XML")
        
        for item in items:
            article = self._parse_item(item)
            if article:
                articles.append(article)
        
        print(f"Extracted {len(articles)} published articles")
        return articles
    
    def _parse_item(self, item: ET.Element) -> Optional[Article]:
        """Parse a single <item> element."""
        
        # Filter by post type and status
        post_type = self._get_text(item, 'wp:post_type')
        status = self._get_text(item, 'wp:status')
        
        if post_type != config.FILTER_POST_TYPE or status != config.FILTER_STATUS:
            return None
        
        # Extract core metadata
        post_id = self._get_text(item, 'wp:post_id')
        title = self._get_text(item, 'title')
        url = self._get_text(item, 'link')
        slug = self._get_text(item, 'wp:post_name')
        author = self._get_text(item, 'dc:creator')
        
        # Parse dates
        pub_date_str = self._get_text(item, 'wp:post_date')
        mod_date_str = self._get_text(item, 'wp:post_modified')
        
        try:
            publication_date = date_parser.parse(pub_date_str)
            modified_date = date_parser.parse(mod_date_str)
        except Exception as e:
            print(f"Warning: Could not parse dates for post {post_id}: {e}")
            return None
        
        # Extract categories and tags
        categories = []
        tags = []
        for category in item.findall('category'):
            domain = category.get('domain')
            value = category.text
            if domain == 'category' and value:
                categories.append(value)
            elif domain == 'post_tag' and value:
                tags.append(value)
        
        # Extract content
        content_html = self._get_text(item, 'content:encoded') or ""
        excerpt = self._get_text(item, 'excerpt:encoded') or ""
        
        # Extract Yoast SEO metadata
        reading_time = self._get_postmeta(item, '_yoast_wpseo_estimated-reading-time-minutes')
        seo_description = self._get_postmeta(item, '_yoast_wpseo_metadesc')
        focus_keyword = self._get_postmeta(item, '_yoast_wpseo_focuskw')
        
        # Convert HTML to Markdown
        content_markdown = self._html_to_markdown(content_html)
        
        # Extract special sections
        tldr = self._extract_tldr(content_html)
        key_insights = self._extract_key_insights(content_html)
        checklists = self._extract_checklists(content_html)
        source_url = self._extract_source_url(content_html)
        
        # Identify section positions in markdown for chunking
        section_markers = self._identify_section_markers(content_markdown)
        
        article = Article(
            document_id=post_id,
            title=title,
            url=url,
            slug=slug,
            author=author,
            publication_date=publication_date,
            modified_date=modified_date,
            categories=categories,
            tags=tags,
            content_html=content_html,
            content_markdown=content_markdown,
            excerpt=excerpt,
            reading_time_minutes=int(reading_time) if reading_time and reading_time.isdigit() else None,
            seo_description=seo_description,
            focus_keyword=focus_keyword,
            tldr=tldr,
            key_insights=key_insights,
            checklists=checklists,
            source_url=source_url,
            section_markers=section_markers,
        )
        
        return article
    
    def _get_text(self, element: ET.Element, tag: str) -> str:
        """Get text content from element with namespace support."""
        # Try with namespace
        for prefix, uri in self.namespaces.items():
            full_tag = f'{{{uri}}}{tag.split(":")[-1]}'
            child = element.find(full_tag)
            if child is not None and child.text:
                return unescape(child.text.strip())
        
        # Try without namespace
        child = element.find(tag)
        if child is not None and child.text:
            return unescape(child.text.strip())
        
        return ""
    
    def _get_postmeta(self, item: ET.Element, meta_key: str) -> Optional[str]:
        """Extract value from wp:postmeta by meta_key."""
        for postmeta in item.findall('wp:postmeta', self.namespaces):
            key = postmeta.find('wp:meta_key', self.namespaces)
            value = postmeta.find('wp:meta_value', self.namespaces)
            
            if key is not None and key.text == meta_key:
                if value is not None and value.text:
                    return value.text.strip()
        
        return None
    
    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML content to Markdown."""
        if not html:
            return ""
        
        # Use markdownify with options to preserve structure
        markdown = md(
            html,
            heading_style="ATX",  # Use # headers
            bullets="-",  # Use - for bullets
            strong_em_symbol="**",  # Use ** for bold
            strip=['script', 'style'],  # Remove scripts and styles
        )
        
        # Clean up excessive newlines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        return markdown.strip()
    
    def _extract_tldr(self, html: str) -> Optional[str]:
        """Extract TL;DR section from HTML content."""
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find TL;DR header
        for header in soup.find_all(['h2', 'h3']):
            header_text = header.get_text(strip=True).upper()
            if 'TL;DR' in header_text or 'TL.DR' in header_text:
                # Collect content until next header of same/higher level
                content_parts = []
                for sibling in header.find_next_siblings():
                    if sibling.name in ['h2', 'h3'] and header.name in ['h2', 'h3']:
                        break
                    content_parts.append(sibling.get_text(separator='\n', strip=True))
                
                tldr_content = '\n'.join(content_parts)
                if tldr_content:
                    return tldr_content
        
        return None
    
    def _extract_key_insights(self, html: str) -> Optional[str]:
        """Extract 'Kluczowy insight' section from HTML content."""
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        for header in soup.find_all(['h2', 'h3']):
            header_text = header.get_text(strip=True).lower()
            if 'kluczowy insight' in header_text or 'key insight' in header_text:
                # Collect content until next h2
                content_parts = []
                for sibling in header.find_next_siblings():
                    if sibling.name == 'h2':
                        break
                    content_parts.append(sibling.get_text(separator='\n', strip=True))
                
                insight_content = '\n'.join(content_parts)
                if insight_content:
                    return insight_content
        
        return None
    
    def _extract_checklists(self, html: str) -> List[str]:
        """Extract checklist items from content."""
        if not html:
            return []
        
        checklists = []
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()
        
        # Pattern 1: Unicode checkmarks
        checkmark_items = re.findall(r'✅[^\n✅]+', text)
        checklists.extend([item.strip() for item in checkmark_items])
        
        # Pattern 2: Lists after "Checklist" headers
        for header in soup.find_all(['h2', 'h3', 'h4']):
            if 'checklist' in header.get_text().lower():
                next_list = header.find_next_sibling(['ul', 'ol'])
                if next_list:
                    for li in next_list.find_all('li', recursive=False):
                        checklists.append(li.get_text(strip=True))
        
        return checklists
    
    def _extract_source_url(self, html: str) -> Optional[str]:
        """Extract source URL from attribution section."""
        if not html:
            return None
        
        # Look for "Źródło:" pattern with link
        match = re.search(r'Źródło:\s*<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def _identify_section_markers(self, markdown: str) -> Dict[str, List[int]]:
        """Identify positions of special sections in markdown for chunking."""
        markers = {
            'tldr': [],
            'checklist': [],
            'key_insight': [],
            'source_attribution': [],
        }
        
        lines = markdown.split('\n')
        char_position = 0
        
        for line in lines:
            line_lower = line.lower()
            
            # Check for TL;DR
            if 'tl;dr' in line_lower or '## tl;dr' in line_lower:
                markers['tldr'].append(char_position)
            
            # Check for checklist markers
            if '✅' in line or 'checklist' in line_lower:
                markers['checklist'].append(char_position)
            
            # Check for key insights
            if 'kluczowy insight' in line_lower or 'key insight' in line_lower:
                markers['key_insight'].append(char_position)
            
            # Check for source attribution
            if 'źródło:' in line_lower or 'ten wpis jest częścią' in line_lower:
                markers['source_attribution'].append(char_position)
            
            char_position += len(line) + 1  # +1 for newline
        
        return markers


def parse_wordpress_xml(xml_path: str = None) -> List[Article]:
    """Convenience function to parse WordPress XML."""
    if xml_path is None:
        xml_path = str(config.WORDPRESS_XML_PATH)
    
    parser = WordPressParser(xml_path)
    return parser.parse()


if __name__ == "__main__":
    # Test parsing
    articles = parse_wordpress_xml()
    
    if articles:
        print(f"\n=== Sample Article ===")
        article = articles[0]
        print(f"ID: {article.document_id}")
        print(f"Title: {article.title}")
        print(f"URL: {article.url}")
        print(f"Author: {article.author}")
        print(f"Date: {article.publication_date}")
        print(f"Categories: {article.categories}")
        print(f"Tags: {article.tags[:5]}...")  # First 5 tags
        print(f"Reading time: {article.reading_time_minutes} min")
        print(f"Content length: {len(article.content_markdown)} chars")
        print(f"Has TL;DR: {article.tldr is not None}")
        print(f"Checklists: {len(article.checklists)} items")
        print(f"Has Key Insights: {article.key_insights is not None}")
        print(f"\nFirst 500 chars of markdown:\n{article.content_markdown[:500]}...")
