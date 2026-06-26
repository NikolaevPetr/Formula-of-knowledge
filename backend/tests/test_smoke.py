"""Интеграционный smoke-тест: REST-настройка + игровой цикл через WebSocket."""
import os
import pathlib
import uuid

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./test_{uuid.uuid4().hex}.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


def _auth_headers(client: TestClient) -> dict:
    email = f"t_{uuid.uuid4().hex[:8]}@uni.ru"
    r = client.post("/api/auth/register", json={
        "email": email, "password": "secret1", "name": "Преп"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, email


def _drain_until(ws, wanted: str, limit: int = 60) -> dict:
    """Читает сообщения WS до получения нужного типа."""
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == wanted:
            return m
    raise AssertionError(f"Не дождались сообщения {wanted}")


def test_full_flow():
    with TestClient(app) as client:
        headers, _ = _auth_headers(client)

        # Банк + вопросы
        bank = client.post("/api/banks", json={"name": "Б", "subject": "Физика"},
                           headers=headers).json()
        for i in range(8):
            r = client.post(f"/api/banks/{bank['id']}/questions", headers=headers, json={
                "type": "zachet", "text": f"Вопрос {i}",
                "options": ["а", "б", "в", "г"], "correct_option_index": 0})
            assert r.status_code == 201, r.text
        client.post(f"/api/banks/{bank['id']}/questions", headers=headers, json={
            "type": "exam", "text": "Экзамен", "reference_answer": "эталон"})

        banks = client.get("/api/banks", headers=headers).json()
        assert banks[0]["approved_count"] == 9

        # Комната
        room = client.post("/api/rooms", headers=headers, json={
            "subject": "Физика", "bank_id": bank["id"],
            "end_condition_type": "rounds", "end_condition_value": 1,
            "turn_timer_sec": 120, "answer_timer_sec": 300, "max_players": 4}).json()
        code = room["code"]

        # Публичный вход по коду
        info = client.get(f"/api/rooms/code/{code}").json()
        assert info["subject"] == "Физика"

        # Два студента подключаются
        with client.websocket_connect(f"/ws/play/{code}") as s1, \
             client.websocket_connect(f"/ws/play/{code}") as s2:
            s1.send_json({"type": "join_room",
                          "payload": {"name": "Иван", "surname": "И", "group": "А1"}})
            j1 = _drain_until(s1, "joined")
            assert "session_token" in j1["payload"]

            s2.send_json({"type": "join_room",
                          "payload": {"name": "Пётр", "surname": "П", "group": "А1"}})
            _drain_until(s2, "joined")

            # Преподаватель подключается и стартует игру
            token = headers["Authorization"].split()[1]
            with client.websocket_connect(f"/ws/teacher/{code}?token={token}") as tws:
                _drain_until(tws, "room_state")
                tws.send_json({"type": "start_game", "payload": {}})

                # Должен начаться ход
                started = _drain_until(s1, "turn_started", limit=80)
                assert "player_id" in started["payload"]

                # Активный игрок бросает кубик; проверяем, что приходит dice_rolled
                # Узнаём, чей ход, из room_state
                # Проще: оба пытаются бросить — движок проигнорирует не активного.
                s1.send_json({"type": "roll_dice", "payload": {}})
                s2.send_json({"type": "roll_dice", "payload": {}})
                dice = _drain_until(s1, "dice_rolled", limit=80)
                assert 1 <= dice["payload"]["value"] <= 6

        # Отчёт доступен
        rep = client.get(f"/api/rooms/{room['id']}/report", headers=headers).json()
        assert "ranking" in rep and len(rep["ranking"]) == 2

    # Чистим тестовую БД
    db = os.environ["DATABASE_URL"].split("///")[-1]
    p = pathlib.Path("backend") / db if (pathlib.Path("backend")).exists() else pathlib.Path(db)
    for cand in (pathlib.Path(db), p):
        try:
            cand.unlink()
        except OSError:
            pass
