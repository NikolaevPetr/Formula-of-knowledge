// Колесо фортуны: 6 секторов. Анимация поворота к выпавшему сектору.
import { useEffect, useState } from "react";

const SECTORS = [
  "Стипендия +5",
  "Сессия +10",
  "Опоздал −5",
  "Олимпиада +15",
  "На экзамен!",
  "Списывание −10",
];
const COLORS = ["#22c55e", "#16a34a", "#ef4444", "#eab308", "#3b82f6", "#dc2626"];

export default function Wheel({
  sectorId,
  spinning,
  onSpin,
  canSpin,
}: {
  sectorId: number | null;
  spinning: boolean;
  onSpin: () => void;
  canSpin: boolean;
}) {
  const [angle, setAngle] = useState(0);

  useEffect(() => {
    if (sectorId == null) return;
    const idx = sectorId - 1;
    const target = 360 * 5 + (360 - idx * 60 - 30);
    setAngle(target);
  }, [sectorId]);

  return (
    <div className="card flex flex-col items-center">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand">
        Колесо фортуны
      </div>
      <div className="relative">
        <div
          className="absolute left-1/2 -top-1 z-10 h-0 w-0 -translate-x-1/2"
          style={{ borderLeft: "8px solid transparent", borderRight: "8px solid transparent", borderTop: "14px solid #f8fafc" }}
        />
        <svg
          viewBox="0 0 200 200"
          className="w-44 h-44 transition-transform duration-[2500ms] ease-out"
          style={{ transform: `rotate(${angle}deg)` }}
        >
          {SECTORS.map((label, i) => {
            const a0 = (i * 60 * Math.PI) / 180;
            const a1 = ((i + 1) * 60 * Math.PI) / 180;
            const x0 = 100 + 95 * Math.cos(a0);
            const y0 = 100 + 95 * Math.sin(a0);
            const x1 = 100 + 95 * Math.cos(a1);
            const y1 = 100 + 95 * Math.sin(a1);
            const mid = (a0 + a1) / 2;
            return (
              <g key={i}>
                <path d={`M100,100 L${x0},${y0} A95,95 0 0,1 ${x1},${y1} Z`} fill={COLORS[i]} opacity={0.9} />
                <text
                  x={100 + 58 * Math.cos(mid)}
                  y={100 + 58 * Math.sin(mid)}
                  fontSize="8"
                  fill="#fff"
                  textAnchor="middle"
                  transform={`rotate(${(mid * 180) / Math.PI + 90} ${100 + 58 * Math.cos(mid)} ${100 + 58 * Math.sin(mid)})`}
                >
                  {label}
                </text>
              </g>
            );
          })}
          <circle cx="100" cy="100" r="14" fill="#1e293b" stroke="#f8fafc" strokeWidth="2" />
        </svg>
      </div>
      {canSpin && (
        <button className="btn-primary mt-3 w-full" disabled={spinning} onClick={onSpin}>
          Крутить колесо
        </button>
      )}
    </div>
  );
}
