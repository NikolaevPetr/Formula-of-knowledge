"""ConnectionManager: WS-подключения по комнатам и broadcast (PLAN §4)."""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # room_code -> { connection_id -> WebSocket }
        self._student_rooms: dict[str, dict[str, WebSocket]] = {}
        # room_code -> set of teacher WebSockets
        self._teacher_rooms: dict[str, set[WebSocket]] = {}
        # WebSocket -> (room_code, player_id) для студентов
        self._player_of: dict[WebSocket, tuple[str, int]] = {}
        self._lock = asyncio.Lock()

    # --- регистрация студентов ---
    async def attach_player(self, room_code: str, player_id: int, ws: WebSocket) -> None:
        async with self._lock:
            room = self._student_rooms.setdefault(room_code, {})
            # Закрываем предыдущее подключение этого игрока, если было.
            key = str(player_id)
            old = room.get(key)
            room[key] = ws
            self._player_of[ws] = (room_code, player_id)
        if old is not None and old is not ws:
            try:
                await old.close()
            except Exception:
                pass

    async def detach(self, ws: WebSocket) -> tuple[str, int] | None:
        async with self._lock:
            info = self._player_of.pop(ws, None)
            if info:
                room_code, player_id = info
                room = self._student_rooms.get(room_code)
                if room and room.get(str(player_id)) is ws:
                    room.pop(str(player_id), None)
            # Убираем из преподавательских комнат, если это был препод.
            for code, conns in list(self._teacher_rooms.items()):
                conns.discard(ws)
                if not conns:
                    self._teacher_rooms.pop(code, None)
            return info

    # --- регистрация преподавателей ---
    async def attach_teacher(self, room_code: str, ws: WebSocket) -> None:
        async with self._lock:
            self._teacher_rooms.setdefault(room_code, set()).add(ws)

    # --- отправка ---
    async def send(self, ws: WebSocket, message: dict[str, Any]) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            pass

    async def send_to_player(
        self, room_code: str, player_id: int, message: dict[str, Any]
    ) -> None:
        ws = self._student_rooms.get(room_code, {}).get(str(player_id))
        if ws is not None:
            await self.send(ws, message)

    async def broadcast(self, room_code: str, message: dict[str, Any]) -> None:
        """Всем студентам и преподавателям комнаты."""
        targets: list[WebSocket] = list(
            self._student_rooms.get(room_code, {}).values()
        ) + list(self._teacher_rooms.get(room_code, set()))
        for ws in targets:
            await self.send(ws, message)

    async def broadcast_teachers(
        self, room_code: str, message: dict[str, Any]
    ) -> None:
        for ws in list(self._teacher_rooms.get(room_code, set())):
            await self.send(ws, message)

    def is_player_connected(self, room_code: str, player_id: int) -> bool:
        return str(player_id) in self._student_rooms.get(room_code, {})


manager = ConnectionManager()
