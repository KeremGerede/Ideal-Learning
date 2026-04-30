from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)

    topic = Column(String, nullable=False)
    level = Column(String, nullable=False)
    goal = Column(Text, nullable=False)
    weekly_hours = Column(Integer, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    learning_preference = Column(String, nullable=True)

    # AI tarafından oluşturulan planın kısa genel özeti.
    summary = Column(Text, nullable=True)

    # Plan sonunda kullanıcının kazanacağı becerileri açıklar.
    final_outcome = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # LearningPlan -> PlanWeek ilişkisi.
    # Bir öğrenme planının birden fazla haftası olabilir.
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

    # Bu hafta için önerilen tahmini çalışma süresi.
    estimated_hours = Column(Integer, nullable=True)

    # Haftanın sonunda yapılabilecek mini uygulama/proje önerisi.
    mini_project = Column(Text, nullable=True)

    # PlanWeek -> LearningPlan ilişkisi.
    plan = relationship(
        "LearningPlan",
        back_populates="weeks"
    )

    # PlanWeek -> PlanTask ilişkisi.
    # Bir haftanın birden fazla görevi olabilir.
    tasks = relationship(
        "PlanTask",
        back_populates="week",
        cascade="all, delete-orphan",
        order_by="PlanTask.id"
    )

    # PlanWeek -> PlanResource ilişkisi.
    # Bir haftanın birden fazla kaynak önerisi olabilir.
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

    # Görevin türü. Örn: Teori, Uygulama, Proje, Tekrar, Araştırma.
    task_type = Column(String, nullable=True)

    # Görev için önerilen tahmini süre.
    estimated_minutes = Column(Integer, nullable=True)

    # Görevin zorluk seviyesi. Örn: Kolay, Orta, Zor.
    difficulty = Column(String, nullable=True)

    # PlanTask -> PlanWeek ilişkisi.
    week = relationship(
        "PlanWeek",
        back_populates="tasks"
    )


class PlanResource(Base):
    __tablename__ = "plan_resources"

    id = Column(Integer, primary_key=True, index=True)

    week_id = Column(Integer, ForeignKey("plan_weeks.id"), nullable=False)
    resource_title = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_description = Column(Text, nullable=True)
    resource_url = Column(Text, nullable=True)

    # PlanResource -> PlanWeek ilişkisi.
    week = relationship(
        "PlanWeek",
        back_populates="resources"
    )

class QuizResult(Base):
    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)

    # Hangi plana ait quiz sonucu olduğunu tutar.
    plan_id = Column(Integer, ForeignKey("learning_plans.id"), nullable=False)

    # Hangi haftaya ait quiz sonucu olduğunu tutar.
    week_id = Column(Integer, ForeignKey("plan_weeks.id"), nullable=False)

    quiz_title = Column(String, nullable=False)

    correct_count = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    score_percentage = Column(Integer, nullable=False)

    # Quizdeki soru, kullanıcının cevabı, doğru cevap ve açıklama detaylarını JSON string olarak saklar.
    # MVP için ayrı quiz_questions / quiz_answers tabloları yerine sade bir JSON alanı kullanıyoruz.
    details_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
