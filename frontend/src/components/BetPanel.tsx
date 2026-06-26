// Панель ставки на знания (PLAN §2.3): выбор 5–20, не больше счёта, можно отказаться.
import { useState } from "react";

interface Props {
  min: number;
  max: number;
  maxAffordable: number;
  onPlace: (amount: number) => void;
  onDecline: () => void;
}

export default function BetPanel({ min, max, maxAffordable, onPlace, onDecline }: Props) {
  const ceiling = Math.min(max, maxAffordable);
  const [amount, setAmount] = useState(Math.max(min, Math.min(ceiling, min)));
  const canBet = ceiling >= min;

  return (
    <div className="card">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand">
        Ставка на знания
      </div>
      {canBet ? (
        <>
          <p className="mb-3 text-sm text-slate-300">
            Поставьте {min}–{max} баллов (не больше {maxAffordable}). Верно → ставка удваивается,
            неверно → сгорает.
          </p>
          <div className="mb-2 text-center text-3xl font-bold">{amount}</div>
          <input
            type="range"
            min={min}
            max={ceiling}
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            className="w-full accent-indigo-500"
          />
          <div className="mt-4 grid grid-cols-2 gap-2">
            <button className="btn-ghost" onClick={onDecline}>
              Отказаться
            </button>
            <button className="btn-primary" onClick={() => onPlace(amount)}>
              Поставить {amount}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className="mb-3 text-sm text-slate-300">Недостаточно баллов для ставки ({min}+).</p>
          <button className="btn-primary w-full" onClick={onDecline}>
            Пропустить
          </button>
        </>
      )}
    </div>
  );
}
