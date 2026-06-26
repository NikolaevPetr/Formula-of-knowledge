// Итоговый отчёт по игре + экспорт CSV/Excel (PLAN §10).
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../../api/client";

export default function Report() {
  const { roomId } = useParams();
  const id = Number(roomId);
  const [report, setReport] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.report(id).then(setReport).catch((e) => setError(e.message));
  }, [id]);

  const download = async (fmt: "csv" | "xlsx") => {
    const token = localStorage.getItem("teacher_token");
    const res = await fetch(api.reportUrl(id, fmt), {
      headers: { Authorization: `Bearer ${token}` },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `report.${fmt}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) return <div className="p-4 text-red-400">{error}</div>;
  if (!report) return <div className="p-4 text-slate-400">Загрузка…</div>;

  return (
    <div className="min-h-full p-4">
      <div className="mx-auto max-w-4xl space-y-5">
        <Link to="/teacher" className="text-sm text-brand">
          ← Дашборд
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="text-2xl font-bold">Отчёт · {report.room.subject}</h1>
          <div className="flex gap-2">
            <button className="btn-ghost" onClick={() => download("csv")}>
              Скачать CSV
            </button>
            <button className="btn-primary" onClick={() => download("xlsx")}>
              Скачать Excel
            </button>
          </div>
        </div>

        <section className="card">
          <h2 className="mb-2 font-semibold">Рейтинг</h2>
          <table className="w-full text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="text-left">Место</th>
                <th className="text-left">Игрок</th>
                <th className="text-left">Группа</th>
                <th className="text-right">Баллы</th>
              </tr>
            </thead>
            <tbody>
              {report.ranking.map((r: any) => (
                <tr key={r.player_id} className="border-t border-slate-700">
                  <td className="py-1">{r.place}</td>
                  <td>{r.name}</td>
                  <td className="text-slate-400">{r.group_name}</td>
                  <td className="text-right font-bold tabular-nums">{r.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <h2 className="mb-2 font-semibold">По игрокам</h2>
          <table className="w-full text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="text-left">Игрок</th>
                <th className="text-right">Верно</th>
                <th className="text-right">Неверно</th>
                <th className="text-right">% успеха</th>
              </tr>
            </thead>
            <tbody>
              {report.players.map((p: any) => (
                <tr key={p.player_id} className="border-t border-slate-700">
                  <td className="py-1">{p.name}</td>
                  <td className="text-right text-green-400">{p.correct}</td>
                  <td className="text-right text-red-400">{p.wrong}</td>
                  <td className="text-right">{p.success_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <h2 className="mb-2 font-semibold">По вопросам</h2>
          <table className="w-full text-sm">
            <thead className="text-slate-400">
              <tr>
                <th className="text-left">Вопрос</th>
                <th className="text-right">Верно</th>
                <th className="text-right">Всего</th>
                <th className="text-right">% успеха</th>
              </tr>
            </thead>
            <tbody>
              {report.questions.map((q: any) => (
                <tr key={q.question_id} className="border-t border-slate-700">
                  <td className="py-1">{q.text}</td>
                  <td className="text-right">{q.correct}</td>
                  <td className="text-right">{q.total}</td>
                  <td className="text-right">{q.success_rate}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>
    </div>
  );
}
