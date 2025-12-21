#!/usr/bin/env python3
"""
arXiv Paper Crawler - Application Entry Point

Usage:
    python run.py
    
Or with custom settings:
    APP_HOST=127.0.0.1 APP_PORT=8080 python run.py
"""
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

import uvicorn
from config import settings


def main():
    """Run the application."""
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   📚 arXiv Paper Crawler                                  ║
║                                                           ║
║   Starting server at http://{settings.app_host}:{settings.app_port}               ║
║                                                           ║
║   API Docs:    http://{settings.app_host}:{settings.app_port}/docs               ║
║   ReDoc:       http://{settings.app_host}:{settings.app_port}/redoc              ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
        log_level="info" if settings.debug else "warning"
    )


if __name__ == "__main__":
    main()

