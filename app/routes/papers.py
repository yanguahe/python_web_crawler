"""
Routes for managing saved papers.
"""
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from urllib.parse import unquote

import re
from fastapi import APIRouter, Request, HTTPException, Query, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from crawler import ArxivClient
from crawler.models import Paper
from storage import FileHandler
from config import settings

router = APIRouter(prefix="/papers", tags=["papers"])

# Backup directory - use parent of data_dir (which is data/papers) to get data/
DATA_ROOT = Path(settings.data_dir).parent  # This gives us "data/"
BACKUP_DIR = DATA_ROOT / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def get_backup_list() -> List[str]:
    """Get list of backup files sorted by name (newest first)."""
    backups = []
    if BACKUP_DIR.exists():
        for f in BACKUP_DIR.glob("*.tar.gz"):
            backups.append(f.name)
    backups.sort(reverse=True)
    return backups

# Setup templates
APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# Initialize handlers
file_handler = FileHandler()
arxiv_client = ArxivClient()


@router.get("", response_class=HTMLResponse)
async def list_saved_papers(request: Request):
    """
    List all saved papers.
    """
    papers = file_handler.list_papers()
    stats = file_handler.get_stats()
    
    # Add PDF/TXT/Analysis status to each paper
    papers_with_status = []
    for paper in papers:
        paper_dict = {
            "paper": paper,
            "pdf_exists": file_handler.pdf_exists(paper.id, paper.title),
            "text_exists": file_handler.text_exists(paper.id, paper.title),
            "analysis_exists": file_handler.analysis_exists(paper.title),
        }
        papers_with_status.append(paper_dict)
    
    # Get backup list
    backups = get_backup_list()
    latest_backup = backups[0] if backups else None
    
    return templates.TemplateResponse(
        "papers.html",
        {
            "request": request,
            "title": "Saved Papers",
            "papers": papers_with_status,
            "stats": stats,
            "backups": backups,
            "latest_backup": latest_backup
        }
    )


@router.get("/api", tags=["api"])
async def api_list_papers() -> dict:
    """
    API endpoint to list all saved papers.
    """
    papers = file_handler.list_papers()
    stats = file_handler.get_stats()
    
    return {
        "success": True,
        "papers": [paper.model_dump() for paper in papers],
        "stats": stats
    }


@router.get("/api/stats", tags=["api"])
async def api_get_stats() -> dict:
    """
    API endpoint to get storage statistics.
    """
    return file_handler.get_stats()


@router.post("/api/backup/create", tags=["api"])
async def api_create_backup():
    """
    Create a backup of the entire data directory.
    Copies the data/ directory (papers, pdfs, texts, analysis) to a timestamped folder 
    and compresses it to .tar.gz
    """
    try:
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create temporary directory name
        backup_name = f"data_backup_{timestamp}"
        temp_backup_dir = BACKUP_DIR / backup_name
        tar_filename = f"{backup_name}.tar.gz"
        tar_path = BACKUP_DIR / tar_filename
        
        # Source is the entire data/ directory (DATA_ROOT)
        source_dir = DATA_ROOT
        
        # Copy data directory to temp backup dir
        # We exclude the backups directory to avoid recursive copying
        if temp_backup_dir.exists():
            shutil.rmtree(temp_backup_dir)
        
        # Create a copy, excluding the backups folder
        temp_backup_dir.mkdir(parents=True, exist_ok=True)
        for item in source_dir.iterdir():
            if item.name == "backups":
                continue  # Skip the backups directory
            dest = temp_backup_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # Create tar.gz file
        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(temp_backup_dir, arcname=backup_name)
        
        # Remove the temporary directory
        shutil.rmtree(temp_backup_dir)
        
        # Get file size
        file_size_mb = tar_path.stat().st_size / (1024 * 1024)
        
        return {
            "success": True,
            "filename": tar_filename,
            "size_mb": round(file_size_mb, 2),
            "path": str(tar_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


@router.get("/api/backup/list", tags=["api"])
async def api_list_backups():
    """
    List all available backups.
    """
    backups = get_backup_list()
    backup_info = []
    
    for backup_name in backups:
        backup_path = BACKUP_DIR / backup_name
        if backup_path.exists():
            stat = backup_path.stat()
            backup_info.append({
                "filename": backup_name,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
    
    return {
        "success": True,
        "backups": backup_info
    }


@router.get("/api/backup/download/{filename}", tags=["api"])
async def api_download_backup(filename: str):
    """
    Download a backup file.
    """
    # Validate filename to prevent directory traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not filename.endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="Invalid backup file format")
    
    backup_path = BACKUP_DIR / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    return FileResponse(
        path=str(backup_path),
        filename=filename,
        media_type="application/gzip"
    )


@router.delete("/api/backup/{filename}", tags=["api"])
async def api_delete_backup(filename: str):
    """
    Delete a backup file.
    """
    # Validate filename to prevent directory traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not filename.endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="Invalid backup file format")
    
    backup_path = BACKUP_DIR / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    backup_path.unlink()
    
    return {"success": True, "message": f"Backup {filename} deleted"}


@router.post("/api/backup/import/{filename}", tags=["api"])
async def api_import_backup(filename: str):
    """
    Import a backup file from data/backups/ and merge it with existing data.
    The backup tar.gz file should contain the data directory structure.
    """
    # Validate filename to prevent directory traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if not filename.endswith('.tar.gz') and not filename.endswith('.tgz'):
        raise HTTPException(status_code=400, detail="Invalid file format. Only .tar.gz or .tgz files are accepted.")
    
    # Check if backup file exists
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail=f"Backup file not found: {filename}")
    
    try:
        # Create a temporary directory for extraction
        temp_extract_dir = BACKUP_DIR / f"temp_extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_extract_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract the tar.gz file from the existing backup
        with tarfile.open(backup_path, "r:gz") as tar:
            tar.extractall(temp_extract_dir)
        
        # Find the data directory in the extracted content
        # The backup structure is: data_backup_YYYYMMDD_HHMMSS/papers/, data_backup_YYYYMMDD_HHMMSS/pdfs/, etc.
        extracted_items = list(temp_extract_dir.iterdir())
        
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            # Single directory containing the backup data
            source_base = extracted_items[0]
        else:
            # Multiple items at root level
            source_base = temp_extract_dir
        
        # Merge the extracted data with existing data
        imported_counts = {"papers": 0, "pdfs": 0, "texts": 0, "analysis": 0, "qa": 0}
        
        for subdir in source_base.iterdir():
            if not subdir.is_dir():
                continue
            
            subdir_name = subdir.name
            
            # Map backup subdirectories to actual data directories
            if subdir_name == "papers":
                dest_dir = DATA_ROOT / "papers"
            elif subdir_name == "pdfs":
                dest_dir = DATA_ROOT / "pdfs"
            elif subdir_name == "texts":
                dest_dir = DATA_ROOT / "texts"
            elif subdir_name == "analysis":
                dest_dir = DATA_ROOT / "analysis"
            elif subdir_name == "qa":
                dest_dir = DATA_ROOT / "qa"
            else:
                # Skip unknown directories (like backups)
                continue
            
            # Ensure destination directory exists
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files from backup to destination
            for item in subdir.iterdir():
                dest_path = dest_dir / item.name
                if item.is_file():
                    shutil.copy2(item, dest_path)
                    if subdir_name in imported_counts:
                        imported_counts[subdir_name] += 1
                elif item.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(item, dest_path)
                    if subdir_name in imported_counts:
                        imported_counts[subdir_name] += 1
        
        # Cleanup: remove temp extraction directory (keep original backup file)
        shutil.rmtree(temp_extract_dir)
        
        # Build result message
        message_parts = []
        if imported_counts["papers"] > 0:
            message_parts.append(f"{imported_counts['papers']} papers")
        if imported_counts["pdfs"] > 0:
            message_parts.append(f"{imported_counts['pdfs']} PDFs")
        if imported_counts["texts"] > 0:
            message_parts.append(f"{imported_counts['texts']} texts")
        if imported_counts["analysis"] > 0:
            message_parts.append(f"{imported_counts['analysis']} analyses")
        if imported_counts["qa"] > 0:
            message_parts.append(f"{imported_counts['qa']} Q&A sessions")
        
        message = "Imported: " + ", ".join(message_parts) if message_parts else "No data imported"
        
        return {
            "success": True,
            "message": message,
            "imported": imported_counts
        }
        
    except tarfile.TarError as e:
        # Cleanup on error
        if temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)
        raise HTTPException(status_code=400, detail=f"Invalid tar.gz file: {str(e)}")
    except Exception as e:
        # Cleanup on error
        if 'temp_extract_dir' in locals() and temp_extract_dir.exists():
            shutil.rmtree(temp_extract_dir)
        raise HTTPException(status_code=500, detail=f"Failed to import backup: {str(e)}")


@router.post("/api/upload-pdf", tags=["api"])
async def api_upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file, extract text, parse title/abstract, and create a paper record.
    """
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    
    try:
        import fitz  # PyMuPDF
        
        # Generate a unique ID for this uploaded paper (using timestamp + filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = Path(file.filename).stem
        paper_id = f"upload_{timestamp}_{base_name[:30]}"
        
        # Save the uploaded PDF
        pdf_filename = f"{file_handler._sanitize_filename(base_name)}.pdf"
        pdf_path = file_handler.pdf_dir / pdf_filename
        
        # Write PDF file in chunks
        CHUNK_SIZE = 1024 * 1024  # 1MB chunks
        with open(pdf_path, "wb") as buffer:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                buffer.write(chunk)
        
        # Extract text from PDF
        doc = fitz.open(pdf_path)
        full_text = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                full_text.append(f"--- Page {page_num + 1} ---\n")
                full_text.append(text)
                full_text.append("\n")
        doc.close()
        
        text_content = "".join(full_text)
        
        # Save text file
        text_filename = f"{file_handler._sanitize_filename(base_name)}.txt"
        text_path = file_handler.text_dir / text_filename
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        # Parse title from text
        title = _parse_title_from_text(text_content, base_name)
        
        # Parse abstract from text
        abstract = _parse_abstract_from_text(text_content)
        
        # Create Paper object
        paper = Paper(
            id=paper_id,
            title=title,
            authors=[],  # Cannot reliably extract authors
            abstract=abstract,
            categories=["uploaded"],
            published=datetime.now(),
            updated=None,
            pdf_url=f"/papers/api/pdf/{paper_id}",
            arxiv_url=""
        )
        
        # Save paper record
        file_handler.save_paper(paper)
        
        # Rename files to use the parsed title
        safe_title = file_handler._sanitize_filename(title)
        
        # Rename PDF if title is different from original filename
        if safe_title != file_handler._sanitize_filename(base_name):
            new_pdf_path = file_handler.pdf_dir / f"{safe_title}.pdf"
            if not new_pdf_path.exists():
                pdf_path.rename(new_pdf_path)
            
            new_text_path = file_handler.text_dir / f"{safe_title}.txt"
            if not new_text_path.exists():
                text_path.rename(new_text_path)
        
        return {
            "success": True,
            "message": f"Paper '{title[:50]}...' added successfully" if len(title) > 50 else f"Paper '{title}' added successfully",
            "paper_id": paper_id,
            "title": title
        }
        
    except ImportError:
        raise HTTPException(status_code=500, detail="PyMuPDF (fitz) is not installed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process PDF: {str(e)}")


def _parse_title_from_text(text: str, fallback_name: str) -> str:
    """
    Parse title from extracted PDF text.
    
    Rules:
    1. Find text between "--- Page 1 ---" and "Abstract" (case-insensitive)
    2. If no "Abstract" found, use first 3 lines after "--- Page 1 ---"
    """
    lines = text.split('\n')
    
    # Find "--- Page 1 ---" position
    page1_idx = -1
    for i, line in enumerate(lines):
        if '--- Page 1 ---' in line:
            page1_idx = i
            break
    
    if page1_idx == -1:
        return fallback_name
    
    # Find "Abstract" position (case-insensitive)
    abstract_idx = -1
    for i in range(page1_idx + 1, min(page1_idx + 50, len(lines))):
        if re.search(r'\babstract\b', lines[i], re.IGNORECASE):
            abstract_idx = i
            break
    
    # Extract title lines
    if abstract_idx != -1:
        # Get lines between Page 1 and Abstract
        title_lines = lines[page1_idx + 1:abstract_idx]
    else:
        # Get first 3 non-empty lines after Page 1
        title_lines = []
        for i in range(page1_idx + 1, min(page1_idx + 20, len(lines))):
            line = lines[i].strip()
            if line and not line.startswith('---'):
                title_lines.append(line)
                if len(title_lines) >= 3:
                    break
    
    # Clean and join title lines
    title_parts = []
    for line in title_lines:
        line = line.strip()
        # Skip page markers and empty lines
        if line and not line.startswith('--- Page'):
            # Skip lines that look like author names or emails
            if '@' not in line and not re.match(r'^[\d\s,]+$', line):
                title_parts.append(line)
    
    if not title_parts:
        return fallback_name
    
    # Join and clean up the title
    title = ' '.join(title_parts[:3])  # Limit to first 3 meaningful lines
    title = re.sub(r'\s+', ' ', title).strip()
    
    # Remove trailing numbers, asterisks, etc.
    title = re.sub(r'[\*†‡§¶]+$', '', title).strip()
    
    return title if title else fallback_name


def _parse_abstract_from_text(text: str) -> str:
    """
    Parse abstract from extracted PDF text.
    
    Rules:
    1. If both "Abstract" and "Introduction" exist (case-insensitive)
    2. Extract text between first "Abstract" and first "Introduction"
    3. Remove page markers like "--- Page num ---"
    """
    text_lower = text.lower()
    
    # Find Abstract position
    abstract_match = re.search(r'\babstract\b', text_lower)
    if not abstract_match:
        return "Abstract not found in document."
    
    # Find Introduction position
    intro_match = re.search(r'\bintroduction\b', text_lower)
    if not intro_match:
        # No Introduction found, try to get some text after Abstract
        abstract_start = abstract_match.end()
        # Get up to 2000 characters after Abstract
        abstract_text = text[abstract_start:abstract_start + 2000]
        # Clean up
        abstract_text = re.sub(r'--- Page \d+ ---', '', abstract_text)
        abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
        return abstract_text[:1500] if abstract_text else "Abstract not found in document."
    
    # Check that Introduction comes after Abstract
    if intro_match.start() <= abstract_match.end():
        return "Abstract not found in document."
    
    # Extract text between Abstract and Introduction
    abstract_text = text[abstract_match.end():intro_match.start()]
    
    # Remove page markers
    abstract_text = re.sub(r'--- Page \d+ ---', '', abstract_text)
    
    # Clean up whitespace
    abstract_text = re.sub(r'\s+', ' ', abstract_text).strip()
    
    # Remove leading numbers or special characters
    abstract_text = re.sub(r'^[\d\.\s]+', '', abstract_text).strip()
    
    return abstract_text if abstract_text else "Abstract not found in document."


@router.get("/api/pdf/{paper_id:path}", tags=["api"])
async def api_get_pdf(paper_id: str, title: Optional[str] = Query(None)):
    """
    API endpoint to get a downloaded PDF file.
    Returns the PDF file for download/viewing.
    """
    decoded_paper_id = unquote(paper_id)
    decoded_title = unquote(title) if title else None
    
    # If no title provided, try to get it from the saved paper
    if not decoded_title:
        paper = file_handler.get_paper(decoded_paper_id)
        decoded_title = paper.title if paper else None
    
    pdf_path = file_handler.get_pdf_path(decoded_paper_id, decoded_title)
    
    if not pdf_path:
        raise HTTPException(status_code=404, detail="PDF not found. Please download it first.")
    
    # Use the actual filename from the path
    filename = pdf_path.name
    
    return FileResponse(
        path=pdf_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.get("/api/pdf-status/{paper_id:path}", tags=["api"])
async def api_pdf_status(paper_id: str, title: Optional[str] = Query(None)) -> dict:
    """
    Check if a PDF has been downloaded and if text has been extracted.
    """
    decoded_paper_id = unquote(paper_id)
    decoded_title = unquote(title) if title else None
    
    # If no title provided, try to get it from the saved paper
    if not decoded_title:
        paper = file_handler.get_paper(decoded_paper_id)
        decoded_title = paper.title if paper else None
    
    pdf_exists = file_handler.pdf_exists(decoded_paper_id, decoded_title)
    text_exists = file_handler.text_exists(decoded_paper_id, decoded_title)
    
    return {
        "paper_id": decoded_paper_id,
        "downloaded": pdf_exists,
        "download_url": f"/papers/api/pdf/{decoded_paper_id}" if pdf_exists else None,
        "filename": file_handler.get_pdf_filename(decoded_paper_id, decoded_title) if pdf_exists else None,
        "text_extracted": text_exists,
        "text_url": f"/papers/api/text/{decoded_paper_id}" if text_exists else None
    }


@router.get("/api/text/{paper_id:path}", tags=["api"])
async def api_get_text(paper_id: str, title: Optional[str] = Query(None)):
    """
    API endpoint to get the extracted text content of a paper.
    Returns the text file for download/viewing.
    """
    decoded_paper_id = unquote(paper_id)
    decoded_title = unquote(title) if title else None
    
    # If no title provided, try to get it from the saved paper
    if not decoded_title:
        paper = file_handler.get_paper(decoded_paper_id)
        decoded_title = paper.title if paper else None
    
    text_path = file_handler.get_text_path(decoded_paper_id, decoded_title)
    
    if not text_path:
        raise HTTPException(status_code=404, detail="Text file not found. Please download the PDF first.")
    
    filename = text_path.name
    
    return FileResponse(
        path=text_path,
        filename=filename,
        media_type="text/plain; charset=utf-8"
    )


@router.get("/api/text-content/{paper_id:path}", tags=["api"])
async def api_get_text_content(paper_id: str) -> dict:
    """
    API endpoint to get the extracted text content as JSON.
    """
    decoded_paper_id = unquote(paper_id)
    
    paper = file_handler.get_paper(decoded_paper_id)
    title = paper.title if paper else None
    
    content = file_handler.get_text_content(decoded_paper_id, title)
    
    if not content:
        raise HTTPException(status_code=404, detail="Text file not found. Please download the PDF first.")
    
    return {
        "paper_id": decoded_paper_id,
        "title": title,
        "content": content,
        "length": len(content)
    }


@router.post("/api/save/{paper_id:path}", tags=["api"])
async def api_save_paper(paper_id: str) -> dict:
    """
    API endpoint to save a paper by its arXiv ID.
    """
    decoded_paper_id = unquote(paper_id)
    
    # Check if already saved
    if file_handler.paper_exists(decoded_paper_id):
        return {"success": True, "message": "Paper already saved", "already_exists": True}
    
    # Fetch from arXiv
    paper = await arxiv_client.get_paper_by_id(decoded_paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found on arXiv")
    
    # Save to disk
    file_path = file_handler.save_paper(paper)
    
    return {
        "success": True,
        "message": f"Paper saved to {file_path}",
        "paper": paper.model_dump()
    }


@router.post("/api/download-pdf/{paper_id:path}", tags=["api"])
async def api_download_pdf(paper_id: str) -> dict:
    """
    API endpoint to download a PDF from arXiv and save it locally.
    The PDF will be named after the paper title.
    Text content will be automatically extracted.
    """
    # Decode URL-encoded paper_id
    decoded_paper_id = unquote(paper_id)
    
    # First check if we have the paper info
    paper = file_handler.get_paper(decoded_paper_id)
    
    if not paper:
        # Try to fetch paper info from arXiv
        paper = await arxiv_client.get_paper_by_id(decoded_paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper not found: {decoded_paper_id}")
    
    # Download the PDF with title as filename (text extraction happens automatically)
    success, result = await file_handler.download_pdf(decoded_paper_id, paper.pdf_url, paper.title)
    
    if success:
        # Check if text was extracted
        text_exists = file_handler.text_exists(decoded_paper_id, paper.title)
        text_path = file_handler.get_text_path(decoded_paper_id, paper.title)
        
        return {
            "success": True,
            "message": "PDF downloaded and text extracted successfully",
            "file_path": result,
            "paper_id": decoded_paper_id,
            "filename": file_handler.get_pdf_filename(decoded_paper_id, paper.title),
            "text_extracted": text_exists,
            "text_file": str(text_path) if text_path else None
        }
    else:
        raise HTTPException(status_code=500, detail=result)


@router.delete("/api/pdf/{paper_id:path}", tags=["api"])
async def api_delete_pdf(paper_id: str, title: Optional[str] = Query(None)) -> dict:
    """
    API endpoint to delete a downloaded PDF and its associated text file.
    """
    decoded_paper_id = unquote(paper_id)
    decoded_title = unquote(title) if title else None
    
    # If no title provided, try to get it from the saved paper
    if not decoded_title:
        paper = file_handler.get_paper(decoded_paper_id)
        decoded_title = paper.title if paper else None
    
    if file_handler.delete_pdf(decoded_paper_id, decoded_title):
        return {"success": True, "message": f"PDF and text files for paper {decoded_paper_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="PDF not found")


@router.delete("/api/{paper_id:path}", tags=["api"])
async def api_delete_paper(paper_id: str) -> dict:
    """
    API endpoint to delete a saved paper.
    """
    decoded_paper_id = unquote(paper_id)
    
    if file_handler.delete_paper(decoded_paper_id):
        return {"success": True, "message": f"Paper {decoded_paper_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Paper not found")


@router.get("/view/{paper_id:path}", response_class=HTMLResponse)
async def view_paper_detail(request: Request, paper_id: str):
    """
    View a paper's details. Works for both saved and unsaved papers.
    For unsaved papers, fetches info from arXiv.
    """
    decoded_paper_id = unquote(paper_id)
    
    # First try to get from saved papers
    paper = file_handler.get_paper(decoded_paper_id)
    is_saved = paper is not None
    
    # If not saved, fetch from arXiv
    if not paper:
        paper = await arxiv_client.get_paper_by_id(decoded_paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
    
    # Check PDF/TXT/Analysis status
    pdf_exists = file_handler.pdf_exists(decoded_paper_id, paper.title)
    text_exists = file_handler.text_exists(decoded_paper_id, paper.title)
    analysis_exists = file_handler.analysis_exists(paper.title)
    reasoning_exists = file_handler.reasoning_exists(paper.title)
    
    # Check fulltext analysis status
    fulltext_analysis_exists = file_handler.fulltext_analysis_exists(paper.title)
    fulltext_reasoning_exists = file_handler.fulltext_reasoning_exists(paper.title)
    
    # Get text content if exists (for fulltext analysis)
    text_content = None
    if text_exists:
        text_content = file_handler.get_text_content(decoded_paper_id, paper.title)
    
    return templates.TemplateResponse(
        "paper_detail.html",
        {
            "request": request,
            "title": paper.title,
            "paper": paper,
            "is_saved": is_saved,
            "pdf_exists": pdf_exists,
            "text_exists": text_exists,
            "text_content": text_content,
            "analysis_exists": analysis_exists,
            "reasoning_exists": reasoning_exists,
            "fulltext_analysis_exists": fulltext_analysis_exists,
            "fulltext_reasoning_exists": fulltext_reasoning_exists
        }
    )


# NOTE: This catch-all route MUST be at the end of the file
# Otherwise it will match /api/* routes before they can be handled
@router.get("/{paper_id:path}", response_class=HTMLResponse)
async def view_paper(request: Request, paper_id: str):
    """
    View a specific saved paper.
    """
    decoded_paper_id = unquote(paper_id)
    
    paper = file_handler.get_paper(decoded_paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Check PDF/TXT/Analysis status
    pdf_exists = file_handler.pdf_exists(decoded_paper_id, paper.title)
    text_exists = file_handler.text_exists(decoded_paper_id, paper.title)
    analysis_exists = file_handler.analysis_exists(paper.title)
    reasoning_exists = file_handler.reasoning_exists(paper.title)
    
    # Check fulltext analysis status
    fulltext_analysis_exists = file_handler.fulltext_analysis_exists(paper.title)
    fulltext_reasoning_exists = file_handler.fulltext_reasoning_exists(paper.title)
    
    # Get text content if exists (for fulltext analysis)
    text_content = None
    if text_exists:
        text_content = file_handler.get_text_content(decoded_paper_id, paper.title)
    
    return templates.TemplateResponse(
        "paper_detail.html",
        {
            "request": request,
            "title": paper.title,
            "paper": paper,
            "is_saved": True,  # This route is for saved papers
            "pdf_exists": pdf_exists,
            "text_exists": text_exists,
            "text_content": text_content,
            "analysis_exists": analysis_exists,
            "reasoning_exists": reasoning_exists,
            "fulltext_analysis_exists": fulltext_analysis_exists,
            "fulltext_reasoning_exists": fulltext_reasoning_exists
        }
    )
