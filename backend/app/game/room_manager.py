"""Реестр активных комнат в памяти (PLAN §5). Загружает состояние из БД при
первом обращении и держит экземпляр GameEngine на комнату."""
from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import select

from app.core.db import SessionLocal
from app.game.engine import GameEngine
from app.game.state import RoomRuntime, RuntimePlayer
from app.models import Player, Room


class RoomManager:
    def __init__(self) -> None:
        self._engines: dict[str, GameEngine] = {}
        self._lock = asyncio.Lock()

    async def get_engine(self, code: str) -> GameEngine | None:
        async with self._lock:
            engine = self._engines.get(code)
            if engine is None:
                engine = await self._load(code)
                if engine is not None:
                    self._engines[code] = engine
        # Вне манагер-лока: при необходимости возобновляем ход после перезапуска.
        if engine is not None:
            await engine.ensure_running()
        return engine

    async def _load(self, code: str) -> GameEngine | None:
        async with SessionLocal() as s:
            room = (
                await s.execute(select(Room).where(Room.code == code))
            ).scalar_one_or_none()
            if room is None or room.status == "finished":
                return None
            players = (
                await s.execute(
                    select(Player).where(Player.room_id == room.id).order_by(Player.turn_order)
                )
            ).scalars().all()
            rt = RoomRuntime(
                code=room.code,
                room_id=room.id,
                teacher_id=room.teacher_id,
                subject=room.subject,
                board=room.board_config or {},
                turn_timer_sec=room.turn_timer_sec,
                answer_timer_sec=room.answer_timer_sec,
                end_condition_type=room.end_condition_type.value,
                end_condition_value=room.end_condition_value,
                bank_id=room.bank_id,
                max_players=room.max_players,
                status=room.status.value,
            )
            for p in players:
                rt.players[p.id] = RuntimePlayer(
                    id=p.id, name=p.name, surname=p.surname, group_name=p.group_name,
                    session_token=p.session_token, turn_order=p.turn_order,
                    score=p.score, position=p.position, connected=False,
                    consecutive_missed_turns=p.consecutive_missed_turns,
                    eliminated=p.eliminated, rounds_completed=p.rounds_completed,
                )
            rt.order = [p.id for p in players if not p.eliminated]
            return GameEngine(rt, SessionLocal)

    async def add_player(
        self, code: str, name: str, surname: str, group: str
    ) -> tuple[GameEngine, RuntimePlayer] | None:
        """Регистрирует нового студента в лобби. Возвращает (engine, player)."""
        engine = await self.get_engine(code)
        if engine is None:
            return None
        rt = engine.rt
        if rt.status != "lobby":
            return None
        async with engine._lock:
            actives = [p for p in rt.players.values() if not p.eliminated]
            if len(actives) >= self._max_players(rt):
                return None
            token = secrets.token_urlsafe(24)
            turn_order = len(rt.players)
            async with SessionLocal() as s:
                db_player = Player(
                    room_id=rt.room_id, name=name, surname=surname, group_name=group,
                    session_token=token, turn_order=turn_order,
                )
                s.add(db_player)
                await s.commit()
                await s.refresh(db_player)
            rp = RuntimePlayer(
                id=db_player.id, name=name, surname=surname, group_name=group,
                session_token=token, turn_order=turn_order, connected=True,
            )
            rt.players[rp.id] = rp
            rt.order.append(rp.id)
            return engine, rp

    def _max_players(self, rt: RoomRuntime) -> int:
        return rt.max_players

    async def find_player_by_token(
        self, code: str, token: str
    ) -> tuple[GameEngine, RuntimePlayer] | None:
        engine = await self.get_engine(code)
        if engine is None:
            return None
        for p in engine.rt.players.values():
            if p.session_token == token:
                return engine, p
        return None

    def drop(self, code: str) -> None:
        self._engines.pop(code, None)


room_manager = RoomManager()
