// Создание игровой комнаты с параметрами (PLAN §2.8).
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../../api/client";

export default function RoomCreate() {
  const nav = useNavigate();
  const [banks, setBanks] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    subject: "",
    bank_id: 0,
    end_condition_type: "rounds" as "rounds" | "time" | "score",
    end_condition_value: 3,
    turn_timer_sec: 15,
    answer_timer_sec: 30,
    max_players: 8,
  });

  useEffect(() => {
    api.listBanks().then((b) => {
      setBanks(b);
      if (b[0]) setForm((f) => ({ ...f, bank_id: b[0].id, subject: b[0].subject }));
    });
  }, []);

  const submit = async () => {
    setError("");
    try {
      const room = await api.createRoom(form);
      nav(`/teacher/rooms/${room.id}/manage/${room.code}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const condLabel: Record<string, string> = {
    rounds: "кругов",
    time: "секунд",
    score: "баллов",
  };

  return (
    <div className="min-h-full p-4">
      <div className="mx-auto max-w-lg space-y-4">
        <h1 className="text-2xl font-bold">Новая комната</h1>
        <div className="card space-y-3">
          <div>
            <label className="label">Банк вопросов</label>
            <select
              className="input"
              value={form.bank_id}
              onChange={(e) => {
                const b = banks.find((x) => x.id === Number(e.target.value));
                setForm({ ...form, bank_id: Number(e.target.value), subject: b?.subject ?? form.subject });
              }}
            >
              {banks.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.approved_count} вопр.)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Предмет</label>
            <input className="input" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />
          </div>
          <div>
            <label className="label">Условие окончания</label>
            <div className="flex gap-2">
              <select
                className="input"
                value={form.end_condition_type}
                onChange={(e) => setForm({ ...form, end_condition_type: e.target.value as any })}
              >
                <option value="rounds">N кругов</option>
                <option value="time">Время</option>
                <option value="score">Первый до N баллов</option>
              </select>
              <input
                className="input w-32"
                type="number"
                min={1}
                value={form.end_condition_value}
                onChange={(e) => setForm({ ...form, end_condition_value: Number(e.target.value) })}
              />
              <span className="flex items-center text-sm text-slate-400">{condLabel[form.end_condition_type]}</span>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="label">Таймер хода</label>
              <input
                className="input"
                type="number"
                value={form.turn_timer_sec}
                onChange={(e) => setForm({ ...form, turn_timer_sec: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="label">Таймер ответа</label>
              <input
                className="input"
                type="number"
                value={form.answer_timer_sec}
                onChange={(e) => setForm({ ...form, answer_timer_sec: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="label">Макс. игроков</label>
              <input
                className="input"
                type="number"
                min={2}
                max={8}
                value={form.max_players}
                onChange={(e) => setForm({ ...form, max_players: Number(e.target.value) })}
              />
            </div>
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button className="btn-primary w-full" disabled={!form.bank_id} onClick={submit}>
            Создать комнату
          </button>
        </div>
      </div>
    </div>
  );
}
