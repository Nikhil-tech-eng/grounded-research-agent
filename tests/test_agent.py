from __future__ import annotations

from typing import Any

from research_agent.agent import ResearchAgent, SynthesisDraft
from research_agent.models import (
    Confidence,
    Finding,
    PlanStep,
    ResearchPlan,
    Source,
    ToolName,
)


class FakeLLM:
    def __init__(self, bad_citation: bool = False) -> None:
        self.bad_citation = bad_citation

    def generate(self, *, system: str, user: str, schema: type[Any]) -> Any:
        if schema is ResearchPlan:
            return ResearchPlan(
                question=user,
                assumptions=["The comparison is for a small product team."],
                steps=[
                    PlanStep(
                        id=1,
                        objective="Find broad evidence",
                        tool=ToolName.WEB_SEARCH,
                        query="vector database comparison",
                        rationale="Collect current comparisons",
                    ),
                    PlanStep(
                        id=2,
                        objective="Find background",
                        tool=ToolName.WIKIPEDIA_SEARCH,
                        query="vector database",
                        rationale="Cross-check definitions",
                    ),
                ],
            )
        citation = "https://evil.example/fake" if self.bad_citation else "https://docs.example/a"
        return SynthesisDraft(
            short_answer="Option A is a reasonable default.",
            key_findings=[
                Finding(
                    claim="A supports feature X.",
                    evidence="The docs describe X.",
                    source_urls=[citation],
                )
            ],
            confidence_level=Confidence.HIGH,
            limitations_or_assumptions=[],
            suggested_next_steps=["Run a workload-specific benchmark."],
        )


class FakeTools:
    def __init__(self, fail_web: bool = False, fail_all: bool = False) -> None:
        self.fail_web = fail_web
        self.fail_all = fail_all

    def web_search(self, query: str) -> list[Source]:
        if self.fail_web or self.fail_all:
            raise RuntimeError("search unavailable")
        return [source("https://docs.example/a", ToolName.WEB_SEARCH, 0.9)]

    def wikipedia_search(self, query: str) -> list[Source]:
        if self.fail_all:
            raise RuntimeError("wikipedia unavailable")
        return [source("https://docs.example/a", ToolName.WIKIPEDIA_SEARCH, 0.5)]

    def fetch_url(self, url: str) -> list[Source]:
        return [source(url, ToolName.FETCH_URL, 0.7)]


def source(url: str, tool: ToolName, relevance: float) -> Source:
    return Source(
        title="Source A",
        url=url,
        snippet="Evidence about feature X.",
        relevance_score=relevance,
        quality_score=0.8,
        tool=tool,
    )


def test_happy_path_is_structured_and_deduplicated() -> None:
    result = ResearchAgent(FakeLLM(), FakeTools()).run("Compare vector databases for a startup")
    assert result.confidence_level == Confidence.MEDIUM
    assert len(result.sources_used) == 1
    assert len(result.key_findings) == 1
    assert result.metrics["plan_step_count"] == 2


def test_web_failure_uses_wikipedia_fallback_and_records_failure() -> None:
    result = ResearchAgent(FakeLLM(), FakeTools(fail_web=True)).run(
        "Compare vector databases for a startup"
    )
    assert result.sources_used
    assert any(failure.tool == ToolName.WEB_SEARCH for failure in result.failures)


def test_total_retrieval_failure_returns_honest_low_confidence_answer() -> None:
    result = ResearchAgent(FakeLLM(), FakeTools(fail_all=True)).run(
        "Compare vector databases for a startup"
    )
    assert result.confidence_level == Confidence.LOW
    assert result.sources_used == []
    assert result.key_findings == []


def test_hallucinated_citation_is_removed() -> None:
    result = ResearchAgent(FakeLLM(bad_citation=True), FakeTools()).run(
        "Compare vector databases for a startup"
    )
    assert result.key_findings == []
    assert result.confidence_level == Confidence.LOW


def test_short_question_is_rejected() -> None:
    try:
        ResearchAgent(FakeLLM(), FakeTools()).run("why?")
    except ValueError as exc:
        assert "8-2000" in str(exc)
    else:
        raise AssertionError("expected ValueError")


class PlannerFailureLLM(FakeLLM):
    def generate(self, *, system: str, user: str, schema: type[Any]) -> Any:
        if schema is ResearchPlan:
            raise ValueError("invalid planner output")
        return super().generate(system=system, user=user, schema=schema)


class SynthesisFailureLLM(FakeLLM):
    def generate(self, *, system: str, user: str, schema: type[Any]) -> Any:
        if schema is SynthesisDraft:
            raise TimeoutError("provider timeout")
        return super().generate(system=system, user=user, schema=schema)


def test_planner_failure_uses_deterministic_fallback_plan() -> None:
    result = ResearchAgent(PlannerFailureLLM(), FakeTools()).run(
        "Compare vector databases for a startup"
    )
    assert len(result.plan.steps) == 2
    assert any("planner failed" in failure.message for failure in result.failures)


def test_synthesis_failure_returns_safe_structured_answer() -> None:
    result = ResearchAgent(SynthesisFailureLLM(), FakeTools()).run(
        "Compare vector databases for a startup"
    )
    assert result.confidence_level == Confidence.LOW
    assert result.key_findings == []
    assert any("synthesis failed" in failure.message for failure in result.failures)


def test_synthesis_schema_avoids_openai_unsupported_url_format() -> None:
    schema = SynthesisDraft.model_json_schema()
    items = schema["$defs"]["Finding"]["properties"]["source_urls"]["items"]
    assert items == {"type": "string"}
