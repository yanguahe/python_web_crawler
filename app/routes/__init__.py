from .search import router as search_router
from .papers import router as papers_router
from .analysis import router as analysis_router

__all__ = ["search_router", "papers_router", "analysis_router"]

