// Обратный отсчёт от дедлайна (клиентская индикация, сервер — источник истины).
import { useEffect, useState } from "react";

interface Props {
  seconds: number; // полная длительность
  startedAt: number; // Date.now() начала
  onExpire?: () => void; // ← добавить

}

export default function Timer({ seconds, startedAt, onExpire }: Props) {
  const [left, setLeft] = useState(seconds);

  useEffect(() => {
    const tick = () => {
      const elapsed = (Date.now() - startedAt) / 1000;
      const remaining = Math.max(0, seconds - elapsed);
      setLeft(remaining);
      if (remaining === 0) {
      clearInterval(id);  // ← остановить интервал
      onExpire?.();       // ← вызвать ровно один раз
    }
    };
    tick();
    const id = setInterval(tick, 200);
    return () => clearInterval(id);
  }, [seconds, startedAt]);

  const pct = Math.max(0, Math.min(100, (left / seconds) * 100));
  const danger = left <= 5;
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">Осталось</span>
        <span className={danger ? "text-red-400 font-bold" : "text-slate-200"}>
          {left.toFixed(0)} с
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-700 overflow-hidden">
        <div
          className={`h-full transition-all duration-200 ${danger ? "bg-red-500" : "bg-brand"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
