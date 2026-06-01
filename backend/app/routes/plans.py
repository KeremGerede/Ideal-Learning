from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.ai_service import (
    generate_learning_plan_with_gemini,
    generate_regenerated_week_with_gemini,
    adapt_week_with_quiz_analysis_with_gemini,
    GeminiSafetyRefusalError,
)
from app.auth import get_current_user
from app.safety import is_harmful_learning_request


router = APIRouter(
    prefix="/plans",
    tags=["Plans"]
)


def sort_plan_response(plan: models.LearningPlan):
    """Sort weeks, tasks, and resources before returning to the client."""

    if not plan:
        return plan

    plan.weeks = sorted(plan.weeks, key=lambda week: week.week_number or 0)

    for week in plan.weeks:
        week.tasks = sorted(week.tasks, key=lambda task: task.id or 0)
        week.resources = sorted(week.resources, key=lambda resource: resource.id or 0)

    return plan


def get_plan_with_details(db: Session, plan_id: int):
    """Fetch a plan with all its weeks, tasks, and resources."""

    plan = (
        db.query(models.LearningPlan)
        .options(
            joinedload(models.LearningPlan.weeks).joinedload(models.PlanWeek.tasks),
            joinedload(models.LearningPlan.weeks).joinedload(models.PlanWeek.resources)
        )
        .filter(models.LearningPlan.id == plan_id)
        .first()
    )

    return sort_plan_response(plan)


def require_plan_ownership(
    plan_id: int,
    current_user: models.User,
    db: Session
) -> models.LearningPlan:
    """
    Returns the plan if it belongs to current_user.
    Raises 404 (not 403) to avoid leaking whether a plan exists.
    """
    plan = (
        db.query(models.LearningPlan)
        .filter(
            models.LearningPlan.id == plan_id,
            models.LearningPlan.user_id == current_user.id
        )
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Plan bulunamadı.")

    return plan


@router.post("/generate", response_model=schemas.PlanResponse)
def generate_learning_plan(
    request: schemas.GeneratePlanRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    AI ile kişisel öğrenme planı oluşturur ve veritabanına kaydeder.

    Akış:
    1. Kullanıcı kimlik doğrulaması (JWT)
    2. Zararlı içerik güvenlik kontrolü (deterministic)
    3. Gemini ile plan üretimi
    4. Gemini güvenlik reddi kontrolü
    5. Planı current_user'a bağlı olarak veritabanına kaydetme
    """

    # ============================================================
    # 1. HARMFUL CONTENT PRE-CHECK
    # ============================================================
    is_harmful, reason = is_harmful_learning_request(
        topic=request.topic,
        goal=request.goal,
        learning_preference=request.learning_preference
    )

    if is_harmful:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu konu güvenli öğrenme politikaları nedeniyle öğrenme planına "
                "dönüştürülemez. Lütfen farklı bir konu veya hedef belirtin."
            )
        )

    # ============================================================
    # 2. GEMINI İLE PLAN ÜRETME
    # ============================================================
    try:
        ai_plan = generate_learning_plan_with_gemini(
            topic=request.topic,
            level=request.level,
            goal=request.goal,
            weekly_hours=request.weekly_hours,
            duration_weeks=request.duration_weeks,
            learning_preference=request.learning_preference
        )

    except GeminiSafetyRefusalError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Bu konu güvenli öğrenme politikaları nedeniyle öğrenme planına "
                "dönüştürülemez. Lütfen farklı bir konu veya hedef belirtin."
            )
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI plan üretimi sırasında hata oluştu: {str(e)}"
        )

    # ============================================================
    # 3. AI ÇIKTISINI KONTROL ETME
    # ============================================================
    weeks = ai_plan.get("weeks", [])

    if not weeks:
        raise HTTPException(
            status_code=500,
            detail="AI geçerli bir haftalık plan döndürmedi."
        )

    # ============================================================
    # 4. PLANI VERİTABANINA KAYDETME (current_user'a bağlı)
    # ============================================================
    plan = models.LearningPlan(
        user_id=current_user.id,
        topic=ai_plan.get("topic", request.topic),
        level=ai_plan.get("level", request.level),
        goal=ai_plan.get("goal", request.goal),
        weekly_hours=ai_plan.get("weekly_hours", request.weekly_hours),
        duration_weeks=ai_plan.get("duration_weeks", request.duration_weeks),
        learning_preference=ai_plan.get("learning_preference", request.learning_preference),
        summary=ai_plan.get("summary"),
        final_outcome=ai_plan.get("final_outcome")
    )

    try:
        db.add(plan)
        db.flush()

        for week_data in weeks:
            week = models.PlanWeek(
                plan_id=plan.id,
                week_number=week_data.get("week_number"),
                title=week_data.get("title", "Hafta Başlığı"),
                description=week_data.get("description"),
                estimated_hours=week_data.get("estimated_hours"),
                mini_project=week_data.get("mini_project")
            )

            db.add(week)
            db.flush()

            for task_data in week_data.get("tasks", []):
                if isinstance(task_data, str):
                    task = models.PlanTask(
                        week_id=week.id,
                        task_text=task_data,
                        is_completed=False
                    )
                else:
                    task = models.PlanTask(
                        week_id=week.id,
                        task_text=task_data.get("task_text", "Görev açıklaması"),
                        task_type=task_data.get("task_type"),
                        estimated_minutes=task_data.get("estimated_minutes"),
                        difficulty=task_data.get("difficulty"),
                        is_completed=False
                    )

                db.add(task)

            for resource_data in week_data.get("resources", []):
                resource = models.PlanResource(
                    week_id=week.id,
                    resource_title=resource_data.get("resource_title", "Kaynak"),
                    resource_type=resource_data.get("resource_type"),
                    resource_description=resource_data.get("resource_description"),
                    resource_url=resource_data.get("resource_url")
                )

                db.add(resource)

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Plan veritabanına kaydedilirken hata oluştu: {str(e)}"
        )

    # ============================================================
    # 5. OLUŞTURULAN PLANI DETAYLI ŞEKİLDE GERİ DÖNDÜRME
    # ============================================================
    return get_plan_with_details(db, plan.id)


@router.get("/", response_model=list[schemas.PlanResponse])
def get_all_plans(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Kimliği doğrulanmış kullanıcının tüm öğrenme planlarını listeler."""

    plans = (
        db.query(models.LearningPlan)
        .options(
            joinedload(models.LearningPlan.weeks).joinedload(models.PlanWeek.tasks),
            joinedload(models.LearningPlan.weeks).joinedload(models.PlanWeek.resources)
        )
        .filter(models.LearningPlan.user_id == current_user.id)
        .order_by(models.LearningPlan.created_at.desc())
        .all()
    )

    return [sort_plan_response(plan) for plan in plans]


@router.get("/{plan_id}", response_model=schemas.PlanResponse)
def get_plan_by_id(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Belirli bir öğrenme planını detaylı şekilde getirir. Kullanıcı sahipliği kontrol edilir."""

    require_plan_ownership(plan_id, current_user, db)
    return get_plan_with_details(db, plan_id)


@router.get("/{plan_id}/progress", response_model=schemas.ProgressResponse)
def get_plan_progress(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Bir öğrenme planındaki görevlerin tamamlanma yüzdesini hesaplar."""

    require_plan_ownership(plan_id, current_user, db)

    tasks = (
        db.query(models.PlanTask)
        .join(models.PlanWeek)
        .filter(models.PlanWeek.plan_id == plan_id)
        .all()
    )

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.is_completed])

    progress_percentage = (
        round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0
    )

    return {
        "plan_id": plan_id,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress_percentage": progress_percentage
    }


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Belirli bir öğrenme planını ve ilgili quiz sonuçlarını siler."""

    plan = require_plan_ownership(plan_id, current_user, db)

    db.query(models.QuizResult).filter(
        models.QuizResult.plan_id == plan_id
    ).delete(synchronize_session=False)

    db.delete(plan)
    db.commit()

    return {"message": "Plan başarıyla silindi.", "deleted_plan_id": plan_id}


@router.patch("/{plan_id}/weeks/{week_id}/regenerate", response_model=schemas.PlanResponse)
def regenerate_plan_week(
    plan_id: int,
    week_id: int,
    request: schemas.RegenerateWeekRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Seçili haftayı AI ile yeniden üretir.
    Sadece seçilen hafta değiştirilir; diğer haftalar korunur.
    """

    # ============================================================
    # HARMFUL CONTENT PRE-CHECK FOR REGISTRATION INSTRUCTION
    # ============================================================
    if request.user_instruction:
        is_harmful, reason = is_harmful_learning_request(
            topic=request.user_instruction,
            goal=""
        )
        if is_harmful:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Bu talep güvenli öğrenme politikaları nedeniyle işlenemez. "
                    "Lütfen farklı veya güvenli bir komut belirtin."
                )
            )

    plan = require_plan_ownership(plan_id, current_user, db)

    week = (
        db.query(models.PlanWeek)
        .filter(
            models.PlanWeek.id == week_id,
            models.PlanWeek.plan_id == plan_id
        )
        .first()
    )

    if not week:
        raise HTTPException(status_code=404, detail="Hafta bulunamadı.")

    current_tasks = [
        {
            "id": task.id,
            "task_text": task.task_text,
            "task_type": task.task_type,
            "estimated_minutes": task.estimated_minutes,
            "difficulty": task.difficulty,
            "is_completed": task.is_completed,
        }
        for task in week.tasks
    ]

    current_resources = [
        {
            "id": resource.id,
            "resource_title": resource.resource_title,
            "resource_type": resource.resource_type,
            "resource_description": resource.resource_description,
            "resource_url": resource.resource_url,
        }
        for resource in week.resources
    ]

    regenerated_week = generate_regenerated_week_with_gemini(
        topic=plan.topic,
        level=plan.level,
        goal=plan.goal,
        weekly_hours=plan.weekly_hours,
        learning_preference=plan.learning_preference,
        week_number=week.week_number,
        current_week_title=week.title,
        current_week_description=week.description,
        current_mini_project=week.mini_project,
        current_tasks=current_tasks,
        current_resources=current_resources,
        user_instruction=request.user_instruction,
    )

    week.title = regenerated_week["title"]
    week.description = regenerated_week["description"]
    week.estimated_hours = regenerated_week["estimated_hours"]
    week.mini_project = regenerated_week["mini_project"]

    for task in list(week.tasks):
        db.delete(task)

    for resource in list(week.resources):
        db.delete(resource)

    old_quiz_results = (
        db.query(models.QuizResult)
        .filter(
            models.QuizResult.plan_id == plan_id,
            models.QuizResult.week_id == week_id
        )
        .all()
    )

    for quiz_result in old_quiz_results:
        db.delete(quiz_result)

    db.flush()

    for task_data in regenerated_week.get("tasks", []):
        new_task = models.PlanTask(
            week_id=week.id,
            task_text=task_data["task_text"],
            task_type=task_data["task_type"],
            estimated_minutes=task_data["estimated_minutes"],
            difficulty=task_data["difficulty"],
            is_completed=False,
        )
        db.add(new_task)

    for resource_data in regenerated_week.get("resources", []):
        new_resource = models.PlanResource(
            week_id=week.id,
            resource_title=resource_data["resource_title"],
            resource_type=resource_data["resource_type"],
            resource_description=resource_data["resource_description"],
            resource_url=resource_data.get("resource_url"),
        )
        db.add(new_resource)

    db.commit()

    return get_plan_with_details(db=db, plan_id=plan_id)


@router.post("/{plan_id}/adapt-from-quiz/{quiz_result_id}", response_model=schemas.PlanResponse)
def adapt_plan_from_quiz(
    plan_id: int,
    quiz_result_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Kullanıcının quiz analizine (zayıf konular) göre müfredatı adapte eder.
    Bir sonraki haftaya veya son haftaysa mevcut haftaya tekrar görevleri & kaynakları ekler.
    """
    import json

    plan = require_plan_ownership(plan_id, current_user, db)

    quiz_result = (
        db.query(models.QuizResult)
        .filter(
            models.QuizResult.id == quiz_result_id,
            models.QuizResult.plan_id == plan_id
        )
        .first()
    )
    if not quiz_result:
        raise HTTPException(status_code=404, detail="Quiz sonucu bulunamadı.")

    if quiz_result.is_adapted:
        raise HTTPException(status_code=400, detail="Bu quiz sonucu için müfredat zaten uyarlandı.")

    if not quiz_result.analysis_json:
        raise HTTPException(
            status_code=400,
            detail="Quiz analiz sonucu bulunamadı. Lütfen önce quiz analizini gerçekleştirin."
        )

    try:
        analysis_data = json.loads(quiz_result.analysis_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Quiz analiz verisi okunamadı.")

    weak_topics = analysis_data.get("weak_topics", [])
    recommended_actions = analysis_data.get("recommended_actions", [])

    if not weak_topics and not recommended_actions:
        raise HTTPException(
            status_code=400,
            detail="Analiz sonucunda zayıf konu veya önerilen eylem bulunmadığı için müfredat uyarlaması yapılamaz."
        )

    # Quiz haftasını bul
    quiz_week = (
        db.query(models.PlanWeek)
        .filter(
            models.PlanWeek.id == quiz_result.week_id,
            models.PlanWeek.plan_id == plan_id
        )
        .first()
    )
    if not quiz_week:
        raise HTTPException(status_code=404, detail="Quizin ait olduğu hafta bulunamadı.")

    # Hedef haftayı belirle (N + 1 veya son haftaysa N)
    n = quiz_week.week_number
    target_week_number = n + 1 if n < plan.duration_weeks else n

    target_week = (
        db.query(models.PlanWeek)
        .filter(
            models.PlanWeek.plan_id == plan_id,
            models.PlanWeek.week_number == target_week_number
        )
        .first()
    )
    if not target_week:
        raise HTTPException(status_code=404, detail=f"Hedef hafta (Hafta {target_week_number}) bulunamadı.")

    # Mevcut görevler ve kaynakları topla
    target_week_tasks = [
        {
            "id": t.id,
            "task_text": t.task_text,
            "task_type": t.task_type,
            "estimated_minutes": t.estimated_minutes,
            "difficulty": t.difficulty,
            "is_completed": t.is_completed
        }
        for t in target_week.tasks
    ]
    target_week_resources = [
        {
            "id": r.id,
            "resource_title": r.resource_title,
            "resource_type": r.resource_type,
            "resource_description": r.resource_description,
            "resource_url": r.resource_url
        }
        for r in target_week.resources
    ]

    # Gemini ile adaptasyon gerçekleştir
    try:
        adapted_data = adapt_week_with_quiz_analysis_with_gemini(
            plan_topic=plan.topic,
            plan_level=plan.level,
            plan_goal=plan.goal,
            plan_weekly_hours=plan.weekly_hours,
            plan_learning_preference=plan.learning_preference,
            target_week_number=target_week.week_number,
            target_week_title=target_week.title,
            target_week_description=target_week.description,
            target_week_mini_project=target_week.mini_project,
            target_week_tasks=target_week_tasks,
            target_week_resources=target_week_resources,
            weak_topics=weak_topics,
            recommended_actions=recommended_actions
        )
    except GeminiSafetyRefusalError:
        raise HTTPException(
            status_code=400,
            detail="Bu istek güvenlik politikaları nedeniyle engellendi."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Müfredat uyarlanırken bir hata oluştu: {str(e)}"
        )

    # Tamamlanma durumlarını korumak için eşleştirme map'i
    original_completed_map = {t["task_text"]: t["is_completed"] for t in target_week_tasks}

    # Hedef haftayı güncelle
    if adapted_data.get("title"):
        target_week.title = adapted_data["title"]
    if adapted_data.get("description"):
        target_week.description = adapted_data["description"]
    if adapted_data.get("estimated_hours"):
        target_week.estimated_hours = adapted_data["estimated_hours"]
    if adapted_data.get("mini_project"):
        target_week.mini_project = adapted_data["mini_project"]

    # Eski görevleri ve kaynakları sil
    for t in list(target_week.tasks):
        db.delete(t)
    for r in list(target_week.resources):
        db.delete(r)
    db.flush()

    # Yeni görevleri ekle
    for task_data in adapted_data.get("tasks", []):
        task_text = task_data["task_text"]
        is_completed = original_completed_map.get(task_text, False)
        new_task = models.PlanTask(
            week_id=target_week.id,
            task_text=task_text,
            task_type=task_data.get("task_type") or "Uygulama",
            estimated_minutes=task_data.get("estimated_minutes") or 60,
            difficulty=task_data.get("difficulty") or "Orta",
            is_completed=is_completed
        )
        db.add(new_task)

    # Yeni kaynakları ekle
    for resource_data in adapted_data.get("resources", []):
        new_resource = models.PlanResource(
            week_id=target_week.id,
            resource_title=resource_data["resource_title"],
            resource_type=resource_data.get("resource_type") or "Dokümantasyon",
            resource_description=resource_data.get("resource_description") or "",
            resource_url=resource_data.get("resource_url")
        )
        db.add(new_resource)

    # Quiz sonucunu güncellendi olarak işaretle
    quiz_result.is_adapted = True

    db.commit()

    return get_plan_with_details(db=db, plan_id=plan_id)
