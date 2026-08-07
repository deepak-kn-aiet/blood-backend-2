"""
FastAPI Application Entry Point

Initializes FastAPI application instance, configures CORS middleware,
registers API routers, initializes database schema, and defines base endpoints.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
import app.models  # Ensures all ORM models are registered in metadata

# Router imports
from app.routes.auth import router as auth_router
from app.routes.requests import router as requests_router
from app.routes.inventory import router as inventory_router
from app.routes.donors import router as donors_router
from app.routes.hospitals import router as hospitals_router
from app.routes.search import router as search_router
from app.routes.ai import router as ai_router
from app.routes.chat import router as chat_router

# Initialize database schema automatically on startup
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Automatic schema creation failed: {e}")

# Create FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Backend API powering Blood Relay Citizen App and Hospital Dashboard",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for all origins (Hackathon / Development friendly)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_router)
app.include_router(requests_router)
app.include_router(inventory_router)
app.include_router(donors_router)
app.include_router(hospitals_router)
app.include_router(search_router)
app.include_router(ai_router)
app.include_router(chat_router)



@app.get("/", tags=["Root"])
def read_root():
    """
    Root Endpoint

    Returns basic API welcoming message and service status.
    """
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health Check Endpoint

    Provides service health status for monitoring and quick sanity checks.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }
