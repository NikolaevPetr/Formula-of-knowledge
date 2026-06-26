// Типы, общие с WebSocket-протоколом бэкенда (PLAN §7).

export type RoomStatus = "lobby" | "playing" | "paused" | "finished";
export type TurnPhase =
  | "idle"
  | "awaiting_roll"
  | "awaiting_answer"
  | "awaiting_bet"
  | "awaiting_wheel";

export interface PlayerPublic {
  id: number;
  name: string;
  surname: string;
  group_name: string;
  score: number;
  position: number;
  turn_order: number;
  connected: boolean;
  eliminated: boolean;
  rounds_completed: number;
}

export interface BoardCell {
  index: number;
  type: "CORNER" | "ZACHET" | "EXAM" | "LOCATION";
  corner?: string;
  effect?: string;
  label: string;
  amount?: number;
}

export interface BoardConfig {
  size: number;
  cells: BoardCell[];
  scoring: Record<string, number>;
  wheel_sectors: { id: number; label: string; kind: string; delta?: number }[];
}

export interface PendingPublic {
  phase: TurnPhase;
  player_id: number;
  cell_index: number;
  time_left: number | null;
  question_type: string | null;
  location_effect: string | null;
}

export interface RoomState {
  code: string;
  subject: string;
  status: RoomStatus;
  phase: TurnPhase;
  board: BoardConfig;
  players: PlayerPublic[];
  order: number[];
  current_player_id: number | null;
  pending: PendingPublic | null;
  end_condition: { type: string; value: number };
  turn_timer_sec: number;
  answer_timer_sec: number;
}

export interface ActiveQuestion {
  question_id: number;
  text: string;
  options: string[] | null;
  cell_type: string;
  is_location: boolean;
  deadline: number;
  shownAt: number;
}

export interface RankingEntry {
  place: number;
  player_id: number;
  name: string;
  group_name: string;
  score: number;
}

export interface WsMessage {
  type: string;
  payload: any;
}
