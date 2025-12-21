"""
File storage handler for saving and loading papers.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import httpx

from crawler.models import Paper
from config import settings


class FileHandler:
    """Handle file operations for paper storage."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize the file handler.
        
        Args:
            data_dir: Directory to store paper files. Defaults to settings.papers_dir
        """
        self.data_dir = data_dir or settings.papers_dir
        self._ensure_dir_exists()
    
    def _ensure_dir_exists(self):
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_paper_path(self, paper_id: str) -> Path:
        """Get the file path for a paper."""
        safe_id = paper_id.replace("/", "_").replace(":", "_")
        return self.data_dir / f"{safe_id}.json"
    
    def save_paper(self, paper: Paper) -> str:
        """
        Save a paper to disk.
        
        Args:
            paper: Paper object to save
        
        Returns:
            Path to the saved file
        """
        file_path = self._get_paper_path(paper.id)
        
        # Convert to dict and handle datetime serialization
        data = paper.model_dump()
        data["published"] = paper.published.isoformat() if paper.published else None
        data["updated"] = paper.updated.isoformat() if paper.updated else None
        data["saved_at"] = datetime.now().isoformat()
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return str(file_path)
    
    def save_batch(self, papers: List[Paper]) -> List[str]:
        """
        Save multiple papers to disk.
        
        Args:
            papers: List of Paper objects to save
        
        Returns:
            List of paths to saved files
        """
        return [self.save_paper(paper) for paper in papers]
    
    def get_paper(self, paper_id: str) -> Optional[Paper]:
        """
        Load a paper from disk.
        
        Args:
            paper_id: arXiv paper ID
        
        Returns:
            Paper object if found, None otherwise
        """
        file_path = self._get_paper_path(paper_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Parse dates back to datetime objects
            if data.get("published"):
                data["published"] = datetime.fromisoformat(data["published"])
            if data.get("updated"):
                data["updated"] = datetime.fromisoformat(data["updated"])
            
            # Remove extra fields that aren't in the model
            data.pop("saved_at", None)
            
            return Paper(**data)
        except (json.JSONDecodeError, ValueError, KeyError):
            return None
    
    def list_papers(self) -> List[Paper]:
        """
        List all saved papers.
        
        Returns:
            List of Paper objects
        """
        papers = []
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Parse dates
                if data.get("published"):
                    data["published"] = datetime.fromisoformat(data["published"])
                if data.get("updated"):
                    data["updated"] = datetime.fromisoformat(data["updated"])
                
                data.pop("saved_at", None)
                papers.append(Paper(**data))
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        # Sort by published date (newest first)
        papers.sort(key=lambda p: p.published, reverse=True)
        
        return papers
    
    def list_paper_ids(self) -> List[str]:
        """
        List all saved paper IDs.
        
        Returns:
            List of paper IDs
        """
        ids = []
        for file_path in self.data_dir.glob("*.json"):
            # Convert filename back to ID
            paper_id = file_path.stem.replace("_", "/", 1)
            ids.append(paper_id)
        return ids
    
    def delete_paper(self, paper_id: str) -> bool:
        """
        Delete a paper from disk.
        
        Args:
            paper_id: arXiv paper ID
        
        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_paper_path(paper_id)
        
        if file_path.exists():
            file_path.unlink()
            return True
        
        return False
    
    def paper_exists(self, paper_id: str) -> bool:
        """
        Check if a paper exists on disk.
        
        Args:
            paper_id: arXiv paper ID
        
        Returns:
            True if exists, False otherwise
        """
        return self._get_paper_path(paper_id).exists()
    
    def get_stats(self) -> dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with statistics
        """
        paper_files = list(self.data_dir.glob("*.json"))
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        text_files = list(self.text_dir.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in paper_files)
        pdf_size = sum(f.stat().st_size for f in pdf_files)
        text_size = sum(f.stat().st_size for f in text_files)
        
        return {
            "total_papers": len(paper_files),
            "total_pdfs": len(pdf_files),
            "total_texts": len(text_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "pdf_size_mb": round(pdf_size / (1024 * 1024), 2),
            "text_size_mb": round(text_size / (1024 * 1024), 2),
            "storage_path": str(self.data_dir)
        }
    
    @property
    def pdf_dir(self) -> Path:
        """Get the PDF storage directory."""
        pdf_path = self.data_dir.parent / "pdfs"
        pdf_path.mkdir(parents=True, exist_ok=True)
        return pdf_path
    
    @property
    def text_dir(self) -> Path:
        """Get the text files storage directory."""
        text_path = self.data_dir.parent / "texts"
        text_path.mkdir(parents=True, exist_ok=True)
        return text_path
    
    def _sanitize_filename(self, title: str, max_length: int = 100) -> str:
        """
        Sanitize a title to be used as a filename.
        
        Args:
            title: The paper title
            max_length: Maximum length for the filename
        
        Returns:
            A safe filename string
        """
        # Remove or replace characters that are not safe for filenames
        # Keep alphanumeric, spaces, hyphens, and underscores
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        safe_title = re.sub(r'\s+', ' ', safe_title).strip()
        # Truncate if too long
        if len(safe_title) > max_length:
            safe_title = safe_title[:max_length].rsplit(' ', 1)[0]
        return safe_title
    
    def _get_pdf_path(self, paper_id: str, title: Optional[str] = None) -> Path:
        """Get the file path for a PDF."""
        if title:
            safe_name = self._sanitize_filename(title)
            return self.pdf_dir / f"{safe_name}.pdf"
        else:
            safe_id = paper_id.replace("/", "_").replace(":", "_")
            return self.pdf_dir / f"{safe_id}.pdf"
    
    def _get_pdf_path_by_id(self, paper_id: str) -> Path:
        """Get the old-style PDF path (by ID) for backward compatibility."""
        safe_id = paper_id.replace("/", "_").replace(":", "_")
        return self.pdf_dir / f"{safe_id}.pdf"
    
    def pdf_exists(self, paper_id: str, title: Optional[str] = None) -> bool:
        """Check if a PDF exists locally."""
        # Check by title first, then by ID for backward compatibility
        if title:
            if self._get_pdf_path(paper_id, title).exists():
                return True
        # Also check old-style path
        return self._get_pdf_path_by_id(paper_id).exists()
    
    def get_pdf_path(self, paper_id: str, title: Optional[str] = None) -> Optional[Path]:
        """Get the path to a downloaded PDF if it exists."""
        # Try title-based path first
        if title:
            pdf_path = self._get_pdf_path(paper_id, title)
            if pdf_path.exists():
                return pdf_path
        # Fall back to ID-based path for backward compatibility
        pdf_path = self._get_pdf_path_by_id(paper_id)
        return pdf_path if pdf_path.exists() else None
    
    def get_pdf_filename(self, paper_id: str, title: Optional[str] = None) -> str:
        """Get the filename for a PDF."""
        if title:
            return f"{self._sanitize_filename(title)}.pdf"
        return f"{paper_id.replace('/', '_').replace(':', '_')}.pdf"
    
    async def download_pdf(self, paper_id: str, pdf_url: str, title: Optional[str] = None) -> Tuple[bool, str]:
        """
        Download a PDF from arXiv and extract its text content.
        
        Args:
            paper_id: arXiv paper ID
            pdf_url: URL to the PDF
            title: Paper title (used for filename)
        
        Returns:
            Tuple of (success, file_path or error_message)
        """
        pdf_path = self._get_pdf_path(paper_id, title)
        
        # Check if already downloaded (either by title or by ID)
        existing_path = self.get_pdf_path(paper_id, title)
        if existing_path:
            # Ensure text file exists
            self.extract_text_from_pdf(existing_path, title)
            return True, str(existing_path)
        
        try:
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                
                # Verify it's a PDF
                content_type = response.headers.get("content-type", "")
                if "pdf" not in content_type.lower() and not pdf_url.endswith(".pdf"):
                    return False, "Response is not a PDF file"
                
                # Save the PDF
                with open(pdf_path, "wb") as f:
                    f.write(response.content)
                
                # Extract text from PDF
                self.extract_text_from_pdf(pdf_path, title)
                
                return True, str(pdf_path)
        
        except httpx.TimeoutException:
            return False, "Download timed out. Please try again."
        except httpx.HTTPStatusError as e:
            return False, f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def extract_text_from_pdf(self, pdf_path: Path, title: Optional[str] = None) -> Tuple[bool, str]:
        """
        Extract text content from a PDF file and save to a text file.
        
        Args:
            pdf_path: Path to the PDF file
            title: Paper title (used for naming the text file)
        
        Returns:
            Tuple of (success, text_file_path or error_message)
        """
        try:
            import fitz  # PyMuPDF
            
            # Determine the text file name (same as PDF but with .txt extension)
            if title:
                safe_name = self._sanitize_filename(title)
                text_filename = f"{safe_name}.txt"
            else:
                text_filename = pdf_path.stem + ".txt"
            
            text_path = self.text_dir / text_filename
            
            # Skip if text file already exists
            if text_path.exists():
                return True, str(text_path)
            
            # Open the PDF
            doc = fitz.open(pdf_path)
            
            # Extract text from all pages
            full_text = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    full_text.append(f"--- Page {page_num + 1} ---\n")
                    full_text.append(text)
                    full_text.append("\n")
            
            doc.close()
            
            # Save the extracted text
            with open(text_path, "w", encoding="utf-8") as f:
                f.write("".join(full_text))
            
            return True, str(text_path)
        
        except ImportError:
            return False, "PyMuPDF (fitz) is not installed. Run: pip install pymupdf"
        except Exception as e:
            return False, f"Failed to extract text: {str(e)}"
    
    def get_text_path(self, paper_id: str, title: Optional[str] = None) -> Optional[Path]:
        """Get the path to extracted text file if it exists."""
        if title:
            safe_name = self._sanitize_filename(title)
            text_path = self.text_dir / f"{safe_name}.txt"
            if text_path.exists():
                return text_path
        
        # Fall back to ID-based path
        safe_id = paper_id.replace("/", "_").replace(":", "_")
        text_path = self.text_dir / f"{safe_id}.txt"
        return text_path if text_path.exists() else None
    
    def text_exists(self, paper_id: str, title: Optional[str] = None) -> bool:
        """Check if extracted text file exists."""
        return self.get_text_path(paper_id, title) is not None
    
    def get_text_content(self, paper_id: str, title: Optional[str] = None) -> Optional[str]:
        """Get the extracted text content."""
        text_path = self.get_text_path(paper_id, title)
        if text_path:
            with open(text_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def delete_pdf(self, paper_id: str, title: Optional[str] = None) -> bool:
        """Delete a downloaded PDF and its associated text file."""
        deleted = False
        
        # Delete PDF files
        if title:
            pdf_path = self._get_pdf_path(paper_id, title)
            if pdf_path.exists():
                pdf_path.unlink()
                deleted = True
            # Delete associated text file
            safe_name = self._sanitize_filename(title)
            text_path = self.text_dir / f"{safe_name}.txt"
            if text_path.exists():
                text_path.unlink()
        
        # Also try to delete old-style paths
        pdf_path = self._get_pdf_path_by_id(paper_id)
        if pdf_path.exists():
            pdf_path.unlink()
            deleted = True
        
        # Delete old-style text file
        safe_id = paper_id.replace("/", "_").replace(":", "_")
        text_path = self.text_dir / f"{safe_id}.txt"
        if text_path.exists():
            text_path.unlink()
        
        return deleted

