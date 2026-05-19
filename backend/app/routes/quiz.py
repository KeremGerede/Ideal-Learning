from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas
from app.ai_service import generate_weekly_quiz_with_gemini
from app.auth import get_current_user


router = APIRouter(
    prefix="/quiz",
    tags=["Quiz"]
)


@router.post(
    "/plans/{plan_id}/weeks/{week_id}/generate",
    response_model=schemas.QuizResponse
)
def generate_weekly_quiz(
    plan_id: int,
    week_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Belirli bir öğrenme planının belirli haftası için quiz üretir.
    Planın kimliği doğrulanmış kullanıcıya ait olması gerekir.
    """

    # Ownership check: plan must belong to current user.
    plan = (
        db.query(models.LearningPlan)
        .options(
            joinedload(models.LearningPlan.weeks).joinedload(models.PlanWeek.tasks)
        )
        .filter(
            models.LearningPlan.id == plan_id,
            models.LearningPlan.user_id == current_user.id
        )
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Plan bulunamadı.")

    selected_week = next(
        (week for week in plan.weeks if week.id == week_id),
        None
    )

    if not selected_week:
        raise HTTPException(status_code=404, detail="Hafta bulunamadı.")

    task_texts = [task.task_text for task in selected_week.tasks]

    try:
        quiz_data = generate_weekly_quiz_with_gemini(
            topic=plan.topic,
            level=plan.level,
            goal=plan.goal,
            week_title=selected_week.title,
            week_description=selected_week.description,
            tasks=task_texts,
            mini_project=selected_week.mini_project,
            question_count=5
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Quiz üretimi sırasında hata oluştu: {str(e)}"
        )

    return {
        "plan_id": plan_id,
        "week_id": week_id,
        "quiz_title": quiz_data.get("quiz_title", f"{selected_week.title} Quiz"),
        "questions": quiz_data.get("questions", [])
    }
