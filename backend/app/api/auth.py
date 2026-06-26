"""REST: регистрация и вход преподавателя (JWT)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_teacher
from app.core.db import get_session
from app.core.security import create_access_token, hash_password, verify_password
from app.models import Teacher
from app.schemas.auth import TeacherOut, TeacherRegister, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: TeacherRegister, session: AsyncSession = Depends(get_session)
) -> TokenResponse:
    exists = (
        await session.execute(select(Teacher).where(Teacher.email == data.email))
    ).scalar_one_or_none()
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Email уже зарегистрирован")
    teacher = Teacher(
        email=data.email, password_hash=hash_password(data.password), name=data.name
    )
    session.add(teacher)
    await session.commit()
    await session.refresh(teacher)
    return TokenResponse(access_token=create_access_token(teacher.id))


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    # OAuth2PasswordRequestForm использует поле username — это email.
    teacher = (
        await session.execute(select(Teacher).where(Teacher.email == form.username))
    ).scalar_one_or_none()
    if teacher is None or not verify_password(form.password, teacher.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль"
        )
    return TokenResponse(access_token=create_access_token(teacher.id))


@router.get("/me", response_model=TeacherOut)
async def me(teacher: Teacher = Depends(get_current_teacher)) -> Teacher:
    return teacher
