"""Video upload tools for YouTube MCP Server."""

import os
from pathlib import Path
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from ..auth import get_credentials
from ..schemas import PrivacyStatus, UploadVideoResult


def upload_video(
    file_path: str,
    title: str,
    description: str = "",
    tags: Optional[list[str]] = None,
    privacy: str = "private",
    category_id: str = "22",
    thumbnail_path: Optional[str] = None,
) -> UploadVideoResult:
    """Upload a video to YouTube.

    Args:
        file_path: Path to the video file
        title: Video title (max 100 characters)
        description: Video description (max 5000 characters)
        tags: List of tags
        privacy: Privacy status (public, private, unlisted)
        category_id: YouTube category ID (default: 22 = People & Blogs)
        thumbnail_path: Optional path to thumbnail image

    Returns:
        UploadVideoResult with video_id and URL

    Raises:
        FileNotFoundError: If video file doesn't exist
        HttpError: If upload fails
    """
    # Validate file exists
    video_path = Path(file_path).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {file_path}")

    # Validate privacy status
    try:
        privacy_status = PrivacyStatus(privacy.lower())
    except ValueError:
        raise ValueError(f"Invalid privacy status: {privacy}. Must be one of: public, private, unlisted")

    # Truncate title and description to YouTube limits
    title = title[:100]
    description = description[:5000]
    tags = tags or []

    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    # Prepare video metadata
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status.value,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Create media upload (resumable for large files)
    media = MediaFileUpload(
        str(video_path),
        chunksize=1024 * 1024,  # 1MB chunks
        resumable=True,
    )

    # Execute upload
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            # Progress reporting could be added here
            pass

    video_id = response["id"]

    # Set thumbnail if provided
    if thumbnail_path:
        try:
            set_thumbnail(video_id, thumbnail_path)
        except Exception as e:
            # Log but don't fail the upload
            pass

    # Clean up source video file after successful upload
    try:
        video_path.unlink()
    except OSError:
        pass  # Best-effort cleanup

    return UploadVideoResult(
        video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        title=response["snippet"]["title"],
        privacy=response["status"]["privacyStatus"],
    )


def set_thumbnail(video_id: str, thumbnail_path: str) -> bool:
    """Set a custom thumbnail for a video.

    Args:
        video_id: YouTube video ID
        thumbnail_path: Path to thumbnail image (must be JPG, PNG, or GIF, max 2MB)

    Returns:
        True if successful

    Raises:
        FileNotFoundError: If thumbnail file doesn't exist
        HttpError: If thumbnail upload fails
    """
    path = Path(thumbnail_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Thumbnail file not found: {thumbnail_path}")

    # Validate file extension
    valid_extensions = {".jpg", ".jpeg", ".png", ".gif"}
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"Invalid thumbnail format. Must be one of: {valid_extensions}")

    # Check file size (max 2MB)
    if path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Thumbnail file must be less than 2MB")

    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    media = MediaFileUpload(str(path), mimetype=f"image/{path.suffix[1:].lower()}")

    youtube.thumbnails().set(
        videoId=video_id,
        media_body=media,
    ).execute()

    return True
