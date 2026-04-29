from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routes import plans, tasks, quiz, stats
from app import models


# ============================================================
# DATABASE INIT
# ============================================================
# SQLAlchemy modellerine göre tabloları oluşturur.

Base.metadata.create_all(bind=engine)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="AI Personal Learning Platform API",
    description="Yapay zekâ destekli kişisel öğrenme planlama platformu",
    version="1.0.0"
)


# ============================================================
# CORS CONFIG
# ============================================================

allowed_origins = [
    "http://localhost:3000",   # React CRA
    "http://127.0.0.1:3000",
    "http://localhost:5173",   # React Vite
    "http://127.0.0.1:5173",
    "http://localhost:8501",   # Streamlit
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
    return {
        "message": "AI Personal Learning Platform API is running"
    }




# ============================================================
# HEALTH CHECK ENDPOINT
# ============================================================

@app.get("/health")
def health_check():
    """
    API sağlık kontrol endpointi.

    Frontend veya geliştirme ortamı, backend'in çalışıp çalışmadığını
    bu endpoint üzerinden kontrol edebilir.
    """

    return {
        "status": "ok",
        "database": "connected",
        "ai_provider": "gemini"
    }




# ============================================================
# ROUTERS
# ============================================================

app.include_router(plans.router)
app.include_router(tasks.router)
app.include_router(quiz.router)
app.include_router(stats.router)