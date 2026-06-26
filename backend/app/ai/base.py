"""Интерфейс провайдера генерации вопросов (PLAN §9).

Архитектура заложена в MVP; конкретные реализации (GigaChat, OpenAI-совместимая,
локальная модель) добавляются в Фазе 8. В игру попадают только approved-вопросы."""
from __future__ import annotations

from typing import Literal, Protocol

from pydantic import BaseModel, Field, model_validator


class QuestionDraft(BaseModel):
    """Строгая схема ответа модели; кривые черновики отбраковываются (PLAN §9)."""

    type: Literal["zachet", "exam"]
    text: str = Field(min_length=1)
    options: list[str] | None = None
    correct_option_index: int | None = None
    reference_answer: str | None = None
    explanation: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None

    @model_validator(mode="after")
    def _check(self) -> "QuestionDraft":
        if self.type == "zachet":
            if not self.options or not (4 <= len(self.options) <= 6):
                raise ValueError("zachet требует 4–6 вариантов")
            if self.correct_option_index is None or not (
                0 <= self.correct_option_index < len(self.options)
            ):
                raise ValueError("некорректный correct_option_index")
        return self


class QuestionGenerator(Protocol):
    """Контракт провайдера. Реализации — gigachat.py / openai_compatible.py / local."""

    async def generate(
        self,
        topic: str,
        qtype: Literal["zachet", "exam"],
        count: int,
        difficulty: str,
    ) -> list[QuestionDraft]: ...


def get_generator(provider: str) -> QuestionGenerator | None:
    """Фабрика провайдера по конфигу. В MVP возвращает None (none)."""
    if provider == "none":
        return None
    # Фаза 8: подключить реальные реализации.
    raise NotImplementedError(f"Провайдер '{provider}' будет добавлен в Фазе 8")
