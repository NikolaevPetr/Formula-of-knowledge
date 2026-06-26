"""WebSocket-эндпоинты: канал студента и канал преподавателя."""
from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_access_token
from app.game.room_manager import room_manager
from app.ws.connection import manager
from app.ws.protocol import ClientMsg, ServerMsg, TeacherMsg, msg

router = APIRouter()


@router.websocket("/ws/play/{code}")
async def play_ws(websocket: WebSocket, code: str) -> None:
    """Канал студента. Первое сообщение — join_room или rejoin."""
    await websocket.accept()
    code = code.upper()
    player_id: int | None = None
    engine = None
    try:
        while True:
            data = await websocket.receive_json()
            mtype = data.get("type")
            payload = data.get("payload") or {}

            if player_id is None:
                # До идентификации принимаем только join/rejoin.
                if mtype == ClientMsg.JOIN_ROOM:
                    res = await room_manager.add_player(
                        code,
                        (payload.get("name") or "").strip(),
                        (payload.get("surname") or "").strip(),
                        (payload.get("group") or "").strip(),
                    )
                    if res is None:
                        await manager.send(websocket, msg(ServerMsg.ERROR, {
                            "code": "join_failed",
                            "message": "Не удалось войти (комната не в лобби или заполнена)"}))
                        continue
                    engine, player = res
                    player_id = player.id
                    await manager.attach_player(code, player_id, websocket)
                    await manager.send(websocket, msg(ServerMsg.JOINED, {
                        "session_token": player.session_token, "player_id": player.id}))
                    await manager.broadcast(code, msg(ServerMsg.PLAYER_JOINED, player.public()))
                    await engine.broadcast_state()
                elif mtype == ClientMsg.REJOIN:
                    res = await room_manager.find_player_by_token(
                        code, payload.get("session_token") or "")
                    if res is None:
                        await manager.send(websocket, msg(ServerMsg.ERROR, {
                            "code": "rejoin_failed", "message": "Сессия не найдена"}))
                        continue
                    engine, player = res
                    player_id = player.id
                    await manager.attach_player(code, player_id, websocket)
                    await manager.send(websocket, msg(ServerMsg.JOINED, {
                        "session_token": player.session_token, "player_id": player.id}))
                    await engine.on_player_connected(player_id)
                else:
                    await manager.send(websocket, msg(ServerMsg.ERROR, {
                        "code": "not_joined", "message": "Сначала войдите в комнату"}))
                continue

            # После идентификации — игровые действия.
            assert engine is not None
            if mtype == ClientMsg.ROLL_DICE:
                await engine.handle_roll(player_id)
            elif mtype == ClientMsg.SUBMIT_ANSWER:
                await engine.handle_answer(player_id, str(payload.get("answer", "")))
            elif mtype == ClientMsg.PLACE_BET:
                await engine.handle_bet(player_id, int(payload.get("amount", 0)))
            elif mtype == ClientMsg.DECLINE_BET:
                await engine.handle_decline_bet(player_id)
            elif mtype == ClientMsg.SPIN_WHEEL:
                await engine.handle_spin(player_id)
            elif mtype == ClientMsg.ACK:
                pass
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await manager.detach(websocket)
        if engine is not None and player_id is not None:
            await engine.on_player_disconnected(player_id)


@router.websocket("/ws/teacher/{code}")
async def teacher_ws(
    websocket: WebSocket, code: str, token: str = Query(default="")
) -> None:
    """Канал преподавателя. Аутентификация через JWT в query-параметре token."""
    await websocket.accept()
    code = code.upper()
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        await manager.send(websocket, msg(ServerMsg.ERROR, {
            "code": "unauthorized", "message": "Недействительный токен"}))
        await websocket.close()
        return
    teacher_id = int(payload["sub"])
    engine = await room_manager.get_engine(code)
    if engine is None or engine.rt.teacher_id != teacher_id:
        await manager.send(websocket, msg(ServerMsg.ERROR, {
            "code": "forbidden", "message": "Нет доступа к этой комнате"}))
        await websocket.close()
        return

    await manager.attach_teacher(code, websocket)
    await engine.broadcast_state()
    await engine._push_exam_queue()
    try:
        while True:
            data = await websocket.receive_json()
            mtype = data.get("type")
            p = data.get("payload") or {}
            if mtype == TeacherMsg.START_GAME:
                await engine.start_game()
            elif mtype == TeacherMsg.PAUSE:
                await engine.pause()
            elif mtype == TeacherMsg.RESUME:
                await engine.resume()
            elif mtype == TeacherMsg.KICK_PLAYER:
                await engine.kick_player(int(p.get("player_id")))
            elif mtype == TeacherMsg.ADJUST_SCORE:
                await engine.adjust_score(int(p.get("player_id")), int(p.get("delta", 0)))
            elif mtype == TeacherMsg.RESOLVE_EXAM:
                await engine.resolve_exam(int(p.get("answer_id")), bool(p.get("accepted")))
            elif mtype == TeacherMsg.END_GAME:
                await engine.end_game()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await manager.detach(websocket)
