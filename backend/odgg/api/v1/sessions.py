"""Session management API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from odgg.models.session import SessionState, StepStatus

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory session store for MVP (SQLite persistence in next iteration)
_sessions: dict[str, SessionState] = {}


class CreateSessionRequest(BaseModel):
    source_db_type: str = "postgresql"


class CreateSessionResponse(BaseModel):
    session_id: str
    state: SessionState


@router.post("", response_model=CreateSessionResponse)
async def create_session(req: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new modeling session."""
    session_id = str(uuid.uuid4())
    state = SessionState(
        session_id=session_id,
        source_db_type=req.source_db_type,
    )
    _sessions[session_id] = state
    return CreateSessionResponse(session_id=session_id, state=state)


@router.get("/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    """Get current session state."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


class UpdateStepRequest(BaseModel):
    step_number: int
    action: str  # confirm | rollback
    user_input: dict | None = None
    version: int  # Optimistic locking


@router.post("/{session_id}/steps")
async def update_step(session_id: str, req: UpdateStepRequest) -> SessionState:
    """Update a step's state with optimistic locking."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = _sessions[session_id]

    # Optimistic lock check
    if req.version != session.version:
        raise HTTPException(
            status_code=409,
            detail="Session was modified by another request. Please refresh.",
        )

    step = next(
        (s for s in session.steps if s.step_number == req.step_number), None
    )
    if not step:
        raise HTTPException(status_code=400, detail="Invalid step number")

    if req.action == "confirm":
        if step.status not in (StepStatus.AI_SUGGESTED, StepStatus.ACTIVE):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm step in state: {step.status}",
            )
        step.user_input = req.user_input
        session.advance_step(req.step_number)

        # Record telemetry
        decision = "accept" if not req.user_input else "modify"
        session.record_decision(req.step_number, decision, req.user_input)

    elif req.action == "rollback":
        session.rollback_to_step(req.step_number)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    return session
