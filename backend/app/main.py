"""Точка входа FastAPI: монтаж REST-роутеров и WebSocket-эндпоинтов."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, banks, questions, reports, rooms
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Для локального SQLite создаём таблицы автоматически (без Alembic).
    if settings.is_sqlite:
        from app.core.db import Base, engine
        import app.models  # noqa: F401  — регистрация моделей в метаданных

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="Образовательная монополия — API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:5173",
                   "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(banks.router)
app.include_router(questions.router)
app.include_router(rooms.router)
app.include_router(reports.router)

# WebSocket-роуты
from app.ws import routes as ws_routes  # noqa: E402

app.include_router(ws_routes.router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
