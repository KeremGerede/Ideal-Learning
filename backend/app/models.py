from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plans = relationship(
        "LearningPlan",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Owner of this plan. nullable=True for safe migration of existing data.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)
    goal = Column(Text, nullable=False)
    weekly_hours = Column(Integer, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    learning_preference = Column(String, nullable=True)

    summary = Column(Text, nullable=True)
    final_outcome = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="plans")

    weeks = relationship(
        "PlanWeek",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanWeek.week_number"
    )


class PlanWeek(Base):
    __tablename__ = "plan_weeks"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False)
    week_number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    mini_project = Column(Text, nullable=True)

    plan = relationship("LearningPlan", back_populates="weeks")

    tasks = relationship(
        "PlanTask",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="PlanTask.id"
    )

    resources = relationship(
        "PlanResource",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="PlanResource.id"
    )


class PlanTask(Base):
    __tablename__ = "plan_tasks"

    id = Column(Integer, primary_key=True, index=True)

    week_id = Column(Integer, ForeignKey("plan_weeks.id"), nullable=False)
    task_text = Column(Text, nullable=False)
    is_completed = Column(Boolean, default=False)

    task_type = Column(String, nullable=True)
    estimated_minutes = Column(Integer, nullable=True)
    difficulty = Column(String, nullable=True)

    week = relationship("PlanWeek", back_populates="tasks")


class PlanResource(Base):
    __tablename__ = "plan_resources"

    id = Column(Integer, primary_key=True, index=True)

    week_id = Column(Integer, ForeignKey("plan_weeks.id"), nullable=False)
    resource_title = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_description = Column(Text, nullable=True)
    resource_url = Column(Text, nullable=True)

    week = relationship("PlanWeek", back_populates="resources")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False)
    week_id = Column(Integer, ForeignKey("plan_weeks.id"), nullable=False)

    quiz_title = Column(String, nullable=False)

    correct_count = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    score_percentage = Column(Integer, nullable=False)

    details_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
