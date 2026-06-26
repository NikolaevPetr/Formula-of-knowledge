"""Конфигурация приложения. Значения читаются из переменных окружения / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # База данных (async URL). По умолчанию — локальный SQLite, чтобы проект
    # запускался без настройки; в .env подставляется PostgreSQL.
    DATABASE_URL: str = "sqlite+aiosqlite:///./monopoly.db"

    # JWT преподавателя
    SECRET_KEY: str = "dev-secret-change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    # Генерация вопросов (Фаза 8). Для MVP — none.
    AI_PROVIDER: str = "none"
    GIGACHAT_CREDENTIALS: str = ""
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    OPENAI_MODEL: str = ""

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
