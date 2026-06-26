"""Изоляция тестов: чистим реестр активных комнат между тестами, чтобы фоновые
таймеры и движки из одного теста не влияли на другой (общий процесс/БД)."""
import pytest


@pytest.fixture(autouse=True)
def _clear_engines():
    from app.game.room_manager import room_manager

    room_manager._engines.clear()
    yield
    room_manager._engines.clear()
