"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import odgg.models.ai_config  # noqa: E402, F401  # Import ORM models before create_all
import odgg.models.brief  # noqa: E402, F401
from odgg.api.v1 import ai_config, briefs, metadata, modeling, sessions
from odgg.core.config import settings, update_runtime_overrides
from odgg.core.database import Base, async_session, engine
from odgg.core.logging import setup_logging
from odgg.models.ai_config import AiConfigRow

setup_logging(debug=settings.debug)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup and load persisted AI config."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load persisted AI config overrides from SQLite
    async with async_session() as db:
        row = await db.get(AiConfigRow, 1)
        if row:
            overrides = {}
            if row.llm_provider:
                overrides["provider"] = row.llm_provider
            if row.llm_model:
                overrides["model"] = row.llm_model
            if row.llm_api_key:
                overrides["api_key"] = row.llm_api_key
            if row.llm_base_url:
                overrides["base_url"] = row.llm_base_url
            if row.llm_timeout:
                overrides["timeout"] = row.llm_timeout
            if overrides:
                update_runtime_overrides(overrides)

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
app.include_router(ai_config.router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
