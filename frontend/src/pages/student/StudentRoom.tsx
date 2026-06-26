// Главный экран студента: лобби → игра → результаты, в зависимости от статуса.
import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useGame } from "../../store/gameStore";
import Board from "../../components/Board";
import ScorePanel from "../../components/ScorePanel";
import QuestionCard from "../../components/QuestionCard";
import BetPanel from "../../components/BetPanel";
import Wheel from "../../components/Wheel";
import Dice from "../../components/Dice";
import Timer from "../../components/Timer";
import TurnBanner from "../../components/TurnBanner";

export default function StudentRoom() {
  const { code = "" } = useParams();
  const g = useGame();

  // Подключаемся при монтировании, отключаемся при размонтировании.
  useEffect(() => {
    useGame.getState().connectStudent(code);
    return () => useGame.getState().disconnect();
  }, [code]);

  // После соединения: если нет токена сессии, отправляем pending_join из Join.
  useEffect(() => {
    if (!g.connected) return;
    if (g.myPlayerId) return;
    const pending = sessionStorage.getItem(`pending_join_${code}`);
    if (pending && !g.sessionToken) {
      const { name, surname, group } = JSON.parse(pending);
      g.joinAs(name, surname, group);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [g.connected, g.myPlayerId]);

  const room = g.room;
  const myTurn = room?.current_player_id != null && room.current_player_id === g.myPlayerId;
  const phase = room?.pending?.phase;
  // Кубик показываем в фазе awaiting_roll, а также как «страховку», если состояние
  // фазы по какой-то причине не пришло, но ход — наш (сервер всё равно проверит).
  const showRoll =
    room?.status === "playing" &&
    (phase === "awaiting_roll" || (phase == null && myTurn));

  if (!room) {
    return (
      <div className="min-h-full flex items-center justify-center p-4">
        <div className="card text-center">
          <p className="text-slate-300">Подключение к комнате {code}…</p>
        </div>
      </div>
    );
  }

  // Экран результатов
  if (room.status === "finished" && g.ranking) {
    return (
      <div className="min-h-full p-4">
        <div className="mx-auto max-w-sm space-y-4">
          <h1 className="text-center text-2xl font-bold">Итоги</h1>
          <div className="card space-y-2">
            {g.ranking.map((r) => (
              <div
                key={r.player_id}
                className={`flex items-center justify-between rounded-lg px-3 py-2 ${
                  r.place === 1 ? "bg-yellow-500/20 ring-1 ring-yellow-500" : "bg-slate-700/40"
                } ${r.player_id === g.myPlayerId ? "font-bold" : ""}`}
              >
                <span>
                  {r.place}. {r.name}
                </span>
                <span className="tabular-nums">{r.score}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-full p-3 pb-24">
      <div className="mx-auto max-w-5xl space-y-3">
        <header className="flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Комната {room.code}</div>
            <div className="text-sm font-semibold">{room.subject}</div>
          </div>
          <StatusBadge status={room.status} />
        </header>

        {/* Чей сейчас ход */}
        <TurnBanner room={room} myPlayerId={g.myPlayerId} />

        {/* Потеря связи: видимый статус + ручное переподключение (важно для dev/HMR
            и случая, когда бэкенд перезапускался). Без этого экран просто «зависал». */}
        {!g.connected && room.status !== "finished" && (
          <div className="rounded-2xl bg-red-600/20 px-4 py-3 text-center text-sm font-medium text-red-200 ring-1 ring-red-500">
            <span className="mr-2">⚠ Соединение потеряно — переподключение…</span>
            <button
              className="underline underline-offset-2 hover:text-white"
              onClick={() => useGame.getState().connectStudent(code)}
            >
              Переподключиться
            </button>
          </div>
        )}

        <div className="grid gap-3 lg:grid-cols-[1fr_340px]">
          {/* Поле + игроки */}
          <div className="space-y-3">
            <Board board={room.board} players={room.players} currentPlayerId={room.current_player_id} />
            <ScorePanel players={room.players} currentPlayerId={room.current_player_id} myPlayerId={g.myPlayerId} />
          </div>

          {/* Панель действий справа от поля */}
          <div className="space-y-3">
            {room.status === "lobby" && (
              <div className="card text-center">
                <p className="text-slate-300">Ожидаем начала игры…</p>
                <p className="mt-1 text-xs text-slate-500">
                  Преподаватель запустит игру, когда все будут готовы.
                </p>
              </div>
            )}

            {showRoll && (
              <div className="card flex flex-col items-center gap-3">
                {room.pending?.time_left != null && (
                  <Timer
                    seconds={room.turn_timer_sec}
                    startedAt={Date.now() - (room.turn_timer_sec - room.pending.time_left) * 1000}
                  />
                )}
                <Dice value={g.dice?.value ?? null} />
                {myTurn ? (
                  <button className="btn-primary w-full text-lg" onClick={() => g.send("roll_dice")}>
                    🎲 Бросить кубик
                  </button>
                ) : (
                  <p className="text-sm text-slate-400">Ход другого игрока…</p>
                )}
              </div>
            )}

            {phase === "awaiting_answer" && g.question && (
              <QuestionCard
                key={g.question.question_id}
                question={g.question}
                canAnswer={myTurn}
                answerTimerSec={room.answer_timer_sec}
                onAnswer={(a) => g.send("submit_answer", { answer: a })}
              />
            )}

            {phase === "awaiting_bet" &&
              (myTurn && g.betRequest ? (
                <BetPanel
                  min={g.betRequest.min}
                  max={g.betRequest.max}
                  maxAffordable={g.betRequest.max_affordable}
                  onPlace={(amount) => g.send("place_bet", { amount })}
                  onDecline={() => g.send("decline_bet")}
                />
              ) : (
                <div className="card text-sm text-slate-400">Игрок делает ставку…</div>
              ))}

            {phase === "awaiting_wheel" && (
              <Wheel
                sectorId={g.wheel?.sector.id ?? null}
                spinning={false}
                canSpin={myTurn}
                onSpin={() => g.send("spin_wheel")}
              />
            )}

            <GameLog />
          </div>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    lobby: "bg-slate-600",
    playing: "bg-green-600",
    paused: "bg-amber-600",
    finished: "bg-slate-700",
  };
  const label: Record<string, string> = {
    lobby: "Лобби",
    playing: "Игра",
    paused: "Пауза",
    finished: "Завершена",
  };
  return <span className={`rounded-full px-3 py-1 text-xs font-semibold ${map[status]}`}>{label[status]}</span>;
}

function GameLog() {
  const log = useGame((s) => s.log);
  if (log.length === 0) return null;
  return (
    <div className="card max-h-40 overflow-y-auto">
      <div className="mb-1 text-xs font-semibold text-slate-400">События</div>
      <ul className="space-y-0.5 text-xs text-slate-300">
        {log.slice().reverse().map((e) => (
          <li key={e.id}>{e.text}</li>
        ))}
      </ul>
    </div>
  );
}
