"""Генерация раскладки поля из 24 клеток (см. PLAN §2.1).

Раскладка выносится в board_config комнаты как снимок, чтобы игра не зависела
от изменений дефолта в коде. Значения эффектов локаций конфигурируемы (PLAN §2.4)."""
from __future__ import annotations

from typing import Any

from app.models.enums import CellType, CornerKind, LocationEffect

BOARD_SIZE = 24

# Дефолтная раскладка. Каждый элемент описывает клетку по индексу 0..23.
DEFAULT_LAYOUT: list[dict[str, Any]] = [
    {"index": 0, "type": CellType.CORNER, "corner": CornerKind.START, "label": "Старт"},
    {"index": 1, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 2, "type": CellType.LOCATION, "effect": LocationEffect.FREE_POINTS, "label": "Столовая"},
    {"index": 3, "type": CellType.EXAM, "label": "Экзамен"},
    {"index": 4, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 5, "type": CellType.LOCATION, "effect": LocationEffect.TIMED_QUESTION, "label": "Спортивный зал"},
    {"index": 6, "type": CellType.CORNER, "corner": CornerKind.BET, "label": "Ставка на знания"},
    {"index": 7, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 8, "type": CellType.LOCATION, "effect": LocationEffect.FREE_POINTS, "label": "Библиотека"},
    {"index": 9, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 10, "type": CellType.EXAM, "label": "Экзамен"},
    {"index": 11, "type": CellType.LOCATION, "effect": LocationEffect.SWAP_WITH_PREVIOUS, "label": "Общежитие"},
    {"index": 12, "type": CellType.CORNER, "corner": CornerKind.WHEEL, "label": "Колесо фортуны"},
    {"index": 13, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 14, "type": CellType.LOCATION, "effect": LocationEffect.FLAT_PENALTY, "label": "Деканат", "amount": -3},
    {"index": 15, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 16, "type": CellType.EXAM, "label": "Экзамен"},
    {"index": 17, "type": CellType.LOCATION, "effect": LocationEffect.TIMED_QUESTION, "label": "Лаборатория"},
    {"index": 18, "type": CellType.CORNER, "corner": CornerKind.SKIP, "label": "Прогул пар"},
    {"index": 19, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 20, "type": CellType.LOCATION, "effect": LocationEffect.FREE_POINTS, "label": "Кафедра"},
    {"index": 21, "type": CellType.ZACHET, "label": "Зачёт"},
    {"index": 22, "type": CellType.EXAM, "label": "Экзамен"},
    {"index": 23, "type": CellType.LOCATION, "effect": LocationEffect.FLAT_BONUS, "label": "Актовый зал", "amount": 3},
]

# Параметры начислений (PLAN §2.2, §2.3). Конфигурируемы.
SCORING = {
    "zachet_correct": 5,
    "zachet_wrong": 0,
    "exam_correct": 10,
    "exam_wrong": -2,
    "start_pass": 10,
    "start_stop": 10,
    "bet_min": 5,
    "bet_max": 20,
    "location_free_correct": 5,
    "location_free_wrong": 0,
    "location_timed_correct": 5,
    "location_timed_wrong": 0,
    "location_timed_sec": 10,
}

# Колесо фортуны: 6 равновероятных секторов (PLAN §2.3).
WHEEL_SECTORS: list[dict[str, Any]] = [
    {"id": 1, "label": "Повышенная стипендия", "kind": "points", "delta": 5},
    {"id": 2, "label": "Закрыл сессию досрочно", "kind": "points", "delta": 10},
    {"id": 3, "label": "Опоздал на экзамен", "kind": "points", "delta": -5},
    {"id": 4, "label": "Выиграл олимпиаду", "kind": "points", "delta": 15},
    {"id": 5, "label": "Отправляйся на ближайший экзамен", "kind": "go_to_exam"},
    {"id": 6, "label": "Поймали на списывании", "kind": "points", "delta": -10},
]


def _serialize_cell(cell: dict[str, Any]) -> dict[str, Any]:
    """Преобразует enum-значения в строки для хранения в JSON board_config."""
    out: dict[str, Any] = {}
    for key, value in cell.items():
        out[key] = value.value if hasattr(value, "value") else value
    return out


def build_board_config() -> dict[str, Any]:
    """Снимок раскладки + параметры начислений для записи в room.board_config."""
    return {
        "size": BOARD_SIZE,
        "cells": [_serialize_cell(c) for c in DEFAULT_LAYOUT],
        "scoring": SCORING,
        "wheel_sectors": WHEEL_SECTORS,
    }


def next_exam_index(start: int, board: dict[str, Any]) -> int:
    """Ближайшая клетка EXAM строго вперёд от start (с переходом через 0).
    PLAN §2.3 / §15.7 — перемещение только вперёд."""
    cells = board["cells"]
    size = board["size"]
    for step in range(1, size + 1):
        idx = (start + step) % size
        if cells[idx]["type"] == CellType.EXAM.value:
            return idx
    return start
