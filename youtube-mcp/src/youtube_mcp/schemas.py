"""Pydantic schemas for YouTube MCP Server."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class PrivacyStatus(str, Enum):
    """YouTube video privacy status."""
    PUBLIC = "public"
    PRIVATE = "private"
    UNLISTED = "unlisted"


class VideoOrder(str, Enum):
    """Order for listing videos."""
    DATE = "date"
    RATING = "rating"
    VIEW_COUNT = "viewCount"
    TITLE = "title"


class AnalyticsMetric(str, Enum):
    """Metrics for top videos analysis."""
    VIEWS = "views"
    WATCH_TIME = "estimatedMinutesWatched"
    LIKES = "likes"
    COMMENTS = "comments"


class CaptionFormat(str, Enum):
    """Caption download format."""
    SRT = "srt"
    SBV = "sbv"
    VTT = "vtt"


class SearchResultType(str, Enum):
    """Type of search result."""
    VIDEO = "video"
    CHANNEL = "channel"
    PLAYLIST = "playlist"


class SearchOrder(str, Enum):
    """Order for search results."""
    RELEVANCE = "relevance"
    DATE = "date"
    VIEW_COUNT = "viewCount"
    RATING = "rating"


# Upload schemas
class UploadVideoParams(BaseModel):
    """Parameters for uploading a video."""
    file_path: str = Field(..., description="Path to the video file")
    title: str = Field(..., description="Video title (max 100 characters)")
    description: str = Field(default="", description="Video description (max 5000 characters)")
    tags: list[str] = Field(default_factory=list, description="Video tags")
    privacy: PrivacyStatus = Field(default=PrivacyStatus.PRIVATE, description="Privacy status")
    thumbnail_path: Optional[str] = Field(default=None, description="Path to thumbnail image")
    category_id: str = Field(default="22", description="YouTube category ID (default: People & Blogs)")


class UploadVideoResult(BaseModel):
    """Result of video upload."""
    video_id: str
    url: str
    title: str
    privacy: str


# Management schemas
class UpdateVideoParams(BaseModel):
    """Parameters for updating a video."""
    video_id: str = Field(..., description="YouTube video ID")
    title: Optional[str] = Field(default=None, description="New title")
    description: Optional[str] = Field(default=None, description="New description")
    tags: Optional[list[str]] = Field(default=None, description="New tags")
    privacy: Optional[PrivacyStatus] = Field(default=None, description="New privacy status")
    category_id: Optional[str] = Field(default=None, description="New category ID")


class ListVideosParams(BaseModel):
    """Parameters for listing videos."""
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    order: VideoOrder = Field(default=VideoOrder.DATE, description="Sort order")


class VideoInfo(BaseModel):
    """Information about a video."""
    video_id: str
    title: str
    description: str
    published_at: str
    privacy: str
    view_count: int
    like_count: int
    comment_count: int
    duration: str
    thumbnail_url: str


# Analytics schemas
class ChannelStats(BaseModel):
    """Channel statistics."""
    channel_id: str
    title: str
    subscriber_count: int
    view_count: int
    video_count: int
    created_at: str


class VideoAnalytics(BaseModel):
    """Analytics for a specific video."""
    video_id: str
    views: int
    estimated_minutes_watched: float
    average_view_duration: float
    likes: int
    dislikes: int
    comments: int
    shares: int
    subscribers_gained: int
    subscribers_lost: int


class AudienceRetention(BaseModel):
    """Audience retention data."""
    video_id: str
    average_view_duration_seconds: float
    average_view_percentage: float
    retention_data: list[dict]  # List of {elapsed_ratio, retention_percentage}


class TrafficSource(BaseModel):
    """Traffic source data."""
    source_type: str
    views: int
    watch_time_minutes: float
    percentage: float


class Demographics(BaseModel):
    """Audience demographics."""
    age_groups: list[dict]  # {age_group, percentage}
    gender: dict  # {male, female, other}
    top_countries: list[dict]  # {country, percentage}


class TopVideo(BaseModel):
    """Top performing video."""
    video_id: str
    title: str
    metric_value: float
    views: int
    watch_time_minutes: float
    likes: int
    comments: int


class RevenueReport(BaseModel):
    """Revenue report (for monetized channels)."""
    estimated_revenue: float
    estimated_ad_revenue: float
    cpm: float
    rpm: float
    playback_based_cpm: float


# Playlist schemas
class PlaylistInfo(BaseModel):
    """Information about a playlist."""
    playlist_id: str
    title: str
    description: str
    privacy: str
    published_at: str
    item_count: int
    thumbnail_url: str


class PlaylistItemInfo(BaseModel):
    """Information about a playlist item."""
    playlist_item_id: str
    video_id: str
    title: str
    description: str
    position: int
    added_at: str
    thumbnail_url: str


# Caption schemas
class CaptionInfo(BaseModel):
    """Information about a caption track."""
    caption_id: str
    video_id: str
    language: str
    name: str
    is_auto_synced: bool
    is_draft: bool
    track_kind: str
    last_updated: str


# Search schemas
class SearchResult(BaseModel):
    """A search result."""
    result_type: str
    resource_id: str
    title: str
    description: str
    channel_title: str
    channel_id: str
    published_at: str
    thumbnail_url: str


# Extended analytics schemas
class DeviceStats(BaseModel):
    """Device type analytics."""
    device_type: str
    views: int
    estimated_minutes_watched: float
    percentage: float


class PlaybackLocation(BaseModel):
    """Playback location analytics."""
    playback_location_type: str
    views: int
    estimated_minutes_watched: float
    percentage: float


class ContentPerformance(BaseModel):
    """Content performance analytics."""
    video_id: str
    title: str
    views: int
    estimated_minutes_watched: float
    average_view_duration: float
    likes: int
    comments: int
    shares: int
    subscribers_gained: int
