// Дашборд преподавателя: банки вопросов и комнаты.
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, clearToken } from "../../api/client";

export default function Dashboard() {
  const nav = useNavigate();
  const [banks, setBanks] = useState<any[]>([]);
  const [rooms, setRooms] = useState<any[]>([]);
  const [newBank, setNewBank] = useState({ name: "", subject: "" });

  const reload = () => {
    api.listBanks().then(setBanks).catch(() => {});
    api.listRooms().then(setRooms).catch(() => {});
  };
  useEffect(reload, []);

  const createBank = async () => {
    if (!newBank.name.trim() || !newBank.subject.trim()) return;
    await api.createBank(newBank.name.trim(), newBank.subject.trim());
    setNewBank({ name: "", subject: "" });
    reload();
  };

  const logout = () => {
    clearToken();
    nav("/teacher/login");
  };

  return (
    <div className="min-h-full p-4">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Дашборд</h1>
          <button className="btn-ghost" onClick={logout}>
            Выйти
          </button>
        </header>

        {/* Банки */}
        <section className="space-y-3">
          <h2 className="text-lg font-semibold">Банки вопросов</h2>
          <div className="card flex flex-col gap-2 sm:flex-row">
            <input
              className="input"
              placeholder="Название банка"
              value={newBank.name}
              onChange={(e) => setNewBank({ ...newBank, name: e.target.value })}
            />
            <input
              className="input"
              placeholder="Предмет"
              value={newBank.subject}
              onChange={(e) => setNewBank({ ...newBank, subject: e.target.value })}
            />
            <button className="btn-primary sm:w-48" onClick={createBank}>
              Создать
            </button>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {banks.map((b) => (
              <Link key={b.id} to={`/teacher/banks/${b.id}`} className="card hover:ring-brand">
                <div className="font-semibold">{b.name}</div>
                <div className="text-sm text-slate-400">{b.subject}</div>
                <div className="mt-1 text-xs text-slate-500">
                  Вопросов: {b.question_count} · одобрено: {b.approved_count}
                </div>
              </Link>
            ))}
            {banks.length === 0 && <p className="text-sm text-slate-500">Пока нет банков.</p>}
          </div>
        </section>

        {/* Комнаты */}
        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Игровые комнаты</h2>
            <Link to="/teacher/rooms/new" className="btn-primary">
              Создать комнату
            </Link>
          </div>
          <div className="grid gap-2">
            {rooms.map((r) => (
              <div key={r.id} className="card flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-mono text-lg font-bold tracking-widest">{r.code}</div>
                  <div className="text-sm text-slate-400">
                    {r.subject} · {r.status}
                  </div>
                </div>
                <div className="flex gap-2">
                  {r.status !== "finished" ? (
                    <Link to={`/teacher/rooms/${r.id}/manage/${r.code}`} className="btn-primary">
                      Управлять
                    </Link>
                  ) : (
                    <Link to={`/teacher/rooms/${r.id}/report`} className="btn-ghost">
                      Отчёт
                    </Link>
                  )}
                </div>
              </div>
            ))}
            {rooms.length === 0 && <p className="text-sm text-slate-500">Пока нет комнат.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
