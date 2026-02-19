"""Video management tools for YouTube MCP Server."""

from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..auth import get_credentials
from ..schemas import PrivacyStatus, VideoInfo, VideoOrder


def get_video(video_id: str) -> VideoInfo:
    """Get detailed information about a specific video.

    Args:
        video_id: YouTube video ID

    Returns:
        VideoInfo with full video details

    Raises:
        HttpError: If video not found or API error
    """
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.videos().list(
        part="snippet,status,statistics,contentDetails",
        id=video_id,
    ).execute()

    if not response.get("items"):
        raise ValueError(f"Video not found: {video_id}")

    item = response["items"][0]
    snippet = item["snippet"]
    status = item["status"]
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})

    return VideoInfo(
        video_id=item["id"],
        title=snippet["title"],
        description=snippet.get("description", ""),
        published_at=snippet["publishedAt"],
        privacy=status["privacyStatus"],
        view_count=int(stats.get("viewCount", 0)),
        like_count=int(stats.get("likeCount", 0)),
        comment_count=int(stats.get("commentCount", 0)),
        duration=content.get("duration", "PT0S"),
        thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
    )


def list_videos(
    max_results: int = 10,
    order: str = "date",
) -> list[VideoInfo]:
    """List videos from the authenticated user's channel.

    Args:
        max_results: Maximum number of videos to return (1-50)
        order: Sort order (date, rating, viewCount, title)

    Returns:
        List of VideoInfo objects
    """
    max_results = max(1, min(50, max_results))

    try:
        video_order = VideoOrder(order)
    except ValueError:
        video_order = VideoOrder.DATE

    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    # First, get the channel's upload playlist
    channels_response = youtube.channels().list(
        part="contentDetails",
        mine=True,
    ).execute()

    if not channels_response.get("items"):
        return []

    uploads_playlist_id = channels_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Get videos from uploads playlist
    playlist_response = youtube.playlistItems().list(
        part="snippet",
        playlistId=uploads_playlist_id,
        maxResults=max_results,
    ).execute()

    if not playlist_response.get("items"):
        return []

    # Get video IDs
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in playlist_response["items"]]

    # Get full video details
    videos_response = youtube.videos().list(
        part="snippet,status,statistics,contentDetails",
        id=",".join(video_ids),
    ).execute()

    videos = []
    for item in videos_response.get("items", []):
        snippet = item["snippet"]
        status = item["status"]
        stats = item.get("statistics", {})
        content = item.get("contentDetails", {})

        videos.append(VideoInfo(
            video_id=item["id"],
            title=snippet["title"],
            description=snippet.get("description", ""),
            published_at=snippet["publishedAt"],
            privacy=status["privacyStatus"],
            view_count=int(stats.get("viewCount", 0)),
            like_count=int(stats.get("likeCount", 0)),
            comment_count=int(stats.get("commentCount", 0)),
            duration=content.get("duration", "PT0S"),
            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        ))

    # Sort based on order
    if video_order == VideoOrder.VIEW_COUNT:
        videos.sort(key=lambda v: v.view_count, reverse=True)
    elif video_order == VideoOrder.RATING:
        videos.sort(key=lambda v: v.like_count, reverse=True)
    elif video_order == VideoOrder.TITLE:
        videos.sort(key=lambda v: v.title.lower())
    # DATE is default (already sorted by YouTube)

    return videos


def update_video(
    video_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    privacy: Optional[str] = None,
    category_id: Optional[str] = None,
) -> VideoInfo:
    """Update video metadata.

    Args:
        video_id: YouTube video ID
        title: New title (optional)
        description: New description (optional)
        tags: New tags (optional)
        privacy: New privacy status (optional)
        category_id: New category ID (optional)

    Returns:
        Updated VideoInfo

    Raises:
        HttpError: If update fails
    """
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    # First, get current video data
    current = youtube.videos().list(
        part="snippet,status",
        id=video_id,
    ).execute()

    if not current.get("items"):
        raise ValueError(f"Video not found: {video_id}")

    item = current["items"][0]
    snippet = item["snippet"]
    status = item["status"]

    # Prepare update body
    body = {
        "id": video_id,
        "snippet": {
            "title": title if title is not None else snippet["title"],
            "description": description if description is not None else snippet.get("description", ""),
            "tags": tags if tags is not None else snippet.get("tags", []),
            "categoryId": category_id if category_id is not None else snippet["categoryId"],
        },
        "status": {
            "privacyStatus": privacy if privacy is not None else status["privacyStatus"],
        },
    }

    # Truncate to YouTube limits
    body["snippet"]["title"] = body["snippet"]["title"][:100]
    body["snippet"]["description"] = body["snippet"]["description"][:5000]

    # Execute update
    response = youtube.videos().update(
        part="snippet,status",
        body=body,
    ).execute()

    # Get updated video info
    return get_video(video_id)


def set_video_localization(
    video_id: str,
    language: str,
    localized_title: str,
    localized_description: str,
) -> dict:
    """Add or update a localized title and description for a video.

    Args:
        video_id: YouTube video ID
        language: BCP-47 language code (e.g., 'es', 'fr', 'de', 'ja', 'pt', 'hi', 'tl')
        localized_title: Translated title (max 100 characters)
        localized_description: Translated description (max 5000 characters)

    Returns:
        Dict with video_id, language, and the localization that was set

    Raises:
        HttpError: If update fails
    """
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    # Get current video data including existing localizations
    current = youtube.videos().list(
        part="snippet,localizations",
        id=video_id,
    ).execute()

    if not current.get("items"):
        raise ValueError(f"Video not found: {video_id}")

    item = current["items"][0]
    snippet = item["snippet"]

    # Preserve existing localizations, add/update the new one
    localizations = item.get("localizations", {})
    localizations[language] = {
        "title": localized_title[:100],
        "description": localized_description[:5000],
    }

    # Set default language if not already set
    if "defaultLanguage" not in snippet:
        snippet["defaultLanguage"] = "en"

    # Build update body
    body = {
        "id": video_id,
        "snippet": {
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "tags": snippet.get("tags", []),
            "categoryId": snippet["categoryId"],
            "defaultLanguage": snippet.get("defaultLanguage", "en"),
        },
        "localizations": localizations,
    }

    # Execute update
    youtube.videos().update(
        part="snippet,localizations",
        body=body,
    ).execute()

    return {
        "video_id": video_id,
        "language": language,
        "localized_title": localized_title[:100],
        "localized_description": localized_description[:5000],
        "total_localizations": len(localizations),
        "all_languages": list(localizations.keys()),
    }


def delete_video(video_id: str) -> bool:
    """Delete a video.

    Args:
        video_id: YouTube video ID

    Returns:
        True if deletion was successful

    Raises:
        HttpError: If deletion fails
    """
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    youtube.videos().delete(id=video_id).execute()
    return True
