"""
Data models for arXiv papers.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Paper(BaseModel):
    """Represents an arXiv paper."""
    
    id: str = Field(..., description="arXiv paper ID (e.g., '2312.12345')")
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    abstract: str = Field(..., description="Paper abstract/summary")
    categories: List[str] = Field(default_factory=list, description="arXiv categories")
    published: datetime = Field(..., description="Publication date")
    updated: Optional[datetime] = Field(None, description="Last update date")
    pdf_url: str = Field(..., description="URL to the PDF")
    arxiv_url: str = Field(..., description="URL to the arXiv page")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
    
    def to_filename(self) -> str:
        """Generate a safe filename for this paper."""
        # Replace characters that are not safe for filenames
        safe_id = self.id.replace("/", "_").replace(":", "_")
        return f"{safe_id}.json"
    
    @property
    def short_abstract(self) -> str:
        """Get a shortened version of the abstract (first 200 chars)."""
        if len(self.abstract) <= 200:
            return self.abstract
        return self.abstract[:197] + "..."
    
    @property
    def formatted_authors(self) -> str:
        """Get authors as a comma-separated string."""
        if len(self.authors) <= 3:
            return ", ".join(self.authors)
        return f"{', '.join(self.authors[:3])} et al."


class SearchResult(BaseModel):
    """Represents search results from arXiv."""
    
    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results available")
    start_index: int = Field(0, description="Starting index of results")
    items_per_page: int = Field(10, description="Number of results per page")
    papers: List[Paper] = Field(default_factory=list, description="List of papers")
    search_time: datetime = Field(default_factory=datetime.now, description="When the search was performed")
    
    @property
    def has_more(self) -> bool:
        """Check if there are more results available."""
        return self.start_index + len(self.papers) < self.total_results

