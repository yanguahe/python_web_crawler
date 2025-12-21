"""
Routes for managing saved papers.
"""
from pathlib import Path
from typing import Optional

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
    
    return templates.TemplateResponse(
        "papers.html",
        {
            "request": request,
            "title": "Saved Papers",
            "papers": papers,
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


@router.get("/{paper_id:path}", response_class=HTMLResponse)
async def view_paper(request: Request, paper_id: str):
    """
    View a specific saved paper.
    """
    paper = file_handler.get_paper(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return templates.TemplateResponse(
        "paper_detail.html",
        {
            "request": request,
            "title": paper.title,
            "paper": paper
        }
    )


@router.delete("/api/{paper_id:path}", tags=["api"])
async def api_delete_paper(paper_id: str) -> dict:
    """
    API endpoint to delete a saved paper.
    """
    if file_handler.delete_paper(paper_id):
        return {"success": True, "message": f"Paper {paper_id} deleted"}
    else:
        raise HTTPException(status_code=404, detail="Paper not found")


@router.post("/api/save/{paper_id:path}", tags=["api"])
async def api_save_paper(paper_id: str) -> dict:
    """
    API endpoint to save a paper by its arXiv ID.
    """
    # Check if already saved
    if file_handler.paper_exists(paper_id):
        return {"success": True, "message": "Paper already saved", "already_exists": True}
    
    # Fetch from arXiv
    paper = await arxiv_client.get_paper_by_id(paper_id)
    
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found on arXiv")
    
    # Save to disk
    file_path = file_handler.save_paper(paper)
    
    return {
        "success": True,
        "message": f"Paper saved to {file_path}",
        "paper": paper.model_dump()
    }


@router.get("/api/stats", tags=["api"])
async def api_get_stats() -> dict:
    """
    API endpoint to get storage statistics.
    """
    return file_handler.get_stats()


@router.post("/api/download-pdf/{paper_id:path}", tags=["api"])
async def api_download_pdf(paper_id: str) -> dict:
    """
    API endpoint to download a PDF from arXiv and save it locally.
    The PDF will be named after the paper title.
    Text content will be automatically extracted.
    """
    # First check if we have the paper info
    paper = file_handler.get_paper(paper_id)
    
    if not paper:
        # Try to fetch paper info from arXiv
        paper = await arxiv_client.get_paper_by_id(paper_id)
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
    
    # Download the PDF with title as filename (text extraction happens automatically)
    success, result = await file_handler.download_pdf(paper_id, paper.pdf_url, paper.title)
    
    if success:
        # Check if text was extracted
        text_exists = file_handler.text_exists(paper_id, paper.title)
        text_path = file_handler.get_text_path(paper_id, paper.title)
        
        return {
            "success": True,
            "message": "PDF downloaded and text extracted successfully",
            "file_path": result,
            "paper_id": paper_id,
            "filename": file_handler.get_pdf_filename(paper_id, paper.title),
            "text_extracted": text_exists,
            "text_file": str(text_path) if text_path else None
        }
    else:
        raise HTTPException(status_code=500, detail=result)


@router.get("/api/pdf/{paper_id:path}", tags=["api"])
async def api_get_pdf(paper_id: str):
    """
    API endpoint to get a downloaded PDF file.
    Returns the PDF file for download/viewing.
    """
    # Get paper info for title
    paper = file_handler.get_paper(paper_id)
    title = paper.title if paper else None
    
    pdf_path = file_handler.get_pdf_path(paper_id, title)
    
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
async def api_pdf_status(paper_id: str) -> dict:
    """
    Check if a PDF has been downloaded and if text has been extracted.
    """
    paper = file_handler.get_paper(paper_id)
    title = paper.title if paper else None
    pdf_exists = file_handler.pdf_exists(paper_id, title)
    text_exists = file_handler.text_exists(paper_id, title)
    
    return {
        "paper_id": paper_id,
        "downloaded": pdf_exists,
        "download_url": f"/papers/api/pdf/{paper_id}" if pdf_exists else None,
        "filename": file_handler.get_pdf_filename(paper_id, title) if pdf_exists else None,
        "text_extracted": text_exists,
        "text_url": f"/papers/api/text/{paper_id}" if text_exists else None
    }


@router.get("/api/text/{paper_id:path}", tags=["api"])
async def api_get_text(paper_id: str):
    """
    API endpoint to get the extracted text content of a paper.
    Returns the text file for download/viewing.
    """
    paper = file_handler.get_paper(paper_id)
    title = paper.title if paper else None
    
    text_path = file_handler.get_text_path(paper_id, title)
    
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
    paper = file_handler.get_paper(paper_id)
    title = paper.title if paper else None
    
    content = file_handler.get_text_content(paper_id, title)
    
    if not content:
        raise HTTPException(status_code=404, detail="Text file not found. Please download the PDF first.")
    
    return {
        "paper_id": paper_id,
        "title": title,
        "content": content,
        "length": len(content)
    }

