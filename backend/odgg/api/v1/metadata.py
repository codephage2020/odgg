"""Metadata discovery API endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from odgg.models.metadata import MetadataSnapshot
from odgg.services.metadata_discovery import discover_metadata

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["metadata"])


class DiscoverRequest(BaseModel):
    connection_url: str  # Passed in request body, never logged
    schema_name: str = "public"
    session_id: str | None = None  # Optional: auto-store metadata in session
    brief_id: str | None = None  # Optional: auto-store metadata in brief


@router.post("/discover", response_model=MetadataSnapshot)
async def discover(req: DiscoverRequest) -> MetadataSnapshot:
    """Discover metadata from a source database.

    The connection URL is used for the discovery query only and is never
    persisted or logged. If session_id is provided, the discovered metadata
    is automatically stored in the session.
    """
    try:
        snapshot = await discover_metadata(
            connection_url=req.connection_url,
            schema=req.schema_name,
        )

        # Store metadata in session if session_id provided
        if req.session_id:
            from odgg.api.v1.sessions import _sessions

            session = _sessions.get(req.session_id)
            if session:
                session.metadata_snapshot = snapshot.model_dump()
                logger.info("Stored metadata in session %s", req.session_id)

        # Store metadata in brief if brief_id provided
        if req.brief_id:
            from sqlalchemy import select

            from odgg.core.database import async_session
            from odgg.models.brief import BriefRow

            async with async_session() as db:
                stmt = select(BriefRow).where(BriefRow.id == req.brief_id)
                result = await db.execute(stmt)
                brief = result.scalar_one_or_none()
                if brief:
                    brief.metadata_snapshot = snapshot.model_dump()
                    brief.database_name = snapshot.database_name
                    await db.commit()
                    logger.info("Stored metadata in brief %s", req.brief_id)

        return snapshot
    except Exception as e:
        # Do NOT log the connection URL — it may contain credentials
        logger.error("Metadata discovery failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect or discover metadata: {type(e).__name__}",
        ) from None
