// Список игроков с баллами, подсветкой активного и индикатором соединения.
import type { PlayerPublic } from "../types";

const PAWN_COLORS = ["#facc15", "#f472b6", "#34d399", "#60a5fa", "#fb923c", "#a78bfa", "#f87171", "#22d3ee"];

interface Props {
  players: PlayerPublic[];
  currentPlayerId: number | null;
  myPlayerId?: number | null;
}

export default function ScorePanel({ players, currentPlayerId, myPlayerId }: Props) {
  const sorted = [...players].sort((a, b) => b.score - a.score);
  return (
    <div className="card">
      <div className="mb-2 text-sm font-semibold text-slate-300">Игроки</div>
      <ul className="space-y-1">
        {sorted.map((p) => {
          const active = p.id === currentPlayerId;
          const me = p.id === myPlayerId;
          return (
            <li
              key={p.id}
              className={`flex items-center gap-2 rounded-lg px-2 py-1.5 ${
                active ? "bg-brand/20 ring-1 ring-brand" : ""
              } ${p.eliminated ? "opacity-40 line-through" : ""}`}
            >
              <span
                className="h-3 w-3 shrink-0 rounded-full"
                style={{ background: PAWN_COLORS[p.turn_order % PAWN_COLORS.length] }}
              />
              <span className="flex-1 truncate text-sm">
                {p.name} {p.surname}
                {me && <span className="ml-1 text-xs text-brand">(вы)</span>}
                {!p.connected && <span className="ml-1 text-xs text-amber-400">●</span>}
              </span>
              <span className="font-bold tabular-nums">{p.score}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
