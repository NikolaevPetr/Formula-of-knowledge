"""Воспроизводим сценарий пользователя: старт → пауза → продолжение.
Проверяем, что после resume студент по-прежнему видит активный ход."""
import os
import uuid

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./pr_{uuid.uuid4().hex}.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _wait(ws, wanted, limit=120):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == wanted:
            return m
    raise AssertionError(f"no {wanted}")


def _drain_last_room_state(ws, n=20):
    """Прочитать n сообщений и вернуть последний room_state."""
    last = None
    for _ in range(n):
        m = ws.receive_json()
        if m["type"] == "room_state":
            last = m["payload"]
    return last


def test_start_pause_resume():
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

        with client.websocket_connect(f"/ws/play/{code}") as s1, \
             client.websocket_connect(f"/ws/play/{code}") as s2:
            s1.send_json({"type": "join_room", "payload": {"name": "A", "surname": "A", "group": "1"}})
            _wait(s1, "joined")
            s2.send_json({"type": "join_room", "payload": {"name": "B", "surname": "B", "group": "1"}})
            _wait(s2, "joined")

            with client.websocket_connect(f"/ws/teacher/{code}?token={tok}") as tws:
                _wait(tws, "room_state")
                tws.send_json({"type": "start_game", "payload": {}})
                _wait(s1, "turn_started")
                _wait(s1, "room_state")  # состояние после старта

                tws.send_json({"type": "pause", "payload": {}})
                _wait(s1, "game_paused")
                _wait(s1, "room_state")  # состояние на паузе

                tws.send_json({"type": "resume", "payload": {}})
                _wait(s1, "game_resumed")
                rs = _wait(s1, "room_state")["payload"]  # состояние после resume

                print("\n=== AFTER RESUME (student s1) ===")
                print("status:", rs.get("status"))
                print("current_player_id:", rs.get("current_player_id"))
                print("pending:", rs.get("pending"))

                assert rs["status"] == "playing"
                assert rs["current_player_id"] is not None, "после resume нет активного игрока!"
                assert rs["pending"] is not None, "после resume потеряна фаза хода!"
                assert rs["pending"]["phase"] == "awaiting_roll"

    for f in os.listdir("."):
        if f.startswith("pr_") and f.endswith(".db"):
            try:
                os.remove(f)
            except OSError:
                pass
