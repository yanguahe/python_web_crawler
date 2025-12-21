"""
Main FastAPI application.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from .routes import search_router, papers_router, analysis_router

# Get the app directory
APP_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    application = FastAPI(
        title=settings.app_name,
        description="A web application to search and save arXiv paper abstracts",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Mount static files
    static_dir = APP_DIR / "static"
    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Include routers
    application.include_router(search_router)
    application.include_router(papers_router)
    application.include_router(analysis_router)
    
    return application


# Create the application instance
app = create_app()

# Setup templates
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@app.get("/", include_in_schema=False)
async def home(request: Request):
    """Render the home page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": settings.app_name
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "app": settings.app_name}

