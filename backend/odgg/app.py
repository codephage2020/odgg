"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import odgg.models.brief  # noqa: E402, F401  # Import ORM models before create_all
from odgg.api.v1 import briefs, metadata, modeling, sessions
from odgg.core.config import settings
from odgg.core.database import Base, engine
from odgg.core.logging import setup_logging

setup_logging(debug=settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="ODGG API",
    description="AI-Assisted Dimensional Model Discovery",
    version="0.2.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 routers
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(metadata.router, prefix="/api/v1")
app.include_router(modeling.router, prefix="/api/v1")
app.include_router(briefs.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
