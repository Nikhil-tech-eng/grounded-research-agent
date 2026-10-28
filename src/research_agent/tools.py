from __future__ import annotations

import re
from typing import Protocol
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from .models import Source, ToolName
from .security import sanitize_untrusted_text, validate_public_url


class ResearchTools(Protocol):
    def web_search(self, query: str) -> list[Source]: ...
    def wikipedia_search(self, query: str) -> list[Source]: ...
    def fetch_url(self, url: str) -> list[Source]: ...


class HttpResearchTools:
    def __init__(self, timeout: float = 12, tavily_api_key: str | None = None) -> None:
        self.tavily_api_key = tavily_api_key
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=False,
            headers={"User-Agent": "GroundedResearchAgent/0.1 (+assignment demo)"},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def web_search(self, query: str) -> list[Source]:
        if not self.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured; fallback search will be used")
        response = self.client.post(
            "https://api.tavily.com/search",
            json={"api_key": self.tavily_api_key, "query": query, "max_results": 5},
        )
        response.raise_for_status()
        results = []
        for item in response.json().get("results", []):
            try:
                url = validate_public_url(item["url"])
                text, _ = sanitize_untrusted_text(item.get("content", ""), 2_000)
                results.append(
                    Source(
                        title=item.get("title") or "Untitled",
                        url=url,
                        snippet=text,
                        publisher=urlparse(url).hostname,
                        relevance_score=float(item.get("score", 0.5)),
                        quality_score=_domain_quality(url),
                        tool=ToolName.WEB_SEARCH,
                    )
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                # One malformed provider item must not discard valid sibling results.
                continue
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def wikipedia_search(self, query: str) -> list[Source]:
        response = self.client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrlimit": 5,
                "prop": "extracts|info",
                "inprop": "url",
                "exintro": 1,
                "explaintext": 1,
                "format": "json",
            },
        )
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            try:
                url = validate_public_url(page["fullurl"])
                snippet, _ = sanitize_untrusted_text(page.get("extract", ""), 2_000)
                results.append(
                    Source(
                        title=page["title"],
                        url=url,
                        snippet=snippet,
                        publisher="Wikipedia",
                        relevance_score=0.62,
                        quality_score=0.58,
                        tool=ToolName.WIKIPEDIA_SEARCH,
                    )
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                continue
        return results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.5, max=4),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        reraise=True,
    )
    def fetch_url(self, url: str) -> list[Source]:
        validate_public_url(url)
        response = self._get_public(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            raise ValueError(f"unsupported content type: {content_type}")
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "nav", "footer", "form", "noscript"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else url
        text, suspicious = sanitize_untrusted_text(soup.get_text(" ", strip=True))
        return [
            Source(
                title=title[:300],
                url=str(response.url),
                snippet=text,
                publisher=urlparse(str(response.url)).hostname,
                relevance_score=0.7 if text else 0.1,
                quality_score=max(
                    0.2, _domain_quality(str(response.url)) - (0.2 if suspicious else 0)
                ),
                tool=ToolName.FETCH_URL,
            )
        ]

    def _get_public(self, url: str) -> httpx.Response:
        """Follow only a few redirects and re-validate every destination for SSRF safety."""
        current_url = url
        for _ in range(4):
            validate_public_url(current_url)
            response = self.client.get(current_url)
            if not response.is_redirect:
                return response
            location = response.headers.get("location")
            if not location:
                raise ValueError("redirect response has no Location header")
            current_url = urljoin(str(response.url), location)
        raise ValueError("too many redirects while fetching URL")


def _domain_quality(url: str) -> float:
    host = (urlparse(url).hostname or "").lower()
    if re.search(r"\.(gov|edu)(\.|$)", host) or host.endswith(".org"):
        return 0.85
    if any(part in host for part in ("docs.", "developer.", "research.")):
        return 0.8
    return 0.6
