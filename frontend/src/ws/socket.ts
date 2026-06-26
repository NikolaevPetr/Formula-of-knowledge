// Нативный WebSocket-клиент с авто-реконнектом (PLAN §3, §12).

import type { WsMessage } from "../types";

type Handler = (msg: WsMessage) => void;

export class GameSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handler: Handler;
  private onOpen?: () => void;
  private onClose?: () => void;
  private shouldReconnect = true;
  private reconnectDelay = 1000;

  constructor(url: string, handler: Handler, onOpen?: () => void, onClose?: () => void) {
    this.url = url;
    this.handler = handler;
    this.onOpen = onOpen;
    this.onClose = onClose;
  }

  connect() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const full = this.url.startsWith("ws")
      ? this.url
      : `${proto}://${location.host}${this.url}`;
    this.ws = new WebSocket(full);

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      this.onOpen?.();
    };
    this.ws.onmessage = (ev) => {
      try {
        this.handler(JSON.parse(ev.data));
      } catch {
        /* ignore malformed */
      }
    };
    this.ws.onclose = () => {
      // Сообщаем стору о потере связи (чтобы показать статус и не «глотать» клики).
      this.onClose?.();
      if (this.shouldReconnect) {
        setTimeout(() => this.connect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, 8000);
      }
    };
    this.ws.onerror = () => this.ws?.close();
  }

  /** Возвращает true, если сообщение действительно ушло (сокет открыт). */
  send(type: string, payload: Record<string, unknown> = {}): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
      return true;
    }
    return false;
  }

  close() {
    this.shouldReconnect = false;
    this.ws?.close();
  }

  get isOpen() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
