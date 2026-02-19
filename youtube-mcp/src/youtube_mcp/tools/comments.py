"""YouTube Comments tools for reading, replying, and moderating comments."""

from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..auth import get_credentials


def list_comments(
    video_id: str,
    max_results: int = 20,
    order: str = "time",
) -> list[dict]:
    """List top-level comments on a video.

    Args:
        video_id: YouTube video ID
        max_results: Maximum number of comment threads to return (1-100)
        order: Sort order ('time' for newest first, 'relevance' for top comments)

    Returns:
        List of comment dicts with id, author, text, likes, published_at, reply_count
    """
    max_results = max(1, min(100, max_results))
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=max_results,
        order=order,
        textFormat="plainText",
    ).execute()

    comments = []
    for item in response.get("items", []):
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "comment_id": item["snippet"]["topLevelComment"]["id"],
            "thread_id": item["id"],
            "author": snippet["authorDisplayName"],
            "author_channel_id": snippet.get("authorChannelId", {}).get("value", ""),
            "text": snippet["textDisplay"],
            "like_count": snippet.get("likeCount", 0),
            "published_at": snippet["publishedAt"],
            "updated_at": snippet.get("updatedAt", snippet["publishedAt"]),
            "reply_count": item["snippet"]["totalReplyCount"],
        })

    return comments


def reply_to_comment(
    comment_id: str,
    text: str,
) -> dict:
    """Reply to a YouTube comment.

    Args:
        comment_id: The parent comment ID to reply to
        text: Reply text (max 10000 characters)

    Returns:
        Dict with reply details
    """
    text = text[:10000]
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.comments().insert(
        part="snippet",
        body={
            "snippet": {
                "parentId": comment_id,
                "textOriginal": text,
            }
        },
    ).execute()

    snippet = response["snippet"]
    return {
        "reply_id": response["id"],
        "parent_id": comment_id,
        "author": snippet["authorDisplayName"],
        "text": snippet["textDisplay"],
        "published_at": snippet["publishedAt"],
    }


def get_comment_replies(
    comment_id: str,
    max_results: int = 20,
) -> list[dict]:
    """Get replies to a specific comment.

    Args:
        comment_id: The parent comment thread ID
        max_results: Maximum number of replies to return (1-100)

    Returns:
        List of reply dicts
    """
    max_results = max(1, min(100, max_results))
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.comments().list(
        part="snippet",
        parentId=comment_id,
        maxResults=max_results,
        textFormat="plainText",
    ).execute()

    replies = []
    for item in response.get("items", []):
        snippet = item["snippet"]
        replies.append({
            "reply_id": item["id"],
            "parent_id": comment_id,
            "author": snippet["authorDisplayName"],
            "author_channel_id": snippet.get("authorChannelId", {}).get("value", ""),
            "text": snippet["textDisplay"],
            "like_count": snippet.get("likeCount", 0),
            "published_at": snippet["publishedAt"],
        })

    return replies


def post_comment(
    video_id: str,
    text: str,
) -> dict:
    """Post a new top-level comment on a video.

    Args:
        video_id: YouTube video ID
        text: Comment text (max 10000 characters)

    Returns:
        Dict with comment details
    """
    text = text[:10000]
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": text,
                    }
                },
            }
        },
    ).execute()

    snippet = response["snippet"]["topLevelComment"]["snippet"]
    return {
        "comment_id": response["snippet"]["topLevelComment"]["id"],
        "thread_id": response["id"],
        "video_id": video_id,
        "author": snippet["authorDisplayName"],
        "text": snippet["textDisplay"],
        "published_at": snippet["publishedAt"],
    }


def moderate_comment(
    comment_id: str,
    moderation_status: str = "published",
    ban_author: bool = False,
) -> dict:
    """Set the moderation status of a comment.

    Args:
        comment_id: The comment ID to moderate
        moderation_status: One of 'published', 'heldForReview', 'rejected'
        ban_author: If True, also ban the comment author (only with 'rejected')

    Returns:
        Dict confirming the action
    """
    valid_statuses = {"published", "heldForReview", "rejected"}
    if moderation_status not in valid_statuses:
        raise ValueError(f"Invalid moderation status: {moderation_status}. Must be one of: {valid_statuses}")

    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    youtube.comments().setModerationStatus(
        id=comment_id,
        moderationStatus=moderation_status,
        banAuthor=ban_author,
    ).execute()

    return {
        "comment_id": comment_id,
        "moderation_status": moderation_status,
        "ban_author": ban_author,
        "success": True,
    }


def list_held_comments(
    video_id: Optional[str] = None,
    max_results: int = 20,
) -> list[dict]:
    """List comments held for review.

    Args:
        video_id: YouTube video ID (optional, if omitted gets all held comments)
        max_results: Maximum number of comments to return (1-100)

    Returns:
        List of comment dicts held for review
    """
    max_results = max(1, min(100, max_results))
    credentials = get_credentials()
    youtube = build("youtube", "v3", credentials=credentials)

    kwargs = {
        "part": "snippet",
        "moderationStatus": "heldForReview",
        "maxResults": max_results,
        "textFormat": "plainText",
    }

    if video_id:
        kwargs["videoId"] = video_id
    else:
        kwargs["allThreadsRelatedToChannelId"] = _get_channel_id(youtube)

    response = youtube.commentThreads().list(**kwargs).execute()

    comments = []
    for item in response.get("items", []):
        snippet = item["snippet"]["topLevelComment"]["snippet"]
        comments.append({
            "comment_id": item["snippet"]["topLevelComment"]["id"],
            "thread_id": item["id"],
            "video_id": item["snippet"].get("videoId", ""),
            "author": snippet["authorDisplayName"],
            "author_channel_id": snippet.get("authorChannelId", {}).get("value", ""),
            "text": snippet["textDisplay"],
            "like_count": snippet.get("likeCount", 0),
            "published_at": snippet["publishedAt"],
            "reply_count": item["snippet"]["totalReplyCount"],
        })

    return comments


def _get_channel_id(youtube) -> str:
    """Get the authenticated user's channel ID."""
    response = youtube.channels().list(part="id", mine=True).execute()
    if not response.get("items"):
        raise ValueError("No channel found for authenticated user")
    return response["items"][0]["id"]
