"""Таблицы БД (SQLAlchemy 2.0). Типы выбраны переносимо между Postgres и SQLite:
JSON вместо JSONB, Enum(native_enum=False) → VARCHAR + CHECK."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import (
    AnswerStatus,
    EndConditionType,
    QuestionDifficulty,
    QuestionSource,
    QuestionStatus,
    QuestionType,
    RoomStatus,
)


def _enum(enum_cls: type) -> sa.Enum:
    """Переносимый ENUM: хранится как VARCHAR + CHECK, значения — .value."""
    return sa.Enum(
        enum_cls,
        native_enum=False,
        validate_strings=True,
        values_callable=lambda e: [m.value for m in e],
    )


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(sa.String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(255))
    name: Mapped[str] = mapped_column(sa.String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    banks: Mapped[list["QuestionBank"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )
    rooms: Mapped[list["Room"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan"
    )


class QuestionBank(Base):
    __tablename__ = "question_banks"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(255))
    subject: Mapped[str] = mapped_column(sa.String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    teacher: Mapped["Teacher"] = relationship(back_populates="banks")
    questions: Mapped[list["Question"]] = relationship(
        back_populates="bank", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(
        ForeignKey("question_banks.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[QuestionType] = mapped_column(_enum(QuestionType))
    text: Mapped[str] = mapped_column(sa.Text)
    options: Mapped[list[str] | None] = mapped_column(sa.JSON, nullable=True)
    correct_option_index: Mapped[int | None] = mapped_column(nullable=True)
    reference_answer: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    difficulty: Mapped[QuestionDifficulty | None] = mapped_column(
        _enum(QuestionDifficulty), nullable=True
    )
    source: Mapped[QuestionSource] = mapped_column(
        _enum(QuestionSource), default=QuestionSource.MANUAL
    )
    status: Mapped[QuestionStatus] = mapped_column(
        _enum(QuestionStatus), default=QuestionStatus.APPROVED
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    bank: Mapped["QuestionBank"] = relationship(back_populates="questions")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), index=True
    )
    code: Mapped[str] = mapped_column(sa.String(12), unique=True, index=True)
    subject: Mapped[str] = mapped_column(sa.String(255))
    bank_id: Mapped[int] = mapped_column(ForeignKey("question_banks.id"))
    end_condition_type: Mapped[EndConditionType] = mapped_column(_enum(EndConditionType))
    end_condition_value: Mapped[int] = mapped_column()
    turn_timer_sec: Mapped[int] = mapped_column(default=15)
    answer_timer_sec: Mapped[int] = mapped_column(default=30)
    max_players: Mapped[int] = mapped_column(default=8)
    board_config: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    status: Mapped[RoomStatus] = mapped_column(
        _enum(RoomStatus), default=RoomStatus.LOBBY
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    teacher: Mapped["Teacher"] = relationship(back_populates="rooms")
    bank: Mapped["QuestionBank"] = relationship()
    players: Mapped[list["Player"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(sa.String(120))
    surname: Mapped[str] = mapped_column(sa.String(120))
    group_name: Mapped[str] = mapped_column(sa.String(120))
    session_token: Mapped[str] = mapped_column(sa.String(64), unique=True, index=True)
    score: Mapped[int] = mapped_column(default=0)
    position: Mapped[int] = mapped_column(default=0)
    turn_order: Mapped[int] = mapped_column(default=0)
    connected: Mapped[bool] = mapped_column(default=True)
    consecutive_missed_turns: Mapped[int] = mapped_column(default=0)
    eliminated: Mapped[bool] = mapped_column(default=False)
    rounds_completed: Mapped[int] = mapped_column(default=0)
    joined_at: Mapped[datetime] = mapped_column(server_default=func.now())

    room: Mapped["Room"] = relationship(back_populates="players")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"))
    question_id: Mapped[int | None] = mapped_column(
        ForeignKey("questions.id"), nullable=True
    )
    cell_index: Mapped[int] = mapped_column()
    given_answer: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    points_delta: Mapped[int] = mapped_column(default=0)
    status: Mapped[AnswerStatus] = mapped_column(_enum(AnswerStatus))
    answered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)


class GameEvent(Base):
    __tablename__ = "game_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(sa.String(64))
    payload: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
