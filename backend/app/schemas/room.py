from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import EndConditionType, RoomStatus


class RoomCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    bank_id: int
    end_condition_type: EndConditionType
    end_condition_value: int = Field(gt=0)
    turn_timer_sec: int = Field(default=15, ge=5, le=120)
    answer_timer_sec: int = Field(default=30, ge=5, le=300)
    max_players: int = Field(default=8, ge=2, le=8)


class RoomOut(BaseModel):
    id: int
    code: str
    subject: str
    bank_id: int
    end_condition_type: EndConditionType
    end_condition_value: int
    turn_timer_sec: int
    answer_timer_sec: int
    max_players: int
    status: RoomStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class RoomJoinInfo(BaseModel):
    """Публичная информация о комнате по коду (для экрана входа студента)."""

    code: str
    subject: str
    status: RoomStatus
    max_players: int
    player_count: int
