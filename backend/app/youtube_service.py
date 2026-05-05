# app/youtube_service.py

import os
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def is_youtube_configured() -> bool:
    """
    YouTube Data API key tanımlı mı kontrol eder.
    """

    return bool(YOUTUBE_API_KEY)


def is_video_like_resource(resource: Dict[str, Any]) -> bool:
    """
    LLM tarafından üretilmiş video benzeri kaynakları tespit eder.

    Bu kaynakları temizleyip sadece YouTube Data API'den gelen
    doğrulanmış videoları ekleyeceğiz.
    """

    resource_type = str(resource.get("resource_type", "")).lower()
    resource_url = str(resource.get("resource_url", "")).lower()

    video_keywords = [
        "video",
        "youtube",
        "ders",
        "kurs",
    ]

    has_video_type = any(keyword in resource_type for keyword in video_keywords)
    has_youtube_url = "youtube.com" in resource_url or "youtu.be" in resource_url

    return has_video_type or has_youtube_url


def build_youtube_search_queries(
    topic: str,
    week_title: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """
    Haftaya uygun YouTube arama sorguları üretir.
    """

    task_keywords = []

    for task in tasks or []:
        task_text = task.get("task_text")

        if task_text:
            task_keywords.append(str(task_text))

    short_tasks = " ".join(task_keywords[:2])

    queries = [
        f"{topic} {week_title} Türkçe ders",
        f"{topic} {week_title} tutorial",
        f"{topic} {short_tasks} Türkçe",
        f"{topic} başlangıç ders",
        f"{topic} tutorial beginner",
    ]

    cleaned_queries = []

    for query in queries:
        cleaned_query = " ".join(query.split())

        if cleaned_query and cleaned_query not in cleaned_queries:
            cleaned_queries.append(cleaned_query)

    return cleaned_queries


def get_video_details(video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Video ID listesi için video detaylarını getirir.

    status.embeddable alanı burada kontrol edilir.
    """

    if not video_ids or not is_youtube_configured():
        return {}

    params = {
        "part": "snippet,status,contentDetails",
        "id": ",".join(video_ids),
        "key": YOUTUBE_API_KEY,
    }

    try:
        response = requests.get(
            YOUTUBE_VIDEOS_URL,
            params=params,
            timeout=12,
        )

        response.raise_for_status()

        data = response.json()
        details = {}

        for item in data.get("items", []):
            video_id = item.get("id")

            if video_id:
                details[video_id] = item

        return details

    except Exception:
        return {}


def search_youtube_videos(
    query: str,
    max_results: int = 10,
    relevance_language: str = "tr",
    region_code: str = "TR",
) -> List[Dict[str, Any]]:
    """
    YouTube Data API ile gerçek ve embed edilebilir video arar.

    Kullanılamayan veya embed edilemeyen videolar listeye eklenmez.
    """

    if not is_youtube_configured():
        return []

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "relevance",
        "safeSearch": "moderate",
        "relevanceLanguage": relevance_language,
        "regionCode": region_code,
        "videoEmbeddable": "true",
        "videoSyndicated": "true",
        "key": YOUTUBE_API_KEY,
    }

    try:
        response = requests.get(
            YOUTUBE_SEARCH_URL,
            params=params,
            timeout=12,
        )

        response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        video_ids = []

        for item in items:
            video_id = item.get("id", {}).get("videoId")

            if video_id:
                video_ids.append(video_id)

        video_details = get_video_details(video_ids)

        videos = []

        for item in items:
            video_id = item.get("id", {}).get("videoId")

            if not video_id:
                continue

            detail = video_details.get(video_id)

            if not detail:
                continue

            status = detail.get("status", {})

            # Sadece kesin olarak embed edilebilir videoları kabul ediyoruz.
            if status.get("embeddable") is not True:
                continue

            snippet = item.get("snippet", {})

            title = snippet.get("title") or "YouTube Video"
            description = (
                snippet.get("description")
                or "Bu haftanın konularını destekleyen YouTube video kaynağı."
            )
            channel_title = snippet.get("channelTitle") or "YouTube"

            videos.append({
                "video_id": video_id,
                "title": title,
                "description": description,
                "channel_title": channel_title,
                "watch_url": f"https://www.youtube.com/watch?v={video_id}",
                "embed_url": f"https://www.youtube.com/embed/{video_id}",
            })

        return videos

    except Exception:
        return []


def get_youtube_resources(
    topic: str,
    week_title: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    max_videos: int = 1,
) -> List[Dict[str, Any]]:
    """
    Haftaya uygun kullanılabilir YouTube videolarını resource formatına çevirir.

    Kurallar:
    - Sadece YouTube Data API'den gelen gerçek videolar kullanılır.
    - Embed edilebilir olmayan videolar zaten search_youtube_videos içinde elenir.
    - Aynı video birden fazla sorguda gelirse tekrar eklenmez.
    - max_videos kadar video döndürülür.
    """

    queries = build_youtube_search_queries(
        topic=topic,
        week_title=week_title,
        tasks=tasks,
    )

    selected_resources = []
    used_video_ids = set()

    for query in queries:
        if len(selected_resources) >= max_videos:
            break

        videos = search_youtube_videos(
            query=query,
            max_results=10,
        )

        for video in videos:
            if len(selected_resources) >= max_videos:
                break

            video_id = video.get("video_id")

            if not video_id or video_id in used_video_ids:
                continue

            used_video_ids.add(video_id)

            selected_resources.append({
                "resource_title": video["title"],
                "resource_type": "YouTube Video",
                "resource_description": (
                    f"{video['channel_title']} kanalından bu haftanın konularını "
                    f"destekleyen video kaynağı. {video['description'][:180]}"
                ),
                "resource_url": video["watch_url"],
            })

    return selected_resources


def enrich_plan_with_youtube_resources(
    plan_data: Dict[str, Any],
    topic: str,
    learning_preference: str,
) -> Dict[str, Any]:
    """
    Normalize edilmiş öğrenme planına gerçek YouTube kaynakları ekler.

    Kurallar:
    - Gemini'nin ürettiği video benzeri kaynaklar temizlenir.
    - Normal öğrenme tercihinde her hafta en fazla 1 YouTube Video eklenir.
    - Video ağırlıklı öğrenme tercihinde her hafta en fazla 3 YouTube Video eklenir.
    - Video sadece YouTube Data API'den doğrulanmışsa eklenir.
    - Video bulunamazsa hiçbir video/arama kaynağı eklenmez.
    - Konsola print basılmaz.
    """

    weeks = plan_data.get("weeks", [])

    if not isinstance(weeks, list):
        return plan_data

    is_video_preference = str(learning_preference or "").lower() == "video ağırlıklı"
    max_youtube_videos = 3 if is_video_preference else 1

    for week in weeks:
        if not isinstance(week, dict):
            continue

        resources = week.get("resources", [])

        if not isinstance(resources, list):
            resources = []

        cleaned_resources = []

        for resource in resources:
            if not isinstance(resource, dict):
                continue

            # Video benzeri tüm LLM kaynaklarını temizliyoruz.
            # Böylece "Video Ders" ama link yok veya kullanılamayan YouTube linki görünmez.
            if is_video_like_resource(resource):
                continue

            cleaned_resources.append(resource)

        week["resources"] = cleaned_resources

        youtube_resources = get_youtube_resources(
            topic=topic,
            week_title=week.get("title", ""),
            tasks=week.get("tasks", []),
            max_videos=max_youtube_videos,
        )

        if youtube_resources:
            week["resources"].extend(youtube_resources)

    return plan_data