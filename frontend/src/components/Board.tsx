// Адаптивное SVG-поле: кольцо из 24 клеток по периметру сетки 7×7 (PLAN §12).
import type { BoardConfig, PlayerPublic } from "../types";

// Порядок координат (col,row) по периметру 7×7, углы на индексах 0,6,12,18.
function perimeter(): [number, number][] {
  const coords: [number, number][] = [];
  for (let c = 0; c <= 6; c++) coords.push([c, 0]); // верх →  (0..6)
  for (let r = 1; r <= 6; r++) coords.push([6, r]); // право ↓ (7..12)
  for (let c = 5; c >= 0; c--) coords.push([c, 6]); // низ ←   (13..18)
  for (let r = 5; r >= 1; r--) coords.push([0, r]); // лево ↑  (19..23)
  return coords;
}
const COORDS = perimeter();
const CELL = 100;

const TYPE_COLOR: Record<string, string> = {
  CORNER: "#b45309",
  ZACHET: "#15803d",
  EXAM: "#b91c1c",
  LOCATION: "#1d4ed8",
};

const PAWN_COLORS = ["#facc15", "#f472b6", "#34d399", "#60a5fa", "#fb923c", "#a78bfa", "#f87171", "#22d3ee"];

interface Props {
  board: BoardConfig;
  players: PlayerPublic[];
  currentPlayerId: number | null;
}

export default function Board({ board, players, currentPlayerId }: Props) {
  const cells = board?.cells ?? [];
  // Сгруппировать игроков по клетке для разведения фишек.
  const byCell = new Map<number, PlayerPublic[]>();
  players.forEach((p) => {
    if (p.eliminated) return;
    const arr = byCell.get(p.position) ?? [];
    arr.push(p);
    byCell.set(p.position, arr);
  });

  return (
    <svg viewBox="0 0 700 700" className="w-full max-w-[560px] mx-auto select-none">
      {cells.map((cell) => {
        const [col, row] = COORDS[cell.index] ?? [0, 0];
        const x = col * CELL;
        const y = row * CELL;
        const isCorner = cell.type === "CORNER";
        return (
          <g key={cell.index}>
            <rect
              x={x + 3}
              y={y + 3}
              width={CELL - 6}
              height={CELL - 6}
              rx={isCorner ? 14 : 8}
              fill={TYPE_COLOR[cell.type] ?? "#334155"}
              opacity={0.92}
              stroke="#0f172a"
              strokeWidth={2}
            />
            <text
              x={x + CELL / 2}
              y={y + 20}
              textAnchor="middle"
              fontSize="11"
              fill="#f8fafc"
              fontWeight="600"
            >
              {cell.index}
            </text>
            <foreignObject x={x + 6} y={y + 26} width={CELL - 12} height={CELL - 40}>
              <div
                style={{
                  fontSize: 10,
                  lineHeight: 1.1,
                  color: "#f1f5f9",
                  textAlign: "center",
                  wordBreak: "break-word",
                }}
              >
                {cell.label}
              </div>
            </foreignObject>
          </g>
        );
      })}

      {/* Фишки */}
      {[...byCell.entries()].map(([pos, group]) =>
        group.map((p, i) => {
          const [col, row] = COORDS[pos] ?? [0, 0];
          const cx = col * CELL + 22 + (i % 3) * 26;
          const cy = row * CELL + CELL - 22 - Math.floor(i / 3) * 22;
          const color = PAWN_COLORS[(p.turn_order ?? 0) % PAWN_COLORS.length];
          const active = p.id === currentPlayerId;
          return (
            <g key={`${pos}-${p.id}`}>
              <circle
                cx={cx}
                cy={cy}
                r={11}
                fill={color}
                stroke={active ? "#ffffff" : "#0f172a"}
                strokeWidth={active ? 3 : 1.5}
              />
              {active && <circle cx={cx} cy={cy} r={15} fill="none" stroke="#ffffff" strokeWidth={1.5} opacity={0.6} />}
            </g>
          );
        }),
      )}

      {/* Центр */}
      <text x={350} y={340} textAnchor="middle" fontSize="26" fill="#475569" fontWeight="800">
        МОНОПОЛИЯ
      </text>
      <text x={350} y={372} textAnchor="middle" fontSize="14" fill="#64748b">
        студенческая
      </text>
    </svg>
  );
}
