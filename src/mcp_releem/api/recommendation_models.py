"""Typed review metadata; arbitrary review evidence is never exposed automatically."""

from typing import Any

from pydantic import Field

from .models import Recommendation, UpstreamModel


class RecommendationEvidence(UpstreamModel):
    href: str
    pointer: str | None = None


class Review(UpstreamModel):
    id: int
    base_score: float | None = None
    score_adjustment_applied: float | None = None
    priority_score: float = Field(ge=0, le=100)
    why_important_now: str
    review_details: dict[str, Any] = Field(default_factory=dict)
    review_input_snapshot: dict[str, Any] | None = None
    created_at: str | None = None


class StatusEvent(UpstreamModel):
    id: int
    event_type: str = "status_changed"
    old_status: str | None = None
    new_status: str
    actor_type: str
    reason: str | None = None
    created_at: str | None = None


class RecommendationDetail(Recommendation):
    evidence: RecommendationEvidence | None = None
    current_review: Review | None = None
    review_history: list[Review] | None = None
    status_history: list[StatusEvent] | None = None
