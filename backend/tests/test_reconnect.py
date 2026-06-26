"""Проверка реконнекта: после переподключения по токену игрок снова получает
состояние и видит свой ход (это поведение, на которое опирается фронтенд)."""
import os
import uuid

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./rc_{uuid.uuid4().hex}.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _wait(ws, wanted, limit=80):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == wanted:
            return m
    raise AssertionError(f"no {wanted}")


def _last_room_state_after(ws, marker, limit=60):
    last, seen = None, False
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == marker:
            seen = True
        if m["type"] == "room_state":
            last = m["payload"]
        if seen and last and last.get("status") == "playing":
            return last
    return last


def test_reconnect_then_play():
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

        # Студент 1 заходит и ЗАПОМИНАЕТ токен, затем «теряет» соединение.
        with client.websocket_connect(f"/ws/play/{code}") as s1:
            s1.send_json({"type": "join_room",
                          "payload": {"name": "A", "surname": "A", "group": "1"}})
            token1 = _wait(s1, "joined")["payload"]["session_token"]

        # Студент 2.
        with client.websocket_connect(f"/ws/play/{code}") as s2:
            s2.send_json({"type": "join_room",
                          "payload": {"name": "B", "surname": "B", "group": "1"}})
            _wait(s2, "joined")

            # Студент 1 ПЕРЕПОДКЛЮЧАЕТСЯ по токену (имитация StrictMode/refresh).
            with client.websocket_connect(f"/ws/play/{code}") as s1b:
                s1b.send_json({"type": "rejoin", "payload": {"session_token": token1}})
                rejoined = _wait(s1b, "joined")
                assert rejoined["payload"]["session_token"] == token1

                # Преподаватель стартует игру.
                with client.websocket_connect(f"/ws/teacher/{code}?token={tok}") as tws:
                    _wait(tws, "room_state")
                    tws.send_json({"type": "start_game", "payload": {}})

                    # ПЕРЕПОДКЛЮЧИВШИЙСЯ студент получает playing-состояние и видит ход.
                    rs = _last_room_state_after(s1b, "turn_started")
                    assert rs["status"] == "playing"
                    assert rs["pending"]["phase"] == "awaiting_roll"
                    assert rs["current_player_id"] is not None

                    # Активный игрок может бросить кубик и получить результат.
                    active = rs["current_player_id"]
                    roller = s1b if active == rejoined["payload"]["player_id"] else s2
                    roller.send_json({"type": "roll_dice", "payload": {}})
                    dice = _wait(roller, "dice_rolled")
                    assert 1 <= dice["payload"]["value"] <= 6

    for f in os.listdir("."):
        if f.startswith("rc_") and f.endswith(".db"):
            try:
                os.remove(f)
            except OSError:
                pass
