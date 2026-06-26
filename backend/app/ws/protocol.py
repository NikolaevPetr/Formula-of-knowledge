"""Типы WebSocket-сообщений (PLAN §7). Сообщение — JSON {type, payload}."""
from __future__ import annotations

from typing import Any


# --- Студент → сервер ---
class ClientMsg:
    JOIN_ROOM = "join_room"
    REJOIN = "rejoin"
    ROLL_DICE = "roll_dice"
    SUBMIT_ANSWER = "submit_answer"
    PLACE_BET = "place_bet"
    DECLINE_BET = "decline_bet"
    SPIN_WHEEL = "spin_wheel"
    ACK = "ack"


# --- Преподаватель → сервер ---
class TeacherMsg:
    AUTH = "auth"  # передать JWT для привязки канала преподавателя
    START_GAME = "start_game"
    PAUSE = "pause"
    RESUME = "resume"
    KICK_PLAYER = "kick_player"
    ADJUST_SCORE = "adjust_score"
    RESOLVE_EXAM = "resolve_exam"
    END_GAME = "end_game"


# --- Сервер → клиенты ---
class ServerMsg:
    JOINED = "joined"
    ROOM_STATE = "room_state"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    PLAYER_RECONNECTED = "player_reconnected"
    PLAYER_ELIMINATED = "player_eliminated"
    GAME_STARTED = "game_started"
    GAME_PAUSED = "game_paused"
    GAME_RESUMED = "game_resumed"
    TURN_STARTED = "turn_started"
    DICE_ROLLED = "dice_rolled"
    PAWN_MOVED = "pawn_moved"
    QUESTION_PRESENTED = "question_presented"
    ANSWER_RESULT = "answer_result"
    EXAM_PENDING_REVIEW = "exam_pending_review"
    WHEEL_RESULT = "wheel_result"
    BET_REQUESTED = "bet_requested"
    BET_PLACED = "bet_placed"
    SCORE_UPDATED = "score_updated"
    GAME_FINISHED = "game_finished"
    EXAM_REVIEW_QUEUE = "exam_review_queue"  # только преподавателю
    ERROR = "error"


def msg(type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": type_, "payload": payload or {}}
