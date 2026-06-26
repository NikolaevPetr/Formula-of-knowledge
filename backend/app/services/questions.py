"""Выдача вопросов в игру: случайный approved-вопрос нужного типа без повтора
до исчерпания банка (PLAN §6)."""
from __future__ import annotations

import random

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Question
from app.models.enums import QuestionStatus, QuestionType


async def pick_question(
    session: AsyncSession,
    bank_id: int,
    qtype: QuestionType,
    used_ids: set[int],
) -> Question | None:
    base = select(Question).where(
        Question.bank_id == bank_id,
        Question.type == qtype,
        Question.status == QuestionStatus.APPROVED,
    )
    # Сначала пробуем не повторять уже выданные.
    stmt = base.where(Question.id.notin_(used_ids)) if used_ids else base
    rows = (await session.execute(stmt)).scalars().all()
    if not rows:
        # Банк исчерпан по этому типу — разрешаем повтор.
        rows = (await session.execute(base)).scalars().all()
    if not rows:
        return None
    return random.choice(rows)


async def count_approved(
    session: AsyncSession, bank_id: int, qtype: QuestionType
) -> int:
    stmt = select(func.count(Question.id)).where(
        Question.bank_id == bank_id,
        Question.type == qtype,
        Question.status == QuestionStatus.APPROVED,
    )
    return int((await session.execute(stmt)).scalar_one())
