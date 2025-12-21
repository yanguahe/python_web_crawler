"""
Tests for the storage module.
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime


class TestFileHandler:
    """Tests for the FileHandler class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def sample_paper(self):
        """Create a sample paper for testing."""
        from crawler.models import Paper
        
        return Paper(
            id="2312.12345",
            title="Test Paper",
            authors=["Author One", "Author Two"],
            abstract="This is a test abstract for the paper.",
            categories=["cs.AI", "cs.LG"],
            published=datetime(2023, 12, 15),
            updated=datetime(2023, 12, 16),
            pdf_url="https://arxiv.org/pdf/2312.12345.pdf",
            arxiv_url="https://arxiv.org/abs/2312.12345"
        )
    
    def test_save_paper(self, temp_dir, sample_paper):
        """Test saving a paper."""
        from storage.file_handler import FileHandler
        
        handler = FileHandler(data_dir=temp_dir)
        path = handler.save_paper(sample_paper)
        
        assert Path(path).exists()
        assert "2312.12345.json" in path
    
    def test_get_paper(self, temp_dir, sample_paper):
        """Test retrieving a saved paper."""
        from storage.file_handler import FileHandler
        
        handler = FileHandler(data_dir=temp_dir)
        handler.save_paper(sample_paper)
        
        loaded_paper = handler.get_paper("2312.12345")
        
        assert loaded_paper is not None
        assert loaded_paper.id == sample_paper.id
        assert loaded_paper.title == sample_paper.title
        assert loaded_paper.authors == sample_paper.authors
    
    def test_get_nonexistent_paper(self, temp_dir):
        """Test getting a paper that doesn't exist."""
        from storage.file_handler import FileHandler
        
        handler = FileHandler(data_dir=temp_dir)
        paper = handler.get_paper("nonexistent")
        
        assert paper is None
    
    def test_list_papers(self, temp_dir, sample_paper):
        """Test listing all papers."""
        from storage.file_handler import FileHandler
        from crawler.models import Paper
        
        handler = FileHandler(data_dir=temp_dir)
        
        # Save multiple papers
        handler.save_paper(sample_paper)
        
        paper2 = Paper(
            id="2312.67890",
            title="Another Paper",
            authors=["Author Three"],
            abstract="Another abstract.",
            categories=["cs.CV"],
            published=datetime(2023, 12, 20),
            pdf_url="https://arxiv.org/pdf/2312.67890.pdf",
            arxiv_url="https://arxiv.org/abs/2312.67890"
        )
        handler.save_paper(paper2)
        
        papers = handler.list_papers()
        
        assert len(papers) == 2
    
    def test_delete_paper(self, temp_dir, sample_paper):
        """Test deleting a paper."""
        from storage.file_handler import FileHandler
        
        handler = FileHandler(data_dir=temp_dir)
        handler.save_paper(sample_paper)
        
        # Verify it exists
        assert handler.paper_exists("2312.12345")
        
        # Delete it
        result = handler.delete_paper("2312.12345")
        
        assert result is True
        assert not handler.paper_exists("2312.12345")
    
    def test_delete_nonexistent_paper(self, temp_dir):
        """Test deleting a paper that doesn't exist."""
        from storage.file_handler import FileHandler
        
        handler = FileHandler(data_dir=temp_dir)
        result = handler.delete_paper("nonexistent")
        
        assert result is False
    
    def test_get_stats(self, temp_dir, sample_paper):
        """Test getting storage statistics."""
        from storage.file_handler import FileHandler
        
        handler = FileHandler(data_dir=temp_dir)
        handler.save_paper(sample_paper)
        
        stats = handler.get_stats()
        
        assert stats["total_papers"] == 1
        assert stats["total_size_bytes"] > 0
        assert "storage_path" in stats
    
    def test_save_batch(self, temp_dir):
        """Test saving multiple papers at once."""
        from storage.file_handler import FileHandler
        from crawler.models import Paper
        
        handler = FileHandler(data_dir=temp_dir)
        
        papers = [
            Paper(
                id=f"2312.{i:05d}",
                title=f"Paper {i}",
                authors=["Author"],
                abstract="Abstract",
                categories=["cs.AI"],
                published=datetime(2023, 12, i + 1),
                pdf_url=f"https://arxiv.org/pdf/2312.{i:05d}.pdf",
                arxiv_url=f"https://arxiv.org/abs/2312.{i:05d}"
            )
            for i in range(5)
        ]
        
        paths = handler.save_batch(papers)
        
        assert len(paths) == 5
        assert handler.get_stats()["total_papers"] == 5

