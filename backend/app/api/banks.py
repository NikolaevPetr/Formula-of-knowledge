"""REST: банки вопросов (CRUD)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_teacher
from app.core.db import get_session
from app.models import Question, QuestionBank, Teacher
from app.models.enums import QuestionStatus
from app.schemas.question import BankCreate, BankOut

router = APIRouter(prefix="/api/banks", tags=["banks"])


async def _bank_or_404(
    session: AsyncSession, bank_id: int, teacher_id: int
) -> QuestionBank:
    bank = await session.get(QuestionBank, bank_id)
    if bank is None or bank.teacher_id != teacher_id:
        raise HTTPException(404, "Банк не найден")
    return bank


async def _counts(session: AsyncSession, bank_id: int) -> tuple[int, int]:
    total = int((await session.execute(
        select(func.count(Question.id)).where(Question.bank_id == bank_id)
    )).scalar_one())
    approved = int((await session.execute(
        select(func.count(Question.id)).where(
            Question.bank_id == bank_id, Question.status == QuestionStatus.APPROVED
        )
    )).scalar_one())
    return total, approved


@router.get("", response_model=list[BankOut])
async def list_banks(
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> list[BankOut]:
    banks = (
        await session.execute(
            select(QuestionBank).where(QuestionBank.teacher_id == teacher.id)
            .order_by(QuestionBank.created_at.desc())
        )
    ).scalars().all()
    out: list[BankOut] = []
    for b in banks:
        total, approved = await _counts(session, b.id)
        out.append(BankOut(id=b.id, name=b.name, subject=b.subject,
                           question_count=total, approved_count=approved))
    return out


@router.post("", response_model=BankOut, status_code=201)
async def create_bank(
    data: BankCreate,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> BankOut:
    bank = QuestionBank(teacher_id=teacher.id, name=data.name, subject=data.subject)
    session.add(bank)
    await session.commit()
    await session.refresh(bank)
    return BankOut(id=bank.id, name=bank.name, subject=bank.subject)


@router.delete("/{bank_id}", status_code=204, response_model=None)
async def delete_bank(
    bank_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> None:
    bank = await _bank_or_404(session, bank_id, teacher.id)
    await session.delete(bank)
    await session.commit()
