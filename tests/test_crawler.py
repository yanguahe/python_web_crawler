"""
Tests for the arXiv crawler module.
"""
import pytest
from datetime import datetime


class TestPaperModel:
    """Tests for the Paper model."""
    
    def test_paper_creation(self):
        """Test creating a Paper instance."""
        from crawler.models import Paper
        
        paper = Paper(
            id="2312.12345",
            title="Test Paper Title",
            authors=["Author One", "Author Two"],
            abstract="This is a test abstract.",
            categories=["cs.AI", "cs.LG"],
            published=datetime.now(),
            pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
            arxiv_url="https://arxiv.org/abs/2312.12345"
        )
        
        assert paper.id == "2312.12345"
        assert paper.title == "Test Paper Title"
        assert len(paper.authors) == 2
        assert "cs.AI" in paper.categories
    
    def test_paper_filename(self):
        """Test generating filename from paper ID."""
        from crawler.models import Paper
        
        paper = Paper(
            id="2312.12345",
            title="Test",
            authors=[],
            abstract="Test",
            categories=[],
            published=datetime.now(),
            pdf_url="",
            arxiv_url=""
        )
        
        filename = paper.to_filename()
        assert filename == "2312.12345.json"
    
    def test_paper_formatted_authors(self):
        """Test formatted authors string."""
        from crawler.models import Paper
        
        # Few authors
        paper = Paper(
            id="test",
            title="Test",
            authors=["Alice", "Bob"],
            abstract="Test",
            categories=[],
            published=datetime.now(),
            pdf_url="",
            arxiv_url=""
        )
        
        assert paper.formatted_authors == "Alice, Bob"
        
        # Many authors
        paper.authors = ["Alice", "Bob", "Charlie", "David", "Eve"]
        assert "et al." in paper.formatted_authors


class TestSearchResult:
    """Tests for the SearchResult model."""
    
    def test_has_more(self):
        """Test has_more property."""
        from crawler.models import Paper, SearchResult
        
        papers = [
            Paper(
                id=f"test{i}",
                title=f"Paper {i}",
                authors=[],
                abstract="Test",
                categories=[],
                published=datetime.now(),
                pdf_url="",
                arxiv_url=""
            )
            for i in range(10)
        ]
        
        # Has more results
        result = SearchResult(
            query="test",
            total_results=100,
            start_index=0,
            items_per_page=10,
            papers=papers
        )
        
        assert result.has_more is True
        
        # No more results
        result = SearchResult(
            query="test",
            total_results=10,
            start_index=0,
            items_per_page=10,
            papers=papers
        )
        
        assert result.has_more is False


class TestArxivClient:
    """Tests for the ArxivClient."""
    
    def test_build_query_url(self):
        """Test building query URLs."""
        from crawler.arxiv_client import ArxivClient
        
        client = ArxivClient()
        url = client._build_query_url("machine learning", start=0, max_results=10)
        
        assert "search_query=all%3Amachine+learning" in url
        assert "max_results=10" in url
        assert "start=0" in url
    
    def test_parse_arxiv_id(self):
        """Test parsing arXiv IDs from URLs."""
        from crawler.arxiv_client import ArxivClient
        
        client = ArxivClient()
        
        # Standard format
        assert client._parse_arxiv_id("http://arxiv.org/abs/2312.12345v1") == "2312.12345"
        
        # Without version
        assert client._parse_arxiv_id("http://arxiv.org/abs/2312.12345") == "2312.12345"


# Integration tests (require network access)
@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_integration():
    """Integration test for search functionality."""
    from crawler.arxiv_client import ArxivClient
    
    client = ArxivClient()
    result = await client.search("quantum computing", max_results=3)
    
    assert result.total_results > 0
    assert len(result.papers) <= 3
    
    if result.papers:
        paper = result.papers[0]
        assert paper.id
        assert paper.title
        assert paper.abstract

