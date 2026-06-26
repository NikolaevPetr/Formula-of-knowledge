// Экран входа студента по коду комнаты (без аккаунта). Mobile-first.
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../../api/client";

export default function Join() {
  const { code: codeParam } = useParams();
  const nav = useNavigate();
  const [code, setCode] = useState(codeParam?.toUpperCase() ?? "");
  const [name, setName] = useState("");
  const [surname, setSurname] = useState("");
  const [group, setGroup] = useState("");
  const [info, setInfo] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!code || code.length < 4) {
      setInfo(null);
      return;
    }
    api
      .roomByCode(code)
      .then(setInfo)
      .catch(() => setInfo(null));
  }, [code]);

  const join = () => {
    setError("");
    if (!name.trim() || !surname.trim() || !group.trim()) {
      setError("Заполните имя, фамилию и группу");
      return;
    }
    // Сохраняем данные для StudentRoom (он установит WS-соединение и отправит join).
    sessionStorage.setItem(
      `pending_join_${code}`,
      JSON.stringify({ name: name.trim(), surname: surname.trim(), group: group.trim() }),
    );
    nav(`/play/${code}`);
  };

  return (
    <div className="min-h-full flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-4">
        <h1 className="text-center text-2xl font-bold">Вход в игру</h1>
        <div className="card space-y-3">
          <div>
            <label className="label">Код комнаты</label>
            <input
              className="input uppercase tracking-widest text-center text-xl"
              value={code}
              maxLength={6}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="ABC123"
            />
          </div>
          {info && (
            <p className="text-sm text-slate-300">
              Предмет: <b>{info.subject}</b> · игроков: {info.player_count}/{info.max_players}
              {info.status !== "lobby" && (
                <span className="text-amber-400"> · игра уже {info.status === "finished" ? "завершена" : "идёт"}</span>
              )}
            </p>
          )}
          <div>
            <label className="label">Имя</label>
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="label">Фамилия</label>
            <input className="input" value={surname} onChange={(e) => setSurname(e.target.value)} />
          </div>
          <div>
            <label className="label">Группа</label>
            <input className="input" value={group} onChange={(e) => setGroup(e.target.value)} placeholder="БИВ-21" />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button className="btn-primary w-full" disabled={!info || info.status === "finished"} onClick={join}>
            Войти
          </button>
        </div>
      </div>
    </div>
  );
}
