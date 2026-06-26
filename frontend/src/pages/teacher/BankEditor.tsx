// Редактор банка: список вопросов, добавление вручную, импорт CSV/JSON.
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";

const EMPTY = {
  type: "zachet" as "zachet" | "exam",
  text: "",
  options: ["", "", "", ""],
  correct_option_index: 0,
  reference_answer: "",
  difficulty: "" as string,
};

export default function BankEditor() {
  const { bankId } = useParams();
  const id = Number(bankId);
  const [questions, setQuestions] = useState<any[]>([]);
  const [form, setForm] = useState({ ...EMPTY });
  const [error, setError] = useState("");
  const [importMsg, setImportMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const reload = () => api.listQuestions(id).then(setQuestions).catch(() => {});
  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const addQuestion = async () => {
    setError("");
    try {
      const payload: any = {
        type: form.type,
        text: form.text.trim(),
        difficulty: form.difficulty || null,
      };
      if (form.type === "zachet") {
        payload.options = form.options.map((o) => o.trim()).filter(Boolean);
        payload.correct_option_index = form.correct_option_index;
      } else {
        payload.reference_answer = form.reference_answer.trim() || null;
      }
      await api.createQuestion(id, payload);
      setForm({ ...EMPTY, options: ["", "", "", ""] });
      reload();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const onImport = async (file: File) => {
    setImportMsg("");
    try {
      const res = await api.importQuestions(id, file);
      setImportMsg(`Импортировано: ${res.created}. Ошибок: ${res.errors.length}`);
      reload();
    } catch (e: any) {
      setImportMsg(e.message);
    }
  };

  const setOption = (i: number, v: string) => {
    const opts = [...form.options];
    opts[i] = v;
    setForm({ ...form, options: opts });
  };

  return (
    <div className="min-h-full p-4">
      <div className="mx-auto max-w-3xl space-y-5">
        <Link to="/teacher" className="text-sm text-brand">
          ← Назад
        </Link>
        <h1 className="text-2xl font-bold">Банк вопросов</h1>

        {/* Импорт */}
        <div className="card flex flex-wrap items-center gap-3">
          <div className="text-sm text-slate-300">
            Импорт CSV/JSON (колонки: type, text, option1..6, correct_index, reference_answer, explanation, difficulty)
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.json"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onImport(e.target.files[0])}
          />
          <button className="btn-ghost" onClick={() => fileRef.current?.click()}>
            Загрузить файл
          </button>
          {importMsg && <span className="text-sm text-slate-400">{importMsg}</span>}
        </div>

        {/* Форма добавления */}
        <div className="card space-y-3">
          <div className="flex gap-2">
            {(["zachet", "exam"] as const).map((t) => (
              <button
                key={t}
                className={`flex-1 rounded-lg py-2 text-sm font-semibold ${
                  form.type === t ? "bg-brand text-white" : "bg-slate-700 text-slate-300"
                }`}
                onClick={() => setForm({ ...form, type: t })}
              >
                {t === "zachet" ? "Зачёт (тест)" : "Экзамен (открытый)"}
              </button>
            ))}
          </div>
          <textarea
            className="input min-h-[64px]"
            placeholder="Текст вопроса"
            value={form.text}
            onChange={(e) => setForm({ ...form, text: e.target.value })}
          />
          {form.type === "zachet" ? (
            <div className="space-y-2">
              {form.options.map((opt, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="radio"
                    name="correct"
                    checked={form.correct_option_index === i}
                    onChange={() => setForm({ ...form, correct_option_index: i })}
                    className="accent-indigo-500"
                  />
                  <input
                    className="input"
                    placeholder={`Вариант ${i + 1}`}
                    value={opt}
                    onChange={(e) => setOption(i, e.target.value)}
                  />
                </div>
              ))}
              <div className="flex gap-2 text-sm">
                <button
                  className="text-brand"
                  disabled={form.options.length >= 6}
                  onClick={() => setForm({ ...form, options: [...form.options, ""] })}
                >
                  + вариант
                </button>
                <button
                  className="text-slate-400"
                  disabled={form.options.length <= 4}
                  onClick={() => setForm({ ...form, options: form.options.slice(0, -1) })}
                >
                  − вариант
                </button>
              </div>
            </div>
          ) : (
            <textarea
              className="input"
              placeholder="Эталонный ответ (для проверки преподавателем)"
              value={form.reference_answer}
              onChange={(e) => setForm({ ...form, reference_answer: e.target.value })}
            />
          )}
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button className="btn-primary w-full" onClick={addQuestion}>
            Добавить вопрос
          </button>
        </div>

        {/* Список вопросов */}
        <div className="space-y-2">
          <h2 className="text-lg font-semibold">Вопросы ({questions.length})</h2>
          {questions.map((q) => (
            <div key={q.id} className="card flex items-start justify-between gap-3">
              <div>
                <span
                  className={`mr-2 rounded px-2 py-0.5 text-xs ${
                    q.type === "exam" ? "bg-red-700" : "bg-green-700"
                  }`}
                >
                  {q.type === "exam" ? "экзамен" : "зачёт"}
                </span>
                <span>{q.text}</span>
                {q.options && (
                  <ul className="mt-1 text-xs text-slate-400">
                    {q.options.map((o: string, i: number) => (
                      <li key={i} className={i === q.correct_option_index ? "text-green-400" : ""}>
                        {String.fromCharCode(1040 + i)}. {o}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <button
                className="text-sm text-red-400"
                onClick={() => api.deleteQuestion(id, q.id).then(reload)}
              >
                Удалить
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
