"""YouTube search tools for YouTube MCP Server."""

from typing import Optional

from googleapiclient.discovery import build

from ..auth import get_credentials
from ..schemas import SearchResult, SearchResultType, SearchOrder


def _get_youtube_service():
    """Get YouTube Data API service."""
    return build("youtube", "v3", credentials=get_credentials())


def search(
    query: str,
    result_type: str = "video",
    max_results: int = 10,
    order: str = "relevance",
    channel_id: Optional[str] = None,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None,
) -> list[SearchResult]:
    """Search YouTube for videos, channels, or playlists.

    Note: Each search call costs 100 quota units.

    Args:
        query: Search query string
        result_type: Type of results — video, channel, or playlist
        max_results: Maximum number of results (1-50)
        order: Sort order — relevance, date, viewCount, rating
        channel_id: Restrict to a specific channel (optional)
        published_after: Filter by publish date (RFC 3339, e.g. '2024-01-01T00:00:00Z')
        published_before: Filter by publish date (RFC 3339)

    Returns:
        List of SearchResult objects
    """
    max_results = max(1, min(50, max_results))

    try:
        search_type = SearchResultType(result_type.lower())
    except ValueError:
        search_type = SearchResultType.VIDEO

    try:
        search_order = SearchOrder(order)
    except ValueError:
        search_order = SearchOrder.RELEVANCE

    youtube = _get_youtube_service()

    kwargs = {
        "part": "snippet",
        "q": query,
        "type": search_type.value,
        "maxResults": max_results,
        "order": search_order.value,
    }

    if channel_id:
        kwargs["channelId"] = channel_id
    if published_after:
        kwargs["publishedAfter"] = published_after
    if published_before:
        kwargs["publishedBefore"] = published_before

    response = youtube.search().list(**kwargs).execute()

    results = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        item_id = item["id"]

        # Extract resource ID based on type
        if "videoId" in item_id:
            resource_id = item_id["videoId"]
            rtype = "video"
        elif "channelId" in item_id:
            resource_id = item_id["channelId"]
            rtype = "channel"
        elif "playlistId" in item_id:
            resource_id = item_id["playlistId"]
            rtype = "playlist"
        else:
            resource_id = ""
            rtype = item_id.get("kind", "unknown")

        results.append(SearchResult(
            result_type=rtype,
            resource_id=resource_id,
            title=snippet.get("title", ""),
            description=snippet.get("description", ""),
            channel_title=snippet.get("channelTitle", ""),
            channel_id=snippet.get("channelId", ""),
            published_at=snippet.get("publishedAt", ""),
            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        ))

    return results
