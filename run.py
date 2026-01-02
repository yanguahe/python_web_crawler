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
    
    # Check if we can use reload mode (requires sufficient inotify watches)
    # If inotify limit is too low, disable reload to avoid crashes
    use_reload = settings.debug
    
    if use_reload:
        try:
            # Check current inotify limit on Linux
            with open('/proc/sys/fs/inotify/max_user_watches', 'r') as f:
                max_watches = int(f.read().strip())
                # Need at least 16384 watches for comfortable development
                if max_watches < 16384:
                    print(f"⚠️  Warning: inotify watch limit is {max_watches}, too low for hot-reload.")
                    print("   Disabling hot-reload. To enable it, run:")
                    print("   sudo sysctl fs.inotify.max_user_watches=524288")
                    print()
                    use_reload = False
        except (FileNotFoundError, PermissionError):
            # Not on Linux or can't read the file, try reload anyway
            pass
    
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=use_reload,
        log_level="info" if settings.debug else "warning"
    )


if __name__ == "__main__":
    main()

