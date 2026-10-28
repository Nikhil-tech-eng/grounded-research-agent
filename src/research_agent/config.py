from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    model: str = "gpt-4.1-mini"
    tavily_api_key: str | None = None
    timeout_seconds: float = 12.0
    max_sources: int = 8
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise ValueError("OPENAI_API_KEY is required. Copy .env.example to .env and add it.")
        return cls(
            openai_api_key=key,
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
            timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "12")),
            max_sources=int(os.getenv("MAX_SOURCES", "8")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
