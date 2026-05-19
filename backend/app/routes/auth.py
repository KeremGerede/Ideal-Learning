from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
def register(request: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Yeni kullanıcı kaydı oluşturur.
    Aynı kullanıcı adı veya e-posta adresi zaten kayıtlıysa hata döner.
    """

    if db.query(models.User).filter(models.User.username == request.username).first():
        raise HTTPException(
            status_code=400,
            detail="Bu kullanıcı adı zaten kullanılıyor."
        )

    if db.query(models.User).filter(models.User.email == request.email).first():
        raise HTTPException(
            status_code=400,
            detail="Bu e-posta adresi zaten kullanılıyor."
        )

    if len(request.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Şifre en az 6 karakter olmalıdır."
        )

    user = models.User(
        username=request.username,
        email=request.email,
        hashed_password=hash_password(request.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(request: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    Kullanıcı adı ve şifre ile giriş yapar.
    Başarılı girişte JWT access token döner.
    """

    user = db.query(models.User).filter(
        models.User.username == request.username
    ).first()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    Geçerli token'ın sahibi olan kullanıcı bilgilerini döner.
    """
    return current_user
