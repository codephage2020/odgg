"""Session state model with per-step tracking and optimistic locking."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    """State machine for each modeling step."""

    LOCKED = "locked"
    ACTIVE = "active"
    AI_THINKING = "ai_thinking"
    AI_SUGGESTED = "ai_suggested"
    USER_CONFIRMED = "user_confirmed"
    COMPLETED = "completed"


class StepState(BaseModel):
    """State for a single modeling step."""

    step_number: int
    status: StepStatus = StepStatus.LOCKED
    ai_suggestion: dict[str, Any] | None = None
    user_input: dict[str, Any] | None = None
    confidence: float | None = None  # AI confidence score 0-1
    error: str | None = None
    updated_at: str = ""


class SessionState(BaseModel):
    """Complete session state with optimistic locking."""

    session_id: str = Field(default_factory=lambda: "")
    version: int = 1  # Optimistic lock version - increment on every write

    # Connection info (Step 1)
    source_db_url: str = ""  # Never logged, stored only in memory or env
    source_db_type: str = "postgresql"

    # Metadata (Step 2)
    metadata_snapshot: dict[str, Any] | None = None

    # Modeling state (Steps 3-6)
    business_process: str = ""
    grain_description: str = ""
    selected_dimensions: list[str] = Field(default_factory=list)
    selected_measures: list[dict[str, Any]] = Field(default_factory=list)

    # Model output (Step 7)
    dimensional_model: dict[str, Any] | None = None

    # Code output (Step 8)
    generated_ddl: str = ""
    generated_etl: str = ""
    generated_dbt: dict[str, str] = Field(default_factory=dict)  # filename -> content

    # Step tracking
    steps: list[StepState] = Field(default_factory=lambda: [
        StepState(step_number=1, status=StepStatus.ACTIVE),
        *[StepState(step_number=i) for i in range(2, 9)],
    ])

    # Telemetry (opt-in)
    step_decisions: list[dict[str, Any]] = Field(default_factory=list)

    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def current_step(self) -> int:
        """Return the number of the currently active step."""
        for step in self.steps:
            if step.status in (
                StepStatus.ACTIVE,
                StepStatus.AI_THINKING,
                StepStatus.AI_SUGGESTED,
            ):
                return step.step_number
        return 8  # All completed

    def advance_step(self, step_number: int) -> None:
        """Mark a step as completed and unlock the next one."""
        for step in self.steps:
            if step.step_number == step_number:
                step.status = StepStatus.COMPLETED
            elif step.step_number == step_number + 1:
                step.status = StepStatus.ACTIVE
        self.version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def rollback_to_step(self, step_number: int) -> None:
        """Roll back to a previous step, invalidating all subsequent steps."""
        for step in self.steps:
            if step.step_number < step_number:
                pass  # Keep completed
            elif step.step_number == step_number:
                step.status = StepStatus.ACTIVE
                step.ai_suggestion = None
                step.user_input = None
                step.error = None
            else:
                step.status = StepStatus.LOCKED
                step.ai_suggestion = None
                step.user_input = None
                step.error = None
        self.version += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def record_decision(
        self, step_number: int, action: str, details: dict[str, Any] | None = None
    ) -> None:
        """Record a user decision for engagement telemetry."""
        self.step_decisions.append({
            "step": step_number,
            "action": action,  # accept | modify | reject
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
        })
