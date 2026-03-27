"""Modeling conversation API endpoints with SSE streaming."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from odgg.models.metadata import MetadataSnapshot
from odgg.models.session import SessionState, StepStatus
from odgg.services.llm_router import stream_completion
from odgg.services.modeling_engine import (
    build_dimensional_model,
    suggest_business_process,
    suggest_dimensions,
    suggest_grain,
    suggest_measures,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modeling", tags=["modeling"])

# Reference to session store (shared with sessions module)
from odgg.api.v1.sessions import _sessions


class ModelingRequest(BaseModel):
    session_id: str
    step_number: int
    user_input: dict | None = None


@router.post("/suggest")
async def get_suggestion(req: ModelingRequest) -> dict:
    """Get AI suggestion for a modeling step."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    step = next(
        (s for s in session.steps if s.step_number == req.step_number), None
    )
    if not step:
        raise HTTPException(status_code=400, detail="Invalid step number")

    # Update step status
    step.status = StepStatus.AI_THINKING

    try:
        snapshot = MetadataSnapshot(**(session.metadata_snapshot or {}))

        if req.step_number == 3:
            result = await suggest_business_process(session, snapshot)
        elif req.step_number == 4:
            result = await suggest_grain(session, snapshot)
        elif req.step_number == 5:
            result = await suggest_dimensions(session, snapshot)
        elif req.step_number == 6:
            result = await suggest_measures(session, snapshot)
        elif req.step_number == 7:
            # Build and validate the model
            model = build_dimensional_model(session)
            result = {"model": model.model_dump(), "status": "valid"}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Step {req.step_number} does not have AI suggestions",
            )

        step.status = StepStatus.AI_SUGGESTED
        step.ai_suggestion = result
        step.confidence = result.get("confidence", 0.8)
        return result

    except Exception as e:
        step.status = StepStatus.ACTIVE
        step.error = str(e)[:500]
        logger.error("Modeling suggestion failed for step %d: %s", req.step_number, e)
        raise HTTPException(status_code=500, detail=str(e)[:500]) from None


@router.post("/suggest/stream")
async def stream_suggestion(req: ModelingRequest):
    """Stream AI suggestion via SSE for real-time display."""
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    snapshot = MetadataSnapshot(**(session.metadata_snapshot or {}))

    # Build context message for streaming
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert helping design "
                "a star schema. Provide clear, concise guidance."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Current step: {req.step_number}. "
                f"Business process: {session.business_process or 'not yet selected'}. "
                f"Help me with the next modeling decision."
            ),
        },
    ]

    async def event_generator():
        try:
            async for chunk in stream_completion(messages):
                yield {"event": "message", "data": json.dumps({"text": chunk})}
            yield {"event": "done", "data": "{}"}
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)[:500]}),
            }

    return EventSourceResponse(event_generator())


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
async def chat_with_model(req: ChatRequest) -> dict:
    """Free-text conversational model editing via AI."""
    from odgg.services.llm_router import chat_completion

    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build context from current session state
    context_parts = [
        f"Business process: {session.business_process or 'not selected'}",
        f"Grain: {session.grain_description or 'not defined'}",
    ]
    if session.selected_dimensions:
        dim_names = [
            d if isinstance(d, str) else d.get("name", "?")
            for d in session.selected_dimensions
        ]
        context_parts.append(f"Dimensions: {', '.join(dim_names)}")
    if session.selected_measures:
        measure_names = [
            m if isinstance(m, str) else m.get("name", "?")
            for m in session.selected_measures
        ]
        context_parts.append(f"Measures: {', '.join(measure_names)}")

    context = "\n".join(context_parts)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Kimball dimensional modeling expert. The user is building "
                "a star schema and wants to modify it. Here is the current model state:\n\n"
                f"{context}\n\n"
                "Help the user modify the model. Reply in Chinese. Be concise."
            ),
        },
        {"role": "user", "content": req.message},
    ]

    try:
        result = await chat_completion(messages)
        # Extract text from the response
        if isinstance(result, dict):
            reply = result.get("content", "") or str(result)
        else:
            reply = str(result)
        return {"reply": reply}
    except Exception as e:
        logger.error("Chat failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e)[:500]) from None


class CodegenRequest(BaseModel):
    session_id: str
    mode: str = "full"  # full | incremental
    include_dbt: bool = True


@router.post("/generate")
async def generate_code(req: CodegenRequest) -> dict:
    """Step 8: Generate DDL, ETL SQL, and dbt models."""
    from odgg.services.codegen import (
        generate_data_dictionary,
        generate_dbt_model,
        generate_ddl,
        generate_etl,
    )

    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session.dimensional_model:
        raise HTTPException(
            status_code=400, detail="No dimensional model built yet (complete Step 7 first)"
        )

    from odgg.models.dimensional import DimensionalModel

    model = DimensionalModel(**session.dimensional_model)

    ddl = generate_ddl(model)
    etl = generate_etl(model, mode=req.mode)

    result = {
        "ddl": ddl,
        "etl": etl,
        "data_dictionary": generate_data_dictionary(model),
    }

    if req.include_dbt:
        result["dbt"] = generate_dbt_model(model)

    # Store in session
    session.generated_ddl = ddl
    session.generated_etl = etl
    if req.include_dbt:
        session.generated_dbt = result["dbt"]

    return result
