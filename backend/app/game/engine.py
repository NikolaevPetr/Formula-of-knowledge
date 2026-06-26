"""Авторитетный игровой движок: конечный автомат хода, таймеры, начисления,
broadcast (PLAN §8). Вся логика и подсчёт очков — здесь, на сервере."""
from __future__ import annotations

import asyncio
import random
import time
from datetime import datetime, timezone

from app.game.board import next_exam_index
from app.game.state import PendingAction, RoomRuntime, RuntimePlayer, TurnPhase
from app.models import Answer, GameEvent, Player
from app.models.enums import (
    AnswerStatus,
    CellType,
    CornerKind,
    LocationEffect,
    QuestionType,
)
from app.services.questions import pick_question
from app.ws.connection import manager
from app.ws.protocol import ServerMsg, msg

def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class GameEngine:
    """Один экземпляр на активную комнату."""

    def __init__(self, runtime: RoomRuntime, session_factory) -> None:
        self.rt = runtime
        self._session_factory = session_factory
        self._lock = asyncio.Lock()

    # ================= вспомогательное =================

    @property
    def scoring(self) -> dict:
        return self.rt.board["scoring"]

    async def _log_event(self, type_: str, player_id: int | None, payload: dict) -> None:
        async with self._session_factory() as s:
            s.add(GameEvent(
                room_id=self.rt.room_id, player_id=player_id,
                type=type_, payload=payload,
            ))
            await s.commit()

    async def _persist_player(self, p: RuntimePlayer) -> None:
        async with self._session_factory() as s:
            db = await s.get(Player, p.id)
            if db is None:
                return
            db.score = p.score
            db.position = p.position
            db.connected = p.connected
            db.consecutive_missed_turns = p.consecutive_missed_turns
            db.eliminated = p.eliminated
            db.rounds_completed = p.rounds_completed
            await s.commit()

    async def _award(self, p: RuntimePlayer, delta: int) -> None:
        if delta == 0:
            return
        p.score += delta
        await self._persist_player(p)
        await manager.broadcast(
            self.rt.code, msg(ServerMsg.SCORE_UPDATED,
                              {"player_id": p.id, "score": p.score, "delta": delta})
        )

    async def broadcast_state(self) -> None:
        await manager.broadcast(self.rt.code, msg(ServerMsg.ROOM_STATE, self.rt.snapshot()))

    # ================= таймеры =================

    def _arm_timer(self, seconds: float) -> int:
        """Готовит дедлайн и токен; возвращает токен для запуска задачи."""
        token = self.rt.next_timer_token()
        if self.rt.pending is not None:
            self.rt.pending.deadline = time.monotonic() + seconds
            self.rt.pending.timer_token = token
        return token

    def _start_timer_task(self, token: int, seconds: float) -> None:
        asyncio.create_task(self._timeout_after(token, seconds))

    async def _timeout_after(self, token: int, seconds: float) -> None:
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return
        async with self._lock:
            # Таймер устарел (был ход/ответ или пауза) — игнорируем.
            if (
                self.rt.status != "playing"
                or self.rt.pending is None
                or self.rt.pending.timer_token != token
            ):
                return
            await self._on_phase_timeout()

    # ================= восстановление после перезапуска =================

    async def ensure_running(self) -> None:
        """Если комната загружена из БД со статусом playing, но ход не активен
        (состояние хода в памяти потеряно после перезапуска сервера) — возобновляем
        игру, начиная новый ход. Идемпотентно."""
        async with self._lock:
            needs_resume = (
                self.rt.status in ("playing", "paused")
                and self.rt.pending is None
                and self.rt.phase == TurnPhase.IDLE
            )
            if not needs_resume:
                return
            actives = self.rt.active_players()
            if len(actives) < 2:
                return
            self.rt.status = "playing"
            if self.rt.started_monotonic is None:
                self.rt.started_monotonic = time.monotonic()
            await self._log_event("game_resumed_after_restart", None, {})
            await self._advance_turn()

    # ================= старт игры =================

    async def start_game(self) -> None:
        async with self._lock:
            if self.rt.status not in ("lobby", "paused"):
                return
            actives = self.rt.active_players()
            if len(actives) < 2:
                await manager.broadcast_teachers(
                    self.rt.code,
                    msg(ServerMsg.ERROR, {"code": "not_enough_players",
                                          "message": "Нужно минимум 2 игрока"}),
                )
                return
            self.rt.status = "playing"
            self.rt.started_monotonic = time.monotonic()
            async with self._session_factory() as s:
                from app.models import Room
                room = await s.get(Room, self.rt.room_id)
                if room:
                    room.status = "playing"  # type: ignore[assignment]
                    room.started_at = utcnow()
                    await s.commit()
            self.rt.current_idx = -1
            await self._log_event("game_started", None, {})
            await manager.broadcast(self.rt.code, msg(ServerMsg.GAME_STARTED, {}))
            await self._advance_turn()

    # ================= переход хода =================

    async def _advance_turn(self) -> None:
        if await self._check_end_condition():
            return
        actives = self.rt.active_players()
        if len(actives) < 2:
            await self._finish_game(reason="not_enough_players")
            return
        # Следующий не выбывший игрок по кругу.
        n = len(self.rt.order)
        for _ in range(n):
            self.rt.current_idx = (self.rt.current_idx + 1) % n
            cand = self.rt.players.get(self.rt.order[self.rt.current_idx])
            if cand and not cand.eliminated:
                break
        player = self.rt.current_player()
        if player is None:
            await self._finish_game(reason="no_players")
            return
        # Отключённый игрок автоматически пропускает свой ход по таймеру.
        self.rt.phase = TurnPhase.AWAITING_ROLL
        self.rt.pending = PendingAction(
            phase=TurnPhase.AWAITING_ROLL,
            player_id=player.id,
            deadline=time.monotonic() + self.rt.turn_timer_sec,
            cell_index=player.position,
        )
        token = self._arm_timer(self.rt.turn_timer_sec)
        await manager.broadcast(
            self.rt.code,
            msg(ServerMsg.TURN_STARTED,
                {"player_id": player.id, "deadline": self.rt.turn_timer_sec}),
        )
        await self.broadcast_state()
        self._start_timer_task(token, self.rt.turn_timer_sec)

    async def _end_turn(self, acted: bool) -> None:
        player = self.rt.current_player()
        if player is not None:
            if acted:
                player.consecutive_missed_turns = 0
            await self._persist_player(player)
        self.rt.phase = TurnPhase.IDLE
        self.rt.pending = None
        await self._advance_turn()

    # ================= таймаут фазы =================

    async def _on_phase_timeout(self) -> None:
        pending = self.rt.pending
        player = self.rt.current_player()
        if pending is None or player is None:
            return
        # Пропуск/неверно: засчитываем штраф пропуска.
        player.consecutive_missed_turns += 1
        eliminated = player.consecutive_missed_turns > 3
        if eliminated:
            player.eliminated = True
        await self._persist_player(player)

        if pending.phase == TurnPhase.AWAITING_ANSWER and pending.question_id is not None:
            # Истёкший ответ = неверно. Для экзамена — timeout без штрафа очков.
            if pending.question_type == QuestionType.EXAM.value:
                await self._record_answer(player, pending, given="", is_correct=False,
                                          delta=0, status=AnswerStatus.TIMEOUT)
            else:
                delta = pending.points_wrong
                await self._record_answer(player, pending, given="", is_correct=False,
                                          delta=delta, status=AnswerStatus.TIMEOUT)
                await self._award(player, delta)
                await manager.broadcast(self.rt.code, msg(ServerMsg.ANSWER_RESULT, {
                    "player_id": player.id, "correct": False, "points_delta": delta,
                    "timeout": True,
                }))
        if eliminated:
            await self._log_event("player_eliminated", player.id, {"reason": "missed_turns"})
            await manager.broadcast(self.rt.code, msg(ServerMsg.PLAYER_ELIMINATED,
                                                      {"player_id": player.id}))
        await self._end_turn(acted=False)

    # ================= бросок кубика =================

    async def handle_roll(self, player_id: int) -> None:
        async with self._lock:
            if not self._is_actor(player_id, TurnPhase.AWAITING_ROLL):
                return
            player = self.rt.players[player_id]
            value = random.randint(1, 6)
            await self._log_event("dice_rolled", player_id, {"value": value})
            await manager.broadcast(self.rt.code, msg(ServerMsg.DICE_ROLLED,
                                                      {"player_id": player_id, "value": value}))
            await self._move(player, value)

    async def _move(self, player: RuntimePlayer, steps: int) -> None:
        size = self.rt.board["size"]
        total = player.position + steps
        passed_start = total >= size
        old = player.position
        player.position = total % size
        if passed_start:
            player.rounds_completed += 1
            # Бонус за прохождение Старта (если не встал ровно на него —
            # за остановку начислит резолвер START).
            if player.position != 0:
                await self._award(player, self.scoring["start_pass"])
        await manager.broadcast(self.rt.code, msg(ServerMsg.PAWN_MOVED, {
            "player_id": player.id, "from": old, "to": player.position,
            "passed_start": passed_start,
        }))
        await self._persist_player(player)
        await self._resolve_cell(player)

    # ================= резолв клетки =================

    async def _resolve_cell(self, player: RuntimePlayer) -> None:
        cell = self.rt.board["cells"][player.position]
        ctype = cell["type"]

        if ctype == CellType.ZACHET.value:
            await self._present_question(
                player, QuestionType.ZACHET,
                self.scoring["zachet_correct"], self.scoring["zachet_wrong"],
                self.rt.answer_timer_sec,
            )
        elif ctype == CellType.EXAM.value:
            await self._present_question(
                player, QuestionType.EXAM,
                self.scoring["exam_correct"], self.scoring["exam_wrong"],
                self.rt.answer_timer_sec,
            )
        elif ctype == CellType.CORNER.value:
            await self._resolve_corner(player, cell)
        elif ctype == CellType.LOCATION.value:
            await self._resolve_location(player, cell)
        else:
            await self._end_turn(acted=True)

    async def _resolve_corner(self, player: RuntimePlayer, cell: dict) -> None:
        corner = cell.get("corner")
        if corner == CornerKind.START.value:
            await self._award(player, self.scoring["start_stop"])
            await self._end_turn(acted=True)
        elif corner == CornerKind.SKIP.value:
            await self._log_event("skip_turn", player.id, {})
            await self._end_turn(acted=True)
        elif corner == CornerKind.BET.value:
            self.rt.phase = TurnPhase.AWAITING_BET
            self.rt.pending = PendingAction(
                phase=TurnPhase.AWAITING_BET, player_id=player.id,
                deadline=time.monotonic() + self.rt.answer_timer_sec,
                cell_index=player.position,
            )
            token = self._arm_timer(self.rt.answer_timer_sec)
            max_bet = min(self.scoring["bet_max"], max(0, player.score))
            await manager.broadcast(self.rt.code, msg(ServerMsg.BET_REQUESTED, {
                "player_id": player.id,
                "min": self.scoring["bet_min"], "max": self.scoring["bet_max"],
                "max_affordable": max_bet, "deadline": self.rt.answer_timer_sec,
            }))
            await self.broadcast_state()
            self._start_timer_task(token, self.rt.answer_timer_sec)
        elif corner == CornerKind.WHEEL.value:
            self.rt.phase = TurnPhase.AWAITING_WHEEL
            self.rt.pending = PendingAction(
                phase=TurnPhase.AWAITING_WHEEL, player_id=player.id,
                deadline=time.monotonic() + self.rt.turn_timer_sec,
                cell_index=player.position,
            )
            token = self._arm_timer(self.rt.turn_timer_sec)
            await self.broadcast_state()
            self._start_timer_task(token, self.rt.turn_timer_sec)
        else:
            await self._end_turn(acted=True)

    async def _resolve_location(self, player: RuntimePlayer, cell: dict) -> None:
        effect = cell.get("effect")
        if effect == LocationEffect.FREE_POINTS.value:
            await self._present_question(
                player, QuestionType.ZACHET,
                self.scoring["location_free_correct"], self.scoring["location_free_wrong"],
                self.rt.answer_timer_sec, is_location=True, location_effect=effect,
            )
        elif effect == LocationEffect.TIMED_QUESTION.value:
            await self._present_question(
                player, QuestionType.ZACHET,
                self.scoring["location_timed_correct"], self.scoring["location_timed_wrong"],
                self.scoring["location_timed_sec"], is_location=True, location_effect=effect,
            )
        elif effect == LocationEffect.FLAT_BONUS.value:
            await self._award(player, int(cell.get("amount", 3)))
            await self._end_turn(acted=True)
        elif effect == LocationEffect.FLAT_PENALTY.value:
            await self._award(player, int(cell.get("amount", -3)))
            await self._end_turn(acted=True)
        elif effect == LocationEffect.SWAP_WITH_PREVIOUS.value:
            await self._swap_with_previous(player)
            await self._end_turn(acted=True)
        else:
            await self._end_turn(acted=True)

    async def _swap_with_previous(self, player: RuntimePlayer) -> None:
        # Предыдущий игрок по очереди хода (среди не выбывших).
        n = len(self.rt.order)
        prev: RuntimePlayer | None = None
        for step in range(1, n + 1):
            idx = (self.rt.current_idx - step) % n
            cand = self.rt.players.get(self.rt.order[idx])
            if cand and not cand.eliminated and cand.id != player.id:
                prev = cand
                break
        if prev is None:
            return
        player.score, prev.score = prev.score, player.score
        await self._persist_player(player)
        await self._persist_player(prev)
        await self._log_event("swap_scores", player.id, {"with": prev.id})
        for pl in (player, prev):
            await manager.broadcast(self.rt.code, msg(ServerMsg.SCORE_UPDATED,
                                                      {"player_id": pl.id, "score": pl.score, "delta": 0}))

    # ================= колесо фортуны =================

    async def handle_spin(self, player_id: int) -> None:
        async with self._lock:
            if not self._is_actor(player_id, TurnPhase.AWAITING_WHEEL):
                return
            player = self.rt.players[player_id]
            sectors = self.rt.board["wheel_sectors"]
            sector = random.choice(sectors)
            await self._log_event("wheel_result", player_id, {"sector": sector["id"]})
            await manager.broadcast(self.rt.code, msg(ServerMsg.WHEEL_RESULT, {
                "player_id": player_id, "sector": sector,
            }))
            if sector["kind"] == "points":
                await self._award(player, int(sector["delta"]))
                await self._end_turn(acted=True)
            elif sector["kind"] == "go_to_exam":
                target = next_exam_index(player.position, self.rt.board)
                old = player.position
                player.position = target
                await self._persist_player(player)
                await manager.broadcast(self.rt.code, msg(ServerMsg.PAWN_MOVED, {
                    "player_id": player.id, "from": old, "to": target, "passed_start": False,
                }))
                await self._present_question(
                    player, QuestionType.EXAM,
                    self.scoring["exam_correct"], self.scoring["exam_wrong"],
                    self.rt.answer_timer_sec,
                )
            else:
                await self._end_turn(acted=True)

    # ================= ставка =================

    async def handle_bet(self, player_id: int, amount: int) -> None:
        async with self._lock:
            if not self._is_actor(player_id, TurnPhase.AWAITING_BET):
                return
            player = self.rt.players[player_id]
            lo, hi = self.scoring["bet_min"], self.scoring["bet_max"]
            if amount < lo or amount > hi or amount > player.score:
                await manager.send_to_player(self.rt.code, player_id, msg(
                    ServerMsg.ERROR, {"code": "invalid_bet",
                                      "message": "Недопустимый размер ставки"}))
                return
            await manager.broadcast(self.rt.code, msg(ServerMsg.BET_PLACED,
                                                      {"player_id": player_id, "amount": amount}))
            # Вопрос на ставку — зачётного типа (авто-проверка), ±ставка.
            await self._present_question(
                player, QuestionType.ZACHET, amount, -amount,
                self.rt.answer_timer_sec, bet_amount=amount,
            )

    async def handle_decline_bet(self, player_id: int) -> None:
        async with self._lock:
            if not self._is_actor(player_id, TurnPhase.AWAITING_BET):
                return
            await self._log_event("bet_declined", player_id, {})
            await self._end_turn(acted=True)

    # ================= вопросы =================

    async def _present_question(
        self, player: RuntimePlayer, qtype: QuestionType,
        points_correct: int, points_wrong: int, timer_sec: int,
        is_location: bool = False, location_effect: str | None = None,
        bet_amount: int | None = None,
    ) -> None:
        async with self._session_factory() as s:
            question = await pick_question(s, self.rt.bank_id, qtype, self.rt.used_question_ids)
        if question is None:
            # Нет вопросов в банке — завершаем ход без начисления.
            await self._end_turn(acted=True)
            return
        self.rt.used_question_ids.add(question.id)
        self.rt.phase = TurnPhase.AWAITING_ANSWER
        self.rt.pending = PendingAction(
            phase=TurnPhase.AWAITING_ANSWER, player_id=player.id,
            deadline=time.monotonic() + timer_sec, cell_index=player.position,
            question_id=question.id, question_type=qtype.value,
            correct_index=question.correct_option_index,
            is_location=is_location, location_effect=location_effect,
            bet_amount=bet_amount, points_correct=points_correct, points_wrong=points_wrong,
        )
        token = self._arm_timer(timer_sec)
        # Клиенту — БЕЗ правильного ответа (PLAN §7.3).
        await manager.broadcast(self.rt.code, msg(ServerMsg.QUESTION_PRESENTED, {
            "player_id": player.id,
            "question_id": question.id,
            "text": question.text,
            "options": question.options,
            "cell_type": qtype.value,
            "is_location": is_location,
            "deadline": timer_sec,
        }))
        await self.broadcast_state()
        self._start_timer_task(token, timer_sec)

    async def handle_answer(self, player_id: int, answer: str) -> None:
        async with self._lock:
            if not self._is_actor(player_id, TurnPhase.AWAITING_ANSWER):
                return
            pending = self.rt.pending
            player = self.rt.players[player_id]
            assert pending is not None

            if pending.question_type == QuestionType.EXAM.value:
                # Экзамен: уходит на ручную проверку, ход переходит сразу (PLAN §15.2).
                ans = await self._record_answer(
                    player, pending, given=answer, is_correct=None, delta=0,
                    status=AnswerStatus.PENDING_REVIEW,
                )
                await manager.broadcast(self.rt.code, msg(ServerMsg.EXAM_PENDING_REVIEW,
                                                          {"player_id": player_id}))
                await self._push_exam_queue()
                await self._end_turn(acted=True)
                return

            # Зачёт / локация / ставка: авто-проверка.
            try:
                chosen = int(answer)
            except (TypeError, ValueError):
                chosen = -1
            correct = chosen == pending.correct_index
            delta = pending.points_correct if correct else pending.points_wrong
            status = AnswerStatus.AUTO_CORRECT if correct else AnswerStatus.AUTO_WRONG
            await self._record_answer(player, pending, given=str(chosen),
                                      is_correct=correct, delta=delta, status=status)
            await self._award(player, delta)
            await manager.broadcast(self.rt.code, msg(ServerMsg.ANSWER_RESULT, {
                "player_id": player_id, "correct": correct, "points_delta": delta,
            }))
            await self._end_turn(acted=True)

    async def _record_answer(
        self, player: RuntimePlayer, pending: PendingAction, given: str,
        is_correct: bool | None, delta: int, status: AnswerStatus,
    ) -> int:
        async with self._session_factory() as s:
            ans = Answer(
                room_id=self.rt.room_id, player_id=player.id,
                question_id=pending.question_id, cell_index=pending.cell_index,
                given_answer=given, is_correct=is_correct, points_delta=delta,
                status=status,
                resolved_at=None if status == AnswerStatus.PENDING_REVIEW
                else utcnow(),
            )
            s.add(ans)
            await s.commit()
            await s.refresh(ans)
            return ans.id

    # ================= экзамен: ручная проверка =================

    async def _push_exam_queue(self) -> None:
        from sqlalchemy import select
        from app.models import Question
        async with self._session_factory() as s:
            stmt = (
                select(Answer, Question)
                .join(Question, Question.id == Answer.question_id, isouter=True)
                .where(Answer.room_id == self.rt.room_id,
                       Answer.status == AnswerStatus.PENDING_REVIEW)
                .order_by(Answer.answered_at)
            )
            rows = (await s.execute(stmt)).all()
        items = []
        for ans, q in rows:
            p = self.rt.players.get(ans.player_id)
            items.append({
                "answer_id": ans.id,
                "player_id": ans.player_id,
                "player": p.full_name if p else str(ans.player_id),
                "question_text": q.text if q else "",
                "reference_answer": q.reference_answer if q else None,
                "given_answer": ans.given_answer,
            })
        await manager.broadcast_teachers(self.rt.code, msg(ServerMsg.EXAM_REVIEW_QUEUE,
                                                           {"items": items}))

    async def resolve_exam(self, answer_id: int, accepted: bool) -> None:
        async with self._lock:
            async with self._session_factory() as s:
                ans = await s.get(Answer, answer_id)
                if ans is None or ans.status != AnswerStatus.PENDING_REVIEW:
                    return
                delta = self.scoring["exam_correct"] if accepted else self.scoring["exam_wrong"]
                ans.is_correct = accepted
                ans.points_delta = delta
                ans.status = AnswerStatus.APPROVED if accepted else AnswerStatus.REJECTED
                ans.resolved_at = utcnow()
                player_id = ans.player_id
                await s.commit()
            player = self.rt.players.get(player_id)
            if player is not None:
                await self._award(player, delta)
                await manager.broadcast(self.rt.code, msg(ServerMsg.ANSWER_RESULT, {
                    "player_id": player_id, "correct": accepted, "points_delta": delta,
                    "exam": True,
                }))
            await self._push_exam_queue()
            await self._check_end_condition_and_maybe_finish()

    # ================= модерация преподавателя =================

    async def pause(self) -> None:
        async with self._lock:
            if self.rt.status != "playing":
                return
            self.rt.status = "paused"
            # Замораживаем оставшееся время, отменяя текущий таймер сменой токена.
            if self.rt.pending is not None:
                remaining = max(0.0, self.rt.pending.deadline - time.monotonic())
                self.rt.pending.bet_amount = self.rt.pending.bet_amount  # noop
                self._paused_remaining = remaining
                self.rt.next_timer_token()  # инвалидируем активный таймер
            await self._update_room_status("paused")
            await self._log_event("game_paused", None, {})
            await manager.broadcast(self.rt.code, msg(ServerMsg.GAME_PAUSED, {}))
            await self.broadcast_state()

    async def resume(self) -> None:
        async with self._lock:
            if self.rt.status != "paused":
                return
            self.rt.status = "playing"
            remaining = getattr(self, "_paused_remaining", None)
            await self._update_room_status("playing")
            await self._log_event("game_resumed", None, {})
            await manager.broadcast(self.rt.code, msg(ServerMsg.GAME_RESUMED, {}))
            if self.rt.pending is not None:
                # Обычное снятие с паузы — продолжаем текущий ход.
                secs = remaining if remaining is not None else self.rt.turn_timer_sec
                token = self._arm_timer(secs)
                self._start_timer_task(token, secs)
                await self.broadcast_state()
            else:
                # Ход был потерян (перезапуск во время паузы) — начинаем новый.
                await self._advance_turn()

    async def kick_player(self, player_id: int) -> None:
        async with self._lock:
            player = self.rt.players.get(player_id)
            if player is None or player.eliminated:
                return
            player.eliminated = True
            await self._persist_player(player)
            await self._log_event("player_kicked", player_id, {})
            await manager.broadcast(self.rt.code, msg(ServerMsg.PLAYER_ELIMINATED,
                                                      {"player_id": player_id, "kicked": True}))
            # Если кикнули текущего — переходим дальше.
            cur = self.rt.current_player()
            if self.rt.status == "playing" and cur and cur.id == player_id:
                self.rt.next_timer_token()
                await self._end_turn(acted=False)
            else:
                await self.broadcast_state()

    async def adjust_score(self, player_id: int, delta: int) -> None:
        async with self._lock:
            player = self.rt.players.get(player_id)
            if player is None:
                return
            await self._log_event("score_adjusted", player_id, {"delta": delta})
            await self._award(player, delta)

    async def end_game(self) -> None:
        async with self._lock:
            await self._finish_game(reason="teacher")

    # ================= завершение игры =================

    async def _check_end_condition(self) -> bool:
        """True если игра завершилась (и уже обработана)."""
        et = self.rt.end_condition_type
        ev = self.rt.end_condition_value
        if et == "rounds":
            if any(p.rounds_completed >= ev for p in self.rt.players.values()):
                await self._finish_game(reason="rounds")
                return True
        elif et == "score":
            if any(p.score >= ev for p in self.rt.players.values()):
                await self._finish_game(reason="score")
                return True
        elif et == "time":
            if self.rt.started_monotonic is not None:
                if time.monotonic() - self.rt.started_monotonic >= ev:
                    await self._finish_game(reason="time")
                    return True
        return False

    async def _check_end_condition_and_maybe_finish(self) -> None:
        await self._check_end_condition()

    async def _finish_game(self, reason: str) -> None:
        if self.rt.status == "finished":
            return
        self.rt.status = "finished"
        self.rt.phase = TurnPhase.IDLE
        self.rt.pending = None
        self.rt.next_timer_token()
        await self._update_room_status("finished", finished=True)
        ranking = self._compute_ranking()
        await self._log_event("game_finished", None, {"reason": reason})
        await manager.broadcast(self.rt.code, msg(ServerMsg.GAME_FINISHED,
                                                  {"ranking": ranking, "reason": reason}))

    def _compute_ranking(self) -> list[dict]:
        players = sorted(self.rt.players.values(), key=lambda p: p.score, reverse=True)
        ranking = []
        last_score = None
        place = 0
        for i, p in enumerate(players):
            if p.score != last_score:
                place = i + 1
                last_score = p.score
            ranking.append({
                "place": place, "player_id": p.id, "name": p.full_name,
                "group_name": p.group_name, "score": p.score,
            })
        return ranking

    async def _update_room_status(self, status: str, finished: bool = False) -> None:
        async with self._session_factory() as s:
            from app.models import Room
            room = await s.get(Room, self.rt.room_id)
            if room:
                room.status = status  # type: ignore[assignment]
                if finished:
                    room.finished_at = utcnow()
                await s.commit()

    # ================= присутствие =================

    async def on_player_connected(self, player_id: int) -> None:
        player = self.rt.players.get(player_id)
        if player is None:
            return
        player.connected = True
        await self._persist_player(player)
        await manager.broadcast(self.rt.code, msg(ServerMsg.PLAYER_RECONNECTED,
                                                  {"player_id": player_id}))
        await self.broadcast_state()

    async def on_player_disconnected(self, player_id: int) -> None:
        player = self.rt.players.get(player_id)
        if player is None:
            return
        player.connected = False
        await self._persist_player(player)
        await manager.broadcast(self.rt.code, msg(ServerMsg.PLAYER_LEFT,
                                                  {"player_id": player_id}))
        await self.broadcast_state()

    # ================= утилиты =================

    def _is_actor(self, player_id: int, expected: TurnPhase) -> bool:
        """Идемпотентность: игнорируем действия не от активного игрока/не в той фазе."""
        if self.rt.status != "playing" or self.rt.pending is None:
            return False
        cur = self.rt.current_player()
        return (
            cur is not None
            and cur.id == player_id
            and self.rt.phase == expected
            and self.rt.pending.player_id == player_id
        )
