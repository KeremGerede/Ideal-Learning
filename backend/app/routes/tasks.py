from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)


@router.patch("/{task_id}/complete", response_model=schemas.TaskResponse)
def update_task_completion(
    task_id: int,
    is_completed: bool,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Görevin tamamlanma durumunu günceller.
    Görevin sahibi olan kullanıcı doğrulanır.
    """

    task = db.query(models.PlanTask).filter(models.PlanTask.id == task_id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

    # Verify ownership: task -> week -> plan -> user
    plan = (
        db.query(models.LearningPlan)
        .join(models.PlanWeek)
        .filter(
            models.PlanWeek.id == task.week_id,
            models.LearningPlan.user_id == current_user.id
        )
        .first()
    )

    if not plan:
        raise HTTPException(status_code=404, detail="Görev bulunamadı.")

    task.is_completed = is_completed
    db.commit()
    db.refresh(task)

    return task
