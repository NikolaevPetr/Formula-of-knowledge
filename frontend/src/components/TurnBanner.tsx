// Индикатор «чей сейчас ход» — для студентов и преподавателя.
import type { RoomState } from "../types";

const PAWN_COLORS = ["#facc15", "#f472b6", "#34d399", "#60a5fa", "#fb923c", "#a78bfa", "#f87171", "#22d3ee"];

export default function TurnBanner({
  room,
  myPlayerId,
}: {
  room: RoomState;
  myPlayerId?: number | null;
}) {
  if (room.status === "lobby")
    return <Banner tone="slate">Ожидание старта игры…</Banner>;
  if (room.status === "finished") return <Banner tone="slate">Игра завершена</Banner>;
  if (room.status === "paused") return <Banner tone="amber">⏸ Игра на паузе</Banner>;

  const cur = room.players.find((p) => p.id === room.current_player_id);
  const mine = room.current_player_id != null && room.current_player_id === myPlayerId;

  if (!cur) return <Banner tone="slate">Ожидание хода…</Banner>;

  const color = PAWN_COLORS[cur.turn_order % PAWN_COLORS.length];
  const phaseLabel: Record<string, string> = {
    awaiting_roll: "бросает кубик",
    awaiting_answer: "отвечает на вопрос",
    awaiting_bet: "делает ставку",
    awaiting_wheel: "крутит колесо",
  };
  const action = room.pending ? phaseLabel[room.pending.phase] ?? "" : "";

  return (
    <Banner tone={mine ? "brand" : "slate"}>
      <span className="inline-flex items-center gap-2">
        <span className="h-3 w-3 rounded-full" style={{ background: color }} />
        {mine ? (
          <b>Ваш ход — {action || "ходите"}!</b>
        ) : (
          <span>
            Ходит <b>{cur.name} {cur.surname}</b>
            {action ? ` — ${action}` : ""}
          </span>
        )}
      </span>
    </Banner>
  );
}

function Banner({ tone, children }: { tone: "brand" | "slate" | "amber"; children: React.ReactNode }) {
  const map = {
    brand: "bg-brand/20 ring-brand text-white",
    slate: "bg-slate-800/80 ring-white/5 text-slate-200",
    amber: "bg-amber-600/20 ring-amber-500 text-amber-200",
  };
  return (
    <div className={`rounded-2xl px-4 py-3 text-center text-sm font-medium shadow ring-1 ${map[tone]}`}>
      {children}
    </div>
  );
}
