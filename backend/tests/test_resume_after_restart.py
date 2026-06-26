"""Воспроизводим причину «Ожидание хода…»: бэкенд перезапустился во время игры
(состояние хода в памяти потеряно), статус в БД остался playing. При следующем
обращении движок должен ВОЗОБНОВИТЬ ход, а не зависнуть без активного игрока."""
import os
import uuid

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./rr_{uuid.uuid4().hex}.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _wait(ws, wanted, limit=120):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == wanted:
            return m
    raise AssertionError(f"no {wanted}")


def test_resume_after_restart():
    with TestClient(app) as client:
        email = f"t_{uuid.uuid4().hex[:6]}@u.ru"
        tok = client.post("/api/auth/register", json={
            "email": email, "password": "secret1", "name": "T"}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        bank = client.post("/api/banks", json={"name": "B", "subject": "X"}, headers=h).json()
        client.post(f"/api/banks/{bank['id']}/questions", headers=h, json={
            "type": "zachet", "text": "Q", "options": ["a", "b", "c", "d"],
            "correct_option_index": 0})
        room = client.post("/api/rooms", headers=h, json={
            "subject": "X", "bank_id": bank["id"], "end_condition_type": "rounds",
            "end_condition_value": 3, "turn_timer_sec": 120, "answer_timer_sec": 120,
            "max_players": 4}).json()
        code = room["code"]

        s1_token = None
        with client.websocket_connect(f"/ws/play/{code}") as s1, \
             client.websocket_connect(f"/ws/play/{code}") as s2:
            s1.send_json({"type": "join_room", "payload": {"name": "A", "surname": "A", "group": "1"}})
            s1_token = _wait(s1, "joined")["payload"]["session_token"]
            s2.send_json({"type": "join_room", "payload": {"name": "B", "surname": "B", "group": "1"}})
            s2_token = _wait(s2, "joined")["payload"]["session_token"]
            with client.websocket_connect(f"/ws/teacher/{code}?token={tok}") as tws:
                _wait(tws, "room_state")
                tws.send_json({"type": "start_game", "payload": {}})
                _wait(s1, "turn_started")

        # ИМИТАЦИЯ ПЕРЕЗАПУСКА БЭКЕНДА: сбрасываем реестр движков в памяти.
        from app.game.room_manager import room_manager
        room_manager._engines.clear()

        # Игрок переподключается — движок должен возобновить игру и активировать ход.
        with client.websocket_connect(f"/ws/play/{code}") as s1b, \
             client.websocket_connect(f"/ws/play/{code}") as s2b:
            s1b.send_json({"type": "rejoin", "payload": {"session_token": s1_token}})
            _wait(s1b, "joined")
            s2b.send_json({"type": "rejoin", "payload": {"session_token": s2_token}})
            _wait(s2b, "joined")

            rs = _wait(s1b, "room_state")["payload"]
            # Дочитываем до состояния с активным игроком (возобновление асинхронно).
            for _ in range(20):
                if rs.get("status") == "playing" and rs.get("current_player_id") is not None:
                    break
                m = s1b.receive_json()
                if m["type"] == "room_state":
                    rs = m["payload"]

            assert rs["status"] == "playing"
            assert rs["current_player_id"] is not None, "ход не возобновился после перезапуска!"
            assert rs["pending"]["phase"] == "awaiting_roll"

    for f in os.listdir("."):
        if f.startswith("rr_") and f.endswith(".db"):
            try:
                os.remove(f)
            except OSError:
                pass
