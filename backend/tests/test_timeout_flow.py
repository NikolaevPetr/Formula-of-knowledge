"""Серверная проверка двух жалоб (изолированно от фронтенда/WS):
  1) движок принимает ответ на зачётный вопрос и начисляет баллы;
  2) при истечении таймера ответа ход переходит к следующему игроку.
Существующие тесты гоняли длинные таймеры (120 c) и всегда отвечали, поэтому
ветка таймаута раньше не покрывалась."""
import os
import uuid

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./to_{uuid.uuid4().hex}.db"
os.environ["SECRET_KEY"] = "test-secret"

import asyncio  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401  (регистрация таблиц)
from app.models import Player, Question, QuestionBank, Room, Teacher  # noqa: E402
from app.models.enums import QuestionType  # noqa: E402
from app.game.board import build_board_config  # noqa: E402
from app.game.room_manager import room_manager  # noqa: E402
from app.game.state import TurnPhase  # noqa: E402


async def _seed() -> str:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    code = f"TO{uuid.uuid4().hex[:4].upper()}"
    async with SessionLocal() as s:
        t = Teacher(email=f"t_{uuid.uuid4().hex[:6]}@u.ru", password_hash="x", name="T")
        s.add(t)
        await s.flush()
        bank = QuestionBank(teacher_id=t.id, name="B", subject="X")
        s.add(bank)
        await s.flush()
        for i in range(8):
            s.add(Question(
                bank_id=bank.id, type=QuestionType.ZACHET, text=f"Q{i}",
                options=["a", "b", "c", "d"], correct_option_index=0,
            ))
        room = Room(
            teacher_id=t.id, code=code, subject="X", bank_id=bank.id,
            end_condition_type="rounds", end_condition_value=100,
            turn_timer_sec=15, answer_timer_sec=15, max_players=4,
            board_config=build_board_config(), status="playing",
        )
        s.add(room)
        await s.flush()
        for i in range(2):
            s.add(Player(
                room_id=room.id, name=f"P{i}", surname="S", group_name="1",
                session_token=f"{code}-tok{i}", turn_order=i, connected=True,
            ))
        await s.commit()
    return code


def test_answer_accepted_and_timeout_advances():
    # pytest-asyncio в проекте не установлен (остальные тесты на синхронном
    # TestClient), поэтому гоняем асинхронное тело через asyncio.run.
    asyncio.run(_run())


async def _run():
    code = await _seed()
    eng = await room_manager.get_engine(code)   # ensure_running начинает ход
    assert eng is not None
    rt = eng.rt
    assert rt.status == "playing"
    assert rt.phase == TurnPhase.AWAITING_ROLL

    # (1) Ответ принимается и начисляет баллы.
    cur = rt.current_player()
    before = cur.score
    await eng._present_question(cur, QuestionType.ZACHET, 5, 0, 15)
    assert rt.phase == TurnPhase.AWAITING_ANSWER
    await eng.handle_answer(cur.id, "0")  # верный индекс 0
    assert rt.players[cur.id].score == before + 5, "движок не начислил баллы за верный ответ"

    # (2) Истечение таймера ответа переводит ход к следующему игроку.
    nxt = rt.current_player()
    stuck_id = nxt.id
    await eng._present_question(nxt, QuestionType.ZACHET, 5, 0, 1)  # таймер 1 c
    assert rt.phase == TurnPhase.AWAITING_ANSWER
    await asyncio.sleep(1.7)
    assert rt.phase == TurnPhase.AWAITING_ROLL, "после таймаута фаза не сбросилась"
    after = rt.current_player()
    assert after is not None and after.id != stuck_id, "ход не перешёл к следующему игроку"

    # Временный файл БД (если использовался именно он) почистится при сборке мусора;
    # общий движок не трогаем — его жизненный цикл у процесса (как в остальных тестах).
