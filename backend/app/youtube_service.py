# app/youtube_service.py

import os
import unicodedata
from typing import Any, Dict, List, Optional, Set

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


def normalize_text(value: Any) -> str:
    """
    Türkçe karakterleri ve özel unicode durumlarını sadeleştirir.

    Özellikle:
    - "İleri" -> "ileri"
    - "Başlangıç" -> "baslangic"
    - "Giriş" -> "giris"

    Böylece seviye ve video başlığı karşılaştırmaları daha güvenilir çalışır.
    """

    text = str(value or "").casefold()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))

    replacements = {
        "ı": "i",
        "ş": "s",
        "ğ": "g",
        "ü": "u",
        "ö": "o",
        "ç": "c",
    }

    for old_char, new_char in replacements.items():
        text = text.replace(old_char, new_char)

    return text


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


def get_text_for_video(video: Dict[str, Any]) -> str:
    """
    Video başlığı ve açıklamasını normalize edilmiş tek metne çevirir.
    """

    title = normalize_text(video.get("title", ""))
    description = normalize_text(video.get("description", ""))

    return f"{title} {description}"


def get_level_group(level: str) -> str:
    """
    Kullanıcı seviyesini standart gruba çevirir.

    Türkçe karakterlerden etkilenmemek için normalize_text kullanılır.
    """

    normalized_level = normalize_text(level)

    if "ileri" in normalized_level or "advanced" in normalized_level:
        return "advanced"

    if "orta" in normalized_level or "intermediate" in normalized_level:
        return "intermediate"

    return "beginner"

def get_task_focuses(
    tasks: Optional[List[Dict[str, Any]]],
    max_focuses: int = 3
) -> List[str]:
    """
    Haftalık görevlerden kısa ve aramaya uygun odak metinleri çıkarır.

    Görev metnini tamamen YouTube'a göndermek bazen sonuçları bozabilir.
    Bu yüzden metni kısaltıp teknik anahtar kelime odaklı kullanıyoruz.
    """

    focuses = []

    stop_words = {
        "bu", "bir", "ve", "veya", "ile", "icin", "için", "olarak",
        "konusunda", "ilgili", "hafta", "haftanın", "öğren", "öğrenmek",
        "incele", "uygula", "oluştur", "geliştir", "teknik", "görev",
        "kavramları", "kullanım", "alanlarını", "örneklerle"
    }

    for task in tasks or []:
        if not isinstance(task, dict):
            continue

        task_text = task.get("task_text")

        if not task_text:
            continue

        normalized = " ".join(str(task_text).replace(",", " ").replace(".", " ").split())
        words = normalized.split()

        selected_words = []

        for word in words:
            clean_word = word.strip()

            if len(clean_word) < 4:
                continue

            if clean_word.lower() in stop_words:
                continue

            selected_words.append(clean_word)

            if len(selected_words) >= 6:
                break

        focus = " ".join(selected_words)

        if focus and focus not in focuses:
            focuses.append(focus)

        if len(focuses) >= max_focuses:
            break

    return focuses

def build_youtube_search_queries(
    topic: str,
    week_title: str,
    level: str,
    goal: str,
    task_focus: str | None = None,
) -> List[str]:
    """
    YouTube için görev odaklı ve seviye uyumlu arama sorguları üretir.

    Öncelik:
    1. Görev odaklı sorgu
    2. Görev + seviye sorgusu
    3. Hafta/hedef bazlı daha genel sorgu
    """

    level_group = get_level_group(level)
    focus = task_focus or week_title

    if level_group == "advanced":
        queries = [
            f"{topic} {focus}",
            f"{topic} {focus} advanced",
            f"{topic} {focus} best practices",
            f"{topic} {week_title} advanced",
        ]

    elif level_group == "intermediate":
        queries = [
            f"{topic} {focus}",
            f"{topic} {focus} intermediate",
            f"{topic} {focus} practical",
            f"{topic} {week_title} project",
        ]

    else:
        queries = [
            f"{topic} {focus}",
            f"{topic} {focus} beginner",
            f"{topic} {focus} tutorial",
            f"{topic} {week_title} basics",
        ]

    cleaned_queries = []

    for query in queries:
        cleaned_query = " ".join(str(query).split())

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
    relevance_language: str = "en",
    region_code: str = "US",
) -> List[Dict[str, Any]]:
    """
    YouTube Data API ile gerçek video arar.

    Önemli:
    - İlk aramada embed/syndicated filtreleri kullanılır.
    - Eğer sonuç gelmezse daha genel ikinci arama yapılır.
    - videos.list detayları gelirse embeddable kontrol edilir.
    - Detay servisi boş dönerse tüm videoları çöpe atmıyoruz; search sonucu kullanılabilir kabul edilir.
    """

    if not is_youtube_configured():
        return []

    search_attempts = [
        {
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
        },
        {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": "relevance",
            "safeSearch": "moderate",
            "key": YOUTUBE_API_KEY,
        },
    ]

    for params in search_attempts:
        try:
            response = requests.get(
                YOUTUBE_SEARCH_URL,
                params=params,
                timeout=12,
            )

            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            if not items:
                continue

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

                # Eğer video detayları geldiyse embed kontrolünü yap.
                # Eğer detay gelmediyse videoyu direkt çöpe atmıyoruz.
                if detail:
                    status = detail.get("status", {})

                    if status.get("embeddable") is False:
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

            if videos:
                return videos

        except Exception:
            continue

    return []

def is_video_level_mismatch(video: Dict[str, Any], level: str) -> bool:
    """
    Videonun kullanıcının seviyesine bariz şekilde ters düşüp düşmediğini kontrol eder.

    İleri seviyede sadece başlığında açıkça beginner/basic geçen videoları eliyoruz.
    Açıklamada beginner geçmesi tek başına eleme sebebi değildir.
    """

    title = normalize_text(video.get("title", ""))
    description = normalize_text(video.get("description", ""))
    level_group = get_level_group(level)

    beginner_keywords = [
        "beginner",
        "beginners",
        "beginer",
        "beginers",
        "begineer",
        "begineers",
        "begginer",
        "begginers",
        "for beginners",
        "complete beginner",
        "absolute beginner",
        "from scratch",
        "basics",
        "basic",
        "fundamentals",
        "crash course",
        "full course",
        "baslangic",
        "temel",
        "giris",
        "sifirdan",
    ]

    advanced_keywords = [
        "advanced",
        "expert",
        "senior",
        "deep dive",
        "best practices",
        "performance",
        "optimization",
        "optimisation",
        "architecture",
        "production",
        "scalable",
        "patterns",
        "design patterns",
        "memoization",
        "custom hooks",
        "state management",
        "testing",
        "profiling",
        "async",
        "decorator",
        "generator",
        "context manager",
        "type hints",
    ]

    has_beginner_in_title = any(keyword in title for keyword in beginner_keywords)

    if level_group == "advanced":
        if has_beginner_in_title:
            return True

        return False

    if level_group == "intermediate":
        if has_beginner_in_title and "intermediate" not in title and "project" not in title:
            return True

        return False

    if level_group == "beginner":
        title_and_description = f"{title} {description}"
        has_advanced_keyword = any(keyword in title_and_description for keyword in advanced_keywords)

        if has_advanced_keyword and not has_beginner_in_title:
            return True

    return False

def score_video_for_level_and_week(
    video: Dict[str, Any],
    level: str,
    week_title: str,
    goal: str,
    task_focus: str | None = None,
) -> int:
    """
    Videoları kullanıcının seviyesine, haftaya, hedefe ve görev odağına göre puanlar.
    """

    text = get_text_for_video(video)
    level_group = get_level_group(level)

    score = 0

    focus_words = [
        normalize_text(word)
        for word in str(task_focus or "").replace(",", " ").replace(".", " ").split()
        if len(word) >= 4
    ]

    week_words = [
        normalize_text(word)
        for word in str(week_title or "").replace("-", " ").split()
        if len(word) >= 4
    ]

    goal_words = [
        normalize_text(word)
        for word in str(goal or "").replace(",", " ").replace(".", " ").split()
        if len(word) >= 5
    ]

    # Görev odağı en yüksek öncelikli olmalı.
    for word in focus_words:
        if word in text:
            score += 8

    for word in week_words:
        if word in text:
            score += 3

    for word in goal_words:
        if word in text:
            score += 2

    if level_group == "advanced":
        advanced_keywords = [
            "advanced",
            "performance",
            "optimization",
            "architecture",
            "production",
            "best practices",
            "patterns",
            "deep dive",
            "scalable",
            "custom hooks",
            "memoization",
            "senior",
            "async",
            "decorator",
            "generator",
            "type hints",
            "testing",
        ]

        for keyword in advanced_keywords:
            if keyword in text:
                score += 6

    elif level_group == "intermediate":
        intermediate_keywords = [
            "intermediate",
            "project",
            "practical",
            "real world",
            "uygulamali",
            "proje",
        ]

        for keyword in intermediate_keywords:
            if keyword in text:
                score += 5

    else:
        beginner_keywords = [
            "beginner",
            "baslangic",
            "temel",
            "giris",
            "fundamentals",
        ]

        for keyword in beginner_keywords:
            if keyword in text:
                score += 5

    return score


def get_youtube_resources(
    topic: str,
    week_title: str,
    level: str,
    goal: str,
    tasks: Optional[List[Dict[str, Any]]] = None,
    max_videos: int = 1,
    used_video_ids: Optional[Set[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Haftaya, hedefe ve kullanıcı seviyesine uygun YouTube videolarını resource formatına çevirir.

    Arama sırası:
    1. Haftalık görev odakları
    2. Hafta başlığı
    3. Kullanıcının hedefi
    4. Genel seviye odaklı konu sorguları

    Böylece görev bazlı video bulunamazsa sistem tamamen videosuz kalmaz.
    """

    if used_video_ids is None:
        used_video_ids = set()

    level_group = get_level_group(level)

    task_focuses = get_task_focuses(
        tasks=tasks,
        max_focuses=max_videos
    )

    fallback_focuses = [
        week_title,
        goal,
    ]

    if level_group == "advanced":
        fallback_focuses.extend([
            f"{topic} advanced tutorial",
            f"{topic} advanced concepts",
            f"{topic} best practices",
            f"{topic} performance optimization",
            f"{topic} clean code",
            f"{topic} testing",
            f"{topic} async await",
            f"{topic} decorators generators",
            f"{topic} type hints",
            f"{topic} packaging",
        ])

    elif level_group == "intermediate":
        fallback_focuses.extend([
            f"{topic} intermediate tutorial",
            f"{topic} practical project",
            f"{topic} real world project",
            f"{topic} testing basics",
        ])

    else:
        fallback_focuses.extend([
            f"{topic} beginner tutorial",
            f"{topic} fundamentals",
            f"{topic} basics",
        ])

    all_focuses = []

    for focus in task_focuses + fallback_focuses:
        cleaned_focus = " ".join(str(focus or "").split())

        if cleaned_focus and cleaned_focus not in all_focuses:
            all_focuses.append(cleaned_focus)

    selected_resources = []

    for focus in all_focuses:
        if len(selected_resources) >= max_videos:
            break

        queries = build_youtube_search_queries(
            topic=topic,
            week_title=week_title,
            level=level,
            goal=goal,
            task_focus=focus,
        )

        candidate_videos = []
        candidate_video_ids = set()

        for query in queries:
            videos = search_youtube_videos(
                query=query,
                max_results=15,
            )

            for video in videos:
                video_id = video.get("video_id")

                if not video_id:
                    continue

                if video_id in used_video_ids:
                    continue

                if video_id in candidate_video_ids:
                    continue

                if is_video_level_mismatch(video, level):
                    continue

                candidate_video_ids.add(video_id)
                candidate_videos.append(video)

        if not candidate_videos:
            continue

        candidate_videos.sort(
            key=lambda video: score_video_for_level_and_week(
                video=video,
                level=level,
                week_title=week_title,
                goal=goal,
                task_focus=focus,
            ),
            reverse=True,
        )

        selected_video = candidate_videos[0]
        selected_video_id = selected_video.get("video_id")

        if not selected_video_id:
            continue

        used_video_ids.add(selected_video_id)

        selected_resources.append({
            "resource_title": selected_video["title"],
            "resource_type": "YouTube Video",
            "resource_description": (
                f"Desteklediği görev/konu: {focus}. "
                f"{selected_video['channel_title']} kanalından bu haftanın konularını "
                f"{level} seviyesine uygun şekilde destekleyen video kaynağı. "
                f"{selected_video['description'][:180]}"
            ),
            "resource_url": selected_video["watch_url"],
        })

    # Eğer görev/hafta odaklı aramalardan hiç video bulunamadıysa,
    # son kez sadece topic + level odaklı daha genel arama yapıyoruz.
    if not selected_resources:
        level_group = get_level_group(level)

        if level_group == "advanced":
            final_queries = [
                f"{topic} advanced tutorial",
                f"{topic} best practices",
                f"{topic} performance optimization",
            ]
        elif level_group == "intermediate":
            final_queries = [
                f"{topic} intermediate tutorial",
                f"{topic} practical project",
            ]
        else:
            final_queries = [
                f"{topic} beginner tutorial",
                f"{topic} basics",
            ]

        for query in final_queries:
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

                if not video_id:
                    continue

                if video_id in used_video_ids:
                    continue

                if is_video_level_mismatch(video, level):
                    continue

                used_video_ids.add(video_id)

                selected_resources.append({
                    "resource_title": video["title"],
                    "resource_type": "YouTube Video",
                    "resource_description": (
                        f"Desteklediği görev/konu: {query}. "
                        f"{video['channel_title']} kanalından {level} seviyesine uygun "
                        f"video kaynağı. {video['description'][:180]}"
                    ),
                    "resource_url": video["watch_url"],
                })

                break

    return selected_resources


def enrich_plan_with_youtube_resources(
    plan_data: Dict[str, Any],
    topic: str,
    level: str,
    goal: str,
    learning_preference: str,
) -> Dict[str, Any]:
    """
    Normalize edilmiş öğrenme planına gerçek YouTube kaynakları ekler.

    Kurallar:
    - Gemini'nin ürettiği video benzeri kaynaklar temizlenir.
    - Normal öğrenme tercihinde her hafta en fazla 1 YouTube Video eklenir.
    - Video ağırlıklı öğrenme tercihinde her hafta en fazla 3 YouTube Video eklenir.
    - Aynı video aynı plan içinde tekrar önerilmez.
    - İleri seviye için beginner/basic videolar önerilmez.
    - Video bulunamazsa hiçbir video/arama kaynağı eklenmez.
    """

    weeks = plan_data.get("weeks", [])

    if not isinstance(weeks, list):
        return plan_data

    is_video_preference = str(learning_preference or "").lower() == "video ağırlıklı"
    max_youtube_videos = 3 if is_video_preference else 1

    used_video_ids: Set[str] = set()

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
            level=level,
            goal=goal,
            tasks=week.get("tasks", []),
            max_videos=max_youtube_videos,
            used_video_ids=used_video_ids,
        )

        if youtube_resources:
            week["resources"].extend(youtube_resources)

    return plan_data