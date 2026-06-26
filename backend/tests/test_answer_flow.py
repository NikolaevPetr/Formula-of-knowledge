"""Воспроизводим жалобу: после возобновления игры ответы/таймеры/проверка экзамена
не работают. Играем несколько ходов, отвечая на вопросы, и проверяем прогресс."""
import os
import uuid

os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///./af_{uuid.uuid4().hex}.db"
os.environ["SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


def _wait(ws, wanted, limit=200):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] == wanted:
            return m
    raise AssertionError(f"no {wanted}")


def _read_until_one_of(ws, wanted: set, limit=200):
    for _ in range(limit):
        m = ws.receive_json()
        if m["type"] in wanted:
            return m
    raise AssertionError(f"none of {wanted}")


def test_answer_after_resume():
    with TestClient(app) as client:
        email = f"t_{uuid.uuid4().hex[:6]}@u.ru"
        tok = client.post("/api/auth/register", json={
            "email": email, "password": "secret1", "name": "T"}).json()["access_token"]
        h = {"Authorization": f"Bearer {tok}"}
        bank = client.post("/api/banks", json={"name": "B", "subject": "X"}, headers=h).json()
        for i in range(10):
            client.post(f"/api/banks/{bank['id']}/questions", headers=h, json={
                "type": "zachet", "text": f"Q{i}", "options": ["a", "b", "c", "d"],
                "correct_option_index": 0})
        room = client.post("/api/rooms", headers=h, json={
            "subject": "X", "bank_id": bank["id"], "end_condition_type": "rounds",
            "end_condition_value": 5, "turn_timer_sec": 120, "answer_timer_sec": 120,
            "max_players": 4}).json()
        code = room["code"]

        with client.websocket_connect(f"/ws/play/{code}") as s1, \
             client.websocket_connect(f"/ws/play/{code}") as s2:
            s1.send_json({"type": "join_room", "payload": {"name": "A", "surname": "A", "group": "1"}})
            t1 = _wait(s1, "joined")["payload"]
            s2.send_json({"type": "join_room", "payload": {"name": "B", "surname": "B", "group": "1"}})
            t2 = _wait(s2, "joined")["payload"]

            with client.websocket_connect(f"/ws/teacher/{code}?token={tok}") as tws:
                _wait(tws, "room_state")
                tws.send_json({"type": "start_game", "payload": {}})
                _wait(s1, "turn_started")

        # === Имитация перезапуска бэкенда ===
        from app.game.room_manager import room_manager
        room_manager._engines.clear()

        socks = {}
        with client.websocket_connect(f"/ws/play/{code}") as s1b, \
             client.websocket_connect(f"/ws/play/{code}") as s2b, \
             client.websocket_connect(f"/ws/teacher/{code}?token={tok}") as tws:
            s1b.send_json({"type": "rejoin", "payload": {"session_token": t1["session_token"]}})
            _wait(s1b, "joined")
            s2b.send_json({"type": "rejoin", "payload": {"session_token": t2["session_token"]}})
            _wait(s2b, "joined")
            socks[t1["player_id"]] = s1b
            socks[t2["player_id"]] = s2b

            def current_state(ws):
                # Возвращает последний известный room_state, дочитав поток.
                rs = None
                for _ in range(30):
                    m = ws.receive_json()
                    if m["type"] == "room_state":
                        rs = m["payload"]
                    if rs and rs.get("current_player_id") is not None and rs.get("pending"):
                        return rs
                return rs

            rs = current_state(s1b)
            assert rs and rs["current_player_id"] is not None, "ход не возобновился"

            # Играем до 8 действий: на каждом ходу активный игрок катит кубик и,
            # если выпал вопрос, отвечает. Проверяем, что игра ПРОДВИГАЕТСЯ.
            progressed = 0
            for _ in range(8):
                cur = rs["current_player_id"]
                ws = socks.get(cur)
                if ws is None:
                    break
                ws.send_json({"type": "roll_dice", "payload": {}})
                # Ждём либо вопрос, либо переход хода (клетки без вопроса).
                m = _read_until_one_of(ws, {"question_presented", "turn_started", "wheel_result", "bet_requested"})
                if m["type"] == "question_presented":
                    if m["payload"]["cell_type"] == "zachet":
                        ws.send_json({"type": "submit_answer", "payload": {"answer": "0"}})
                        res = _wait(ws, "answer_result")
                        assert res["payload"]["correct"] is True
                        progressed += 1
                    else:  # exam → уходит преподавателю
                        _wait(ws, "exam_pending_review")
                        # резолвим экзамен преподавателем
                        eq = _wait(tws, "exam_review_queue")["payload"]["items"]
                        if eq:
                            tws.send_json({"type": "resolve_exam",
                                           "payload": {"answer_id": eq[-1]["answer_id"], "accepted": True}})
                            _wait(ws, "answer_result")
                            progressed += 1
                elif m["type"] in ("bet_requested",):
                    ws.send_json({"type": "decline_bet", "payload": {}})
                    progressed += 1
                elif m["type"] in ("wheel_result", "turn_started"):
                    progressed += 1
                # Обновляем состояние для следующего хода.
                rs = current_state(ws)
                if rs is None or rs.get("status") != "playing":
                    break

            assert progressed >= 3, f"игра не продвигается после возобновления (progressed={progressed})"

    for f in os.listdir("."):
        if f.startswith("af_") and f.endswith(".db"):
            try:
                os.remove(f)
            except OSError:
                pass
