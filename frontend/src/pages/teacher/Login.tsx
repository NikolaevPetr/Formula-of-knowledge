// Вход / регистрация преподавателя (JWT).
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setToken } from "../../api/client";

export default function Login() {
  const nav = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setError("");
    setBusy(true);
    try {
      const res =
        mode === "login"
          ? await api.login(email, password)
          : await api.register(email, password, name);
      setToken(res.access_token);
      nav("/teacher");
    } catch (e: any) {
      setError(e.message || "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-full flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-4">
        <h1 className="text-center text-2xl font-bold">Кабинет преподавателя</h1>
        <div className="card space-y-3">
          <div className="flex rounded-xl bg-slate-900 p-1">
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                className={`flex-1 rounded-lg py-2 text-sm font-semibold ${
                  mode === m ? "bg-brand text-white" : "text-slate-400"
                }`}
                onClick={() => setMode(m)}
              >
                {m === "login" ? "Вход" : "Регистрация"}
              </button>
            ))}
          </div>
          {mode === "register" && (
            <div>
              <label className="label">Имя</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
          )}
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label">Пароль</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button className="btn-primary w-full" disabled={busy} onClick={submit}>
            {mode === "login" ? "Войти" : "Зарегистрироваться"}
          </button>
        </div>
      </div>
    </div>
  );
}
