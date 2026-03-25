"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odgg.api.v1 import metadata, modeling, sessions
from odgg.core.config import settings
from odgg.core.logging import setup_logging

setup_logging(debug=settings.debug)

app = FastAPI(
    title="ODGG API",
    description="Conversational Dimensional Modeling Notebook",
    version="0.1.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
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


@app.get("/api/v1/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
