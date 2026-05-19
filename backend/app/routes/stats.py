from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user


router = APIRouter(
    prefix="/stats",
    tags=["Stats"]
)


@router.get("/overview", response_model=schemas.StatsOverviewResponse)
def get_stats_overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Kimliği doğrulanmış kullanıcıya ait dashboard istatistiklerini döndürür.
    Her kullanıcı yalnızca kendi planlarına ve quiz sonuçlarına ait istatistikleri görür.
    """

    # Kullanıcıya ait plan ID'lerini al
    user_plan_ids = (
        db.query(models.LearningPlan.id)
        .filter(models.LearningPlan.user_id == current_user.id)
        .subquery()
    )

    total_plans = (
        db.query(models.LearningPlan)
        .filter(models.LearningPlan.user_id == current_user.id)
        .count()
    )

    total_tasks = (
        db.query(models.PlanTask)
        .join(models.PlanWeek)
        .filter(models.PlanWeek.plan_id.in_(user_plan_ids))
        .count()
    )

    completed_tasks = (
        db.query(models.PlanTask)
        .join(models.PlanWeek)
        .filter(
            models.PlanWeek.plan_id.in_(user_plan_ids),
            models.PlanTask.is_completed == True
        )
        .count()
    )

    overall_progress_percentage = (
        round((completed_tasks / total_tasks) * 100, 2) if total_tasks > 0 else 0
    )

    total_quizzes = (
        db.query(models.QuizResult)
        .filter(models.QuizResult.plan_id.in_(user_plan_ids))
        .count()
    )

    average_quiz_score = (
        db.query(func.avg(models.QuizResult.score_percentage))
        .filter(models.QuizResult.plan_id.in_(user_plan_ids))
        .scalar()
    )

    if average_quiz_score is None:
        average_quiz_score = 0
    else:
        average_quiz_score = round(float(average_quiz_score), 2)

    latest_quiz = (
        db.query(models.QuizResult)
        .filter(models.QuizResult.plan_id.in_(user_plan_ids))
        .order_by(models.QuizResult.created_at.desc())
        .first()
    )

    latest_quiz_score = latest_quiz.score_percentage if latest_quiz else None

    return {
        "total_plans": total_plans,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overall_progress_percentage": overall_progress_percentage,
        "total_quizzes": total_quizzes,
        "average_quiz_score": average_quiz_score,
        "latest_quiz_score": latest_quiz_score
    }
