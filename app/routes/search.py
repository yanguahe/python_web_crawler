"""
Search routes for the web application.
"""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, Form, Query, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from crawler import ArxivClient, SearchResult
from storage import FileHandler
from config import settings

router = APIRouter(tags=["search"])

# Setup templates
APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# Initialize clients
arxiv_client = ArxivClient()
file_handler = FileHandler()


@router.post("/search", response_class=HTMLResponse)
async def search_papers(
    request: Request,
    query: str = Form(..., min_length=1, max_length=500),
    max_results: int = Form(default=10, ge=1, le=50),
    save_results: bool = Form(default=False)
):
    """
    Search for papers on arXiv and display results.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        save_results: Whether to save results to disk
    """
    try:
        # Perform the search
        result = await arxiv_client.search(
            query=query,
            max_results=max_results
        )
        
        # Save papers if requested
        saved_count = 0
        if save_results and result.papers:
            saved_paths = file_handler.save_batch(result.papers)
            saved_count = len(saved_paths)
        
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "title": f"Search Results: {query}",
                "query": query,
                "result": result,
                "saved_count": saved_count,
                "save_results": save_results
            }
        )
    
    except Exception as e:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "title": "Search Error",
                "query": query,
                "error": str(e),
                "result": None
            }
        )


@router.get("/search", response_class=HTMLResponse)
async def search_papers_get(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500),
    max_results: int = Query(default=10, ge=1, le=50),
    start: int = Query(default=0, ge=0),
    save: bool = Query(default=False)
):
    """
    Search for papers on arXiv via GET request (for pagination).
    """
    try:
        result = await arxiv_client.search(
            query=q,
            start=start,
            max_results=max_results
        )
        
        saved_count = 0
        if save and result.papers:
            saved_paths = file_handler.save_batch(result.papers)
            saved_count = len(saved_paths)
        
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "title": f"Search Results: {q}",
                "query": q,
                "result": result,
                "saved_count": saved_count,
                "save_results": save,
                "current_start": start,
                "max_results": max_results
            }
        )
    
    except Exception as e:
        return templates.TemplateResponse(
            "results.html",
            {
                "request": request,
                "title": "Search Error",
                "query": q,
                "error": str(e),
                "result": None
            }
        )


@router.get("/api/search")
async def api_search(
    query: str = Query(..., min_length=1, max_length=500),
    max_results: int = Query(default=10, ge=1, le=50),
    start: int = Query(default=0, ge=0),
    save: bool = Query(default=False)
) -> dict:
    """
    API endpoint for searching papers.
    
    Returns JSON response with search results.
    """
    try:
        result = await arxiv_client.search(
            query=query,
            start=start,
            max_results=max_results
        )
        
        saved_count = 0
        if save and result.papers:
            saved_paths = file_handler.save_batch(result.papers)
            saved_count = len(saved_paths)
        
        return {
            "success": True,
            "query": query,
            "total_results": result.total_results,
            "start_index": result.start_index,
            "items_per_page": result.items_per_page,
            "papers": [paper.model_dump() for paper in result.papers],
            "saved_count": saved_count
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/search/author")
async def api_search_by_author(
    author: str = Query(..., min_length=1, max_length=200),
    max_results: int = Query(default=10, ge=1, le=50),
    start: int = Query(default=0, ge=0)
) -> dict:
    """
    API endpoint for searching papers by author.
    """
    try:
        result = await arxiv_client.search_by_author(
            author=author,
            start=start,
            max_results=max_results
        )
        
        return {
            "success": True,
            "author": author,
            "total_results": result.total_results,
            "papers": [paper.model_dump() for paper in result.papers]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/search/category")
async def api_search_by_category(
    category: str = Query(..., min_length=1, max_length=50),
    max_results: int = Query(default=10, ge=1, le=50),
    start: int = Query(default=0, ge=0)
) -> dict:
    """
    API endpoint for searching papers by category.
    """
    try:
        result = await arxiv_client.search_by_category(
            category=category,
            start=start,
            max_results=max_results
        )
        
        return {
            "success": True,
            "category": category,
            "total_results": result.total_results,
            "papers": [paper.model_dump() for paper in result.papers]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

