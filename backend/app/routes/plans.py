from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.ai_service import generate_learning_plan_with_gemini, generate_regenerated_week_with_gemini



router = APIRouter(
    prefix="/plans",
    tags=["Plans"]
)



def sort_plan_response(plan: models.LearningPlan):
    """
    API response dönmeden önce plan içindeki haftaları, görevleri ve kaynakları sıralar.

    Amaç:
    - Haftalar her zaman week_number sırasıyla gelsin.
    - Görevler her zaman id sırasıyla gelsin.
    - Kaynaklar her zaman id sırasıyla gelsin.
    - Streamlit ve React tarafında sıralama problemi yaşanmasın.
    """

    if not plan:
        return plan

    plan.weeks = sorted(
        plan.weeks,
        key=lambda week: week.week_number or 0
    )

    for week in plan.weeks:
        week.tasks = sorted(
            week.tasks,
            key=lambda task: task.id or 0
        )

        week.resources = sorted(
            week.resources,
            key=lambda resource: resource.id or 0
        )

    return plan

# Bu fonksiyon, bir planı haftaları/görevleri/kaynakları ile birlikte getirir.
def get_plan_with_details(
    db: Session,
    plan_id: int
):
    """
    Bir öğrenme planını haftaları, görevleri ve kaynakları ile birlikte getirir.
    """

    plan = (
        db.query(models.LearningPlan)
        .options(
            joinedload(models.LearningPlan.weeks)
            .joinedload(models.PlanWeek.tasks),
            joinedload(models.LearningPlan.weeks)
            .joinedload(models.PlanWeek.resources)
        )
        .filter(models.LearningPlan.id == plan_id)
        .first()
    )

    return sort_plan_response(plan)


#Bu fonksiyon, AI’dan gelen normalize edilmiş planı veritabanına kaydeder
def create_plan_from_ai_data(
    db: Session,
    ai_plan: dict,
    fallback_request: schemas.GeneratePlanRequest
):
    """
    AI'dan gelen öğrenme planı verisini veritabanına kaydeder.

    Kaydedilen yapılar:
    - LearningPlan
    - PlanWeek
    - PlanTask
    - PlanResource
    """

    weeks = ai_plan.get("weeks", [])

    if not weeks:
        raise HTTPException(
            status_code=500,
            detail="AI geçerli bir haftalık plan döndürmedi."
        )

    plan = models.LearningPlan(
        topic=ai_plan.get("topic", fallback_request.topic),
        level=ai_plan.get("level", fallback_request.level),
        goal=ai_plan.get("goal", fallback_request.goal),
        weekly_hours=ai_plan.get(
            "weekly_hours",
            fallback_request.weekly_hours
        ),
        duration_weeks=ai_plan.get(
            "duration_weeks",
            fallback_request.duration_weeks
        ),
        learning_preference=ai_plan.get(
            "learning_preference",
            fallback_request.learning_preference
        ),
        summary=ai_plan.get("summary"),
        final_outcome=ai_plan.get("final_outcome")
    )

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
    db.refresh(plan)

    return get_plan_with_details(db, plan.id)


@router.post("/generate", response_model=schemas.PlanResponse)
def generate_learning_plan(
    request: schemas.GeneratePlanRequest,
    db: Session = Depends(get_db)
):
    """
    Kullanıcıdan gelen bilgilere göre Gemini ile kişisel öğrenme planı üretir.
    Üretilen plan, haftalar, görevler ve kaynaklar SQLite veritabanına kaydedilir.
    """

    # ============================================================
    # 1. GEMINI İLE PLAN ÜRETME
    # ============================================================
    # Kullanıcıdan gelen form bilgilerini Gemini'ye gönderiyoruz.
    # Gemini'den beklenen çıktı JSON formatında haftalık öğrenme planıdır.
    try:
        ai_plan = generate_learning_plan_with_gemini(
            topic=request.topic,
            level=request.level,
            goal=request.goal,
            weekly_hours=request.weekly_hours,
            duration_weeks=request.duration_weeks,
            learning_preference=request.learning_preference
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI plan üretimi sırasında hata oluştu: {str(e)}"
        )

    # ============================================================
    # 2. AI ÇIKTISINI KONTROL ETME
    # ============================================================
    # Gemini'den weeks alanı gelmezse planı kaydetmek mantıklı değil.
    weeks = ai_plan.get("weeks", [])

    if not weeks:
        raise HTTPException(
            status_code=500,
            detail="AI geçerli bir haftalık plan döndürmedi."
        )

    # ============================================================
    # 3. ANA PLANI VERİTABANINA KAYDETME
    # ============================================================
    # AI'dan gelen temel plan bilgilerini kaydediyoruz.
    # Eğer AI bazı alanları döndürmezse request içindeki orijinal değerleri kullanıyoruz.
    plan = models.LearningPlan(
        topic=ai_plan.get("topic", request.topic),
        level=ai_plan.get("level", request.level),
        goal=ai_plan.get("goal", request.goal),
        weekly_hours=ai_plan.get("weekly_hours", request.weekly_hours),
        duration_weeks=ai_plan.get("duration_weeks", request.duration_weeks),
        learning_preference=ai_plan.get(
            "learning_preference",
            request.learning_preference
        ),

        # Yeni alanlar:
        summary=ai_plan.get("summary"),
        final_outcome=ai_plan.get("final_outcome")
    )

    try:
        db.add(plan)
        db.flush()

        # ============================================================
        # 4. HAFTALARI, GÖREVLERİ VE KAYNAKLARI KAYDETME
        # ============================================================
        # Artık placeholder plan üretmiyoruz.
        # Doğrudan Gemini'den gelen weeks listesi üzerinden dönüyoruz.
        for week_data in weeks:
            week = models.PlanWeek(
                plan_id=plan.id,
                week_number=week_data.get("week_number"),
                title=week_data.get("title", "Hafta Başlığı"),
                description=week_data.get("description"),

                # Yeni alanlar:
                estimated_hours=week_data.get("estimated_hours"),
                mini_project=week_data.get("mini_project")
            )

            db.add(week)
            db.flush()

            # ========================================================
            # 4.1. HAFTAYA AİT GÖREVLERİ KAYDETME
            # ========================================================
            # Yeni beklenen format:
            # {
            #   "task_text": "...",
            #   "task_type": "Teori",
            #   "estimated_minutes": 60,
            #   "difficulty": "Kolay"
            # }
            #
            # Güvenlik için eski string format gelirse onu da destekliyoruz.
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

            # ========================================================
            # 4.2. HAFTAYA AİT KAYNAKLARI KAYDETME
            # ========================================================
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
    # Planı haftaları, görevleri ve kaynaklarıyla birlikte tekrar çekiyoruz.
    created_plan = (
        db.query(models.LearningPlan)
        .options(
            joinedload(models.LearningPlan.weeks)
            .joinedload(models.PlanWeek.tasks),
            joinedload(models.LearningPlan.weeks)
            .joinedload(models.PlanWeek.resources)
        )
        .filter(models.LearningPlan.id == plan.id)
        .first()
    )

    return sort_plan_response(created_plan)


@router.get("/", response_model=list[schemas.PlanResponse])
def get_all_plans(db: Session = Depends(get_db)):
    """
    Veritabanındaki tüm öğrenme planlarını listeler.
    """

    plans = (
        db.query(models.LearningPlan)
        .options(
            joinedload(models.LearningPlan.weeks)
            .joinedload(models.PlanWeek.tasks),
            joinedload(models.LearningPlan.weeks)
            .joinedload(models.PlanWeek.resources)
        )
        .order_by(models.LearningPlan.created_at.desc())
        .all()
    )

    return [sort_plan_response(plan) for plan in plans]


@router.get("/{plan_id}", response_model=schemas.PlanResponse)
def get_plan_by_id(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Belirli bir öğrenme planını ID'ye göre detaylı şekilde getirir.
    """

    plan = get_plan_with_details(db, plan_id)

    if not plan:
        raise HTTPException(status_code=404, detail="Plan bulunamadı.")

    return plan


@router.get("/{plan_id}/progress", response_model=schemas.ProgressResponse)
def get_plan_progress(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Belirli bir öğrenme planındaki görevlerin tamamlanma yüzdesini hesaplar.
    """

    plan = (
        db.query(models.LearningPlan)
        .filter(models.LearningPlan.id == plan_id)
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Plan bulunamadı.")

    tasks = (
        db.query(models.PlanTask)
        .join(models.PlanWeek)
        .filter(models.PlanWeek.plan_id == plan_id)
        .all()
    )

    total_tasks = len(tasks)
    completed_tasks = len([task for task in tasks if task.is_completed])

    if total_tasks == 0:
        progress_percentage = 0
    else:
        progress_percentage = round((completed_tasks / total_tasks) * 100, 2)

    return {
        "plan_id": plan_id,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "progress_percentage": progress_percentage
    }


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db)
):
    """
    Belirli bir öğrenme planını siler.

    Plana bağlı quiz sonuçları da silinir.
    """

    plan = (
        db.query(models.LearningPlan)
        .filter(models.LearningPlan.id == plan_id)
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Plan bulunamadı.")

    # Plan silinmeden önce bu plana ait quiz sonuçlarını temizliyoruz.
    db.query(models.QuizResult).filter(
        models.QuizResult.plan_id == plan_id
    ).delete(synchronize_session=False)

    db.delete(plan)
    db.commit()

    return {
        "message": "Plan başarıyla silindi.",
        "deleted_plan_id": plan_id
    }


@router.patch("/{plan_id}/weeks/{week_id}/regenerate", response_model=schemas.PlanResponse)
def regenerate_plan_week(
    plan_id: int,
    week_id: int,
    request: schemas.RegenerateWeekRequest,
    db: Session = Depends(get_db)
):
    """
    Seçili haftayı AI ile yeniden üretir.

    Bu endpoint:
    - Sadece seçilen haftayı değiştirir.
    - Planın diğer haftalarına dokunmaz.
    - Eski task/resource kayıtlarını siler.
    - Yeni task/resource kayıtlarını ekler.
    - İlgili haftaya ait eski quiz sonuçlarını temizler.
    """

    plan = (
        db.query(models.LearningPlan)
        .filter(models.LearningPlan.id == plan_id)
        .first()
    )

    if not plan:
        raise HTTPException(
            status_code=404,
            detail="Plan bulunamadı."
        )

    week = (
        db.query(models.PlanWeek)
        .filter(
            models.PlanWeek.id == week_id,
            models.PlanWeek.plan_id == plan_id
        )
        .first()
    )

    if not week:
        raise HTTPException(
            status_code=404,
            detail="Hafta bulunamadı."
        )

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

    updated_plan = get_plan_with_details(
        db=db,
        plan_id=plan_id
    )

    return updated_plan