import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user
from app.ai_service import analyze_quiz_results_with_gemini


router = APIRouter(
    prefix="/quiz-results",
    tags=["Quiz Results"]
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


@router.post("/", response_model=schemas.QuizResultResponse)
def save_quiz_result(
    request: schemas.QuizResultCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Tamamlanan quiz sonucunu veritabanına kaydeder."""

    _verify_plan_ownership(request.plan_id, current_user, db)

    week = (
        db.query(models.PlanWeek)
        .filter(
            models.PlanWeek.id == request.week_id,
            models.PlanWeek.plan_id == request.plan_id
        )
        .first()
    )

    if not week:
        raise HTTPException(status_code=404, detail="Hafta bulunamadı.")

    if request.total_questions <= 0:
        raise HTTPException(status_code=400, detail="Toplam soru sayısı 0'dan büyük olmalıdır.")

    if request.correct_count < 0:
        raise HTTPException(status_code=400, detail="Doğru cevap sayısı negatif olamaz.")

    if request.correct_count > request.total_questions:
        raise HTTPException(
            status_code=400,
            detail="Doğru cevap sayısı toplam soru sayısından büyük olamaz."
        )

    score_percentage = round(
        (request.correct_count / request.total_questions) * 100, 2
    )

    if request.details_json:
        try:
            json.loads(request.details_json)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400,
                detail="details_json geçerli bir JSON formatında olmalıdır."
            )

    quiz_result = models.QuizResult(
        plan_id=request.plan_id,
        week_id=request.week_id,
        quiz_title=request.quiz_title,
        correct_count=request.correct_count,
        total_questions=request.total_questions,
        score_percentage=score_percentage,
        details_json=request.details_json
    )

    db.add(quiz_result)
    db.commit()
    db.refresh(quiz_result)

    return quiz_result


@router.get("/", response_model=list[schemas.QuizResultResponse])
def get_all_quiz_results(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Kimliği doğrulanmış kullanıcıya ait tüm quiz sonuçlarını listeler."""

    user_plan_ids = (
        db.query(models.LearningPlan.id)
        .filter(models.LearningPlan.user_id == current_user.id)
        .subquery()
    )

    results = (
        db.query(models.QuizResult)
        .filter(models.QuizResult.plan_id.in_(user_plan_ids))
        .order_by(models.QuizResult.created_at.desc())
        .all()
    )

    return results


@router.get("/plan/{plan_id}", response_model=list[schemas.QuizResultResponse])
def get_quiz_results_by_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Belirli bir plana ait tüm quiz sonuçlarını listeler."""

    _verify_plan_ownership(plan_id, current_user, db)

    results = (
        db.query(models.QuizResult)
        .filter(models.QuizResult.plan_id == plan_id)
        .order_by(models.QuizResult.created_at.desc())
        .all()
    )

    return results


@router.get("/week/{week_id}", response_model=list[schemas.QuizResultResponse])
def get_quiz_results_by_week(
    week_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Belirli bir haftaya ait quiz sonuçlarını listeler."""

    user_plan_ids = (
        db.query(models.LearningPlan.id)
        .filter(models.LearningPlan.user_id == current_user.id)
        .subquery()
    )

    results = (
        db.query(models.QuizResult)
        .filter(
            models.QuizResult.week_id == week_id,
            models.QuizResult.plan_id.in_(user_plan_ids)
        )
        .order_by(models.QuizResult.created_at.desc())
        .all()
    )

    return results


@router.post("/{result_id}/analyze", response_model=schemas.QuizAnalysisResponse)
def analyze_quiz_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Belirli bir quiz sonucunu Gemini ile analiz ederek zayıf konuları ve çalışma önerilerini döndürür.
    Analiz yapıldıktan sonra veritabanına cache'lenir.
    """
    result = db.query(models.QuizResult).filter(models.QuizResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Quiz sonucu bulunamadı.")

    _verify_plan_ownership(result.plan_id, current_user, db)

    if result.analysis_json:
        try:
            return json.loads(result.analysis_json)
        except json.JSONDecodeError:
            pass

    if not result.details_json:
        raise HTTPException(status_code=400, detail="Bu quiz sonucuna ait detaylı cevap bulunamadı.")

    try:
        details_list = json.loads(result.details_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Cevap detayları okunamadı (geçersiz format).")

    plan = db.query(models.LearningPlan).filter(models.LearningPlan.id == result.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Öğrenme planı bulunamadı.")

    analysis_data = analyze_quiz_results_with_gemini(
        quiz_title=result.quiz_title,
        plan_topic=plan.topic,
        plan_level=plan.level,
        plan_goal=plan.goal,
        details_list=details_list
    )

    result.analysis_json = json.dumps(analysis_data)
    db.commit()

    return analysis_data

