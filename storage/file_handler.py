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
        List all saved papers, sorted by save time (newest first).
        
        Returns:
            List of Paper objects
        """
        papers_with_saved_at = []
        
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Parse dates
                if data.get("published"):
                    data["published"] = datetime.fromisoformat(data["published"])
                if data.get("updated"):
                    data["updated"] = datetime.fromisoformat(data["updated"])
                
                # Get saved_at for sorting, default to file modification time
                saved_at = data.pop("saved_at", None)
                if saved_at:
                    saved_at = datetime.fromisoformat(saved_at)
                else:
                    # Fallback to file modification time
                    saved_at = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                papers_with_saved_at.append((Paper(**data), saved_at))
            except (json.JSONDecodeError, ValueError, KeyError):
                continue
        
        # Sort by saved_at (newest first)
        papers_with_saved_at.sort(key=lambda x: x[1], reverse=True)
        
        return [paper for paper, _ in papers_with_saved_at]
    
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
        analysis_files = list(self.analysis_dir.glob("*.html"))
        total_size = sum(f.stat().st_size for f in paper_files)
        pdf_size = sum(f.stat().st_size for f in pdf_files)
        text_size = sum(f.stat().st_size for f in text_files)
        
        return {
            "total_papers": len(paper_files),
            "total_pdfs": len(pdf_files),
            "total_texts": len(text_files),
            "total_analyses": len(analysis_files),
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
    
    @property
    def analysis_dir(self) -> Path:
        """Get the analysis HTML files storage directory."""
        analysis_path = self.data_dir.parent / "analysis"
        analysis_path.mkdir(parents=True, exist_ok=True)
        return analysis_path
    
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
    
    # ==================== Analysis HTML Methods ====================
    
    def _get_analysis_filename(self, title: str) -> str:
        """Generate analysis HTML filename from paper title."""
        safe_title = self._sanitize_filename(title, max_length=80)
        return f"{safe_title}_abstract_ds_analyze.html"
    
    def _get_analysis_path(self, title: str) -> Path:
        """Get the file path for an analysis HTML file."""
        filename = self._get_analysis_filename(title)
        return self.analysis_dir / filename
    
    def save_analysis_html(self, title: str, html_content: str) -> str:
        """
        Save analysis result as HTML file.
        
        Args:
            title: Paper title (used for filename)
            html_content: HTML content from DeepSeek
        
        Returns:
            Path to the saved file
        """
        file_path = self._get_analysis_path(title)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return str(file_path)
    
    def get_analysis_path(self, title: str) -> Optional[Path]:
        """Get the path to an analysis HTML file if it exists."""
        file_path = self._get_analysis_path(title)
        return file_path if file_path.exists() else None
    
    def analysis_exists(self, title: str) -> bool:
        """Check if analysis HTML file exists."""
        return self._get_analysis_path(title).exists()
    
    def get_analysis_content(self, title: str) -> Optional[str]:
        """Get the analysis HTML content."""
        file_path = self.get_analysis_path(title)
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def delete_analysis(self, title: str) -> bool:
        """Delete an analysis HTML file and its reasoning file."""
        deleted = False
        
        # Delete HTML file
        file_path = self._get_analysis_path(title)
        if file_path.exists():
            file_path.unlink()
            deleted = True
        
        # Delete reasoning file
        reasoning_path = self._get_reasoning_path(title)
        if reasoning_path.exists():
            reasoning_path.unlink()
            deleted = True
        
        return deleted
    
    # ==================== Reasoning Content Methods ====================
    
    def _get_reasoning_filename(self, title: str) -> str:
        """Generate reasoning filename from paper title."""
        safe_title = self._sanitize_filename(title, max_length=80)
        return f"{safe_title}_abstract_ds_reasoning.txt"
    
    def _get_reasoning_path(self, title: str) -> Path:
        """Get the file path for a reasoning file."""
        filename = self._get_reasoning_filename(title)
        return self.analysis_dir / filename
    
    def save_reasoning(self, title: str, reasoning_content: str) -> str:
        """
        Save reasoning content to file.
        
        Args:
            title: Paper title (used for filename)
            reasoning_content: Reasoning content from DeepSeek
        
        Returns:
            Path to the saved file
        """
        file_path = self._get_reasoning_path(title)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(reasoning_content)
        
        return str(file_path)
    
    def get_reasoning_path(self, title: str) -> Optional[Path]:
        """Get the path to a reasoning file if it exists."""
        file_path = self._get_reasoning_path(title)
        return file_path if file_path.exists() else None
    
    def reasoning_exists(self, title: str) -> bool:
        """Check if reasoning file exists."""
        return self._get_reasoning_path(title).exists()
    
    def get_reasoning_content(self, title: str) -> Optional[str]:
        """Get the reasoning content."""
        file_path = self.get_reasoning_path(title)
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def list_analyses(self) -> List[dict]:
        """List all saved analysis files."""
        analyses = []
        for file_path in self.analysis_dir.glob("*_abstract_ds_analyze.html"):
            analyses.append({
                "filename": file_path.name,
                "title": file_path.stem.replace("_abstract_ds_analyze", ""),
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })
        # Sort by modification time (newest first)
        analyses.sort(key=lambda x: x['modified'], reverse=True)
        return analyses
    
    # ==================== Fulltext Analysis Methods ====================
    
    def _get_fulltext_analysis_filename(self, title: str) -> str:
        """Generate fulltext analysis HTML filename from paper title."""
        safe_title = self._sanitize_filename(title, max_length=80)
        return f"{safe_title}_fulltext_ds_analyze.html"
    
    def _get_fulltext_analysis_path(self, title: str) -> Path:
        """Get the file path for a fulltext analysis HTML file."""
        filename = self._get_fulltext_analysis_filename(title)
        return self.analysis_dir / filename
    
    def _get_fulltext_reasoning_filename(self, title: str) -> str:
        """Generate fulltext reasoning filename from paper title."""
        safe_title = self._sanitize_filename(title, max_length=80)
        return f"{safe_title}_fulltext_ds_reasoning.txt"
    
    def _get_fulltext_reasoning_path(self, title: str) -> Path:
        """Get the file path for a fulltext reasoning file."""
        filename = self._get_fulltext_reasoning_filename(title)
        return self.analysis_dir / filename
    
    def save_fulltext_analysis_html(self, title: str, html_content: str) -> str:
        """Save fulltext analysis result as HTML file."""
        file_path = self._get_fulltext_analysis_path(title)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return str(file_path)
    
    def save_fulltext_reasoning(self, title: str, reasoning_content: str) -> str:
        """Save fulltext reasoning content to file."""
        file_path = self._get_fulltext_reasoning_path(title)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(reasoning_content)
        return str(file_path)
    
    def get_fulltext_analysis_path(self, title: str) -> Optional[Path]:
        """Get the path to a fulltext analysis HTML file if it exists."""
        file_path = self._get_fulltext_analysis_path(title)
        return file_path if file_path.exists() else None
    
    def get_fulltext_reasoning_path(self, title: str) -> Optional[Path]:
        """Get the path to a fulltext reasoning file if it exists."""
        file_path = self._get_fulltext_reasoning_path(title)
        return file_path if file_path.exists() else None
    
    def fulltext_analysis_exists(self, title: str) -> bool:
        """Check if fulltext analysis HTML file exists."""
        return self._get_fulltext_analysis_path(title).exists()
    
    def fulltext_reasoning_exists(self, title: str) -> bool:
        """Check if fulltext reasoning file exists."""
        return self._get_fulltext_reasoning_path(title).exists()
    
    def get_fulltext_analysis_content(self, title: str) -> Optional[str]:
        """Get the fulltext analysis HTML content."""
        file_path = self.get_fulltext_analysis_path(title)
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def get_fulltext_reasoning_content(self, title: str) -> Optional[str]:
        """Get the fulltext reasoning content."""
        file_path = self.get_fulltext_reasoning_path(title)
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return None
    
    def delete_fulltext_analysis(self, title: str) -> bool:
        """Delete fulltext analysis HTML and reasoning files."""
        deleted = False
        
        # Delete HTML file
        html_path = self._get_fulltext_analysis_path(title)
        if html_path.exists():
            html_path.unlink()
            deleted = True
        
        # Delete reasoning file
        reasoning_path = self._get_fulltext_reasoning_path(title)
        if reasoning_path.exists():
            reasoning_path.unlink()
            deleted = True
        
        return deleted
    
    # ==================== Q&A Session Methods ====================
    
    @property
    def qa_dir(self) -> Path:
        """Get the Q&A storage directory."""
        qa_path = self.data_dir.parent / "qa"
        qa_path.mkdir(parents=True, exist_ok=True)
        return qa_path
    
    def _get_qa_filename(self, title: str) -> str:
        """Generate Q&A session filename from paper title."""
        safe_title = self._sanitize_filename(title, max_length=80)
        return f"{safe_title}_qa_session.json"
    
    def _get_qa_path(self, title: str) -> Path:
        """Get the file path for a Q&A session file."""
        filename = self._get_qa_filename(title)
        return self.qa_dir / filename
    
    def get_qa_history(self, title: str) -> List[dict]:
        """
        Get Q&A history for a paper.
        
        Args:
            title: Paper title
            
        Returns:
            List of Q&A pairs, each containing:
            - question: str
            - reasoning: str
            - answer: str
            - timestamp: str (ISO format)
        """
        file_path = self._get_qa_path(title)
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return []
    
    def save_qa_entry(self, title: str, question: str, reasoning: str, answer: str) -> int:
        """
        Save a new Q&A entry for a paper.
        
        Args:
            title: Paper title
            question: User's question
            reasoning: DeepSeek's reasoning content
            answer: DeepSeek's answer content
            
        Returns:
            Index of the new entry (0-based)
        """
        history = self.get_qa_history(title)
        
        entry = {
            "question": question,
            "reasoning": reasoning,
            "answer": answer,
            "timestamp": datetime.now().isoformat()
        }
        
        history.append(entry)
        
        file_path = self._get_qa_path(title)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return len(history) - 1
    
    def update_qa_entry(self, title: str, index: int, reasoning: str, answer: str) -> bool:
        """
        Update an existing Q&A entry (used during streaming).
        
        Args:
            title: Paper title
            index: Entry index to update
            reasoning: Updated reasoning content
            answer: Updated answer content
            
        Returns:
            True if updated, False if index not found
        """
        history = self.get_qa_history(title)
        
        if index < 0 or index >= len(history):
            return False
        
        history[index]["reasoning"] = reasoning
        history[index]["answer"] = answer
        
        file_path = self._get_qa_path(title)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        
        return True
    
    def qa_exists(self, title: str) -> bool:
        """Check if Q&A session exists for a paper."""
        return self._get_qa_path(title).exists()
    
    def delete_qa(self, title: str) -> bool:
        """Delete Q&A session for a paper."""
        file_path = self._get_qa_path(title)
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def delete_qa_entry(self, title: str, index: int) -> bool:
        """
        Delete a specific Q&A entry.
        
        Args:
            title: Paper title
            index: Entry index to delete
            
        Returns:
            True if deleted, False if index not found
        """
        history = self.get_qa_history(title)
        
        if index < 0 or index >= len(history):
            return False
        
        history.pop(index)
        
        file_path = self._get_qa_path(title)
        if history:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        else:
            # Delete file if no entries left
            file_path.unlink()
        
        return True
    
    def get_qa_messages_for_deepseek(self, title: str) -> List[dict]:
        """
        Get Q&A history formatted for DeepSeek API multi-turn conversation.
        
        Args:
            title: Paper title
            
        Returns:
            List of messages in DeepSeek format:
            [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]
        """
        history = self.get_qa_history(title)
        messages = []
        
        for entry in history:
            messages.append({"role": "user", "content": entry["question"]})
            messages.append({"role": "assistant", "content": entry["answer"]})
        
        return messages

