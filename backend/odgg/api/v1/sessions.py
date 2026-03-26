"""Session management API endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from odgg.models.session import SessionState, StepStatus

router = APIRouter(prefix="/sessions", tags=["sessions"])

# In-memory session store for MVP (SQLite persistence in next iteration)
_sessions: dict[str, SessionState] = {}


def _apply_step_input(
    session: SessionState,
    step_number: int,
    user_input: dict,
    step: "StepState",
) -> None:
    """Map step-specific user_input to session-level modeling fields.

    When a user confirms a step, the selected values (business process, grain,
    dimensions, measures) need to be stored at the session level so that
    subsequent AI suggestions have the context they need.
    """
    from odgg.models.session import StepState  # noqa: F811

    ai = step.ai_suggestion or {}

    if step_number == 3:
        # Business process selection
        session.business_process = (
            user_input.get("business_process")
            or (ai.get("processes", [{}])[0].get("name") if ai.get("processes") else "")
        )

    elif step_number == 4:
        # Grain definition
        session.grain_description = (
            user_input.get("grain")
            or user_input.get("grain_description")
            or ""
        )
        # If user just accepted, pull from AI suggestion
        if not session.grain_description and ai.get("options"):
            rec = next((o for o in ai["options"] if o.get("recommended")), ai["options"][0])
            session.grain_description = rec.get("description", "")

    elif step_number == 5:
        # Dimension selection
        dims = user_input.get("dimensions", [])
        if dims:
            session.selected_dimensions = dims
        elif ai.get("dimensions"):
            # User accepted AI suggestion as-is
            session.selected_dimensions = ai["dimensions"]

    elif step_number == 6:
        # Measure selection
        measures = user_input.get("measures", [])
        if measures:
            session.selected_measures = measures
        elif ai.get("measures"):
            session.selected_measures = ai["measures"]

    elif step_number == 7:
        # Build and store the dimensional model
        model = ai.get("model")
        if model:
            session.dimensional_model = model


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

        # Map user_input fields to session-level modeling state
        _apply_step_input(session, req.step_number, req.user_input or {}, step)

        session.advance_step(req.step_number)

        # Record telemetry
        decision = "accept" if not req.user_input else "modify"
        session.record_decision(req.step_number, decision, req.user_input)

    elif req.action == "rollback":
        session.rollback_to_step(req.step_number)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    return session
