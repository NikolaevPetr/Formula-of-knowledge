from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.models.enums import (
    QuestionDifficulty,
    QuestionSource,
    QuestionStatus,
    QuestionType,
)


class QuestionBase(BaseModel):
    type: QuestionType
    text: str = Field(min_length=1)
    options: list[str] | None = None
    correct_option_index: int | None = None
    reference_answer: str | None = None
    explanation: str | None = None
    difficulty: QuestionDifficulty | None = None

    @model_validator(mode="after")
    def _validate_by_type(self) -> Self:
        if self.type == QuestionType.ZACHET:
            if not self.options or not (4 <= len(self.options) <= 6):
                raise ValueError("Зачёт: требуется от 4 до 6 вариантов ответа")
            if self.correct_option_index is None or not (
                0 <= self.correct_option_index < len(self.options)
            ):
                raise ValueError("Зачёт: некорректный индекс правильного ответа")
        else:  # EXAM
            self.options = None
            self.correct_option_index = None
        return self


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    text: str | None = None
    options: list[str] | None = None
    correct_option_index: int | None = None
    reference_answer: str | None = None
    explanation: str | None = None
    difficulty: QuestionDifficulty | None = None
    status: QuestionStatus | None = None


class QuestionOut(QuestionBase):
    id: int
    bank_id: int
    source: QuestionSource
    status: QuestionStatus

    model_config = {"from_attributes": True}


class BankBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=255)


class BankCreate(BankBase):
    pass


class BankOut(BankBase):
    id: int
    question_count: int = 0
    approved_count: int = 0

    model_config = {"from_attributes": True}
