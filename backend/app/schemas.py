from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class GeneratePlanRequest(BaseModel):
    topic: str
    level: str
    goal: str
    weekly_hours: int
    duration_weeks: int
    learning_preference: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    task_text: str
    is_completed: bool

    # Yeni alanlar:
    task_type: Optional[str] = None
    estimated_minutes: Optional[int] = None
    difficulty: Optional[str] = None

    class Config:
        from_attributes = True


class ResourceResponse(BaseModel):
    id: int
    resource_title: str
    resource_type: Optional[str] = None
    resource_description: Optional[str] = None
    resource_url: Optional[str] = None

    class Config:
        from_attributes = True


class WeekResponse(BaseModel):
    id: int
    week_number: int
    title: str
    description: Optional[str] = None

    # Yeni alanlar:
    estimated_hours: Optional[int] = None
    mini_project: Optional[str] = None

    tasks: List[TaskResponse] = []
    resources: List[ResourceResponse] = []

    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    id: int
    topic: str
    level: str
    goal: str
    weekly_hours: int
    duration_weeks: int
    learning_preference: Optional[str] = None

    # Yeni alanlar:
    summary: Optional[str] = None
    final_outcome: Optional[str] = None

    created_at: datetime
    weeks: List[WeekResponse] = []

    class Config:
        from_attributes = True


class ProgressResponse(BaseModel):
    plan_id: int
    total_tasks: int
    completed_tasks: int
    progress_percentage: float


class QuizQuestionResponse(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: str


class QuizResponse(BaseModel):
    plan_id: int
    week_id: int
    quiz_title: str
    questions: List[QuizQuestionResponse]


class StatsOverviewResponse(BaseModel):
    total_plans: int
    total_tasks: int
    completed_tasks: int
    overall_progress_percentage: float

    # Quiz istatistikleri
    total_quizzes: int
    average_quiz_score: float
    latest_quiz_score: float | None = None

class QuizResultCreate(BaseModel):
    plan_id: int
    week_id: int
    quiz_title: str
    correct_count: int
    total_questions: int

    # Quiz soru/cevap detayları JSON string olarak backend'e gönderilir.
    details_json: Optional[str] = None


class QuizResultResponse(BaseModel):
    id: int
    plan_id: int
    week_id: int
    quiz_title: str
    correct_count: int
    total_questions: int
    score_percentage: float

    # Kaydedilmiş quiz detayları.
    details_json: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True


class RegenerateWeekRequest(BaseModel):
    """
    Seçili haftayı AI ile yeniden düzenlemek için kullanılan request modeli.

    user_instruction:
    Kullanıcının o hafta için özel isteğini tutar.
    Örnek:
    - "Bu haftayı daha uygulama ağırlıklı yap."
    - "Kaynakları daha teknik hale getir."
    - "Görevleri ileri seviyeye çek."
    """

    user_instruction: Optional[str] = None

    

class LearningRecommendation(BaseModel):
    """
    Kullanıcının önceki öğrenme planlarına göre önerilen yeni konu.
    """

    topic: str
    reason: str
    suggested_level: str
    suggested_goal: str
    suggested_learning_preference: Optional[str] = None


class LearningRecommendationsResponse(BaseModel):
    """
    Öneri endpointinin response modeli.
    """

    based_on_plan_count: int
    recommendations: List[LearningRecommendation]