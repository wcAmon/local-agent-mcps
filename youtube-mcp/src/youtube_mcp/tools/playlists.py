"""Playlist management tools for YouTube MCP Server."""

from typing import Optional

from googleapiclient.discovery import build

from ..auth import get_credentials
from ..schemas import PlaylistInfo, PlaylistItemInfo, PrivacyStatus


def _get_youtube_service():
    """Get YouTube Data API service."""
    return build("youtube", "v3", credentials=get_credentials())


def _parse_playlist(item: dict) -> PlaylistInfo:
    """Parse a playlist API response item into PlaylistInfo."""
    snippet = item["snippet"]
    status = item.get("status", {})
    content = item.get("contentDetails", {})
    return PlaylistInfo(
        playlist_id=item["id"],
        title=snippet["title"],
        description=snippet.get("description", ""),
        privacy=status.get("privacyStatus", "private"),
        published_at=snippet.get("publishedAt", ""),
        item_count=int(content.get("itemCount", 0)),
        thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
    )


def list_playlists(max_results: int = 25) -> list[PlaylistInfo]:
    """List playlists owned by the authenticated user.

    Args:
        max_results: Maximum number of playlists to return (1-50)

    Returns:
        List of PlaylistInfo objects
    """
    max_results = max(1, min(50, max_results))
    youtube = _get_youtube_service()

    response = youtube.playlists().list(
        part="snippet,status,contentDetails",
        mine=True,
        maxResults=max_results,
    ).execute()

    return [_parse_playlist(item) for item in response.get("items", [])]


def create_playlist(
    title: str,
    description: str = "",
    privacy: str = "private",
) -> PlaylistInfo:
    """Create a new playlist.

    Args:
        title: Playlist title (max 150 characters)
        description: Playlist description (max 5000 characters)
        privacy: Privacy status (public, private, unlisted)

    Returns:
        PlaylistInfo for the created playlist
    """
    title = title[:150]
    description = description[:5000]

    try:
        privacy_status = PrivacyStatus(privacy.lower())
    except ValueError:
        privacy_status = PrivacyStatus.PRIVATE

    youtube = _get_youtube_service()

    response = youtube.playlists().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": title,
                "description": description,
            },
            "status": {
                "privacyStatus": privacy_status.value,
            },
        },
    ).execute()

    return _parse_playlist(response)


def update_playlist(
    playlist_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    privacy: Optional[str] = None,
) -> PlaylistInfo:
    """Update a playlist's metadata.

    Args:
        playlist_id: YouTube playlist ID
        title: New title (optional)
        description: New description (optional)
        privacy: New privacy status (optional)

    Returns:
        Updated PlaylistInfo
    """
    youtube = _get_youtube_service()

    # Fetch current data
    current = youtube.playlists().list(
        part="snippet,status,contentDetails",
        id=playlist_id,
    ).execute()

    if not current.get("items"):
        raise ValueError(f"Playlist not found: {playlist_id}")

    item = current["items"][0]
    snippet = item["snippet"]
    status = item["status"]

    body = {
        "id": playlist_id,
        "snippet": {
            "title": (title if title is not None else snippet["title"])[:150],
            "description": (description if description is not None else snippet.get("description", ""))[:5000],
        },
        "status": {
            "privacyStatus": privacy if privacy is not None else status["privacyStatus"],
        },
    }

    response = youtube.playlists().update(
        part="snippet,status,contentDetails",
        body=body,
    ).execute()

    return _parse_playlist(response)


def delete_playlist(playlist_id: str) -> bool:
    """Delete a playlist.

    Args:
        playlist_id: YouTube playlist ID

    Returns:
        True if deletion was successful
    """
    youtube = _get_youtube_service()
    youtube.playlists().delete(id=playlist_id).execute()
    return True


def list_playlist_items(
    playlist_id: str,
    max_results: int = 25,
) -> list[PlaylistItemInfo]:
    """List items in a playlist.

    Args:
        playlist_id: YouTube playlist ID
        max_results: Maximum number of items to return (1-50)

    Returns:
        List of PlaylistItemInfo objects
    """
    max_results = max(1, min(50, max_results))
    youtube = _get_youtube_service()

    response = youtube.playlistItems().list(
        part="snippet,contentDetails",
        playlistId=playlist_id,
        maxResults=max_results,
    ).execute()

    items = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        items.append(PlaylistItemInfo(
            playlist_item_id=item["id"],
            video_id=snippet["resourceId"]["videoId"],
            title=snippet["title"],
            description=snippet.get("description", ""),
            position=snippet["position"],
            added_at=snippet.get("publishedAt", ""),
            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        ))

    return items


def add_to_playlist(
    playlist_id: str,
    video_id: str,
    position: Optional[int] = None,
) -> PlaylistItemInfo:
    """Add a video to a playlist.

    Args:
        playlist_id: YouTube playlist ID
        video_id: YouTube video ID to add
        position: Position in playlist (0-based, optional — appends if omitted)

    Returns:
        PlaylistItemInfo for the added item
    """
    youtube = _get_youtube_service()

    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {
                "kind": "youtube#video",
                "videoId": video_id,
            },
        },
    }

    if position is not None:
        body["snippet"]["position"] = max(0, position)

    response = youtube.playlistItems().insert(
        part="snippet",
        body=body,
    ).execute()

    snippet = response["snippet"]
    return PlaylistItemInfo(
        playlist_item_id=response["id"],
        video_id=snippet["resourceId"]["videoId"],
        title=snippet["title"],
        description=snippet.get("description", ""),
        position=snippet["position"],
        added_at=snippet.get("publishedAt", ""),
        thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
    )


def remove_from_playlist(playlist_item_id: str) -> bool:
    """Remove an item from a playlist.

    Args:
        playlist_item_id: The playlist item ID (from list_playlist_items)

    Returns:
        True if removal was successful
    """
    youtube = _get_youtube_service()
    youtube.playlistItems().delete(id=playlist_item_id).execute()
    return True
