// Карточка вопроса. Для зачёта — варианты, для экзамена — поле открытого ответа.
import { useState } from "react";
import type { ActiveQuestion } from "../types";
import Timer from "./Timer";

interface Props {
  question: ActiveQuestion;
  canAnswer: boolean;
  answerTimerSec: number;
  onAnswer: (answer: string) => void;
}

export default function QuestionCard({ question, canAnswer, answerTimerSec, onAnswer }: Props) {
  const [text, setText] = useState("");
  const [sent, setSent] = useState(false);
  const isExam = question.cell_type === "exam";

  const submit = (a: string) => {
    if (sent) return;
    setSent(true);
    onAnswer(a);
  };

  const handleExpire = () => {
    if (!sent && canAnswer) submit("");
  };

  return (
    <div className="card">
      <div className="mb-3">
        <Timer
          seconds={question.deadline || answerTimerSec} startedAt={question.shownAt} onExpire={handleExpire}  // ← добавить
        />
      </div>
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-brand">
        {isExam ? "Экзамен (открытый ответ)" : question.is_location ? "Локация" : "Зачёт"}
      </div>
      <p className="mb-4 text-lg font-medium">{question.text}</p>

      {!canAnswer ? (
        <p className="text-slate-400 text-sm">Отвечает другой игрок…</p>
      ) : isExam ? (
        <div className="space-y-3">
          <textarea
            className="input min-h-[96px]"
            placeholder="Ваш ответ…"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={sent}
          />
          <button className="btn-primary w-full" disabled={sent || !text.trim()} onClick={() => submit(text.trim())}>
            {sent ? "Отправлено на проверку" : "Отправить ответ"}
          </button>
        </div>
      ) : (
        <div className="grid gap-2">
          {(question.options ?? []).map((opt, i) => (
            <button key={i} className="btn-ghost text-left justify-start" disabled={sent} onClick={() => submit(String(i))}>
              <span className="mr-2 font-bold text-brand">{String.fromCharCode(1040 + i)}.</span>
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
