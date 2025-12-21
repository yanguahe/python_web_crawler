"""
Routes for managing saved papers.
"""
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from crawler import ArxivClient
from storage import FileHandler
from config import settings

router = APIRouter(prefix="/papers", tags=["papers"])

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
    
    return templates.TemplateResponse(
        "papers.html",
        {
            "request": request,
            "title": "Saved Papers",
            "papers": papers_with_status,
            "stats": stats
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
