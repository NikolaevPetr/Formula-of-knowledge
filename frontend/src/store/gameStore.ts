// Zustand-стор игрового состояния. Используется и студентом, и преподавателем.
import { create } from "zustand";
import { GameSocket } from "../ws/socket";
import type {
  ActiveQuestion,
  RankingEntry,
  RoomState,
  WsMessage,
} from "../types";

export interface LogEntry {
  id: number;
  text: string;
}

interface DiceRoll {
  playerId: number;
  value: number;
  ts: number;
}
interface WheelResult {
  playerId: number;
  sector: { id: number; label: string };
  ts: number;
}
interface ExamItem {
  answer_id: number;
  player_id: number;
  player: string;
  question_text: string;
  reference_answer: string | null;
  given_answer: string;
}

interface GameStore {
  socket: GameSocket | null;
  connected: boolean;
  role: "student" | "teacher" | null;
  code: string | null;
  myPlayerId: number | null;
  sessionToken: string | null;

  room: RoomState | null;
  question: ActiveQuestion | null;
  betRequest: { min: number; max: number; max_affordable: number } | null;
  dice: DiceRoll | null;
  wheel: WheelResult | null;
  ranking: RankingEntry[] | null;
  examQueue: ExamItem[];
  log: LogEntry[];
  error: string | null;

  connectStudent: (code: string, savedToken?: string) => void;
  joinAs: (name: string, surname: string, group: string) => void;
  connectTeacher: (code: string, token: string) => void;
  send: (type: string, payload?: Record<string, unknown>) => void;
  disconnect: () => void;
  clearError: () => void;
}

let logId = 0;
// sessionStorage — НЕ localStorage: токен сессии у каждой вкладки свой, чтобы
// два студента в одном браузере не перезаписывали друг другу сессию.
const SESSION_KEY = (code: string) => `student_session_${code}`;
const saveToken = (code: string, token: string) =>
  sessionStorage.setItem(SESSION_KEY(code), token);
const loadToken = (code: string) => sessionStorage.getItem(SESSION_KEY(code));

export const useGame = create<GameStore>((set, get) => {
  function pushLog(text: string) {
    set((s) => ({ log: [...s.log.slice(-40), { id: ++logId, text }] }));
  }

  function handle(msg: WsMessage) {
    const p = msg.payload || {};
    switch (msg.type) {
      case "joined": {
        set({ myPlayerId: p.player_id, sessionToken: p.session_token });
        // Код комнаты берём из стора (он известен при подключении), а не из
        // room_state, который приходит ПОСЛЕ joined.
        const code = get().code;
        if (p.session_token && code) saveToken(code, p.session_token);
        break;
      }
      case "room_state":
        set({ room: p as RoomState });
        if (p.pending?.phase !== "awaiting_answer") {
          // вопрос снимается при смене фазы
          if (get().question && p.phase !== "awaiting_answer") set({ question: null });
        }
        if (p.phase !== "awaiting_bet") set({ betRequest: null });
        break;
      case "player_joined":
        pushLog(`${p.name} ${p.surname} присоединился`);
        break;
      case "player_left":
        pushLog(`Игрок отключился`);
        break;
      case "player_reconnected":
        pushLog(`Игрок вернулся`);
        break;
      case "player_eliminated":
        pushLog(p.kicked ? `Игрок исключён преподавателем` : `Игрок выбыл (пропуски)`);
        break;
      case "game_started":
        pushLog("Игра началась!");
        set({ ranking: null });
        break;
      case "game_paused":
        pushLog("Пауза");
        break;
      case "game_resumed":
        pushLog("Игра продолжается");
        break;
      case "turn_started":
        set({ dice: null, wheel: null, question: null, betRequest: null });
        break;
      case "dice_rolled":
        set({ dice: { playerId: p.player_id, value: p.value, ts: Date.now() } });
        break;
      case "pawn_moved":
        if (p.passed_start) pushLog("Прохождение Старта: +баллы");
        break;
      case "question_presented":
        set({
          question: {
            question_id: p.question_id,
            text: p.text,
            options: p.options,
            cell_type: p.cell_type,
            is_location: p.is_location,
            deadline: p.deadline,
            shownAt: Date.now(),
          },
        });
        break;
      case "answer_result":
        pushLog(
          `${p.correct ? "Верно" : "Неверно"}: ${p.points_delta >= 0 ? "+" : ""}${p.points_delta}`,
        );
        set({ question: null });
        break;
      case "exam_pending_review":
        pushLog("Экзамен отправлен на проверку преподавателю");
        set({ question: null });
        break;
      case "wheel_result":
        set({ wheel: { playerId: p.player_id, sector: p.sector, ts: Date.now() } });
        pushLog(`Колесо: ${p.sector.label}`);
        break;
      case "bet_requested":
        set({ betRequest: { min: p.min, max: p.max, max_affordable: p.max_affordable } });
        break;
      case "bet_placed":
        pushLog(`Ставка ${p.amount}`);
        set({ betRequest: null });
        break;
      case "score_updated": {
        // Локально обновляем счёт игрока, не дожидаясь следующего room_state.
        const room = get().room;
        if (room) {
          set({
            room: {
              ...room,
              players: room.players.map((pl) =>
                pl.id === p.player_id ? { ...pl, score: p.score } : pl,
              ),
            },
          });
        }
        break;
      }
      case "game_finished":
        set({ ranking: p.ranking, question: null, betRequest: null });
        pushLog("Игра завершена");
        break;
      case "exam_review_queue":
        set({ examQueue: p.items || [] });
        break;
      case "error":
        set({ error: p.message || "Ошибка" });
        break;
    }
  }

  return {
    socket: null,
    connected: false,
    role: null,
    code: null,
    myPlayerId: null,
    sessionToken: null,
    room: null,
    question: null,
    betRequest: null,
    dice: null,
    wheel: null,
    ranking: null,
    examQueue: [],
    log: [],
    error: null,

    connectStudent: (code, savedToken) => {
      get().socket?.close();
      const saved = savedToken ?? loadToken(code);
      const sock = new GameSocket(
        `/ws/play/${code}`,
        handle,
        () => {
          set({ connected: true });
          // На каждом открытии сокета (вкл. авто-реконнект) повторно
          // идентифицируемся, если уже есть токен сессии.
          const token = saved ?? loadToken(code);
          if (token) sock.send("rejoin", { session_token: token });
        },
        // При обрыве отмечаем потерю связи — UI покажет статус, авто-реконнект поднимет заново.
        () => set({ connected: false }),
      );
      set({
        socket: sock,
        role: "student",
        code,
        room: null,
        myPlayerId: null,
        sessionToken: saved,
      });
      sock.connect();
    },

    joinAs: (name, surname, group) => {
      get().socket?.send("join_room", { name, surname, group });
    },

    connectTeacher: (code, token) => {
      get().socket?.close();
      const sock = new GameSocket(
        `/ws/teacher/${code}?token=${encodeURIComponent(token)}`,
        handle,
        () => set({ connected: true }),
        () => set({ connected: false }),
      );
      set({ socket: sock, role: "teacher" });
      sock.connect();
    },

    send: (type, payload = {}) => {
      const sock = get().socket;
      // Если сокета нет или он не открыт — действие не уйдёт. Раньше это «глоталось»
      // молча («нажимаю — ничего»). Теперь даём явную обратную связь.
      if (!sock || !sock.send(type, payload)) {
        set({ connected: false, error: "Нет соединения с сервером — переподключение…" });
      }
    },

    disconnect: () => {
      get().socket?.close();
      set({ socket: null, connected: false, room: null });
    },

    clearError: () => set({ error: null }),
  };
});

// При горячей замене модуля (Vite HMR) закрываем старый сокет, чтобы он не
// «висел» осиротевшим и не ломал отправку действий.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    try {
      useGame.getState().socket?.close();
    } catch {
      /* ignore */
    }
  });
}
