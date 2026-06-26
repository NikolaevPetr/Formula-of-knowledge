"""Перечисления предметной области. Используются и в моделях, и в схемах."""
from __future__ import annotations

from enum import Enum


class QuestionType(str, Enum):
    ZACHET = "zachet"
    EXAM = "exam"


class QuestionDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuestionSource(str, Enum):
    MANUAL = "manual"
    AI = "ai"
    AI_REVIEWED = "ai_reviewed"


class QuestionStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"


class EndConditionType(str, Enum):
    ROUNDS = "rounds"
    TIME = "time"
    SCORE = "score"


class RoomStatus(str, Enum):
    LOBBY = "lobby"
    PLAYING = "playing"
    PAUSED = "paused"
    FINISHED = "finished"


class AnswerStatus(str, Enum):
    AUTO_CORRECT = "auto_correct"
    AUTO_WRONG = "auto_wrong"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class CellType(str, Enum):
    CORNER = "CORNER"
    ZACHET = "ZACHET"
    EXAM = "EXAM"
    LOCATION = "LOCATION"


class CornerKind(str, Enum):
    START = "start"
    BET = "bet"
    WHEEL = "wheel"
    SKIP = "skip"


class LocationEffect(str, Enum):
    FREE_POINTS = "free_points"
    TIMED_QUESTION = "timed_question"
    SWAP_WITH_PREVIOUS = "swap_with_previous"
    FLAT_PENALTY = "flat_penalty"
    FLAT_BONUS = "flat_bonus"
