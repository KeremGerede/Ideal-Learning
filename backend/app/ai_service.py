import json
import os
import time
import random
import unicodedata
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types

from app.youtube_service import enrich_plan_with_youtube_resources
from app.safety import detect_gemini_safety_refusal


class GeminiSafetyRefusalError(Exception):
    """Raised when Gemini refuses a request due to safety/policy concerns."""
    pass


# ============================================================
# ENV CONFIG
# ============================================================
# .env dosyasındaki GEMINI_API_KEY ve GEMINI_MODEL değerlerini okuyoruz.
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ============================================================
# GEMINI CLIENT
# ============================================================
# Gemini API istemcisi. API key yoksa fallback akışlarını kullanacağız.
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


# ============================================================
# SAFETY CONFIG & HELPERS
# ============================================================
# Gemini güvenlik filtrelerini (Safety Settings) yapılandırıyoruz.
# Eşik değerleri (threshold):
# - BLOCK_LOW_AND_ABOVE: Düşük hassasiyetli/olasılıklı zararlar dahil engeller (En katı).
# - BLOCK_MEDIUM_AND_ABOVE: Orta ve yüksek hassasiyetli/olasılıklı zararları engeller (Standart/Dengeli).
# - BLOCK_ONLY_HIGH: Yalnızca yüksek olasılıklı zararları engeller.
# - BLOCK_NONE: İlgili kategorideki filtrelemeyi kapatır.
DEFAULT_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    ),
]


def check_safety_refusal(response) -> None:
    """Gemini cevabının güvenlik filtrelerine takılıp takılmadığını denetler."""
    if not response:
        return

    # Aday cevapların (candidates) bitiş nedenini (finish_reason) kontrol ediyoruz
    if response.candidates:
        candidate = response.candidates[0]
        finish_reason = getattr(candidate, 'finish_reason', None)
        if finish_reason:
            finish_reason_str = str(finish_reason).upper()
            if "SAFETY" in finish_reason_str or "RECITATION" in finish_reason_str or "OTHER" in finish_reason_str:
                raise GeminiSafetyRefusalError(
                    f"Gemini güvenlik politikaları nedeniyle içerik üretmeyi reddetti. Bitiş nedeni: {finish_reason}"
                )

    # Promptun kendisinin engellenip engellenmediğini kontrol ediyoruz
    prompt_feedback = getattr(response, 'prompt_feedback', None)
    if prompt_feedback:
        block_reason = getattr(prompt_feedback, 'block_reason', None)
        if block_reason:
            raise GeminiSafetyRefusalError(
                f"Gemini güvenlik politikaları nedeniyle girdiyi (prompt) engelledi. Engel nedeni: {block_reason}"
            )


def get_response_text_safely(response) -> str:
    """Gemini cevabının metnini güvenli bir şekilde alır, filtre takılmalarını yakalar."""
    check_safety_refusal(response)
    try:
        return response.text
    except Exception as e:
        err_msg = str(e).lower()
        if "safety" in err_msg or "block" in err_msg or "finish_reason" in err_msg:
            raise GeminiSafetyRefusalError(
                "Gemini güvenlik politikaları nedeniyle içerik üretilemedi."
            ) from e
        raise e


# ============================================================
# PROMPT BUILDER
# ============================================================

def build_learning_plan_prompt(
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    duration_weeks: int,
    learning_preference: str | None = None
) -> str:
    """
    Builds the prompt sent to Gemini.

    Prompt structure:
    1. Context
    2. Role
    3. Constraints
    4. Task
    5. Template variables
    6. Output control

    The prompt is written in English, but the generated learning plan content
    must be in Turkish because the application currently targets Turkish users.
    """

    return f"""
# 1. Context

You are generating a personalized learning plan for a user in an AI-powered learning platform.

The platform receives the user's learning goal, current level, available weekly study time, preferred learning style, and desired plan duration. Based on this information, the system creates a weekly learning roadmap with technical tasks, resources, estimated effort, difficulty level, mini projects, a general summary, and a final learning outcome.

The generated plan will be saved into a database and displayed in a learning dashboard. Therefore, the output must be consistent, structured, technical, and easy to parse.

# 2. Role

Act as an expert AI learning coach, curriculum designer, and technical mentor.

You should design a realistic, beginner-friendly, technically useful, actionable, and personalized learning roadmap.

# 3. Constraints

- Return only valid JSON.
- Do not use Markdown.
- Do not add explanations outside the JSON.
- The JSON must be parseable by Python's json.loads().
- The learning plan content must be written in Turkish.
- The total number of weeks must be exactly {duration_weeks}.
- Each week must include at least 4 tasks.
- Each week must include at least 2 learning resources.
- Each week must include exactly one mini project in the mini_project field.
- Do not include the mini project as a task inside the tasks array.
- The mini project must only appear in the mini_project field.
- The summary field must briefly explain the overall purpose of the plan.
- The final_outcome field must explain what the user will be able to do after completing the plan.
- summary and final_outcome must be written in Turkish.

Technical task quality rules:
- Tasks must be technical, topic-specific, and concrete.
- Avoid generic tasks such as "konuyu çalış", "araştırma yap", "video izle", "not al", "pratik yap", or "tekrar et" unless they include specific technical subtopics.
- Each task_text must include concrete subtopics, concepts, tools, commands, implementation targets, or practice outputs related to the selected topic.
- task_text must be written as a clear action sentence.
- task_text should not use a title-colon-description format.
- Avoid task_text values like "Topic: explanation".
- Prefer action-oriented Turkish task sentences.
- Do not write the task type inside task_text.
- Do not add labels like "(Teori)", "(Uygulama)", "(Proje)" inside task_text.
- For technical topics, include relevant concepts, tools, commands, APIs, configuration files, implementation details, or debugging steps when appropriate.
- Each task must be specific, measurable, and actionable.

Weekly progression rules:
- Each week must focus on a different learning stage.
- Weekly topics must not repeat each other.
- Do not generate the same task pattern for every week.
- The plan must progress from fundamentals to applied practice.
- The plan should gradually increase in difficulty.
- Week 1 should focus on foundations and environment setup if relevant.
- Middle weeks should focus on core concepts and applied usage.
- Final weeks should focus on integration, mini project, debugging, and real-world practice.

Task metadata rules:
- task_type must be one of: "Teori", "Uygulama", "Proje", "Tekrar", "Araştırma".
- difficulty must be one of: "Kolay", "Orta", "Zor".
- estimated_minutes must be a positive integer.
- The total estimated_minutes of all tasks in a week should approximately match {weekly_hours} hours.
- estimated_hours for each week should be close to {weekly_hours}.

Resource rules:
- Each week must include at least 2 learning resources.
- Resources must be directly related to that week's tasks, week title, or mini project.
- Avoid generic resources that are not connected to the weekly tasks.
- Each resource should support at least one specific task or subtopic from that week.
- Each resource_description must clearly mention which task or subtopic it supports.
- Use this style in resource_description: "Desteklediği görev/konu: ... Bu kaynak ..."
- At least one resource per week should include a real URL when possible.
- If the topic has official documentation, include it as a resource only when it supports a specific weekly task.
- Prefer official documentation URLs when possible.
- Prefer reliable, beginner-friendly, and relevant resources.
- Resource URLs must be real and useful.
- If you are not sure about the exact URL, use null instead of inventing fake links.
- Avoid repeating the exact same resources every week unless it is official documentation and still relevant to that week's tasks.
- Do not create YouTube resources.
- Do not create video resources with resource_type such as "Video", "Video Ders", "YouTube Video", or "Video / Kurs".
- YouTube video resources will be added separately by the backend using YouTube Data API.
- If learning_preference is "Video ağırlıklı", the backend will try to add real YouTube video resources automatically.

# 4. Task

Generate a personalized weekly learning plan for the user.

The plan should help the user move from their current level toward their stated learning goal. The output must include a general plan summary, a final learning outcome, and weekly learning sections. Each week should have a clear theme, a short description, estimated study hours, technical and actionable tasks, a mini project, and learning resources.

# 5. Template Variables

User input:

- topic: "{topic}"
- current_level: "{level}"
- learning_goal: "{goal}"
- weekly_hours: {weekly_hours}
- duration_weeks: {duration_weeks}
- learning_preference: "{learning_preference or "Belirtilmedi"}"

# 6. Output Control

Return the output using exactly this JSON structure:

{{
  "topic": "{topic}",
  "level": "{level}",
  "goal": "{goal}",
  "weekly_hours": {weekly_hours},
  "duration_weeks": {duration_weeks},
  "learning_preference": "{learning_preference or "Belirtilmedi"}",
  "summary": "Bu planın genel amacı ve kullanıcıya nasıl yardımcı olacağının kısa açıklaması",
  "final_outcome": "Bu plan tamamlandığında kullanıcının kazanacağı becerilerin açıklaması",
  "weeks": [
    {{
      "week_number": 1,
      "title": "Hafta başlığı",
      "description": "Bu haftanın kısa açıklaması",
      "estimated_hours": {weekly_hours},
      "mini_project": "Bu haftanın sonunda yapılacak teknik mini proje veya uygulama önerisi",
      "tasks": [
        {{
          "task_text": "Konuya özel teknik görev açıklaması",
          "task_type": "Teori",
          "estimated_minutes": 60,
          "difficulty": "Kolay"
        }},
        {{
          "task_text": "Konuya özel uygulamalı görev açıklaması",
          "task_type": "Uygulama",
          "estimated_minutes": 90,
          "difficulty": "Orta"
        }},
        {{
          "task_text": "Konuya özel tekrar veya analiz görevi",
          "task_type": "Tekrar",
          "estimated_minutes": 45,
          "difficulty": "Kolay"
        }},
        {{
          "task_text": "Konuya özel proje veya entegrasyon görevi",
          "task_type": "Proje",
          "estimated_minutes": 120,
          "difficulty": "Orta"
        }}
      ],
      "resources": [
        {{
          "resource_title": "Kaynak adı",
          "resource_type": "Dokümantasyon",
          "resource_description": "Desteklediği görev/konu: Bu haftadaki belirli görev veya teknik alt konu. Bu kaynak ilgili görevi anlamaya veya uygulamaya yardımcı olur.",
          "resource_url": "https://example.com"
        }},
        {{
          "resource_title": "Kaynak adı",
          "resource_type": "Makale",
          "resource_description": "Desteklediği görev/konu: Bu haftadaki belirli görev veya teknik alt konu. Bu kaynak ilgili görevi anlamaya veya uygulamaya yardımcı olur.",
          "resource_url": null
        }}
      ]
    }}
  ]
}}
"""


# ============================================================
# AI RESPONSE PARSER
# ============================================================

def parse_gemini_json_response(response_text: str) -> Dict[str, Any]:
    """
    Gemini'den gelen cevabı JSON'a çevirir.

    Normalde response_mime_type='application/json' kullandığımız için
    model doğrudan JSON döndürmeli. Yine de güvenlik için markdown code block
    temizliği yapıyoruz.
    """

    cleaned_text = response_text.strip()

    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.replace("```json", "", 1).strip()

    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.replace("```", "", 1).strip()

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3].strip()

    return json.loads(cleaned_text)


# ============================================================
# LEARNING PLAN FINALIZER
# ============================================================

def finalize_learning_plan(
    ai_plan: Dict[str, Any],
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    duration_weeks: int,
    learning_preference: str | None = None
) -> Dict[str, Any]:
    """
    AI veya fallback tarafından üretilen öğrenme planını son haline getirir.

    Bu adımda:
    - Plan normalize edilir.
    - Eksik veya bozuk alanlar güvenli hale getirilir.
    - YouTube Data API aktifse gerçek YouTube kaynakları eklenir.
    """

    normalized_plan = normalize_learning_plan(
        ai_plan=ai_plan,
        topic=topic,
        level=level,
        goal=goal,
        weekly_hours=weekly_hours,
        duration_weeks=duration_weeks,
        learning_preference=learning_preference
    )

    normalized_plan = enrich_plan_with_youtube_resources(
        plan_data=normalized_plan,
        topic=topic,
        level=level,
        goal=goal,
        learning_preference=learning_preference or "Belirtilmedi"
    )

    return normalized_plan


# ============================================================
# MAIN LEARNING PLAN FUNCTION
# ============================================================

def generate_learning_plan_with_gemini(
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    duration_weeks: int,
    learning_preference: str | None = None
) -> Dict[str, Any]:
    """
    Gemini API ile kişiselleştirilmiş öğrenme planı üretir.

    Eğer Gemini geçici olarak cevap veremezse:
    - Birkaç kez tekrar dener
    - Yine başarısız olursa fallback plan üretir
    - Hem Gemini çıktısı hem fallback plan YouTube enrichment adımından geçirilir
    """

    if client is None:
        print("[Gemini Fallback] GEMINI_API_KEY bulunamadı. Fallback plan kullanılacak.")

        fallback_plan = generate_fallback_learning_plan(
            topic=topic,
            level=level,
            goal=goal,
            weekly_hours=weekly_hours,
            duration_weeks=duration_weeks,
            learning_preference=learning_preference
        )

        return finalize_learning_plan(
            ai_plan=fallback_plan,
            topic=topic,
            level=level,
            goal=goal,
            weekly_hours=weekly_hours,
            duration_weeks=duration_weeks,
            learning_preference=learning_preference
        )

    prompt = build_learning_plan_prompt(
        topic=topic,
        level=level,
        goal=goal,
        weekly_hours=weekly_hours,
        duration_weeks=duration_weeks,
        learning_preference=learning_preference
    )

    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                    safety_settings=DEFAULT_SAFETY_SETTINGS
                )
            )

            response_text = get_response_text_safely(response)

            # If Gemini responded with a safety refusal instead of JSON,
            # raise immediately — do NOT fall back to a generic plan.
            if detect_gemini_safety_refusal(response_text):
                raise GeminiSafetyRefusalError(
                    "Gemini güvenlik politikaları bu konu için içerik üretmeyi reddetti."
                )

            parsed_plan = parse_gemini_json_response(response_text)

            return finalize_learning_plan(
                ai_plan=parsed_plan,
                topic=topic,
                level=level,
                goal=goal,
                weekly_hours=weekly_hours,
                duration_weeks=duration_weeks,
                learning_preference=learning_preference
            )

        except GeminiSafetyRefusalError:
            # Re-raise safety refusals — they must not be swallowed by the fallback.
            raise

        except Exception as e:
            error_message = str(e)

            # Eğer hata güvenlik filtreleri veya engelleme ile ilgiliyse, doğrudan fırlatıyoruz ve fallback üretmiyoruz.
            if any(sig in error_message.lower() for sig in ["safety", "block", "harmful", "policy", "abuse", "finish_reason"]):
                raise GeminiSafetyRefusalError(
                    f"Gemini güvenlik politikaları nedeniyle istek engellendi: {error_message}"
                ) from e

            print(f"[Gemini Error] Attempt {attempt}/{max_retries}: {error_message}")

            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue

            print("[Gemini Fallback] Gemini unavailable. Using fallback learning plan.")

            fallback_plan = generate_fallback_learning_plan(
                topic=topic,
                level=level,
                goal=goal,
                weekly_hours=weekly_hours,
                duration_weeks=duration_weeks,
                learning_preference=learning_preference
            )

            return finalize_learning_plan(
                ai_plan=fallback_plan,
                topic=topic,
                level=level,
                goal=goal,
                weekly_hours=weekly_hours,
                duration_weeks=duration_weeks,
                learning_preference=learning_preference
            )


# ============================================================
# LEARNING PLAN NORMALIZER
# ============================================================

def pick_supported_task_text(
    tasks: list[Dict[str, Any]],
    resource_index: int,
    topic: str
) -> str:
    """
    Kaynağın destekleyeceği görev metnini seçer.

    Aynı haftada birden fazla kaynak varsa kaynakları farklı görevlere
    dağıtmaya çalışır.
    """

    if not tasks:
        return f"{topic} konusundaki haftalık teknik görevler"

    task_position = (resource_index - 1) % len(tasks)
    selected_task = tasks[task_position]

    return selected_task.get("task_text") or f"{topic} konusundaki haftalık teknik görevler"


def ensure_task_linked_resource_description(
    description: str | None,
    supported_task_text: str,
    topic: str
) -> str:
    """
    Kaynak açıklamasının bir haftalık görev/konu ile ilişkili olmasını garanti eder.

    Gemini zaten 'Desteklediği görev/konu:' formatında açıklama üretmişse
    açıklamayı korur. Üretmemişse backend açıklamayı görev odaklı hale getirir.
    """

    cleaned_description = str(description or "").strip()

    if "desteklediği görev/konu:" in cleaned_description.lower():
        return cleaned_description

    if not cleaned_description:
        cleaned_description = f"Bu kaynak {topic} öğrenimini desteklemek için önerilmiştir."

    return (
        f"Desteklediği görev/konu: {supported_task_text}. "
        f"{cleaned_description}"
    )


def normalize_learning_plan(
    ai_plan: Dict[str, Any],
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    duration_weeks: int,
    learning_preference: str | None = None
) -> Dict[str, Any]:
    """
    Gemini'den veya fallback sistemden gelen öğrenme planını normalize eder.

    Amaç:
    - Eksik alanları doldurmak
    - Yanlış veri tiplerini düzeltmek
    - Backend'in beklediği JSON yapısını garanti etmek
    - Veritabanına kaydetmeden önce planı güvenli hale getirmek
    """

    allowed_task_types = {"Teori", "Uygulama", "Proje", "Tekrar", "Araştırma"}
    allowed_difficulties = {"Kolay", "Orta", "Zor"}

    normalized_plan = {
        "topic": ai_plan.get("topic") or topic,
        "level": ai_plan.get("level") or level,
        "goal": ai_plan.get("goal") or goal,
        "weekly_hours": ai_plan.get("weekly_hours") or weekly_hours,
        "duration_weeks": ai_plan.get("duration_weeks") or duration_weeks,
        "learning_preference": (
            ai_plan.get("learning_preference")
            or learning_preference
            or "Belirtilmedi"
        ),
        "summary": ai_plan.get("summary") or (
            f"Bu plan, {topic} konusunu {level} seviyesinden başlayarak "
            f"düzenli ve uygulanabilir adımlarla öğrenmek için oluşturulmuştur."
        ),
        "final_outcome": ai_plan.get("final_outcome") or (
            f"Plan sonunda kullanıcı {topic} konusunda temel bilgileri anlayabilecek "
            f"ve basit uygulamalar geliştirebilecek seviyeye gelecektir."
        ),
        "weeks": []
    }

    raw_weeks = ai_plan.get("weeks")

    if not isinstance(raw_weeks, list) or len(raw_weeks) == 0:
        return generate_fallback_learning_plan(
            topic=topic,
            level=level,
            goal=goal,
            weekly_hours=weekly_hours,
            duration_weeks=duration_weeks,
            learning_preference=learning_preference
        )

    raw_weeks = raw_weeks[:duration_weeks]

    for index, week_data in enumerate(raw_weeks, start=1):
        if not isinstance(week_data, dict):
            week_data = {}

        normalized_week = {
            "week_number": week_data.get("week_number") or index,
            "title": week_data.get("title") or f"{topic} - Hafta {index}",
            "description": week_data.get("description") or (
                f"Bu hafta {topic} konusunda seviyene uygun teknik çalışmalar yapılacaktır."
            ),
            "estimated_hours": week_data.get("estimated_hours") or weekly_hours,
            "mini_project": week_data.get("mini_project") or (
                f"{topic} ile ilgili küçük ve uygulanabilir bir teknik mini proje geliştir."
            ),
            "tasks": [],
            "resources": []
        }

        raw_tasks = week_data.get("tasks", [])

        if not isinstance(raw_tasks, list):
            raw_tasks = []

        for task_index, task_data in enumerate(raw_tasks, start=1):
            if isinstance(task_data, str):
                task_text = task_data
                task_type = "Uygulama"
                estimated_minutes = 60
                difficulty = "Orta"

            elif isinstance(task_data, dict):
                task_text = (
                    task_data.get("task_text")
                    or f"{topic} konusunda teknik görev {task_index} tamamla."
                )
                task_type = task_data.get("task_type") or "Uygulama"
                estimated_minutes = task_data.get("estimated_minutes") or 60
                difficulty = task_data.get("difficulty") or "Orta"

            else:
                task_text = f"{topic} konusunda teknik görev {task_index} tamamla."
                task_type = "Uygulama"
                estimated_minutes = 60
                difficulty = "Orta"

            if task_type not in allowed_task_types:
                task_type = "Uygulama"

            if difficulty not in allowed_difficulties:
                difficulty = "Orta"

            try:
                estimated_minutes = int(estimated_minutes)
            except (TypeError, ValueError):
                estimated_minutes = 60

            if estimated_minutes <= 0:
                estimated_minutes = 60

            normalized_week["tasks"].append({
                "task_text": task_text,
                "task_type": task_type,
                "estimated_minutes": estimated_minutes,
                "difficulty": difficulty
            })

        technical_fallback_tasks = [
            {
                "task_text": f"{topic} konusundaki temel kavramları ve kullanım alanlarını teknik örneklerle öğren.",
                "task_type": "Teori",
                "estimated_minutes": 60,
                "difficulty": "Kolay" if index == 1 else "Orta"
            },
            {
                "task_text": f"{topic} için kullanılan temel araçları, komutları veya yapılandırma adımlarını incele.",
                "task_type": "Araştırma",
                "estimated_minutes": 60,
                "difficulty": "Kolay" if index == 1 else "Orta"
            },
            {
                "task_text": f"{topic} konusunda küçük bir örnek uygulama veya teknik deneme oluştur.",
                "task_type": "Uygulama",
                "estimated_minutes": 90,
                "difficulty": "Orta"
            },
            {
                "task_text": f"{topic} ile ilgili öğrendiğin teknik kavramları kısa bir kontrol listesine dönüştür.",
                "task_type": "Tekrar",
                "estimated_minutes": 45,
                "difficulty": "Kolay"
            }
        ]

        while len(normalized_week["tasks"]) < 4:
            fallback_index = len(normalized_week["tasks"]) % len(technical_fallback_tasks)
            normalized_week["tasks"].append(technical_fallback_tasks[fallback_index].copy())

        raw_resources = week_data.get("resources", [])

        if not isinstance(raw_resources, list):
            raw_resources = []

        for resource_index, resource_data in enumerate(raw_resources, start=1):
            if not isinstance(resource_data, dict):
                resource_data = {}

            resource_url = resource_data.get("resource_url")
            resource_type = resource_data.get("resource_type") or "Dokümantasyon"

            if isinstance(resource_url, str):
                lower_url = resource_url.lower()

                if "youtube.com" in lower_url or "youtu.be" in lower_url:
                    resource_type = "YouTube Video"

            supported_task_text = pick_supported_task_text(
                tasks=normalized_week["tasks"],
                resource_index=resource_index,
                topic=topic
            )

            resource_description = ensure_task_linked_resource_description(
                description=resource_data.get("resource_description"),
                supported_task_text=supported_task_text,
                topic=topic
            )

            normalized_week["resources"].append({
                "resource_title": (
                    resource_data.get("resource_title")
                    or f"{topic} kaynağı {resource_index}"
                ),
                "resource_type": resource_type,
                "resource_description": resource_description,
                "resource_url": resource_url
            })

        while len(normalized_week["resources"]) < 2:
            resource_number = len(normalized_week["resources"]) + 1

            supported_task_text = pick_supported_task_text(
                tasks=normalized_week["tasks"],
                resource_index=resource_number,
                topic=topic
            )

            normalized_week["resources"].append({
                "resource_title": f"{topic} ek kaynak {resource_number}",
                "resource_type": "Dokümantasyon",
                "resource_description": (
                    f"Desteklediği görev/konu: {supported_task_text}. "
                    f"Bu kaynak ilgili haftadaki görevi anlamaya ve uygulamaya yardımcı olur."
                ),
                "resource_url": None
            })

        normalized_plan["weeks"].append(normalized_week)

    while len(normalized_plan["weeks"]) < duration_weeks:
        week_number = len(normalized_plan["weeks"]) + 1

        normalized_plan["weeks"].append({
            "week_number": week_number,
            "title": f"{topic} - Hafta {week_number}",
            "description": f"Bu hafta {topic} konusunda teknik ek çalışmalar yapılacaktır.",
            "estimated_hours": weekly_hours,
            "mini_project": f"{topic} ile ilgili küçük ve uygulanabilir bir mini proje geliştir.",
            "tasks": [
                {
                    "task_text": f"{topic} konusundaki temel kavramları ve kullanım alanlarını teknik örneklerle öğren.",
                    "task_type": "Teori",
                    "estimated_minutes": 60,
                    "difficulty": "Kolay"
                },
                {
                    "task_text": f"{topic} için kullanılan temel araçları, komutları veya yapılandırma adımlarını incele.",
                    "task_type": "Araştırma",
                    "estimated_minutes": 60,
                    "difficulty": "Kolay"
                },
                {
                    "task_text": f"{topic} konusunda küçük bir örnek uygulama veya teknik deneme oluştur.",
                    "task_type": "Uygulama",
                    "estimated_minutes": 90,
                    "difficulty": "Orta"
                },
                {
                    "task_text": f"{topic} ile ilgili öğrendiğin teknik kavramları kısa bir kontrol listesine dönüştür.",
                    "task_type": "Tekrar",
                    "estimated_minutes": 45,
                    "difficulty": "Kolay"
                }
            ],
            "resources": [
                {
                    "resource_title": f"{topic} dokümantasyonu",
                    "resource_type": "Dokümantasyon",
                    "resource_description": f"{topic} öğrenimini destekleyen temel kaynak.",
                    "resource_url": None
                },
                {
                    "resource_title": f"{topic} başlangıç kaynağı",
                    "resource_type": "Video / Kurs",
                    "resource_description": f"{topic} için başlangıç seviyesinde kaynak.",
                    "resource_url": None
                }
            ]
        })

    return normalized_plan


# ============================================================
# FALLBACK LEARNING PLAN
# ============================================================

def generate_fallback_learning_plan(
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    duration_weeks: int,
    learning_preference: str | None = None
) -> Dict[str, Any]:
    """
    Gemini API çalışmadığında kullanılacak basit fallback plan üreticisi.

    Amaç:
    - Demo sırasında sistemin tamamen çökmesini engellemek
    - Kullanıcıya yine de kaydedilebilir ve görüntülenebilir bir plan sunmak
    - Gemini tekrar çalışana kadar MVP akışını korumak
    """

    weeks = []

    for week_number in range(1, duration_weeks + 1):
        weeks.append({
            "week_number": week_number,
            "title": f"{topic} - Hafta {week_number}",
            "description": (
                f"Bu hafta {topic} konusunda seviyene uygun temel çalışmalar yapacaksın."
            ),
            "estimated_hours": weekly_hours,
            "mini_project": (
                f"{topic} ile ilgili küçük ve uygulanabilir bir mini proje geliştir."
            ),
            "tasks": [
                {
                    "task_text": f"{topic} konusundaki temel kavramları öğren.",
                    "task_type": "Teori",
                    "estimated_minutes": 60,
                    "difficulty": "Kolay" if week_number == 1 else "Orta"
                },
                {
                    "task_text": f"{topic} ile ilgili başlangıç seviyesinde örnekleri incele.",
                    "task_type": "Araştırma",
                    "estimated_minutes": 45,
                    "difficulty": "Kolay"
                },
                {
                    "task_text": f"{topic} konusunda basit bir uygulama yap.",
                    "task_type": "Uygulama",
                    "estimated_minutes": 90,
                    "difficulty": "Orta"
                },
                {
                    "task_text": f"Bu hafta öğrendiğin {topic} konularını kısa notlar halinde tekrar et.",
                    "task_type": "Tekrar",
                    "estimated_minutes": 45,
                    "difficulty": "Kolay"
                }
            ],
            "resources": [
                {
                    "resource_title": f"{topic} resmi dokümantasyonu",
                    "resource_type": "Dokümantasyon",
                    "resource_description": (
                        f"{topic} konusunu temel kaynaktan öğrenmek için kullanılabilir."
                    ),
                    "resource_url": None
                },
                {
                    "resource_title": f"{topic} başlangıç seviyesi eğitim içeriği",
                    "resource_type": "Video / Kurs",
                    "resource_description": (
                        f"{topic} konusuna giriş yapmak için başlangıç seviyesinde kaynak araştır."
                    ),
                    "resource_url": None
                }
            ]
        })

    return {
        "topic": topic,
        "level": level,
        "goal": goal,
        "weekly_hours": weekly_hours,
        "duration_weeks": duration_weeks,
        "learning_preference": learning_preference or "Belirtilmedi",
        "summary": (
            f"Bu fallback plan, {topic} konusunu {level} seviyesindeki kullanıcı için "
            f"haftalık görevler ve mini projelerle öğrenilebilir hale getirmek amacıyla oluşturulmuştur."
        ),
        "final_outcome": (
            f"Plan sonunda kullanıcı {topic} konusunda temel kavramları anlayabilecek, "
            f"basit uygulamalar geliştirebilecek ve kendi öğrenme sürecini sürdürebilecek seviyeye gelecektir."
        ),
        "weeks": weeks
    }

def build_regenerate_week_prompt(
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    learning_preference: str | None,
    week_number: int,
    current_week_title: str,
    current_week_description: str | None,
    current_mini_project: str | None,
    current_tasks: list[dict],
    current_resources: list[dict],
    user_instruction: str | None = None
) -> str:
    """
    Mevcut bir haftayı AI ile yeniden düzenlemek için prompt oluşturur.

    Amaç:
    - Sadece seçili haftayı yenilemek
    - Planın diğer haftalarına dokunmamak
    - Daha teknik, görev odaklı ve kaynakları görevlerle ilişkili bir hafta üretmek
    """

    current_tasks_text = "\n".join(
        [
            f"- {task.get('task_text', '')}"
            for task in current_tasks
        ]
    )

    current_resources_text = "\n".join(
        [
            f"- {resource.get('resource_title', '')}: {resource.get('resource_description', '')}"
            for resource in current_resources
        ]
    )

    return f"""
# 1. Context

You are updating one selected week of an existing AI-powered personalized learning plan.

The full plan already exists in the database. You must regenerate only week {week_number}. Other weeks must not be changed.

The updated week will replace the old week content in the database. Therefore, the output must be consistent, structured, technical, and easy to parse.

# 2. Role

Act as an expert AI learning coach, technical mentor, and curriculum designer.

You should improve the selected week by making it more useful, technical, actionable, and aligned with the user's learning goal.

# 3. Constraints

- Return only valid JSON.
- Do not use Markdown.
- Do not add explanations outside the JSON.
- The JSON must be parseable by Python's json.loads().
- All generated content must be written in Turkish.
- Regenerate only week {week_number}.
- Do not generate a full learning plan.
- The week must include at least 4 tasks.
- The week must include at least 2 learning resources.
- The week must include exactly one mini_project field.
- Do not include the mini project as a task.
- Tasks must be technical, concrete, measurable, and topic-specific.
- Avoid generic tasks such as "konuyu çalış", "video izle", "araştırma yap", "not al", or "tekrar et" unless they include specific technical subtopics.
- Each task_text must include concrete concepts, tools, commands, APIs, implementation targets, debugging steps, or practice outputs related to the selected topic.
- task_type must be one of: "Teori", "Uygulama", "Proje", "Tekrar", "Araştırma".
- difficulty must be one of: "Kolay", "Orta", "Zor".
- estimated_minutes must be a positive integer.
- estimated_hours should be close to {weekly_hours}.
- Resources must be directly related to the week's tasks, week title, or mini project.
- Each resource_description must clearly mention which task or subtopic it supports.
- Use this style in resource_description: "Desteklediği görev/konu: ... Bu kaynak ..."
- Do not create YouTube resources.
- Do not create video resources with resource_type such as "Video", "Video Ders", "YouTube Video", or "Video / Kurs".
- YouTube video resources will be added separately by the backend using YouTube Data API.

# 4. Existing Week Data

Plan information:

- topic: "{topic}"
- current_level: "{level}"
- learning_goal: "{goal}"
- weekly_hours: {weekly_hours}
- learning_preference: "{learning_preference or "Belirtilmedi"}"

Selected week:

- week_number: {week_number}
- current_week_title: "{current_week_title}"
- current_week_description: "{current_week_description or "No description"}"
- current_mini_project: "{current_mini_project or "No mini project"}"

Current tasks:

{current_tasks_text or "- No current tasks"}

Current resources:

{current_resources_text or "- No current resources"}

User instruction for this regeneration:

"{user_instruction or "Bu haftayı daha teknik, görev odaklı ve kaynakları görevlerle ilişkili olacak şekilde iyileştir."}"

# 5. Task

Regenerate only this selected week.

The updated week should fit the existing plan, user's level, learning goal, weekly study hours, and learning preference.

# 6. Output Control

Return exactly this JSON structure:

{{
  "week_number": {week_number},
  "title": "Güncellenmiş hafta başlığı",
  "description": "Bu haftanın güncellenmiş kısa açıklaması",
  "estimated_hours": {weekly_hours},
  "mini_project": "Bu haftanın sonunda yapılacak teknik mini proje veya uygulama önerisi",
  "tasks": [
    {{
      "task_text": "Konuya özel teknik görev açıklaması",
      "task_type": "Teori",
      "estimated_minutes": 60,
      "difficulty": "Kolay"
    }},
    {{
      "task_text": "Konuya özel uygulamalı görev açıklaması",
      "task_type": "Uygulama",
      "estimated_minutes": 90,
      "difficulty": "Orta"
    }},
    {{
      "task_text": "Konuya özel tekrar veya analiz görevi",
      "task_type": "Tekrar",
      "estimated_minutes": 45,
      "difficulty": "Kolay"
    }},
    {{
      "task_text": "Konuya özel proje veya entegrasyon görevi",
      "task_type": "Proje",
      "estimated_minutes": 120,
      "difficulty": "Orta"
    }}
  ],
  "resources": [
    {{
      "resource_title": "Kaynak adı",
      "resource_type": "Dokümantasyon",
      "resource_description": "Desteklediği görev/konu: Bu haftadaki belirli görev veya teknik alt konu. Bu kaynak ilgili görevi anlamaya veya uygulamaya yardımcı olur.",
      "resource_url": "https://example.com"
    }},
    {{
      "resource_title": "Kaynak adı",
      "resource_type": "Makale",
      "resource_description": "Desteklediği görev/konu: Bu haftadaki belirli görev veya teknik alt konu. Bu kaynak ilgili görevi anlamaya veya uygulamaya yardımcı olur.",
      "resource_url": null
    }}
  ]
}}
"""

def generate_regenerated_week_with_gemini(
    topic: str,
    level: str,
    goal: str,
    weekly_hours: int,
    learning_preference: str | None,
    week_number: int,
    current_week_title: str,
    current_week_description: str | None,
    current_mini_project: str | None,
    current_tasks: list[dict],
    current_resources: list[dict],
    user_instruction: str | None = None
) -> Dict[str, Any]:
    """
    Seçili haftayı Gemini ile yeniden üretir.

    Gemini hata verirse fallback olarak mevcut haftaya benzer,
    teknik ve güvenli bir hafta yapısı döndürür.
    """

    prompt = build_regenerate_week_prompt(
        topic=topic,
        level=level,
        goal=goal,
        weekly_hours=weekly_hours,
        learning_preference=learning_preference,
        week_number=week_number,
        current_week_title=current_week_title,
        current_week_description=current_week_description,
        current_mini_project=current_mini_project,
        current_tasks=current_tasks,
        current_resources=current_resources,
        user_instruction=user_instruction
    )

    if client is None:
        return generate_fallback_regenerated_week(
            topic=topic,
            weekly_hours=weekly_hours,
            week_number=week_number,
            user_instruction=user_instruction
        )

    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                    safety_settings=DEFAULT_SAFETY_SETTINGS
                )
            )

            response_text = get_response_text_safely(response)
            parsed_week = parse_gemini_json_response(response_text)

            return normalize_regenerated_week(
                week_data=parsed_week,
                topic=topic,
                weekly_hours=weekly_hours,
                week_number=week_number
            )

        except GeminiSafetyRefusalError:
            # Güvenlik reddi durumunda doğrudan fırlatıyoruz, fallback üretilmemeli.
            raise
        except Exception as error:
            error_message = str(error)
            if any(sig in error_message.lower() for sig in ["safety", "block", "harmful", "policy", "abuse", "finish_reason"]):
                raise GeminiSafetyRefusalError(
                    f"Gemini güvenlik politikaları nedeniyle istek engellendi: {error_message}"
                ) from error

            print(f"[Gemini Week Regenerate Error] Attempt {attempt}/{max_retries}: {error}")

            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue

            return generate_fallback_regenerated_week(
                topic=topic,
                weekly_hours=weekly_hours,
                week_number=week_number,
                user_instruction=user_instruction
            )

def normalize_regenerated_week(
    week_data: Dict[str, Any],
    topic: str,
    weekly_hours: int,
    week_number: int
) -> Dict[str, Any]:
    """
    AI tarafından yeniden üretilen haftayı güvenli hale getirir.
    """

    allowed_task_types = {"Teori", "Uygulama", "Proje", "Tekrar", "Araştırma"}
    allowed_difficulties = {"Kolay", "Orta", "Zor"}

    if not isinstance(week_data, dict):
        return generate_fallback_regenerated_week(
            topic=topic,
            weekly_hours=weekly_hours,
            week_number=week_number
        )

    normalized_week = {
        "week_number": week_number,
        "title": week_data.get("title") or f"{topic} - Hafta {week_number}",
        "description": week_data.get("description") or (
            f"Bu hafta {topic} konusunda teknik ve uygulanabilir çalışmalar yapılacaktır."
        ),
        "estimated_hours": week_data.get("estimated_hours") or weekly_hours,
        "mini_project": week_data.get("mini_project") or (
            f"{topic} ile ilgili küçük ve uygulanabilir bir mini proje geliştir."
        ),
        "tasks": [],
        "resources": []
    }

    raw_tasks = week_data.get("tasks", [])

    if not isinstance(raw_tasks, list):
        raw_tasks = []

    for task_index, task_data in enumerate(raw_tasks, start=1):
        if not isinstance(task_data, dict):
            task_data = {}

        task_type = task_data.get("task_type") or "Uygulama"
        difficulty = task_data.get("difficulty") or "Orta"
        estimated_minutes = task_data.get("estimated_minutes") or 60

        if task_type not in allowed_task_types:
            task_type = "Uygulama"

        if difficulty not in allowed_difficulties:
            difficulty = "Orta"

        try:
            estimated_minutes = int(estimated_minutes)
        except (TypeError, ValueError):
            estimated_minutes = 60

        if estimated_minutes <= 0:
            estimated_minutes = 60

        normalized_week["tasks"].append({
            "task_text": (
                task_data.get("task_text")
                or f"{topic} konusunda teknik görev {task_index} tamamla."
            ),
            "task_type": task_type,
            "estimated_minutes": estimated_minutes,
            "difficulty": difficulty
        })

    while len(normalized_week["tasks"]) < 4:
        task_number = len(normalized_week["tasks"]) + 1

        normalized_week["tasks"].append({
            "task_text": f"{topic} konusunda teknik uygulama görevi {task_number} tamamla.",
            "task_type": "Uygulama",
            "estimated_minutes": 60,
            "difficulty": "Orta"
        })

    raw_resources = week_data.get("resources", [])

    if not isinstance(raw_resources, list):
        raw_resources = []

    for resource_index, resource_data in enumerate(raw_resources, start=1):
        if not isinstance(resource_data, dict):
            resource_data = {}

        supported_task_text = pick_supported_task_text(
            tasks=normalized_week["tasks"],
            resource_index=resource_index,
            topic=topic
        )

        resource_description = ensure_task_linked_resource_description(
            description=resource_data.get("resource_description"),
            supported_task_text=supported_task_text,
            topic=topic
        )

        normalized_week["resources"].append({
            "resource_title": (
                resource_data.get("resource_title")
                or f"{topic} kaynağı {resource_index}"
            ),
            "resource_type": resource_data.get("resource_type") or "Dokümantasyon",
            "resource_description": resource_description,
            "resource_url": resource_data.get("resource_url")
        })

    while len(normalized_week["resources"]) < 2:
        resource_number = len(normalized_week["resources"]) + 1

        supported_task_text = pick_supported_task_text(
            tasks=normalized_week["tasks"],
            resource_index=resource_number,
            topic=topic
        )

        normalized_week["resources"].append({
            "resource_title": f"{topic} ek kaynak {resource_number}",
            "resource_type": "Dokümantasyon",
            "resource_description": (
                f"Desteklediği görev/konu: {supported_task_text}. "
                f"Bu kaynak ilgili haftadaki görevi anlamaya ve uygulamaya yardımcı olur."
            ),
            "resource_url": None
        })

    return normalized_week

def generate_fallback_regenerated_week(
    topic: str,
    weekly_hours: int,
    week_number: int,
    user_instruction: str | None = None
) -> Dict[str, Any]:
    """
    Gemini çalışmazsa seçili hafta için güvenli fallback içerik üretir.
    """

    instruction_text = user_instruction or "teknik ve uygulanabilir"

    return {
        "week_number": week_number,
        "title": f"{topic} - Güncellenmiş Hafta {week_number}",
        "description": (
            f"Bu hafta {topic} konusunda {instruction_text} odaklı çalışmalar yapılacaktır."
        ),
        "estimated_hours": weekly_hours,
        "mini_project": (
            f"{topic} konusunda bu haftanın görevlerini birleştiren küçük bir uygulama geliştir."
        ),
        "tasks": [
            {
                "task_text": f"{topic} konusunda bu haftanın ana teknik kavramlarını örneklerle incele.",
                "task_type": "Teori",
                "estimated_minutes": 60,
                "difficulty": "Orta"
            },
            {
                "task_text": f"{topic} için küçük bir uygulama senaryosu oluştur ve temel akışı kodla.",
                "task_type": "Uygulama",
                "estimated_minutes": 90,
                "difficulty": "Orta"
            },
            {
                "task_text": f"{topic} çalışmasında oluşabilecek hata durumlarını analiz et ve çözüm notları çıkar.",
                "task_type": "Tekrar",
                "estimated_minutes": 45,
                "difficulty": "Orta"
            },
            {
                "task_text": f"{topic} ile ilgili haftalık mini projeyi tamamla ve çıktıyı test et.",
                "task_type": "Proje",
                "estimated_minutes": 120,
                "difficulty": "Zor"
            }
        ],
        "resources": [
            {
                "resource_title": f"{topic} resmi dokümantasyonu",
                "resource_type": "Dokümantasyon",
                "resource_description": (
                    f"Desteklediği görev/konu: {topic} konusunda bu haftanın ana teknik kavramlarını örneklerle incele. "
                    f"Bu kaynak resmi veya temel teknik referans olarak kullanılabilir."
                ),
                "resource_url": None
            },
            {
                "resource_title": f"{topic} uygulama kaynağı",
                "resource_type": "Makale",
                "resource_description": (
                    f"Desteklediği görev/konu: {topic} için küçük bir uygulama senaryosu oluştur ve temel akışı kodla. "
                    f"Bu kaynak uygulama odaklı ilerlemeye yardımcı olur."
                ),
                "resource_url": None
            }
        ]
    }


def build_learning_recommendations_prompt(
    plan_history: list[dict],
    existing_topics: list[str],
    limit: int = 6
) -> str:
    """
    Kullanıcının önceki öğrenme planlarına göre yeni öğrenme önerileri üretmek için prompt oluşturur.
    """

    history_text = json.dumps(
        plan_history,
        ensure_ascii=False,
        indent=2
    )

    existing_topics_text = ", ".join(existing_topics)

    return f"""
# 1. Context

You are generating personalized next-learning recommendations for an AI-powered learning platform.

The user has previously created learning plans. Each plan includes a topic, level, goal, weekly study hours, duration, and learning preference.

Your task is to analyze this learning history and suggest new topics the user may want to learn next.

# 2. Role

Act as an expert AI learning advisor, software engineering mentor, and curriculum designer.

# 3. Constraints

- Return only valid JSON.
- Do not use Markdown.
- Do not add explanations outside JSON.
- The JSON must be parseable by Python's json.loads().
- All text content must be written in Turkish.
- Generate exactly {limit} recommendations if possible.
- Do not recommend topics that already exist in the user's learning history.
- Avoid duplicate recommendations.
- Recommendations should be realistic next steps based on the user's previous topics, goals, and levels.
- Prefer recommendations that are naturally related to the user's learning history.
- If the history includes software topics, suggest software, AI, backend, frontend, data, DevOps, testing, architecture, and production-readiness related topics.
- If the history includes gaming, language, design, sport, or other domains, suggest relevant next topics in those domains too.
- Each recommendation must include a clear reason.
- suggested_goal should be specific enough to be used directly when creating a new learning plan.
- suggested_level should be one of: "Başlangıç", "Orta", "İleri".
- suggested_learning_preference should be one of: "Dengeli", "Uygulama ağırlıklı", "Quiz ve tekrar ağırlıklı", "Video ağırlıklı".

# 4. User Learning History

Existing topics:
{existing_topics_text}

Plan history:
{history_text}

# 5. Task

Generate personalized learning recommendations based on the user's previous learning plans.

# 6. Output Control

Return exactly this JSON structure:

{{
  "recommendations": [
    {{
      "topic": "Önerilen konu",
      "reason": "Bu konunun neden önerildiğinin kısa açıklaması",
      "suggested_level": "Orta",
      "suggested_goal": "Bu konu için önerilen öğrenme hedefi",
      "suggested_learning_preference": "Uygulama ağırlıklı"
    }}
  ]
}}
"""

def normalize_recommendation_topic(value: str) -> str:
    """
    Topic karşılaştırması için normalize işlemi yapar.
    """

    return normalize_recommendation_text(value)


def generate_fallback_learning_recommendations(
    existing_topics: list[str],
    limit: int = 6
) -> Dict[str, Any]:
    """
    Gemini çalışmazsa kullanılacak basit öneri sistemi.

    Bu fallback, mevcut topic geçmişine göre statik ama mantıklı öneriler döndürür.
    """

    existing_normalized = {
        normalize_recommendation_topic(topic)
        for topic in existing_topics
    }

    related_topics = {
        "python": [
            {
                "topic": "FastAPI",
                "reason": "Python bilginizi backend API geliştirme tarafına taşıyabilir.",
                "suggested_level": "Orta",
                "suggested_goal": "FastAPI ile REST API geliştirme, veri doğrulama, veritabanı bağlantısı ve endpoint tasarımını öğrenmek.",
                "suggested_learning_preference": "Uygulama ağırlıklı",
            },
            {
                "topic": "Python Unit Testing",
                "reason": "Production seviyesinde Python kodu yazmak için test yazma becerisi önemlidir.",
                "suggested_level": "Orta",
                "suggested_goal": "pytest ve unittest kullanarak test edilebilir Python kodu yazmayı öğrenmek.",
                "suggested_learning_preference": "Quiz ve tekrar ağırlıklı",
            },
        ],
        "react": [
            {
                "topic": "TypeScript",
                "reason": "React projelerinde daha güvenli ve sürdürülebilir kod yazmak için TypeScript iyi bir sonraki adımdır.",
                "suggested_level": "Orta",
                "suggested_goal": "TypeScript ile tip güvenli React componentleri ve frontend uygulamaları geliştirmeyi öğrenmek.",
                "suggested_learning_preference": "Uygulama ağırlıklı",
            },
            {
                "topic": "Next.js",
                "reason": "React bilginizi production seviyesinde full-stack frontend geliştirmeye taşıyabilir.",
                "suggested_level": "Orta",
                "suggested_goal": "Next.js ile routing, SSR, API routes ve production frontend mimarisi öğrenmek.",
                "suggested_learning_preference": "Uygulama ağırlıklı",
            },
        ],
        "docker": [
            {
                "topic": "Kubernetes",
                "reason": "Docker bilgisini container orchestration seviyesine taşımak için uygun bir sonraki konudur.",
                "suggested_level": "Orta",
                "suggested_goal": "Kubernetes ile deployment, service, pod, configmap ve temel cluster yönetimini öğrenmek.",
                "suggested_learning_preference": "Uygulama ağırlıklı",
            },
            {
                "topic": "CI/CD",
                "reason": "Docker ve deployment süreçlerini otomasyonla birleştirmek için CI/CD önemli bir beceridir.",
                "suggested_level": "Orta",
                "suggested_goal": "GitHub Actions veya benzeri araçlarla otomatik test, build ve deployment pipeline oluşturmayı öğrenmek.",
                "suggested_learning_preference": "Uygulama ağırlıklı",
            },
        ],
        "ai": [
            {
                "topic": "RAG Sistemleri",
                "reason": "Yapay zekâ projelerini daha kullanışlı hale getirmek için doküman tabanlı cevaplama sistemleri önemli bir adımdır.",
                "suggested_level": "Orta",
                "suggested_goal": "Embedding, vector database, retrieval ve LLM cevap üretimi ile temel RAG sistemi geliştirmeyi öğrenmek.",
                "suggested_learning_preference": "Uygulama ağırlıklı",
            },
            {
                "topic": "Prompt Engineering",
                "reason": "LLM tabanlı projelerde daha güvenilir çıktı almak için prompt tasarımı önemlidir.",
                "suggested_level": "Orta",
                "suggested_goal": "Context, role, constraints, task ve output format kullanarak etkili promptlar yazmayı öğrenmek.",
                "suggested_learning_preference": "Quiz ve tekrar ağırlıklı",
            },
        ],
    }

    recommendations = []

    for existing_topic in existing_normalized:
        for key, candidates in related_topics.items():
            if key in existing_topic:
                for candidate in candidates:
                    candidate_topic = normalize_recommendation_topic(candidate["topic"])

                    if candidate_topic not in existing_normalized:
                        recommendations.append(candidate)

    generic_recommendations = [
        {
            "topic": "Git ve GitHub Workflow",
            "reason": "Yazılım projelerinde branch, commit, merge ve pull request süreçlerini daha profesyonel yönetmek için önerilir.",
            "suggested_level": "Orta",
            "suggested_goal": "Git branch yönetimi, merge conflict çözümü, pull request akışı ve temiz commit alışkanlıklarını öğrenmek.",
            "suggested_learning_preference": "Uygulama ağırlıklı",
        },
        {
            "topic": "SQL ve Veritabanı Tasarımı",
            "reason": "Backend ve full-stack projelerde güçlü veritabanı bilgisi önemli bir temel beceridir.",
            "suggested_level": "Orta",
            "suggested_goal": "SQL sorguları, tablo ilişkileri, index mantığı ve temel veritabanı tasarımını öğrenmek.",
            "suggested_learning_preference": "Quiz ve tekrar ağırlıklı",
        },
        {
            "topic": "Software Architecture Basics",
            "reason": "Projeleri daha sürdürülebilir ve ölçeklenebilir tasarlamak için mimari bakış açısı kazandırır.",
            "suggested_level": "Orta",
            "suggested_goal": "Katmanlı mimari, servis yapısı, modüler tasarım ve clean code prensiplerini öğrenmek.",
            "suggested_learning_preference": "Uygulama ağırlıklı",
        },
    ]

    for candidate in generic_recommendations:
        candidate_topic = normalize_recommendation_topic(candidate["topic"])

        if candidate_topic not in existing_normalized:
            recommendations.append(candidate)

    return {
        "recommendations": recommendations[:limit]
    }


def normalize_recommendation_text(value: str) -> str:
    """
    Öneri sistemi için metinleri karşılaştırılabilir hale getirir.

    Özellikle:
    - "İleri" -> "ileri"
    - "Başlangıç" -> "baslangic"
    - "Uygulama Ağırlıklı" -> "uygulama agirlikli"
    """

    text = str(value or "").strip().casefold()

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


def normalize_suggested_level(value: str) -> str:
    """
    Gemini'den gelen seviye değerini frontend'deki standart değerlere çevirir.
    """

    normalized = normalize_recommendation_text(value)

    if "bas" in normalized or "beginner" in normalized:
        return "Başlangıç"

    if "ileri" in normalized or "advanced" in normalized:
        return "İleri"

    return "Orta"


def normalize_suggested_learning_preference(value: str) -> str:
    """
    Gemini'den gelen öğrenme tercihini uygulamadaki standart değerlere çevirir.
    """

    normalized = normalize_recommendation_text(value)

    if "video" in normalized:
        return "Video ağırlıklı"

    if "quiz" in normalized or "tekrar" in normalized:
        return "Quiz ve tekrar ağırlıklı"

    if "uygulama" in normalized or "proje" in normalized or "practical" in normalized:
        return "Uygulama ağırlıklı"

    return "Dengeli"



def normalize_learning_recommendations(
    recommendation_data: Dict[str, Any],
    existing_topics: list[str],
    limit: int = 6
) -> Dict[str, Any]:
    """
    Gemini'den gelen öneri çıktısını güvenli hale getirir.
    """

    existing_normalized = {
        normalize_recommendation_topic(topic)
        for topic in existing_topics
    }

    if not isinstance(recommendation_data, dict):
        return generate_fallback_learning_recommendations(
            existing_topics=existing_topics,
            limit=limit
        )

    raw_recommendations = recommendation_data.get("recommendations", [])

    if not isinstance(raw_recommendations, list):
        return generate_fallback_learning_recommendations(
            existing_topics=existing_topics,
            limit=limit
        )

    normalized_recommendations = []
    used_topics = set()

    allowed_levels = {"Başlangıç", "Orta", "İleri"}
    allowed_preferences = {
        "Dengeli",
        "Uygulama ağırlıklı",
        "Quiz ve tekrar ağırlıklı",
        "Video ağırlıklı",
    }

    for item in raw_recommendations:
        if not isinstance(item, dict):
            continue

        topic = str(item.get("topic") or "").strip()

        if not topic:
            continue

        normalized_topic = normalize_recommendation_topic(topic)

        if normalized_topic in existing_normalized:
            continue

        if normalized_topic in used_topics:
            continue

        suggested_level = normalize_suggested_level(
            item.get("suggested_level")
        )

        suggested_learning_preference = normalize_suggested_learning_preference(
            item.get("suggested_learning_preference")
        )

        normalized_recommendations.append({
            "topic": topic,
            "reason": (
                item.get("reason")
                or "Bu konu, önceki öğrenme geçmişinize göre uygun bir sonraki adım olabilir."
            ),
            "suggested_level": suggested_level,
            "suggested_goal": (
                item.get("suggested_goal")
                or f"{topic} konusunda temel ve uygulamalı beceriler kazanmak."
            ),
            "suggested_learning_preference": suggested_learning_preference,
        })

        used_topics.add(normalized_topic)

        if len(normalized_recommendations) >= limit:
            break

    if len(normalized_recommendations) < limit:
        fallback_data = generate_fallback_learning_recommendations(
            existing_topics=existing_topics,
            limit=limit
        )

        for fallback_item in fallback_data.get("recommendations", []):
            if len(normalized_recommendations) >= limit:
                break

            fallback_topic = normalize_recommendation_topic(fallback_item["topic"])

            if fallback_topic in existing_normalized or fallback_topic in used_topics:
                continue

            normalized_recommendations.append(fallback_item)
            used_topics.add(fallback_topic)

    return {
        "recommendations": normalized_recommendations[:limit]
    }




def generate_learning_recommendations_with_gemini(
    plan_history: list[dict],
    limit: int = 6
) -> Dict[str, Any]:
    """
    Kullanıcının önceki öğrenme planlarına göre Gemini ile yeni öğrenme önerileri üretir.

    Kullanıcı sistemi henüz olmadığı için plan_history şu anda veritabanındaki mevcut planlardan oluşur.
    """

    existing_topics = [
        plan.get("topic")
        for plan in plan_history
        if plan.get("topic")
    ]

    if not plan_history:
        return generate_fallback_learning_recommendations(
            existing_topics=[],
            limit=limit
        )

    if client is None:
        return generate_fallback_learning_recommendations(
            existing_topics=existing_topics,
            limit=limit
        )

    prompt = build_learning_recommendations_prompt(
        plan_history=plan_history,
        existing_topics=existing_topics,
        limit=limit
    )

    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                    safety_settings=DEFAULT_SAFETY_SETTINGS
                )
            )

            response_text = get_response_text_safely(response)
            parsed_recommendations = parse_gemini_json_response(response_text)

            return normalize_learning_recommendations(
                recommendation_data=parsed_recommendations,
                existing_topics=existing_topics,
                limit=limit
            )

        except GeminiSafetyRefusalError:
            # Güvenlik reddi durumunda doğrudan fırlatıyoruz
            raise
        except Exception as error:
            error_message = str(error)
            if any(sig in error_message.lower() for sig in ["safety", "block", "harmful", "policy", "abuse", "finish_reason"]):
                raise GeminiSafetyRefusalError(
                    f"Gemini güvenlik politikaları nedeniyle istek engellendi: {error_message}"
                ) from error

            print(f"[Gemini Recommendation Error] Attempt {attempt}/{max_retries}: {error}")

            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue

            return generate_fallback_learning_recommendations(
                existing_topics=existing_topics,
                limit=limit
            )

# ============================================================
# WEEKLY QUIZ PROMPT BUILDER
# ============================================================

def build_weekly_quiz_prompt(
    topic: str,
    level: str,
    goal: str,
    week_title: str,
    week_description: str | None,
    tasks: list[str],
    mini_project: str | None,
    question_count: int = 5
) -> str:
    """
    Builds the prompt for generating a weekly quiz.

    Prompt structure:
    1. Context
    2. Role
    3. Constraints
    4. Task
    5. Template variables
    6. Output control

    The prompt is written in English, but the quiz content must be in Turkish.
    """

    tasks_text = "\n".join([f"- {task}" for task in tasks])

    return f"""
# 1. Context

You are generating a weekly assessment quiz for an AI-powered personalized learning platform.

The user has a learning plan divided into weekly sections. Each week contains a title, description, technical tasks, resources, and a mini project. The quiz should evaluate whether the user understood the main concepts, technical details, and practical goals of the selected week.

The generated quiz will be displayed in the application UI. Therefore, the output must be structured, clear, specific, and easy to parse.

# 2. Role

Act as an expert educational assessment designer, technical mentor, and technical interviewer.

You should create beginner-friendly, fair, practical, concept-focused, and technically relevant multiple-choice questions.

# 3. Constraints

- Return only valid JSON.
- Do not use Markdown.
- Do not add explanations outside the JSON.
- The JSON must be parseable by Python's json.loads().
- All quiz content must be written in Turkish.
- Generate exactly {question_count} questions.
- Each question must have exactly 4 options.
- The correct_answer must exactly match one of the options.
- Each explanation must briefly explain why the answer is correct.
- Questions must be based only on the selected week content.
- Questions must be specific to the week's tasks, week title, week description, and mini project.
- Avoid overly generic learning-process questions.
- Avoid generic questions such as "Why is practice important?" unless the week itself is non-technical.
- Avoid trick questions.
- Avoid duplicate questions.
- Avoid using the same wording pattern in multiple questions.
- Each question must test a different concept from the selected week.
- Include a mix of conceptual, practical, scenario-based, comparison, and debugging-style questions when possible.
- The quiz must be suitable for the user's current level: "{level}".
- Do not include answer labels such as "A)", "B)", "C)", "D)" in the options.
- Do not make the correct answer always the first option.
- Distribute correct answers across different option positions.
- Options must be plausible but clearly distinguishable.
- Incorrect options should be realistic misconceptions, not obviously silly answers.

Question quality rules:
- Question 1 should test a core concept from the week.
- Question 2 should test practical usage or implementation.
- Question 3 should test comparison between two related concepts if possible.
- Question 4 should test scenario-based understanding.
- Question 5 should test mini project or debugging/application logic.
- Do not repeat the same question meaning with different wording.
- Do not ask multiple questions with the same correct answer pattern.

# 4. Task

Generate a weekly multiple-choice quiz for the selected learning week.

The quiz should help the user check their understanding of the week's technical concepts, tasks, and mini project. The questions should be specific enough that they clearly relate to the selected week.

# 5. Template Variables

User and plan information:

- topic: "{topic}"
- current_level: "{level}"
- learning_goal: "{goal}"
- week_title: "{week_title}"
- week_description: "{week_description or "No description provided"}"
- mini_project: "{mini_project or "No mini project provided"}"

Week tasks:

{tasks_text}

# 6. Output Control

Return the output using exactly this JSON structure:

{{
  "quiz_title": "{week_title} Quiz",
  "questions": [
    {{
      "question": "Soru metni",
      "options": [
        "Seçenek 1",
        "Seçenek 2",
        "Seçenek 3",
        "Seçenek 4"
      ],
      "correct_answer": "Doğru seçenek",
      "explanation": "Doğru cevabın kısa açıklaması"
    }}
  ]
}}
"""


# ============================================================
# WEEKLY QUIZ NORMALIZER
# ============================================================

def normalize_quiz_data(
    quiz_data: Dict[str, Any],
    topic: str,
    week_title: str,
    question_count: int = 5
) -> Dict[str, Any]:
    """
    Gemini'den gelen quiz verisini güvenli ve standart hale getirir.

    Amaç:
    - Quiz response yapısının backend ve Streamlit için güvenli olmasını sağlamak
    - Eksik soru varsa fallback sorularla tamamlamak
    - Her soruda tam olarak 4 seçenek olmasını garanti etmek
    - correct_answer değerinin options içinde olmasını garanti etmek
    - Gemini bazen "A", "B", "C", "D" gibi cevap döndürürse bunu gerçek seçenek metnine çevirmek
    - Eksik açıklama varsa varsayılan açıklama eklemek
    """

    def clean_option_text(value: Any) -> str:
        """
        Seçenek metinlerini temizler.

        Örnek:
        - "A) Jenkins pipeline" -> "Jenkins pipeline"
        - "B. Docker container" -> "Docker container"

        Bu işlem UI tarafında daha temiz seçenek göstermemizi sağlar.
        """

        if value is None:
            return ""

        text = str(value).strip()

        prefixes = [
            "A)", "B)", "C)", "D)",
            "A.", "B.", "C.", "D.",
            "1)", "2)", "3)", "4)"
        ]

        for prefix in prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()

        return text

    def resolve_correct_answer(
        correct_answer: Any,
        options: list[str]
    ) -> str:
        """
        correct_answer değerini gerçek seçenek metnine çevirir.

        Gemini bazen doğru cevabı direkt seçenek metni olarak değil,
        "A", "B", "C", "D" gibi harf ile döndürebilir.
        """

        if correct_answer is None:
            return options[0] if options else f"{topic} ile ilgili doğru teknik yaklaşım"

        answer_text = str(correct_answer).strip()

        letter_map = {
            "A": 0,
            "B": 1,
            "C": 2,
            "D": 3,
            "A)": 0,
            "B)": 1,
            "C)": 2,
            "D)": 3,
            "A.": 0,
            "B.": 1,
            "C.": 2,
            "D.": 3,
        }

        if answer_text in letter_map:
            option_index = letter_map[answer_text]

            if 0 <= option_index < len(options):
                return options[option_index]

        return clean_option_text(answer_text)

    if not isinstance(quiz_data, dict):
        return generate_fallback_weekly_quiz(
            topic=topic,
            week_title=week_title,
            question_count=question_count
        )

    quiz_title = quiz_data.get("quiz_title") or f"{week_title} Quiz"
    raw_questions = quiz_data.get("questions", [])

    if not isinstance(raw_questions, list) or len(raw_questions) == 0:
        return generate_fallback_weekly_quiz(
            topic=topic,
            week_title=week_title,
            question_count=question_count
        )

    normalized_questions = []

    for index, question_data in enumerate(raw_questions[:question_count], start=1):
        if not isinstance(question_data, dict):
            continue

        question_text = (
            question_data.get("question")
            or f"{topic} konusunda {index}. teknik değerlendirme sorusu"
        )

        raw_options = question_data.get("options", [])

        if not isinstance(raw_options, list):
            raw_options = []

        cleaned_options = []

        for option in raw_options:
            option_text = clean_option_text(option)

            if option_text and option_text not in cleaned_options:
                cleaned_options.append(option_text)

        correct_answer = resolve_correct_answer(
            question_data.get("correct_answer"),
            cleaned_options
        )

        if correct_answer not in cleaned_options:
            cleaned_options.insert(0, correct_answer)

        fallback_options = [
            f"{topic} ile ilgili temel kavramları anlamak",
            f"{topic} için uygulamalı örnek geliştirmek",
            f"{topic} dokümantasyonunu doğru kullanmak",
            f"{topic} ile ilgili hata çıktısını analiz etmek"
        ]

        for fallback_option in fallback_options:
            if len(cleaned_options) >= 4:
                break

            if fallback_option not in cleaned_options:
                cleaned_options.append(fallback_option)

        if len(cleaned_options) > 4:
            limited_options = [correct_answer]

            for option in cleaned_options:
                if option == correct_answer:
                    continue

                if len(limited_options) >= 4:
                    break

                limited_options.append(option)

            cleaned_options = limited_options

        explanation = (
            question_data.get("explanation")
            or "Bu cevap, haftanın teknik konusu ve görevleriyle doğrudan ilişkilidir."
        )

        normalized_questions.append({
            "question": str(question_text).strip(),
            "options": cleaned_options,
            "correct_answer": correct_answer,
            "explanation": str(explanation).strip()
        })

    if len(normalized_questions) < question_count:
        fallback_quiz = generate_fallback_weekly_quiz(
            topic=topic,
            week_title=week_title,
            question_count=question_count
        )

        for fallback_question in fallback_quiz.get("questions", []):
            if len(normalized_questions) >= question_count:
                break

            normalized_questions.append(fallback_question)

    return {
        "quiz_title": quiz_title,
        "questions": normalized_questions[:question_count]
    }


# ============================================================
# QUIZ OPTION SHUFFLER
# ============================================================

def shuffle_quiz_options(quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quiz seçeneklerini karıştırır.

    Amaç:
    - Doğru cevabın her zaman ilk seçenek olarak gelmesini engellemek
    - Quiz deneyimini daha gerçekçi hale getirmek
    """

    questions = quiz_data.get("questions", [])

    if not isinstance(questions, list):
        quiz_data["questions"] = []
        return quiz_data

    for question in questions:
        if not isinstance(question, dict):
            continue

        options = question.get("options", [])
        correct_answer = question.get("correct_answer")

        if not isinstance(options, list):
            continue

        if correct_answer not in options:
            continue

        random.shuffle(options)
        question["options"] = options

    return quiz_data


# ============================================================
# MAIN WEEKLY QUIZ FUNCTION
# ============================================================

def generate_weekly_quiz_with_gemini(
    topic: str,
    level: str,
    goal: str,
    week_title: str,
    week_description: str | None,
    tasks: list[str],
    mini_project: str | None,
    question_count: int = 5
) -> Dict[str, Any]:
    """
    Gemini API ile seçili hafta için quiz üretir.

    Gemini geçici olarak hata verirse local fallback quiz üretir.
    """

    if client is None:
        print("[Gemini Quiz Fallback] GEMINI_API_KEY bulunamadı. Fallback quiz kullanılacak.")

        fallback_quiz = generate_fallback_weekly_quiz(
            topic=topic,
            week_title=week_title,
            question_count=question_count
        )

        normalized_fallback_quiz = normalize_quiz_data(
            quiz_data=fallback_quiz,
            topic=topic,
            week_title=week_title,
            question_count=question_count
        )

        return shuffle_quiz_options(normalized_fallback_quiz)

    prompt = build_weekly_quiz_prompt(
        topic=topic,
        level=level,
        goal=goal,
        week_title=week_title,
        week_description=week_description,
        tasks=tasks,
        mini_project=mini_project,
        question_count=question_count
    )

    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                    safety_settings=DEFAULT_SAFETY_SETTINGS
                )
            )

            response_text = get_response_text_safely(response)
            parsed_quiz = parse_gemini_json_response(response_text)

            normalized_quiz = normalize_quiz_data(
                quiz_data=parsed_quiz,
                topic=topic,
                week_title=week_title,
                question_count=question_count
            )

            return shuffle_quiz_options(normalized_quiz)

        except GeminiSafetyRefusalError:
            # Güvenlik reddi durumunda doğrudan fırlatıyoruz
            raise
        except Exception as e:
            error_message = str(e)
            if any(sig in error_message.lower() for sig in ["safety", "block", "harmful", "policy", "abuse", "finish_reason"]):
                raise GeminiSafetyRefusalError(
                    f"Gemini güvenlik politikaları nedeniyle istek engellendi: {error_message}"
                ) from e

            print(f"[Gemini Quiz Error] Attempt {attempt}/{max_retries}: {error_message}")

            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue

            print("[Gemini Quiz Fallback] Gemini unavailable. Using fallback quiz.")

            fallback_quiz = generate_fallback_weekly_quiz(
                topic=topic,
                week_title=week_title,
                question_count=question_count
            )

            normalized_fallback_quiz = normalize_quiz_data(
                quiz_data=fallback_quiz,
                topic=topic,
                week_title=week_title,
                question_count=question_count
            )

            return shuffle_quiz_options(normalized_fallback_quiz)


# ============================================================
# FALLBACK WEEKLY QUIZ
# ============================================================

def generate_fallback_weekly_quiz(
    topic: str,
    week_title: str,
    question_count: int = 5
) -> Dict[str, Any]:
    """
    Gemini çalışmadığında kullanılacak konuya bağlı teknik fallback quiz üreticisi.

    Bu fallback tamamen mükemmel teknik doğruluk hedeflemez; amacı sistemin
    çökmeden, konuya yakın ve genel teknik mantığı ölçen bir quiz üretmesidir.
    """

    questions = [
        {
            "question": f"{topic} öğrenirken ilk olarak hangi yaklaşım daha doğru olur?",
            "options": [
                f"{topic} ile ilgili temel kavramları ve kullanım amacını öğrenmek",
                "Sadece ezber yaparak ilerlemek",
                "Hiç uygulama yapmadan sadece sonuçlara bakmak",
                "Kaynakları tamamen atlayarak deneme yapmak"
            ],
            "correct_answer": f"{topic} ile ilgili temel kavramları ve kullanım amacını öğrenmek",
            "explanation": f"{topic} gibi teknik bir konuda önce temel kavramları ve kullanım amacını anlamak daha sağlam bir öğrenme başlangıcı sağlar."
        },
        {
            "question": f"{week_title} kapsamında uygulamalı çalışma yapmanın temel amacı nedir?",
            "options": [
                "Öğrenilen teknik kavramları gerçek veya örnek bir senaryoda pekiştirmek",
                "Konuyu tamamen ezberlemek",
                "Dokümantasyon okumayı gereksiz hale getirmek",
                "Hataları görmezden gelmek"
            ],
            "correct_answer": "Öğrenilen teknik kavramları gerçek veya örnek bir senaryoda pekiştirmek",
            "explanation": "Uygulamalı çalışmalar, teorik bilgilerin pratik kullanımını görmeyi ve hataları erken fark etmeyi sağlar."
        },
        {
            "question": f"{topic} ile çalışırken hata çıktıları veya loglar neden önemlidir?",
            "options": [
                "Sorunun kaynağını anlamak ve doğru çözüm adımını belirlemek için",
                "Sistemi daha yavaş çalıştırmak için",
                "Tüm yapılandırmaları silmek için",
                "Öğrenme sürecini tamamen durdurmak için"
            ],
            "correct_answer": "Sorunun kaynağını anlamak ve doğru çözüm adımını belirlemek için",
            "explanation": "Loglar ve hata çıktıları, teknik problemlerin nedenini anlamak ve doğru düzeltmeyi yapmak için kullanılır."
        },
        {
            "question": f"{topic} konusunda resmi dokümantasyon kullanmanın temel avantajı nedir?",
            "options": [
                "Güncel ve güvenilir bilgiye ulaşmak",
                "Yanlış komutları ezberlemek",
                "Kurulum adımlarını tahmin etmek",
                "Teknik kavramları karıştırmak"
            ],
            "correct_answer": "Güncel ve güvenilir bilgiye ulaşmak",
            "explanation": "Resmi dokümantasyon, teknik araçların güncel kullanımını ve doğru yapılandırma bilgilerini öğrenmek için en güvenilir kaynaklardan biridir."
        },
        {
            "question": f"{week_title} sonunda yapılan mini projenin en önemli katkısı nedir?",
            "options": [
                "Haftanın teknik konularını somut bir çıktıya dönüştürmek",
                "Görevleri tamamen atlamak",
                "Sadece teorik bilgiyle yetinmek",
                "Kaynakları kullanmadan ilerlemek"
            ],
            "correct_answer": "Haftanın teknik konularını somut bir çıktıya dönüştürmek",
            "explanation": "Mini proje, öğrenilen teknik konuların gerçek bir çıktı üzerinde uygulanmasını sağlar."
        }
    ]

    selected_questions = questions[:question_count]

    return {
        "quiz_title": f"{week_title} Quiz",
        "questions": selected_questions
    }


# ============================================================
# QUIZ ANALYSIS FUNCTION
# ============================================================

def analyze_quiz_results_with_gemini(
    quiz_title: str,
    plan_topic: str,
    plan_level: str,
    plan_goal: str,
    details_list: list[dict]
) -> Dict[str, Any]:
    """
    Gemini ile quiz sonuçlarındaki yanlış cevapları analiz ederek zayıf konuları ve önerileri tespit eder.
    """
    if client is None:
        # Fallback analysis
        return {
            "weak_topics": [f"{plan_topic} Temelleri"],
            "summary": "AI Analiz hizmeti şu anda kullanılamıyor. Lütfen quizi genel olarak gözden geçirin.",
            "recommended_actions": ["Yanlış yaptığınız soruların çözümlerini detaylarıyla inceleyin."],
            "recommended_resources": [f"Google üzerinde '{plan_topic} fundamentals' kelimeleriyle arama yapın."]
        }

    # Format the quiz details nicely for Gemini
    formatted_details = []
    for item in details_list:
        status = "Doğru" if item.get("is_correct") else "Yanlış"
        formatted_details.append(
            f"Soru: {item.get('question')}\n"
            f"Kullanıcının Cevabı: {item.get('selected_answer') or 'Boş'}\n"
            f"Doğru Cevap: {item.get('correct_answer')}\n"
            f"Durum: {status}\n"
            f"Açıklama: {item.get('explanation')}\n"
            "---"
        )
    formatted_details_str = "\n".join(formatted_details)

    prompt = f"""
Sistemin Öğrenme Konusu: "{plan_topic}"
Kullanıcı Seviyesi: "{plan_level}"
Öğrenme Hedefi: "{plan_goal}"
Quiz Başlığı: "{quiz_title}"

Kullanıcının çözdüğü quize ait soru ve cevap detayları aşağıdadır:
{formatted_details_str}

Lütfen bu sonuçları analiz et. Özellikle kullanıcının yanlış cevapladığı sorulara odaklanarak zayıf kaldığı veya anlamadığı alt konuları (weak topics) belirle.
Sonucu sadece Türkçe olarak ve aşağıdaki JSON formatında döndür. JSON dışında hiçbir açıklama veya markdown bloğu (```json gibi) ekleme.

Format:
{{
  "weak_topics": ["Zayıf olunan alt konu 1", "Zayıf olunan alt konu 2"],
  "summary": "Kullanıcının quiz genelindeki durumunun, nerede zorlandığının kısa bir özeti.",
  "recommended_actions": [
    "Kullanıcıya özel somut ve uygulanabilir çalışma önerisi 1",
    "Kullanıcıya özel somut ve uygulanabilir çalışma önerisi 2"
  ],
  "recommended_resources": [
    "Kullanıcının bu eksikleri kapatmak için yapabileceği spesifik arama terimleri veya resmi doküman önerileri"
  ]
}}
"""

    max_attempts = 3
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                    safety_settings=DEFAULT_SAFETY_SETTINGS
                )
            )
            response_text = get_response_text_safely(response)
            parsed_analysis = parse_gemini_json_response(response_text)

            return {
                "weak_topics": parsed_analysis.get("weak_topics", []),
                "summary": parsed_analysis.get("summary", "Analiz başarıyla tamamlandı."),
                "recommended_actions": parsed_analysis.get("recommended_actions", []),
                "recommended_resources": parsed_analysis.get("recommended_resources", [])
            }
        except Exception as e:
            last_error = e
            print(f"[Gemini Quiz Analysis Attempt {attempt}/{max_attempts} Failed]: {e}")
            if attempt < max_attempts:
                import time
                time.sleep(1)

    print(f"[Gemini Quiz Analysis Error - All Attempts Failed]: {last_error}")
    return {
        "weak_topics": ["İlgili Konular"],
        "summary": f"Analiz sırasında hata oluştu ({last_error}). Lütfen yanlış cevaplarınızı inceleyin.",
        "recommended_actions": ["Yanlış yaptığınız konulara ait görevleri tekrar gözden geçirin."],
        "recommended_resources": ["Resmi dokümanları kontrol edin."]
    }


# ============================================================
# AI TUTOR CHAT FUNCTION
# ============================================================

def ask_ai_tutor_with_gemini(
    plan_topic: str,
    plan_level: str,
    plan_goal: str,
    week_title: str | None,
    week_description: str | None,
    tasks: list[str],
    chat_history: list[dict],
    user_message: str
) -> str:
    """
    Kullanıcının o anki planı ve haftalık görevleriyle ilgili sorularını cevaplayan AI Eğitmeni.
    """
    if client is None:
        return "Gemini API key tanımlı değil. AI Eğitmeni şu anda çevrimdışı."

    # Build history context
    history_str = ""
    for msg in chat_history:
        sender_label = "Öğrenci" if msg["sender"] == "user" else "Eğitmen"
        history_str += f"{sender_label}: {msg['message']}\n"

    # Context about the active week
    week_context = ""
    if week_title:
        week_context = (
            f"Kullanıcının Şu Anda Çalıştığı Hafta: {week_title}\n"
            f"Hafta Açıklaması: {week_description or 'Yok'}\n"
            f"Haftalık Görevler:\n" + "\n".join([f"- {t}" for t in tasks])
        )
    else:
        week_context = "Kullanıcı genel plan sayfasında, belirli bir haftayı incelemiyor."

    system_instruction = (
        "Sen yapay zekâ destekli kişisel öğrenme platformunda uzman bir Yazılım ve Teknik Eğitmensin (AI Tutor).\n"
        "Görevin, öğrencinin sorularını nazikçe, motive edici, son derece açıklayıcı ve teknik olarak doğru şekilde yanıtlamaktır.\n"
        "Yanıtlarında öğrencilere kod örnekleri sunabilir, teknik kavramları analojilerle açıklayabilirsin.\n"
        "Öğrencinin öğrenme planı ve şu anda çalıştığı haftanın detayları sana verilecektir. Yanıtlarını bu bağlamla doğrudan ilişkilendir.\n"
        "Yanıtlarını Türkçe olarak ver. Kısa ve öz tut, ancak kod örnekleri veya detay gerektiğinde cömert ol. Markdown formatını kullanabilirsin."
    )

    prompt = f"""
--- BAĞLAM ---
Öğrenilen Konu: {plan_topic}
Öğrencinin Seviyesi: {plan_level}
Öğrencinin Hedefi: {plan_goal}

{week_context}

--- SOHBET GEÇMİŞİ ---
{history_str}
Öğrenci: {user_message}
Eğitmen:
"""

    max_attempts = 3
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    safety_settings=DEFAULT_SAFETY_SETTINGS
                )
            )
            return get_response_text_safely(response)
        except Exception as e:
            last_error = e
            print(f"[Gemini AI Tutor Attempt {attempt}/{max_attempts} Failed]: {e}")
            if attempt < max_attempts:
                import time
                time.sleep(1)

    print(f"[Gemini AI Tutor Error - All Attempts Failed]: {last_error}")
    return f"Üzgünüm, sorunuzu işlerken teknik bir hata oluştu ({last_error}). Lütfen tekrar deneyin."