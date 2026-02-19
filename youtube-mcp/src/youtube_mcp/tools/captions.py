"""Caption management tools for YouTube MCP Server."""

import io
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload

from ..auth import get_credentials
from ..schemas import CaptionInfo, CaptionFormat


def _get_youtube_service():
    """Get YouTube Data API service."""
    return build("youtube", "v3", credentials=get_credentials())


def _parse_caption(item: dict, video_id: str) -> CaptionInfo:
    """Parse a caption API response item into CaptionInfo."""
    snippet = item["snippet"]
    return CaptionInfo(
        caption_id=item["id"],
        video_id=video_id,
        language=snippet.get("language", ""),
        name=snippet.get("name", ""),
        is_auto_synced=snippet.get("isAutoSynced", False),
        is_draft=snippet.get("isDraft", False),
        track_kind=snippet.get("trackKind", "standard"),
        last_updated=snippet.get("lastUpdated", ""),
    )


def list_captions(video_id: str) -> list[CaptionInfo]:
    """List caption tracks for a video.

    Args:
        video_id: YouTube video ID

    Returns:
        List of CaptionInfo objects
    """
    youtube = _get_youtube_service()

    response = youtube.captions().list(
        part="snippet",
        videoId=video_id,
    ).execute()

    return [_parse_caption(item, video_id) for item in response.get("items", [])]


def upload_caption(
    video_id: str,
    language: str,
    name: str = "",
    body: str = "",
    file_path: Optional[str] = None,
    is_draft: bool = False,
) -> CaptionInfo:
    """Upload a caption track for a video.

    Provide caption content via either `body` (raw caption text) or `file_path`.

    Args:
        video_id: YouTube video ID
        language: BCP-47 language code (e.g., 'en', 'es', 'fr')
        name: Caption track name (e.g., 'English CC')
        body: Caption content as string (SRT, SBV, or VTT format)
        file_path: Path to caption file (alternative to body)
        is_draft: Whether the caption is a draft

    Returns:
        CaptionInfo for the uploaded caption
    """
    youtube = _get_youtube_service()

    caption_body = {
        "snippet": {
            "videoId": video_id,
            "language": language,
            "name": name,
            "isDraft": is_draft,
        },
    }

    if file_path:
        media = MediaFileUpload(file_path, mimetype="application/octet-stream")
    elif body:
        media = MediaIoBaseUpload(
            io.BytesIO(body.encode("utf-8")),
            mimetype="application/octet-stream",
        )
    else:
        raise ValueError("Either body or file_path must be provided")

    response = youtube.captions().insert(
        part="snippet",
        body=caption_body,
        media_body=media,
    ).execute()

    return _parse_caption(response, video_id)


def update_caption(
    caption_id: str,
    video_id: str = "",
    name: Optional[str] = None,
    is_draft: Optional[bool] = None,
    body: Optional[str] = None,
    file_path: Optional[str] = None,
) -> CaptionInfo:
    """Update an existing caption track.

    Args:
        caption_id: Caption track ID
        video_id: YouTube video ID (for response only)
        name: New caption track name (optional)
        is_draft: New draft status (optional)
        body: New caption content as string (optional)
        file_path: Path to new caption file (optional)

    Returns:
        Updated CaptionInfo
    """
    youtube = _get_youtube_service()

    caption_body = {
        "id": caption_id,
    }

    snippet = {}
    if name is not None:
        snippet["name"] = name
    if is_draft is not None:
        snippet["isDraft"] = is_draft

    if snippet:
        caption_body["snippet"] = snippet

    kwargs = {
        "part": "snippet",
        "body": caption_body,
    }

    if file_path:
        kwargs["media_body"] = MediaFileUpload(file_path, mimetype="application/octet-stream")
    elif body is not None:
        kwargs["media_body"] = MediaIoBaseUpload(
            io.BytesIO(body.encode("utf-8")),
            mimetype="application/octet-stream",
        )

    response = youtube.captions().update(**kwargs).execute()

    return _parse_caption(response, video_id)


def download_caption(
    caption_id: str,
    fmt: str = "srt",
) -> str:
    """Download a caption track's content.

    Args:
        caption_id: Caption track ID
        fmt: Download format — srt, sbv, or vtt (default: srt)

    Returns:
        Caption content as string
    """
    try:
        caption_format = CaptionFormat(fmt.lower())
    except ValueError:
        caption_format = CaptionFormat.SRT

    youtube = _get_youtube_service()

    response = youtube.captions().download(
        id=caption_id,
        tfmt=caption_format.value,
    ).execute()

    if isinstance(response, bytes):
        return response.decode("utf-8")
    return str(response)


def delete_caption(caption_id: str) -> bool:
    """Delete a caption track.

    Args:
        caption_id: Caption track ID

    Returns:
        True if deletion was successful
    """
    youtube = _get_youtube_service()
    youtube.captions().delete(id=caption_id).execute()
    return True
