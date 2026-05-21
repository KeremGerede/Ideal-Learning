from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# ================================================================
# AUTH SCHEMAS
# ================================================================

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


# ================================================================
# PLAN SCHEMAS
# ================================================================

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


# ================================================================
# QUIZ SCHEMAS
# ================================================================

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


# ================================================================
# STATS SCHEMAS
# ================================================================

class StatsOverviewResponse(BaseModel):
    total_plans: int
    total_tasks: int
    completed_tasks: int
    overall_progress_percentage: float
    total_quizzes: int
    average_quiz_score: float
    latest_quiz_score: float | None = None


# ================================================================
# QUIZ RESULT SCHEMAS
# ================================================================

class QuizResultCreate(BaseModel):
    plan_id: int
    week_id: int
    quiz_title: str
    correct_count: int
    total_questions: int
    details_json: Optional[str] = None


class QuizResultResponse(BaseModel):
    id: int
    plan_id: int
    week_id: int
    quiz_title: str
    correct_count: int
    total_questions: int
    score_percentage: float
    details_json: Optional[str] = None
    analysis_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ================================================================
# CHAT SCHEMAS
# ================================================================

class ChatMessageCreate(BaseModel):
    message: str
    week_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: int
    plan_id: int
    week_id: Optional[int] = None
    sender: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuizAnalysisResponse(BaseModel):
    weak_topics: List[str]
    summary: str
    recommended_actions: List[str]
    recommended_resources: List[str]


# ================================================================
# WEEK REGENERATION SCHEMA
# ================================================================

class RegenerateWeekRequest(BaseModel):
    user_instruction: Optional[str] = None


# ================================================================
# RECOMMENDATIONS SCHEMAS
# ================================================================

class LearningRecommendation(BaseModel):
    topic: str
    reason: str
    suggested_level: str
    suggested_goal: str
    suggested_learning_preference: Optional[str] = None


class LearningRecommendationsResponse(BaseModel):
    based_on_plan_count: int
    recommendations: List[LearningRecommendation]
