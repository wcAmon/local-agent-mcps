"""Analytics tools for YouTube MCP Server."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build

from ..auth import get_credentials
from ..schemas import (
    ChannelStats,
    VideoAnalytics,
    AudienceRetention,
    TrafficSource,
    Demographics,
    TopVideo,
    RevenueReport,
    AnalyticsMetric,
    DeviceStats,
    PlaybackLocation,
    ContentPerformance,
)


def _get_youtube_service():
    """Get YouTube Data API service."""
    return build("youtube", "v3", credentials=get_credentials())


def _get_analytics_service():
    """Get YouTube Analytics API service."""
    return build("youtubeAnalytics", "v2", credentials=get_credentials())


def _get_channel_id() -> str:
    """Get the authenticated user's channel ID."""
    youtube = _get_youtube_service()
    response = youtube.channels().list(part="id", mine=True).execute()
    if not response.get("items"):
        raise ValueError("No channel found for authenticated user")
    return response["items"][0]["id"]


def get_channel_stats() -> ChannelStats:
    """Get channel statistics.

    Returns:
        ChannelStats with subscriber count, view count, video count, etc.
    """
    youtube = _get_youtube_service()

    response = youtube.channels().list(
        part="snippet,statistics",
        mine=True,
    ).execute()

    if not response.get("items"):
        raise ValueError("No channel found for authenticated user")

    item = response["items"][0]
    snippet = item["snippet"]
    stats = item["statistics"]

    return ChannelStats(
        channel_id=item["id"],
        title=snippet["title"],
        subscriber_count=int(stats.get("subscriberCount", 0)),
        view_count=int(stats.get("viewCount", 0)),
        video_count=int(stats.get("videoCount", 0)),
        created_at=snippet["publishedAt"],
    )


def get_video_analytics(
    video_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> VideoAnalytics:
    """Get analytics for a specific video.

    Args:
        video_id: YouTube video ID
        start_date: Start date (YYYY-MM-DD), defaults to 28 days ago
        end_date: End date (YYYY-MM-DD), defaults to today

    Returns:
        VideoAnalytics with views, watch time, likes, comments, etc.
    """
    analytics = _get_analytics_service()

    # Default date range: last 28 days
    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    response = analytics.reports().query(
        ids=f"channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes,dislikes,comments,shares,subscribersGained,subscribersLost",
        filters=f"video=={video_id}",
    ).execute()

    rows = response.get("rows", [[0] * 9])
    row = rows[0] if rows else [0] * 9

    return VideoAnalytics(
        video_id=video_id,
        views=int(row[0]),
        estimated_minutes_watched=float(row[1]),
        average_view_duration=float(row[2]),
        likes=int(row[3]),
        dislikes=int(row[4]),
        comments=int(row[5]),
        shares=int(row[6]),
        subscribers_gained=int(row[7]),
        subscribers_lost=int(row[8]),
    )


def get_audience_retention(
    video_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> AudienceRetention:
    """Get audience retention data for a video.

    Args:
        video_id: YouTube video ID
        start_date: Start date (YYYY-MM-DD), defaults to 28 days ago
        end_date: End date (YYYY-MM-DD), defaults to today

    Returns:
        AudienceRetention with retention curve data
    """
    analytics = _get_analytics_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    # Get average view duration and percentage
    summary_response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="averageViewDuration,averageViewPercentage",
        filters=f"video=={video_id}",
    ).execute()

    summary_row = summary_response.get("rows", [[0, 0]])[0]

    # Get retention curve (audienceWatchRatio by elapsedVideoTimeRatio)
    retention_response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="audienceWatchRatio",
        dimensions="elapsedVideoTimeRatio",
        filters=f"video=={video_id}",
        sort="elapsedVideoTimeRatio",
    ).execute()

    retention_data = []
    for row in retention_response.get("rows", []):
        retention_data.append({
            "elapsed_ratio": float(row[0]),
            "retention_percentage": float(row[1]) * 100,
        })

    return AudienceRetention(
        video_id=video_id,
        average_view_duration_seconds=float(summary_row[0]),
        average_view_percentage=float(summary_row[1]),
        retention_data=retention_data,
    )


def get_traffic_sources(
    video_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[TrafficSource]:
    """Get traffic source breakdown.

    Args:
        video_id: YouTube video ID (optional, if None gets channel-wide data)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of TrafficSource objects
    """
    analytics = _get_analytics_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    query_params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched",
        "dimensions": "insightTrafficSourceType",
        "sort": "-views",
    }

    if video_id:
        query_params["filters"] = f"video=={video_id}"

    response = analytics.reports().query(**query_params).execute()

    # Calculate total views for percentage
    total_views = sum(int(row[1]) for row in response.get("rows", []))

    sources = []
    for row in response.get("rows", []):
        source_type = row[0]
        views = int(row[1])
        watch_time = float(row[2])
        percentage = (views / total_views * 100) if total_views > 0 else 0

        sources.append(TrafficSource(
            source_type=source_type,
            views=views,
            watch_time_minutes=watch_time,
            percentage=round(percentage, 2),
        ))

    return sources


def get_demographics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Demographics:
    """Get audience demographics.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        Demographics with age, gender, and geographic distribution
    """
    analytics = _get_analytics_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    # Get age and gender breakdown
    age_gender_response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="viewerPercentage",
        dimensions="ageGroup,gender",
    ).execute()

    # Process age groups
    age_totals = {}
    gender_totals = {"male": 0, "female": 0, "user_specified": 0}

    for row in age_gender_response.get("rows", []):
        age_group = row[0]
        gender = row[1]
        percentage = float(row[2])

        # Aggregate by age group
        if age_group not in age_totals:
            age_totals[age_group] = 0
        age_totals[age_group] += percentage

        # Aggregate by gender
        if gender in gender_totals:
            gender_totals[gender] += percentage

    age_groups = [
        {"age_group": k, "percentage": round(v, 2)}
        for k, v in sorted(age_totals.items())
    ]

    # Get country breakdown
    country_response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views",
        dimensions="country",
        sort="-views",
        maxResults=10,
    ).execute()

    total_country_views = sum(int(row[1]) for row in country_response.get("rows", []))
    top_countries = []
    for row in country_response.get("rows", []):
        country = row[0]
        views = int(row[1])
        percentage = (views / total_country_views * 100) if total_country_views > 0 else 0
        top_countries.append({
            "country": country,
            "percentage": round(percentage, 2),
        })

    return Demographics(
        age_groups=age_groups,
        gender={
            "male": round(gender_totals["male"], 2),
            "female": round(gender_totals["female"], 2),
            "other": round(gender_totals["user_specified"], 2),
        },
        top_countries=top_countries,
    )


def get_top_videos(
    metric: str = "views",
    period_days: int = 28,
    limit: int = 10,
) -> list[TopVideo]:
    """Get top performing videos by a specific metric.

    Args:
        metric: Metric to sort by (views, estimatedMinutesWatched, likes, comments)
        period_days: Number of days to analyze
        limit: Maximum number of videos to return

    Returns:
        List of TopVideo objects
    """
    analytics = _get_analytics_service()
    youtube = _get_youtube_service()

    # Map friendly metric names
    metric_map = {
        "views": "views",
        "watchTime": "estimatedMinutesWatched",
        "watch_time": "estimatedMinutesWatched",
        "likes": "likes",
        "comments": "comments",
    }
    api_metric = metric_map.get(metric, "views")

    end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start_date = (datetime.now(timezone.utc) - timedelta(days=period_days)).strftime("%Y-%m-%d")

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics=f"views,estimatedMinutesWatched,likes,comments",
        dimensions="video",
        sort=f"-{api_metric}",
        maxResults=limit,
    ).execute()

    video_ids = [row[0] for row in response.get("rows", [])]
    if not video_ids:
        return []

    # Get video titles
    videos_response = youtube.videos().list(
        part="snippet",
        id=",".join(video_ids),
    ).execute()

    title_map = {
        item["id"]: item["snippet"]["title"]
        for item in videos_response.get("items", [])
    }

    # Map metrics index
    metric_index = {"views": 1, "estimatedMinutesWatched": 2, "likes": 3, "comments": 4}

    top_videos = []
    for row in response.get("rows", []):
        video_id = row[0]
        top_videos.append(TopVideo(
            video_id=video_id,
            title=title_map.get(video_id, "Unknown"),
            metric_value=float(row[metric_index.get(api_metric, 1)]),
            views=int(row[1]),
            watch_time_minutes=float(row[2]),
            likes=int(row[3]),
            comments=int(row[4]),
        ))

    return top_videos


def get_revenue_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> RevenueReport:
    """Get revenue report (requires monetization enabled).

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        RevenueReport with estimated revenue, CPM, RPM

    Note:
        This requires the channel to have monetization enabled and
        the yt-analytics-monetary.readonly scope.
    """
    analytics = _get_analytics_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="estimatedRevenue,estimatedAdRevenue,cpm,playbackBasedCpm",
        currency="USD",
    ).execute()

    rows = response.get("rows", [[0, 0, 0, 0]])
    row = rows[0] if rows else [0, 0, 0, 0]

    # Calculate RPM (Revenue per Mille)
    # RPM = (Total Revenue / Views) * 1000
    # We need to get views separately
    views_response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views",
    ).execute()

    views_rows = views_response.get("rows", [[0]])
    views = int(views_rows[0][0]) if views_rows else 0
    estimated_revenue = float(row[0])
    rpm = (estimated_revenue / views * 1000) if views > 0 else 0

    return RevenueReport(
        estimated_revenue=estimated_revenue,
        estimated_ad_revenue=float(row[1]),
        cpm=float(row[2]),
        rpm=round(rpm, 2),
        playback_based_cpm=float(row[3]),
    )


def get_device_analytics(
    video_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[DeviceStats]:
    """Get analytics by device type.

    Args:
        video_id: YouTube video ID (optional, if None gets channel-wide data)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of DeviceStats objects
    """
    analytics = _get_analytics_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    query_params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched",
        "dimensions": "deviceType",
        "sort": "-views",
    }

    if video_id:
        query_params["filters"] = f"video=={video_id}"

    response = analytics.reports().query(**query_params).execute()

    total_views = sum(int(row[1]) for row in response.get("rows", []))

    devices = []
    for row in response.get("rows", []):
        views = int(row[1])
        devices.append(DeviceStats(
            device_type=row[0],
            views=views,
            estimated_minutes_watched=float(row[2]),
            percentage=round((views / total_views * 100) if total_views > 0 else 0, 2),
        ))

    return devices


def get_playback_locations(
    video_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[PlaybackLocation]:
    """Get analytics by playback location.

    Args:
        video_id: YouTube video ID (optional, if None gets channel-wide data)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        List of PlaybackLocation objects
    """
    analytics = _get_analytics_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    query_params = {
        "ids": "channel==MINE",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched",
        "dimensions": "insightPlaybackLocationType",
        "sort": "-views",
    }

    if video_id:
        query_params["filters"] = f"video=={video_id}"

    response = analytics.reports().query(**query_params).execute()

    total_views = sum(int(row[1]) for row in response.get("rows", []))

    locations = []
    for row in response.get("rows", []):
        views = int(row[1])
        locations.append(PlaybackLocation(
            playback_location_type=row[0],
            views=views,
            estimated_minutes_watched=float(row[2]),
            percentage=round((views / total_views * 100) if total_views > 0 else 0, 2),
        ))

    return locations


def get_content_performance(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_results: int = 25,
) -> list[ContentPerformance]:
    """Get detailed performance metrics for each video.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        max_results: Maximum number of videos to return (1-50)

    Returns:
        List of ContentPerformance objects
    """
    max_results = max(1, min(50, max_results))
    analytics = _get_analytics_service()
    youtube = _get_youtube_service()

    if not end_date:
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now(timezone.utc) - timedelta(days=28)).strftime("%Y-%m-%d")

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date,
        endDate=end_date,
        metrics="views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares,subscribersGained",
        dimensions="video",
        sort="-views",
        maxResults=max_results,
    ).execute()

    video_ids = [row[0] for row in response.get("rows", [])]
    if not video_ids:
        return []

    # Get video titles
    videos_response = youtube.videos().list(
        part="snippet",
        id=",".join(video_ids),
    ).execute()

    title_map = {
        item["id"]: item["snippet"]["title"]
        for item in videos_response.get("items", [])
    }

    results = []
    for row in response.get("rows", []):
        vid = row[0]
        results.append(ContentPerformance(
            video_id=vid,
            title=title_map.get(vid, "Unknown"),
            views=int(row[1]),
            estimated_minutes_watched=float(row[2]),
            average_view_duration=float(row[3]),
            likes=int(row[4]),
            comments=int(row[5]),
            shares=int(row[6]),
            subscribers_gained=int(row[7]),
        ))

    return results
