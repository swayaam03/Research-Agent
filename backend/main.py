# ============================================
# AI Research Agent - Entry Point
# ============================================
"""
Application entry point. Run with:
    python -m backend.main

Or from the project root:
    python backend/main.py
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'from backend...' imports work when run directly
root_dir = Path(__file__).parent.parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import uvicorn
from backend.api.app import create_app
from backend.config.settings import get_settings


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=True,         # Auto-reload on code changes (development only)
        log_level=settings.log_level.lower(),
    )
