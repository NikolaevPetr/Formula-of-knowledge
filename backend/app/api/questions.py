"""REST: вопросы внутри банка (CRUD + импорт CSV/JSON)."""
from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.banks import _bank_or_404
from app.api.deps import get_current_teacher
from app.core.db import get_session
from app.models import Question, Teacher
from app.models.enums import QuestionSource, QuestionStatus, QuestionType
from app.schemas.question import QuestionCreate, QuestionOut, QuestionUpdate

router = APIRouter(prefix="/api/banks/{bank_id}/questions", tags=["questions"])


@router.get("", response_model=list[QuestionOut])
async def list_questions(
    bank_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> list[Question]:
    await _bank_or_404(session, bank_id, teacher.id)
    return list((await session.execute(
        select(Question).where(Question.bank_id == bank_id).order_by(Question.id)
    )).scalars().all())


@router.post("", response_model=QuestionOut, status_code=201)
async def create_question(
    bank_id: int,
    data: QuestionCreate,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Question:
    await _bank_or_404(session, bank_id, teacher.id)
    q = Question(
        bank_id=bank_id, type=data.type, text=data.text, options=data.options,
        correct_option_index=data.correct_option_index,
        reference_answer=data.reference_answer, explanation=data.explanation,
        difficulty=data.difficulty, source=QuestionSource.MANUAL,
        status=QuestionStatus.APPROVED,
    )
    session.add(q)
    await session.commit()
    await session.refresh(q)
    return q


@router.patch("/{question_id}", response_model=QuestionOut)
async def update_question(
    bank_id: int,
    question_id: int,
    data: QuestionUpdate,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Question:
    await _bank_or_404(session, bank_id, teacher.id)
    q = await session.get(Question, question_id)
    if q is None or q.bank_id != bank_id:
        raise HTTPException(404, "Вопрос не найден")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(q, field, value)
    await session.commit()
    await session.refresh(q)
    return q


@router.delete("/{question_id}", status_code=204, response_model=None)
async def delete_question(
    bank_id: int,
    question_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> None:
    await _bank_or_404(session, bank_id, teacher.id)
    q = await session.get(Question, question_id)
    if q is None or q.bank_id != bank_id:
        raise HTTPException(404, "Вопрос не найден")
    await session.delete(q)
    await session.commit()


def _row_to_create(row: dict) -> QuestionCreate:
    qtype = (row.get("type") or "").strip().lower()
    if qtype == QuestionType.ZACHET.value:
        options = [
            row[k].strip()
            for k in ("option1", "option2", "option3", "option4", "option5", "option6")
            if row.get(k) and str(row[k]).strip()
        ]
        ci = row.get("correct_index")
        return QuestionCreate(
            type=QuestionType.ZACHET, text=(row.get("text") or "").strip(),
            options=options,
            correct_option_index=int(ci) if ci not in (None, "") else None,
            explanation=(row.get("explanation") or None),
            difficulty=(row.get("difficulty") or None) or None,
        )
    return QuestionCreate(
        type=QuestionType.EXAM, text=(row.get("text") or "").strip(),
        reference_answer=(row.get("reference_answer") or None),
        explanation=(row.get("explanation") or None),
        difficulty=(row.get("difficulty") or None) or None,
    )


@router.post("/import", status_code=201)
async def import_questions(
    bank_id: int,
    file: UploadFile,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Импорт вопросов из CSV или JSON. CSV-колонки:
    type, text, option1..option6, correct_index, reference_answer, explanation, difficulty.
    """
    await _bank_or_404(session, bank_id, teacher.id)
    raw = (await file.read()).decode("utf-8-sig")
    rows: list[dict]
    if (file.filename or "").lower().endswith(".json"):
        parsed = json.loads(raw)
        rows = parsed if isinstance(parsed, list) else [parsed]
    else:
        rows = list(csv.DictReader(io.StringIO(raw)))

    created, errors = 0, []
    for i, row in enumerate(rows, start=1):
        try:
            data = _row_to_create(row)
            session.add(Question(
                bank_id=bank_id, type=data.type, text=data.text, options=data.options,
                correct_option_index=data.correct_option_index,
                reference_answer=data.reference_answer, explanation=data.explanation,
                difficulty=data.difficulty, source=QuestionSource.MANUAL,
                status=QuestionStatus.APPROVED,
            ))
            created += 1
        except (ValidationError, ValueError, KeyError) as e:
            errors.append({"row": i, "error": str(e)})
    await session.commit()
    return {"created": created, "errors": errors}
