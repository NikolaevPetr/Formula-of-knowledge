"""Общие зависимости REST API: текущий преподаватель из JWT."""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models import Teacher

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Не удалось проверить учётные данные",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_teacher(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> Teacher:
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise _CREDENTIALS_EXC
    teacher = await session.get(Teacher, int(payload["sub"]))
    if teacher is None:
        raise _CREDENTIALS_EXC
    return teacher
