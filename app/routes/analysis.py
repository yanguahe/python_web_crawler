"""
Routes for AI-powered paper analysis using DeepSeek.
"""
from pathlib import Path
from typing import Optional, List
from urllib.parse import unquote

from fastapi import APIRouter, Request, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from crawler import DeepSeekClient
from storage import FileHandler
from config import settings

router = APIRouter(prefix="/analysis", tags=["analysis"])

# Setup templates
APP_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

# Initialize clients
deepseek_client = DeepSeekClient()
file_handler = FileHandler()


class AnalyzeRequest(BaseModel):
    """Request model for paper analysis."""
    paper_id: str
    title: str
    abstract: str
    prompt: str


class BatchAnalyzeRequest(BaseModel):
    """Request model for batch paper analysis."""
    papers: List[dict]  # List of {id, title, abstract}
    prompt: str


class FulltextAnalyzeRequest(BaseModel):
    """Request model for fulltext paper analysis."""
    paper_id: str
    title: str
    fulltext: str  # Full text content from PDF
    prompt: str


@router.get("/status", tags=["api"])
async def api_analysis_status() -> dict:
    """
    Check if DeepSeek API is configured and available.
    """
    return {
        "configured": deepseek_client.is_configured(),
        "model": settings.deepseek_model,
        "message": "DeepSeek API is ready" if deepseek_client.is_configured() 
                   else "DeepSeek API key not configured. Please set DEEPSEEK_API_KEY."
    }


@router.post("/analyze", tags=["api"])
async def api_analyze_paper(request: AnalyzeRequest) -> dict:
    """
    Analyze a single paper abstract using DeepSeek.
    The analysis result (HTML) will be saved to local storage.
    
    Args:
        request: AnalyzeRequest containing paper info and prompt
    
    Returns:
        Analysis result with reasoning and content
    """
    if not deepseek_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API is not configured. Please set DEEPSEEK_API_KEY."
        )
    
    result = deepseek_client.analyze_abstract(
        abstract=request.abstract,
        prompt=request.prompt,
        title=request.title
    )
    
    if result.success:
        # Save the HTML content to file
        html_content = result.content
        saved_path = None
        
        # Check if content looks like HTML
        if html_content and ("<html" in html_content.lower() or "<!doctype" in html_content.lower()):
            saved_path = file_handler.save_analysis_html(request.title, html_content)
        
        return {
            "success": True,
            "paper_id": request.paper_id,
            "title": request.title,
            "reasoning": result.reasoning_content,
            "analysis": result.content,
            "html_saved": saved_path is not None,
            "html_path": saved_path,
            "view_url": f"/analysis/view/{request.title}" if saved_path else None
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.post("/analyze/stream", tags=["api"])
async def api_analyze_paper_stream(request: AnalyzeRequest):
    """
    Analyze a paper abstract with streaming response.
    Saves reasoning and HTML content when complete.
    """
    import asyncio
    import json
    import threading
    
    if not deepseek_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API is not configured. Please set DEEPSEEK_API_KEY."
        )
    
    async def generate():
        yield f"data: {json.dumps({'type': 'start', 'paper_id': request.paper_id})}\n\n"
        
        reasoning_buffer = ""
        content_buffer = ""
        
        # Use asyncio.Queue for better async compatibility
        data_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        
        def run_stream():
            """Run the sync generator in a thread."""
            try:
                for reasoning_chunk, content_chunk, is_reasoning in deepseek_client.analyze_abstract_stream(
                    abstract=request.abstract,
                    prompt=request.prompt,
                    title=request.title
                ):
                    # Put data into async queue from thread
                    asyncio.run_coroutine_threadsafe(
                        data_queue.put((reasoning_chunk, content_chunk, is_reasoning)),
                        loop
                    )
            finally:
                # Signal completion
                asyncio.run_coroutine_threadsafe(data_queue.put(None), loop)
        
        # Start the streaming in a background thread
        thread = threading.Thread(target=run_stream, daemon=True)
        thread.start()
        
        # Consume from queue and yield SSE events immediately
        while True:
            item = await data_queue.get()
            
            if item is None:
                break
            
            reasoning_chunk, content_chunk, is_reasoning = item
            
            if is_reasoning and reasoning_chunk:
                reasoning_buffer += reasoning_chunk
                yield f"data: {json.dumps({'type': 'reasoning', 'content': reasoning_chunk})}\n\n"
            elif content_chunk:
                content_buffer += content_chunk
                yield f"data: {json.dumps({'type': 'content', 'content': content_chunk})}\n\n"
        
        # Wait for thread to finish
        thread.join(timeout=5)
        
        # Save files when streaming is complete
        html_saved = False
        reasoning_saved = False
        view_url = None
        
        # Save reasoning content
        if reasoning_buffer:
            try:
                file_handler.save_reasoning(request.title, reasoning_buffer)
                reasoning_saved = True
            except Exception as e:
                print(f"Error saving reasoning: {e}")
        
        # Save HTML content
        if content_buffer and ("<html" in content_buffer.lower() or "<!doctype" in content_buffer.lower()):
            try:
                file_handler.save_analysis_html(request.title, content_buffer)
                html_saved = True
                view_url = f"/analysis/view/{request.title}"
            except Exception as e:
                print(f"Error saving HTML: {e}")
        
        yield f"data: {json.dumps({'type': 'done', 'paper_id': request.paper_id, 'html_saved': html_saved, 'reasoning_saved': reasoning_saved, 'view_url': view_url})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Type": "text/event-stream; charset=utf-8"
        }
    )


@router.get("/reasoning/{title:path}", tags=["api"])
async def api_get_reasoning(title: str) -> dict:
    """
    Get saved reasoning content for a paper.
    """
    decoded_title = unquote(title)
    reasoning = file_handler.get_reasoning_content(decoded_title)
    
    if reasoning:
        return {
            "success": True,
            "title": decoded_title,
            "reasoning": reasoning
        }
    else:
        return {
            "success": False,
            "title": decoded_title,
            "reasoning": None,
            "message": "Reasoning not found"
        }


@router.post("/batch", tags=["api"])
async def api_batch_analyze(request: BatchAnalyzeRequest) -> dict:
    """
    Analyze multiple paper abstracts.
    
    Args:
        request: BatchAnalyzeRequest containing papers and prompt
    
    Returns:
        List of analysis results
    """
    if not deepseek_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API is not configured. Please set DEEPSEEK_API_KEY."
        )
    
    results = []
    for paper in request.papers:
        result = deepseek_client.analyze_abstract(
            abstract=paper.get('abstract', ''),
            prompt=request.prompt,
            title=paper.get('title')
        )
        
        results.append({
            "paper_id": paper.get('id'),
            "title": paper.get('title'),
            "success": result.success,
            "reasoning": result.reasoning_content if result.success else "",
            "analysis": result.content if result.success else "",
            "error": result.error if not result.success else None
        })
    
    return {
        "success": True,
        "total": len(results),
        "successful": sum(1 for r in results if r['success']),
        "results": results
    }


@router.get("/view/{title:path}", response_class=HTMLResponse, tags=["api"])
async def view_analysis_html(title: str):
    """
    View a saved analysis HTML file.
    """
    # URL decode the title
    decoded_title = unquote(title)
    
    html_content = file_handler.get_analysis_content(decoded_title)
    
    if not html_content:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return HTMLResponse(content=html_content)


@router.get("/download/{title:path}", tags=["api"])
async def download_analysis_html(title: str):
    """
    Download a saved analysis HTML file.
    """
    decoded_title = unquote(title)
    
    html_path = file_handler.get_analysis_path(decoded_title)
    
    if not html_path:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return FileResponse(
        path=html_path,
        filename=html_path.name,
        media_type="text/html"
    )


@router.get("/exists/{title:path}", tags=["api"])
async def check_analysis_exists(title: str) -> dict:
    """
    Check if an analysis exists for a paper.
    """
    decoded_title = unquote(title)
    exists = file_handler.analysis_exists(decoded_title)
    
    return {
        "title": decoded_title,
        "exists": exists,
        "view_url": f"/analysis/view/{title}" if exists else None,
        "download_url": f"/analysis/download/{title}" if exists else None
    }


@router.get("/list", tags=["api"])
async def list_analyses() -> dict:
    """
    List all saved analysis files.
    """
    analyses = file_handler.list_analyses()
    
    return {
        "success": True,
        "total": len(analyses),
        "analyses": analyses
    }


@router.delete("/delete/{title:path}", tags=["api"])
async def delete_analysis(title: str) -> dict:
    """
    Delete a saved analysis file.
    """
    decoded_title = unquote(title)
    
    if file_handler.delete_analysis(decoded_title):
        return {"success": True, "message": f"Analysis for '{decoded_title}' deleted"}
    else:
        raise HTTPException(status_code=404, detail="Analysis not found")


# ==================== Fulltext Analysis Endpoints ====================

@router.post("/analyze/fulltext/stream", tags=["api"])
async def api_analyze_fulltext_stream(request: FulltextAnalyzeRequest):
    """
    Analyze paper fulltext with streaming response.
    Saves reasoning and HTML content when complete.
    """
    import asyncio
    import json
    import threading
    
    if not deepseek_client.is_configured():
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API is not configured. Please set DEEPSEEK_API_KEY."
        )
    
    async def generate():
        yield f"data: {json.dumps({'type': 'start', 'paper_id': request.paper_id})}\n\n"
        
        reasoning_buffer = ""
        content_buffer = ""
        
        # Use asyncio.Queue for better async compatibility
        data_queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        
        def run_stream():
            """Run the sync generator in a thread."""
            try:
                for reasoning_chunk, content_chunk, is_reasoning in deepseek_client.analyze_fulltext_stream(
                    fulltext=request.fulltext,
                    prompt=request.prompt,
                    title=request.title
                ):
                    # Put data into async queue from thread
                    asyncio.run_coroutine_threadsafe(
                        data_queue.put((reasoning_chunk, content_chunk, is_reasoning)),
                        loop
                    )
            finally:
                # Signal completion
                asyncio.run_coroutine_threadsafe(data_queue.put(None), loop)
        
        # Start the streaming in a background thread
        thread = threading.Thread(target=run_stream, daemon=True)
        thread.start()
        
        # Consume from queue and yield SSE events immediately
        while True:
            item = await data_queue.get()
            
            if item is None:
                break
            
            reasoning_chunk, content_chunk, is_reasoning = item
            
            if is_reasoning and reasoning_chunk:
                reasoning_buffer += reasoning_chunk
                yield f"data: {json.dumps({'type': 'reasoning', 'content': reasoning_chunk})}\n\n"
            elif content_chunk:
                content_buffer += content_chunk
                yield f"data: {json.dumps({'type': 'content', 'content': content_chunk})}\n\n"
        
        # Wait for thread to finish
        thread.join(timeout=5)
        
        # Save files when streaming is complete
        html_saved = False
        reasoning_saved = False
        view_url = None
        
        # Save reasoning content
        if reasoning_buffer:
            try:
                file_handler.save_fulltext_reasoning(request.title, reasoning_buffer)
                reasoning_saved = True
            except Exception as e:
                print(f"Error saving fulltext reasoning: {e}")
        
        # Save HTML content
        if content_buffer and ("<html" in content_buffer.lower() or "<!doctype" in content_buffer.lower()):
            try:
                file_handler.save_fulltext_analysis_html(request.title, content_buffer)
                html_saved = True
                view_url = f"/analysis/fulltext/view/{request.title}"
            except Exception as e:
                print(f"Error saving fulltext HTML: {e}")
        
        yield f"data: {json.dumps({'type': 'done', 'paper_id': request.paper_id, 'html_saved': html_saved, 'reasoning_saved': reasoning_saved, 'view_url': view_url})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream; charset=utf-8"
        }
    )


@router.get("/fulltext/reasoning/{title:path}", tags=["api"])
async def api_get_fulltext_reasoning(title: str) -> dict:
    """
    Get saved fulltext reasoning content for a paper.
    """
    decoded_title = unquote(title)
    reasoning = file_handler.get_fulltext_reasoning_content(decoded_title)
    
    if reasoning:
        return {
            "success": True,
            "title": decoded_title,
            "reasoning": reasoning
        }
    else:
        return {
            "success": False,
            "title": decoded_title,
            "reasoning": None,
            "message": "Fulltext reasoning not found"
        }


@router.get("/fulltext/view/{title:path}", response_class=HTMLResponse)
async def view_fulltext_analysis_html(request: Request, title: str):
    """
    View the fulltext analysis HTML file directly.
    """
    decoded_title = unquote(title)
    
    html_content = file_handler.get_fulltext_analysis_content(decoded_title)
    
    if not html_content:
        raise HTTPException(status_code=404, detail="Fulltext analysis not found")
    
    return HTMLResponse(content=html_content)


@router.get("/fulltext/download/{title:path}")
async def download_fulltext_analysis(title: str):
    """
    Download the fulltext analysis HTML file.
    """
    decoded_title = unquote(title)
    
    html_path = file_handler.get_fulltext_analysis_path(decoded_title)
    
    if not html_path:
        raise HTTPException(status_code=404, detail="Fulltext analysis not found")
    
    return FileResponse(
        path=html_path,
        filename=html_path.name,
        media_type="text/html"
    )


@router.get("/fulltext/exists/{title:path}", tags=["api"])
async def check_fulltext_analysis_exists(title: str) -> dict:
    """
    Check if a fulltext analysis exists for a paper.
    """
    decoded_title = unquote(title)
    analysis_exists = file_handler.fulltext_analysis_exists(decoded_title)
    reasoning_exists = file_handler.fulltext_reasoning_exists(decoded_title)
    
    return {
        "title": decoded_title,
        "analysis_exists": analysis_exists,
        "reasoning_exists": reasoning_exists,
        "view_url": f"/analysis/fulltext/view/{title}" if analysis_exists else None
    }


@router.delete("/fulltext/delete/{title:path}", tags=["api"])
async def delete_fulltext_analysis(title: str) -> dict:
    """
    Delete fulltext analysis HTML and reasoning files.
    """
    decoded_title = unquote(title)
    
    if file_handler.delete_fulltext_analysis(decoded_title):
        return {"success": True, "message": f"Fulltext analysis for '{decoded_title}' deleted"}
    else:
        raise HTTPException(status_code=404, detail="Fulltext analysis not found")

