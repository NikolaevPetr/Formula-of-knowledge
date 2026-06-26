"""ORM-модели. Импортируются здесь, чтобы Alembic видел все таблицы."""
from app.models.enums import (
    AnswerStatus,
    EndConditionType,
    QuestionSource,
    QuestionStatus,
    QuestionType,
    RoomStatus,
)
from app.models.tables import (
    Answer,
    GameEvent,
    Player,
    Question,
    QuestionBank,
    Room,
    Teacher,
)

__all__ = [
    "AnswerStatus",
    "EndConditionType",
    "QuestionSource",
    "QuestionStatus",
    "QuestionType",
    "RoomStatus",
    "Answer",
    "GameEvent",
    "Player",
    "Question",
    "QuestionBank",
    "Room",
    "Teacher",
]
