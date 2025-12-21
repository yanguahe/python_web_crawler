"""
arXiv API client for searching and retrieving papers.
"""
import asyncio
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlencode

import httpx
import feedparser
from dateutil import parser as date_parser

from .models import Paper, SearchResult
from config import settings


class ArxivClient:
    """Client for interacting with the arXiv API."""
    
    def __init__(self):
        self.base_url = settings.arxiv_api_base_url
        self.max_results = settings.arxiv_max_results
        self.rate_limit_delay = settings.arxiv_rate_limit_delay
        self._last_request_time: Optional[float] = None
    
    async def _rate_limit(self):
        """Ensure we respect arXiv's rate limit."""
        if self._last_request_time is not None:
            elapsed = asyncio.get_event_loop().time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
    
    def _build_query_url(
        self,
        query: str,
        start: int = 0,
        max_results: Optional[int] = None,
        sort_by: str = "relevance",
        sort_order: str = "descending"
    ) -> str:
        """
        Build the arXiv API query URL.
        
        Args:
            query: Search query string
            start: Starting index for results
            max_results: Maximum number of results to return
            sort_by: Sort field ('relevance', 'lastUpdatedDate', 'submittedDate')
            sort_order: Sort order ('ascending', 'descending')
        
        Returns:
            Complete API URL
        """
        if max_results is None:
            max_results = self.max_results
        
        # Build the search query - search in all fields
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order
        }
        
        return f"{self.base_url}?{urlencode(params)}"
    
    def _parse_arxiv_id(self, entry_id: str) -> str:
        """Extract the arXiv ID from the entry URL."""
        # Entry ID format: http://arxiv.org/abs/2312.12345v1
        match = re.search(r"abs/(.+?)(?:v\d+)?$", entry_id)
        if match:
            return match.group(1)
        return entry_id.split("/")[-1]
    
    def _parse_entry(self, entry: dict) -> Paper:
        """Parse a feedparser entry into a Paper object."""
        # Extract arXiv ID
        arxiv_id = self._parse_arxiv_id(entry.get("id", ""))
        
        # Extract authors
        authors = []
        if "authors" in entry:
            authors = [author.get("name", "") for author in entry.get("authors", [])]
        elif "author" in entry:
            authors = [entry.get("author", "")]
        
        # Extract categories
        categories = []
        if "tags" in entry:
            categories = [tag.get("term", "") for tag in entry.get("tags", [])]
        
        # Parse dates
        published = datetime.now()
        if "published" in entry:
            try:
                published = date_parser.parse(entry["published"])
            except (ValueError, TypeError):
                pass
        
        updated = None
        if "updated" in entry:
            try:
                updated = date_parser.parse(entry["updated"])
            except (ValueError, TypeError):
                pass
        
        # Build URLs
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        # Check for explicit PDF link
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", pdf_url)
                break
        
        # Clean abstract (remove newlines and extra whitespace)
        abstract = entry.get("summary", "").strip()
        abstract = re.sub(r"\s+", " ", abstract)
        
        return Paper(
            id=arxiv_id,
            title=entry.get("title", "").strip().replace("\n", " "),
            authors=authors,
            abstract=abstract,
            categories=categories,
            published=published,
            updated=updated,
            pdf_url=pdf_url,
            arxiv_url=arxiv_url
        )
    
    async def search(
        self,
        query: str,
        start: int = 0,
        max_results: Optional[int] = None
    ) -> SearchResult:
        """
        Search for papers on arXiv.
        
        Args:
            query: Search query string
            start: Starting index for results
            max_results: Maximum number of results to return
        
        Returns:
            SearchResult containing matching papers
        """
        await self._rate_limit()
        
        url = self._build_query_url(query, start, max_results)
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        
        # Parse the Atom feed
        feed = feedparser.parse(response.text)
        
        # Extract total results from opensearch namespace
        total_results = int(feed.feed.get("opensearch_totalresults", 0))
        start_index = int(feed.feed.get("opensearch_startindex", start))
        items_per_page = int(feed.feed.get("opensearch_itemsperpage", max_results or self.max_results))
        
        # Parse each entry
        papers = [self._parse_entry(entry) for entry in feed.entries]
        
        return SearchResult(
            query=query,
            total_results=total_results,
            start_index=start_index,
            items_per_page=items_per_page,
            papers=papers,
            search_time=datetime.now()
        )
    
    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Paper]:
        """
        Get a specific paper by its arXiv ID.
        
        Args:
            arxiv_id: The arXiv paper ID (e.g., '2312.12345')
        
        Returns:
            Paper object if found, None otherwise
        """
        await self._rate_limit()
        
        # Use id_list parameter for specific paper lookup
        params = {
            "id_list": arxiv_id,
            "max_results": 1
        }
        url = f"{self.base_url}?{urlencode(params)}"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        
        if feed.entries:
            return self._parse_entry(feed.entries[0])
        
        return None
    
    async def search_by_author(
        self,
        author: str,
        start: int = 0,
        max_results: Optional[int] = None
    ) -> SearchResult:
        """
        Search for papers by author name.
        
        Args:
            author: Author name to search for
            start: Starting index for results
            max_results: Maximum number of results
        
        Returns:
            SearchResult containing matching papers
        """
        await self._rate_limit()
        
        params = {
            "search_query": f"au:{author}",
            "start": start,
            "max_results": max_results or self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        url = f"{self.base_url}?{urlencode(params)}"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        
        total_results = int(feed.feed.get("opensearch_totalresults", 0))
        papers = [self._parse_entry(entry) for entry in feed.entries]
        
        return SearchResult(
            query=f"author:{author}",
            total_results=total_results,
            start_index=start,
            items_per_page=max_results or self.max_results,
            papers=papers,
            search_time=datetime.now()
        )
    
    async def search_by_category(
        self,
        category: str,
        start: int = 0,
        max_results: Optional[int] = None
    ) -> SearchResult:
        """
        Search for papers by arXiv category.
        
        Args:
            category: arXiv category (e.g., 'cs.AI', 'math.CO')
            start: Starting index for results
            max_results: Maximum number of results
        
        Returns:
            SearchResult containing matching papers
        """
        await self._rate_limit()
        
        params = {
            "search_query": f"cat:{category}",
            "start": start,
            "max_results": max_results or self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        url = f"{self.base_url}?{urlencode(params)}"
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        
        feed = feedparser.parse(response.text)
        
        total_results = int(feed.feed.get("opensearch_totalresults", 0))
        papers = [self._parse_entry(entry) for entry in feed.entries]
        
        return SearchResult(
            query=f"category:{category}",
            total_results=total_results,
            start_index=start,
            items_per_page=max_results or self.max_results,
            papers=papers,
            search_time=datetime.now()
        )

