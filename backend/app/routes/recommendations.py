from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.ai_service import generate_learning_recommendations_with_gemini
from app.auth import get_current_user
from app.database import get_db


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"]
)


@router.get("/", response_model=schemas.LearningRecommendationsResponse)
def get_learning_recommendations(
    limit: int = 6,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Kimliği doğrulanmış kullanıcının öğrenme planlarına göre
    kişiselleştirilmiş yeni öğrenme önerileri üretir.
    Her kullanıcı yalnızca kendi planlarına göre öneri alır.
    """

    plans = (
        db.query(models.LearningPlan)
        .filter(models.LearningPlan.user_id == current_user.id)
        .order_by(models.LearningPlan.id.desc())
        .limit(10)
        .all()
    )

    plan_history = [
        {
            "id": plan.id,
            "topic": plan.topic,
            "level": plan.level,
            "goal": plan.goal,
            "weekly_hours": plan.weekly_hours,
            "duration_weeks": plan.duration_weeks,
            "learning_preference": plan.learning_preference,
        }
        for plan in plans
    ]

    recommendation_data = generate_learning_recommendations_with_gemini(
        plan_history=plan_history,
        limit=limit
    )

    return {
        "based_on_plan_count": len(plan_history),
        "recommendations": recommendation_data.get("recommendations", [])
    }
