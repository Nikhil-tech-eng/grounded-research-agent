from __future__ import annotations

import json
from typing import Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

T = TypeVar("T", bound=BaseModel)


class StructuredLLM(Protocol):
    def generate(self, *, system: str, user: str, schema: type[T]) -> T: ...


class OpenAIStructuredLLM:
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=1, max=8),
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        reraise=True,
    )
    def generate(self, *, system: str, user: str, schema: type[T]) -> T:
        response = self.client.responses.parse(
            model=self.model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=schema,
        )
        if response.output_parsed is None:
            raise ValueError("model returned no structured output")
        return response.output_parsed


def as_json(value: BaseModel) -> str:
    return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, indent=2)
