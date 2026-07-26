# ============================================
# AI Research Agent - FastAPI Application
# ============================================
"""
FastAPI application factory with CORS configuration.

WHY AN APPLICATION FACTORY?
---------------------------
Instead of creating the FastAPI app at module level, we use a factory
function. This enables:
1. Different configurations for testing vs production
2. Lazy initialization (dependencies loaded only when needed)
3. Clean separation of app creation from app startup
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.api.routes.research import router as research_router
from backend.config.settings import get_settings


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application with routes and middleware.
    """
    # Configure logging
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    
    logger = logging.getLogger(__name__)
    
    # Create FastAPI app
    app = FastAPI(
        title="AI Research Agent",
        description="Autonomous AI Research Agent powered by LangGraph",
        version="0.1.0",
    )
    
    # ---- CORS Middleware ----
    # Allow the frontend (served from different port/origin) to call the API.
    # In development, we allow all origins. In production, restrict this.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],      # Development: allow all
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ---- Register Routes ----
    app.include_router(research_router)
    
    # ---- Serve Frontend Static Files ----
    # Mount the frontend directory so the API server also serves the UI
    frontend_path = Path(__file__).parent.parent.parent / "frontend"
    if frontend_path.exists():
        app.mount(
            "/",
            StaticFiles(directory=str(frontend_path), html=True),
            name="frontend",
        )
        logger.info(f"📁 Serving frontend from: {frontend_path}")
    else:
        logger.warning(f"⚠️ Frontend directory not found: {frontend_path}")
    
    logger.info("🚀 AI Research Agent API initialized")
    return app
