"""Рантайм-состояние комнаты в памяти процесса (PLAN §13: live-состояние в памяти)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TurnPhase(str, Enum):
    IDLE = "idle"                # игра не идёт / между ходами
    AWAITING_ROLL = "awaiting_roll"
    AWAITING_ANSWER = "awaiting_answer"
    AWAITING_BET = "awaiting_bet"
    AWAITING_WHEEL = "awaiting_wheel"


@dataclass
class RuntimePlayer:
    id: int
    name: str
    surname: str
    group_name: str
    session_token: str
    turn_order: int
    score: int = 0
    position: int = 0
    connected: bool = True
    consecutive_missed_turns: int = 0
    eliminated: bool = False
    rounds_completed: int = 0

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}".strip()

    def public(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "group_name": self.group_name,
            "score": self.score,
            "position": self.position,
            "turn_order": self.turn_order,
            "connected": self.connected,
            "eliminated": self.eliminated,
            "rounds_completed": self.rounds_completed,
        }


@dataclass
class PendingAction:
    """Контекст текущей ожидаемой фазы (вопрос/ставка/колесо)."""

    phase: TurnPhase
    player_id: int
    deadline: float                       # monotonic-время дедлайна
    cell_index: int
    question_id: int | None = None
    question_type: str | None = None      # zachet / exam
    correct_index: int | None = None      # для zachet (на сервере!)
    answer_db_id: int | None = None
    is_location: bool = False
    location_effect: str | None = None
    bet_amount: int | None = None         # выбранная ставка (после place_bet)
    points_correct: int = 0
    points_wrong: int = 0
    timer_token: int = 0                  # для отмены устаревших таймеров


@dataclass
class RoomRuntime:
    code: str
    room_id: int
    teacher_id: int
    subject: str
    board: dict[str, Any]
    turn_timer_sec: int
    answer_timer_sec: int
    end_condition_type: str
    end_condition_value: int
    bank_id: int
    max_players: int = 8
    status: str = "lobby"                  # lobby/playing/paused/finished
    players: dict[int, RuntimePlayer] = field(default_factory=dict)
    order: list[int] = field(default_factory=list)  # turn_order → player_id
    current_idx: int = -1                  # индекс в order текущего игрока
    phase: TurnPhase = TurnPhase.IDLE
    pending: PendingAction | None = None
    used_question_ids: set[int] = field(default_factory=set)
    started_monotonic: float | None = None
    timer_token: int = 0                   # глобальный счётчик для отмены таймеров

    # --- помощники ---
    def active_players(self) -> list[RuntimePlayer]:
        return [
            self.players[pid]
            for pid in self.order
            if pid in self.players and not self.players[pid].eliminated
        ]

    def current_player(self) -> RuntimePlayer | None:
        if 0 <= self.current_idx < len(self.order):
            pid = self.order[self.current_idx]
            return self.players.get(pid)
        return None

    def next_timer_token(self) -> int:
        self.timer_token += 1
        return self.timer_token

    def time_left(self) -> float | None:
        if self.pending is None:
            return None
        return max(0.0, self.pending.deadline - time.monotonic())

    def snapshot(self) -> dict[str, Any]:
        """Полный room_state для broadcast (PLAN §7.3)."""
        cur = self.current_player()
        pending_pub: dict[str, Any] | None = None
        if self.pending is not None:
            pending_pub = {
                "phase": self.pending.phase.value,
                "player_id": self.pending.player_id,
                "cell_index": self.pending.cell_index,
                "time_left": self.time_left(),
                "question_type": self.pending.question_type,
                "location_effect": self.pending.location_effect,
            }
        return {
            "code": self.code,
            "subject": self.subject,
            "status": self.status,
            "phase": self.phase.value,
            "board": self.board,
            "players": [p.public() for p in self.players.values()],
            "order": self.order,
            "current_player_id": cur.id if cur else None,
            "pending": pending_pub,
            "end_condition": {
                "type": self.end_condition_type,
                "value": self.end_condition_value,
            },
            "turn_timer_sec": self.turn_timer_sec,
            "answer_timer_sec": self.answer_timer_sec,
        }
