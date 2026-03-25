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


@router.post("/discover", response_model=MetadataSnapshot)
async def discover(req: DiscoverRequest) -> MetadataSnapshot:
    """Discover metadata from a source database.

    The connection URL is used for the discovery query only and is never
    persisted or logged.
    """
    try:
        snapshot = await discover_metadata(
            connection_url=req.connection_url,
            schema=req.schema_name,
        )
        return snapshot
    except Exception as e:
        # Do NOT log the connection URL — it may contain credentials
        logger.error("Metadata discovery failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect or discover metadata: {type(e).__name__}",
        ) from None
