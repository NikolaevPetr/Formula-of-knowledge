// REST-клиент. Токен преподавателя хранится в localStorage.

const TOKEN_KEY = "teacher_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  // auth
  register: (email: string, password: string, name: string) =>
    request<{ access_token: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    }),
  login: async (email: string, password: string) => {
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? "Ошибка входа");
    return res.json() as Promise<{ access_token: string }>;
  },
  me: () => request<{ id: number; email: string; name: string }>("/api/auth/me"),

  // banks
  listBanks: () => request<any[]>("/api/banks"),
  createBank: (name: string, subject: string) =>
    request<any>("/api/banks", { method: "POST", body: JSON.stringify({ name, subject }) }),
  deleteBank: (id: number) => request<void>(`/api/banks/${id}`, { method: "DELETE" }),

  // questions
  listQuestions: (bankId: number) => request<any[]>(`/api/banks/${bankId}/questions`),
  createQuestion: (bankId: number, q: any) =>
    request<any>(`/api/banks/${bankId}/questions`, { method: "POST", body: JSON.stringify(q) }),
  deleteQuestion: (bankId: number, id: number) =>
    request<void>(`/api/banks/${bankId}/questions/${id}`, { method: "DELETE" }),
  importQuestions: async (bankId: number, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const headers: Record<string, string> = {};
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`/api/banks/${bankId}/questions/import`, {
      method: "POST",
      headers,
      body: fd,
    });
    if (!res.ok) throw new Error((await res.json()).detail ?? "Ошибка импорта");
    return res.json();
  },

  // rooms
  listRooms: () => request<any[]>("/api/rooms"),
  createRoom: (data: any) =>
    request<any>("/api/rooms", { method: "POST", body: JSON.stringify(data) }),
  getRoom: (id: number) => request<any>(`/api/rooms/${id}`),
  roomByCode: (code: string) => request<any>(`/api/rooms/code/${code}`),

  // reports
  report: (roomId: number) => request<any>(`/api/rooms/${roomId}/report`),
  reportUrl: (roomId: number, fmt: "csv" | "xlsx") =>
    `/api/rooms/${roomId}/report/${fmt}`,
};
