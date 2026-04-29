import json
import os
import time
import random
from typing import Any, Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types


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
# Gemini API istemcisi. API key yoksa fonksiyon çağrıldığında hata vereceğiz.
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None


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
- At least one resource per week should include a real URL.
- Prefer official documentation URLs when possible.
- If the topic has official documentation, include it as a resource.
- Prefer reliable, beginner-friendly, and relevant resources.
- Resource URLs must be real and useful.
- If you are not sure about the exact URL, use null instead of inventing fake links.
- Avoid repeating the exact same resources every week unless it is official documentation and still relevant.

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
          "resource_type": "Video / Dokümantasyon / Makale / Uygulama / Kurs",
          "resource_description": "Kaynağın neden önerildiği",
          "resource_url": "https://example.com"
        }},
        {{
          "resource_title": "Kaynak adı",
          "resource_type": "Video / Dokümantasyon / Makale / Uygulama / Kurs",
          "resource_description": "Kaynağın neden önerildiği",
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

    # Model bazen ```json ... ``` şeklinde dönerse temizliyoruz.
    if cleaned_text.startswith("```json"):
        cleaned_text = cleaned_text.replace("```json", "", 1).strip()

    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.replace("```", "", 1).strip()

    if cleaned_text.endswith("```"):
        cleaned_text = cleaned_text[:-3].strip()

    return json.loads(cleaned_text)


# ============================================================
# MAIN AI FUNCTION
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

    Bu sayede demo sırasında sistem tamamen çökmez.
    """

    if client is None:
        raise RuntimeError(
            "GEMINI_API_KEY bulunamadı. Lütfen backend/.env dosyasına GEMINI_API_KEY ekle."
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
                    temperature=0.4
                )
            )

            parsed_plan = parse_gemini_json_response(response.text)

            return normalize_learning_plan(
                ai_plan=parsed_plan,
                topic=topic,
                level=level,
                goal=goal,
                weekly_hours=weekly_hours,
                duration_weeks=duration_weeks,
                learning_preference=learning_preference
            )

        except Exception as e:
            error_message = str(e)

            print(f"[Gemini Error] Attempt {attempt}/{max_retries}: {error_message}")

            # 503, timeout veya geçici servis hatalarında kısa bekleyip tekrar deniyoruz.
            if attempt < max_retries:
                time.sleep(2 * attempt)
                continue

            # Son deneme de başarısızsa fallback plan döndürüyoruz.
            print("[Gemini Fallback] Gemini unavailable. Using fallback learning plan.")

            return generate_fallback_learning_plan(
                topic=topic,
                level=level,
                goal=goal,
                weekly_hours=weekly_hours,
                duration_weeks=duration_weeks,
                learning_preference=learning_preference
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

    # AI istenenden fazla hafta döndürürse kesiyoruz.
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

            normalized_week["resources"].append({
                "resource_title": (
                    resource_data.get("resource_title")
                    or f"{topic} kaynağı {resource_index}"
                ),
                "resource_type": (
                    resource_data.get("resource_type")
                    or "Dokümantasyon"
                ),
                "resource_description": (
                    resource_data.get("resource_description")
                    or f"{topic} öğrenimini destekleyen kaynak."
                ),
                "resource_url": resource_data.get("resource_url")
            })

        while len(normalized_week["resources"]) < 2:
            resource_number = len(normalized_week["resources"]) + 1

            normalized_week["resources"].append({
                "resource_title": f"{topic} ek kaynak {resource_number}",
                "resource_type": "Dokümantasyon",
                "resource_description": f"{topic} öğrenimini destekleyen ek kaynak.",
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

def shuffle_quiz_options(quiz_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Quiz seçeneklerini karıştırır.

    Amaç:
    - Doğru cevabın her zaman ilk seçenek olarak gelmesini engellemek
    - Quiz deneyimini daha gerçekçi hale getirmek

    correct_answer metni değişmez.
    Sadece options sırası karıştırılır.
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
        raise RuntimeError(
            "GEMINI_API_KEY bulunamadı. Lütfen backend/.env dosyasına GEMINI_API_KEY ekle."
        )

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
                    temperature=0.3
                )
            )

            parsed_quiz = parse_gemini_json_response(response.text)
            return shuffle_quiz_options(parsed_quiz)

        except Exception as e:
            error_message = str(e)
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

            return shuffle_quiz_options(fallback_quiz)


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