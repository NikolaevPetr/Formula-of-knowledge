"""REST: создание и просмотр комнат преподавателем + публичный вход по коду."""
from __future__ import annotations

import secrets
import string

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_teacher
from app.core.db import get_session
from app.game.board import build_board_config
from app.models import Player, QuestionBank, Room, Teacher
from app.models.enums import QuestionType, RoomStatus
from app.schemas.room import RoomCreate, RoomJoinInfo, RoomOut
from app.services.questions import count_approved

router = APIRouter(prefix="/api/rooms", tags=["rooms"])

_ALPHABET = string.ascii_uppercase + string.digits


async def _unique_code(session: AsyncSession) -> str:
    for _ in range(20):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(6))
        exists = (
            await session.execute(select(Room.id).where(Room.code == code))
        ).first()
        if not exists:
            return code
    raise HTTPException(500, "Не удалось сгенерировать код комнаты")


@router.post("", response_model=RoomOut, status_code=201)
async def create_room(
    data: RoomCreate,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Room:
    bank = await session.get(QuestionBank, data.bank_id)
    if bank is None or bank.teacher_id != teacher.id:
        raise HTTPException(404, "Банк вопросов не найден")
    # Предупреждение о малом числе вопросов (PLAN §6) — мягкая проверка.
    z = await count_approved(session, bank.id, QuestionType.ZACHET)
    e = await count_approved(session, bank.id, QuestionType.EXAM)
    if z == 0 and e == 0:
        raise HTTPException(
            400, "В банке нет одобренных вопросов — добавьте вопросы перед игрой"
        )
    code = await _unique_code(session)
    room = Room(
        teacher_id=teacher.id, code=code, subject=data.subject, bank_id=bank.id,
        end_condition_type=data.end_condition_type,
        end_condition_value=data.end_condition_value,
        turn_timer_sec=data.turn_timer_sec, answer_timer_sec=data.answer_timer_sec,
        max_players=data.max_players, board_config=build_board_config(),
        status=RoomStatus.LOBBY,
    )
    session.add(room)
    await session.commit()
    await session.refresh(room)
    return room


@router.get("", response_model=list[RoomOut])
async def list_rooms(
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> list[Room]:
    return list((await session.execute(
        select(Room).where(Room.teacher_id == teacher.id).order_by(Room.created_at.desc())
    )).scalars().all())


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(
    room_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Room:
    room = await session.get(Room, room_id)
    if room is None or room.teacher_id != teacher.id:
        raise HTTPException(404, "Комната не найдена")
    return room


@router.get("/code/{code}", response_model=RoomJoinInfo)
async def room_by_code(
    code: str, session: AsyncSession = Depends(get_session)
) -> RoomJoinInfo:
    """Публичная информация для экрана входа студента (без аутентификации)."""
    room = (
        await session.execute(select(Room).where(Room.code == code.upper()))
    ).scalar_one_or_none()
    if room is None:
        raise HTTPException(404, "Комната не найдена")
    count = int((await session.execute(
        select(func.count(Player.id)).where(
            Player.room_id == room.id, Player.eliminated.is_(False)
        )
    )).scalar_one())
    return RoomJoinInfo(
        code=room.code, subject=room.subject, status=room.status,
        max_players=room.max_players, player_count=count,
    )
