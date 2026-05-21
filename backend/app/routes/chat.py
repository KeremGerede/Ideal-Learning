from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.ai_service import ask_ai_tutor_with_gemini

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


def _verify_plan_ownership(plan_id: int, current_user: models.User, db: Session):
    """Raises 404 if the plan doesn't exist or doesn't belong to current_user."""
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


@router.get("/plans/{plan_id}/messages", response_model=list[schemas.ChatMessageResponse])
def get_chat_messages(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Belirli bir öğrenme planı için geçmiş sohbet mesajlarını listeler."""
    _verify_plan_ownership(plan_id, current_user, db)

    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.plan_id == plan_id)
        .order_by(models.ChatMessage.created_at.asc())
        .all()
    )
    return messages


@router.post("/plans/{plan_id}/ask", response_model=schemas.ChatMessageResponse)
def ask_ai_tutor(
    plan_id: int,
    request: schemas.ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    AI Eğitmenine soru sorar.
    O anki haftanın bağlamını ve sohbet geçmişini Gemini'a gönderir, yanıtı veritabanına kaydeder.
    """
    plan = _verify_plan_ownership(plan_id, current_user, db)

    # 1. Save user message to database
    user_msg = models.ChatMessage(
        plan_id=plan_id,
        week_id=request.week_id,
        sender="user",
        message=request.message
    )
    db.add(user_msg)
    db.commit()

    # 2. Get recent chat history (last 10 messages)
    history_msgs = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.plan_id == plan_id)
        .order_by(models.ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )
    history_msgs.reverse()

    chat_history_data = [
        {"sender": msg.sender, "message": msg.message}
        for msg in history_msgs
        if msg.id != user_msg.id  # Exclude the message we just added so it's not duplicated
    ]

    # 3. Retrieve week details if week_id is active
    week_title = None
    week_description = None
    tasks = []

    if request.week_id:
        week = (
            db.query(models.PlanWeek)
            .filter(
                models.PlanWeek.id == request.week_id,
                models.PlanWeek.plan_id == plan_id
            )
            .first()
        )
        if week:
            week_title = week.title
            week_description = week.description
            tasks = [t.task_text for t in week.tasks]

    # 4. Invoke Gemini with contexts
    ai_response = ask_ai_tutor_with_gemini(
        plan_topic=plan.topic,
        plan_level=plan.level,
        plan_goal=plan.goal,
        week_title=week_title,
        week_description=week_description,
        tasks=tasks,
        chat_history=chat_history_data,
        user_message=request.message
    )

    # 5. Save AI response to database
    assistant_msg = models.ChatMessage(
        plan_id=plan_id,
        week_id=request.week_id,
        sender="assistant",
        message=ai_response
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return assistant_msg
