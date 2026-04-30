from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas


router = APIRouter(
    prefix="/stats",
    tags=["Stats"]
)


@router.get("/overview", response_model=schemas.StatsOverviewResponse)
def get_stats_overview(db: Session = Depends(get_db)):
    """
    Sistemdeki genel dashboard istatistiklerini döndürür.

    Şu an authentication olmadığı için tüm kayıtlı planlar, görevler
    ve quiz sonuçları üzerinden genel bir özet hesaplanır.
    """

    # Plan ve görev sayıları
    total_plans = db.query(models.LearningPlan).count()
    total_tasks = db.query(models.PlanTask).count()

    completed_tasks = (
        db.query(models.PlanTask)
        .filter(models.PlanTask.is_completed == True)
        .count()
    )

    # Genel görev ilerleme yüzdesi
    if total_tasks == 0:
        overall_progress_percentage = 0
    else:
        overall_progress_percentage = round(
            (completed_tasks / total_tasks) * 100,
            2
        )

    # Toplam kaydedilmiş quiz sonucu sayısı
    total_quizzes = db.query(models.QuizResult).count()

    # Ortalama quiz başarı oranı
    average_quiz_score = (
        db.query(func.avg(models.QuizResult.score_percentage))
        .scalar()
    )

    if average_quiz_score is None:
        average_quiz_score = 0
    else:
        average_quiz_score = round(float(average_quiz_score), 2)

    # En son kaydedilen quiz sonucu
    latest_quiz = (
        db.query(models.QuizResult)
        .order_by(models.QuizResult.created_at.desc())
        .first()
    )

    latest_quiz_score = None

    if latest_quiz:
        latest_quiz_score = latest_quiz.score_percentage

    return {
        "total_plans": total_plans,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overall_progress_percentage": overall_progress_percentage,
        "total_quizzes": total_quizzes,
        "average_quiz_score": average_quiz_score,
        "latest_quiz_score": latest_quiz_score
    }