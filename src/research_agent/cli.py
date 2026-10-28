from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Annotated

import typer

from .agent import ResearchAgent
from .config import Settings
from .llm import OpenAIStructuredLLM
from .tools import HttpResearchTools

app = typer.Typer(add_completion=False, help="Source-grounded AI research agent")


@app.command()
def research(
    question: Annotated[str, typer.Argument(help="Research-style question")],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Plan, retrieve, filter, and synthesize a cited answer."""
    try:
        settings = Settings.from_env()
        logging.basicConfig(
            level=settings.log_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        agent = ResearchAgent(
            llm=OpenAIStructuredLLM(settings.openai_api_key, settings.model),
            tools=HttpResearchTools(settings.timeout_seconds, settings.tavily_api_key),
            max_sources=settings.max_sources,
        )
        result = agent.run(question)
        rendered = json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(rendered + "\n", encoding="utf-8")
            typer.echo(f"Saved {output}")
        else:
            typer.echo(rendered)
    except Exception as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(code=1) from exc


if __name__ == "__main__":
    app()
