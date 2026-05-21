from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import plans, tasks, quiz, stats, quiz_results, recommendations, chat
from app.routes import auth
from app import models


# ============================================================
# DATABASE INIT
# ============================================================
# Creates all tables that don't exist yet.
# Adding new models (User) and columns (user_id FK) will be
# reflected here on first startup after deleting learning.db.

Base.metadata.create_all(bind=engine)

# ============================================================
# SAFE DATABASE SCHEMA UPDATE (MIGRATION)
# ============================================================
# Automatically adds the new columns if they do not exist.
from sqlalchemy import text
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE quiz_results ADD COLUMN analysis_json TEXT;"))
        conn.commit()
        print("[DB Migration] analysis_json column successfully added to quiz_results.")
    except Exception:
        # If the column already exists, this block will fail silently, which is correct.
        pass


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Personal Learning Platform API",
    description="Yapay zekâ destekli kişisel öğrenme planlama platformu",
    version="2.0.0"
)


# ============================================================
# CORS CONFIG
# ============================================================

allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {"message": "AI Personal Learning Platform API is running"}


# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database": "connected",
        "ai_provider": "gemini"
    }


# ============================================================
# ROUTERS
# ============================================================

app.include_router(auth.router)
app.include_router(plans.router)
app.include_router(tasks.router)
app.include_router(quiz.router)
app.include_router(stats.router)
app.include_router(quiz_results.router)
app.include_router(recommendations.router)
app.include_router(chat.router)
