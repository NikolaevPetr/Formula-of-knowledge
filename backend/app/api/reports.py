"""REST: отчёт по игре и экспорт CSV/Excel."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_teacher
from app.core.db import get_session
from app.models import Room, Teacher
from app.services.report import build_report, report_to_csv, report_to_xlsx

router = APIRouter(prefix="/api/rooms/{room_id}/report", tags=["reports"])


async def _room_or_404(session: AsyncSession, room_id: int, teacher_id: int) -> Room:
    room = await session.get(Room, room_id)
    if room is None or room.teacher_id != teacher_id:
        raise HTTPException(404, "Комната не найдена")
    return room


@router.get("")
async def report_json(
    room_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> dict:
    room = await _room_or_404(session, room_id, teacher.id)
    return await build_report(session, room)


@router.get("/csv")
async def report_csv(
    room_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    room = await _room_or_404(session, room_id, teacher.id)
    data = report_to_csv(await build_report(session, room))
    return Response(
        content=data, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{room.code}.csv"'},
    )


@router.get("/xlsx")
async def report_xlsx(
    room_id: int,
    teacher: Teacher = Depends(get_current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    room = await _room_or_404(session, room_id, teacher.id)
    data = report_to_xlsx(await build_report(session, room))
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="report_{room.code}.xlsx"'},
    )
