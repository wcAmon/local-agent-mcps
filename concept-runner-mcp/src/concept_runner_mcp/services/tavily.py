"""Tavily web search and extract service."""

import asyncio
import logging
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")


def _get_client():
    from tavily import TavilyClient
    return TavilyClient(api_key=TAVILY_API_KEY)


async def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via Tavily. Returns list of {title, url, content}."""
    def _search():
        client = _get_client()
        response = client.search(query=query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
            })
        return results

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        logger.exception(f"Tavily search failed: {e}")
        return []


async def search_with_content(query: str, max_results: int = 5) -> list[dict]:
    """Search with include_raw_content=True. Returns list of {title, url, content, raw_content, domain}."""
    def _search():
        client = _get_client()
        response = client.search(
            query=query,
            max_results=max_results,
            include_raw_content=True,
        )
        results = []
        for r in response.get("results", []):
            url = r.get("url", "")
            domain = urlparse(url).netloc if url else ""
            results.append({
                "title": r.get("title", ""),
                "url": url,
                "content": r.get("content", ""),
                "raw_content": r.get("raw_content", ""),
                "domain": domain,
            })
        return results

    try:
        return await asyncio.to_thread(_search)
    except Exception as e:
        logger.exception(f"Tavily search_with_content failed: {e}")
        return []


async def extract_urls(urls: list[str], extract_depth: str = "basic") -> list[dict]:
    """Extract full content from URLs via Tavily Extract API.
    Returns list of {url, raw_content}. Max 20 URLs per call.
    Basic: 1 credit/5 URLs. Advanced: 2 credits/5 URLs.
    """
    if not urls:
        return []

    def _extract():
        client = _get_client()
        response = client.extract(
            urls=urls[:20],
            extract_depth=extract_depth,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "url": r.get("url", ""),
                "raw_content": r.get("raw_content", ""),
            })
        return results

    try:
        return await asyncio.to_thread(_extract)
    except Exception as e:
        logger.exception(f"Tavily extract failed: {e}")
        return []
