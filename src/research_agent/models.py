from __future__ import annotations

from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ToolName(str, Enum):
    WEB_SEARCH = "web_search"
    WIKIPEDIA_SEARCH = "wikipedia_search"
    FETCH_URL = "fetch_url"


class PlanStep(BaseModel):
    id: int = Field(ge=1)
    objective: str = Field(min_length=3, max_length=300)
    tool: ToolName
    query: str = Field(min_length=2, max_length=500)
    rationale: str = Field(min_length=3, max_length=300)


class ResearchPlan(BaseModel):
    question: str
    assumptions: list[str] = Field(default_factory=list, max_length=6)
    steps: list[PlanStep] = Field(min_length=2, max_length=8)

    @field_validator("steps")
    @classmethod
    def unique_step_ids(cls, value: list[PlanStep]) -> list[PlanStep]:
        if len({step.id for step in value}) != len(value):
            raise ValueError("plan step ids must be unique")
        return value


class Source(BaseModel):
    title: str
    url: HttpUrl
    snippet: str
    publisher: str | None = None
    published_at: str | None = None
    relevance_score: float = Field(default=0.5, ge=0, le=1)
    quality_score: float = Field(default=0.5, ge=0, le=1)
    tool: ToolName

    @property
    def combined_score(self) -> float:
        return round(0.65 * self.relevance_score + 0.35 * self.quality_score, 4)


class ToolFailure(BaseModel):
    step_id: int
    tool: ToolName
    error_type: str
    message: str
    retryable: bool = False


class Finding(BaseModel):
    claim: str
    evidence: str
    # Keep citations as strings in the LLM-facing schema. OpenAI structured outputs rejects
    # JSON Schema's `format: url`, while this validator preserves the same boundary here.
    source_urls: list[str] = Field(min_length=1)

    @field_validator("source_urls")
    @classmethod
    def absolute_http_urls(cls, value: list[str]) -> list[str]:
        for url in value:
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError("finding citations must be absolute http(s) URLs")
        return value


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FinalAnswer(BaseModel):
    user_question: str
    short_answer: str
    key_findings: list[Finding]
    sources_used: list[Source]
    confidence_level: Confidence
    limitations_or_assumptions: list[str]
    suggested_next_steps: list[str]
    trace_id: str
    plan: ResearchPlan
    failures: list[ToolFailure] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
