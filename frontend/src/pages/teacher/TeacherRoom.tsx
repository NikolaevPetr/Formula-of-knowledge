// Управление комнатой преподавателем: лобби, старт, модерация, проверка экзаменов.
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getToken } from "../../api/client";
import { useGame } from "../../store/gameStore";
import Board from "../../components/Board";
import TurnBanner from "../../components/TurnBanner";

export default function TeacherRoom() {
  const { code = "", roomId } = useParams();
  const g = useGame();

  // Подключаемся при монтировании, отключаемся при размонтировании.
  // (StrictMode в dev делает mount→unmount→mount — реконнект отработает корректно.)
  useEffect(() => {
    const token = getToken();
    if (token) useGame.getState().connectTeacher(code, token);
    return () => useGame.getState().disconnect();
  }, [code]);

  const room = g.room;
  const joinLink = `${location.origin}/join/${code}`;

  if (!room) {
    return (
      <div className="min-h-full flex items-center justify-center p-4">
        <div className="card">Подключение к комнате {code}…</div>
      </div>
    );
  }

  const activePlayers = room.players.filter((p) => !p.eliminated);

  return (
    <div className="min-h-full p-4">
      <div className="mx-auto max-w-6xl space-y-4">
        <header className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <Link to="/teacher" className="text-sm text-brand">
              ← Дашборд
            </Link>
            <h1 className="text-2xl font-bold">
              Комната <span className="font-mono tracking-widest">{code}</span>
            </h1>
            <div className="text-sm text-slate-400">
              {room.subject} · статус: {room.status}
            </div>
          </div>
          <div className="flex gap-2">
            {room.status === "lobby" && (
              <button className="btn-primary" disabled={activePlayers.length < 2} onClick={() => g.send("start_game")}>
                Начать игру
              </button>
            )}
            {room.status === "playing" && (
              <button className="btn-ghost" onClick={() => g.send("pause")}>
                Пауза
              </button>
            )}
            {room.status === "paused" && (
              <button className="btn-primary" onClick={() => g.send("resume")}>
                Продолжить
              </button>
            )}
            {(room.status === "playing" || room.status === "paused") && (
              <button className="btn-ghost" onClick={() => g.send("end_game")}>
                Завершить
              </button>
            )}
            {room.status === "finished" && (
              <Link to={`/teacher/rooms/${roomId}/report`} className="btn-primary">
                Отчёт
              </Link>
            )}
          </div>
        </header>

        {room.status === "lobby" && (
          <div className="card">
            <div className="text-sm text-slate-300">Ссылка для студентов:</div>
            <div className="mt-1 flex items-center gap-2">
              <code className="rounded bg-slate-900 px-3 py-2 text-brand">{joinLink}</code>
              <button className="btn-ghost" onClick={() => navigator.clipboard.writeText(joinLink)}>
                Копировать
              </button>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Игроков в лобби: {activePlayers.length}/{room.players.length || 0}. Нужно минимум 2.
            </p>
          </div>
        )}

        {/* Чей сейчас ход */}
        {room.status !== "lobby" && <TurnBanner room={room} />}

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <Board board={room.board} players={room.players} currentPlayerId={room.current_player_id} />
          </div>

          <div className="space-y-4">
            {/* Игроки + модерация */}
            <div className="card">
              <div className="mb-2 text-sm font-semibold text-slate-300">Игроки</div>
              <ul className="space-y-2">
                {[...room.players]
                  .sort((a, b) => b.score - a.score)
                  .map((p) => (
                    <li key={p.id} className="flex items-center gap-2">
                      <span
                        className={`flex-1 truncate text-sm ${p.eliminated ? "line-through opacity-50" : ""} ${
                          p.id === room.current_player_id ? "font-bold text-brand" : ""
                        }`}
                      >
                        {p.name} {p.surname}
                        <span className="text-xs text-slate-500"> · {p.group_name}</span>
                        {!p.connected && <span className="ml-1 text-amber-400">●</span>}
                      </span>
                      <span className="w-8 text-right font-bold tabular-nums">{p.score}</span>
                      <button className="text-xs text-slate-400 hover:text-green-400" onClick={() => g.send("adjust_score", { player_id: p.id, delta: 1 })}>
                        +1
                      </button>
                      <button className="text-xs text-slate-400 hover:text-red-400" onClick={() => g.send("adjust_score", { player_id: p.id, delta: -1 })}>
                        −1
                      </button>
                      {!p.eliminated && (
                        <button className="text-xs text-red-400" onClick={() => g.send("kick_player", { player_id: p.id })}>
                          кик
                        </button>
                      )}
                    </li>
                  ))}
              </ul>
            </div>

            {/* Очередь проверки экзаменов */}
            <div className="card">
              <div className="mb-2 text-sm font-semibold text-slate-300">
                Проверка экзаменов ({g.examQueue.length})
              </div>
              {g.examQueue.length === 0 ? (
                <p className="text-xs text-slate-500">Нет ответов на проверке.</p>
              ) : (
                <ul className="space-y-3">
                  {g.examQueue.map((it) => (
                    <li key={it.answer_id} className="rounded-lg bg-slate-900/60 p-3">
                      <div className="text-xs text-slate-400">{it.player}</div>
                      <div className="text-sm font-medium">{it.question_text}</div>
                      {it.reference_answer && (
                        <div className="mt-1 text-xs text-slate-400">Эталон: {it.reference_answer}</div>
                      )}
                      <div className="mt-1 rounded bg-slate-800 p-2 text-sm">
                        Ответ: {it.given_answer || <span className="text-slate-500">— пусто —</span>}
                      </div>
                      <div className="mt-2 flex gap-2">
                        <button
                          className="btn-primary flex-1 py-2"
                          onClick={() => g.send("resolve_exam", { answer_id: it.answer_id, accepted: true })}
                        >
                          Принять (+10)
                        </button>
                        <button
                          className="btn-ghost flex-1 py-2"
                          onClick={() => g.send("resolve_exam", { answer_id: it.answer_id, accepted: false })}
                        >
                          Отклонить (−2)
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
