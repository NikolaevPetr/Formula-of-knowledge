// Кубик с короткой анимацией «прокрутки» перед фиксацией значения.
import { useEffect, useState } from "react";

const PIPS: Record<number, [number, number][]> = {
  1: [[50, 50]],
  2: [[30, 30], [70, 70]],
  3: [[30, 30], [50, 50], [70, 70]],
  4: [[30, 30], [70, 30], [30, 70], [70, 70]],
  5: [[30, 30], [70, 30], [50, 50], [30, 70], [70, 70]],
  6: [[30, 30], [70, 30], [30, 50], [70, 50], [30, 70], [70, 70]],
};

export default function Dice({ value }: { value: number | null }) {
  const [shown, setShown] = useState(value ?? 1);
  const [rolling, setRolling] = useState(false);

  useEffect(() => {
    if (value == null) return;
    setRolling(true);
    let n = 0;
    const id = setInterval(() => {
      setShown(Math.floor(Math.random() * 6) + 1);
      if (++n > 8) {
        clearInterval(id);
        setShown(value);
        setRolling(false);
      }
    }, 70);
    return () => clearInterval(id);
  }, [value]);

  return (
    <svg viewBox="0 0 100 100" className={`w-16 h-16 ${rolling ? "animate-spin" : ""}`}>
      <rect x="6" y="6" width="88" height="88" rx="16" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
      {PIPS[shown]?.map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="8" fill="#1e293b" />
      ))}
    </svg>
  );
}
