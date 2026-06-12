/**
 * useStream — event-driven SSE/WebSocket composable.
 *
 * Encapsulates the lifecycle of a streaming connection (SSE for single-agent,
 * WebSocket for roundtable) and emits typed events via a simple callback map.
 *
 * Features:
 * - SSE: exponential backoff reconnection on errors
 * - WebSocket: heartbeat ping/pong to detect stale connections
 *
 * Usage:
 *   const stream = useStream()
 *   stream.on('token', (ev) => { ... })
 *   stream.on('done',  (ev) => { ... })
 *   await stream.openSSE(url)
 *   // ...
 *   stream.close()
 */
import { ref } from "vue";
import type { StreamEvent } from "@/types";

export type StreamEventType = StreamEvent["type"];

/** Callback for a specific stream event type. */
export type StreamEventHandler<T extends StreamEvent = StreamEvent> = (ev: T) => void;

/** WebSocket ping interval (ms). Server should respond with pong within this time. */
const WS_PING_INTERVAL = 30_000;
/** Max consecutive SSE errors before giving up. */
const SSE_MAX_ERRORS = 8;
/** Initial SSE reconnect delay (ms). Doubles on each failure, capped at 30s. */
const SSE_INITIAL_BACKOFF = 1_000;
/** Max SSE reconnect delay (ms). */
const SSE_MAX_BACKOFF = 30_000;

/**
 * Composable: creates a managed stream connection.
 * Returns reactive state + lifecycle methods.
 */
export function useStream() {
  const connected = ref(false);
  const error = ref<string | null>(null);

  let es: EventSource | null = null;
  let ws: WebSocket | null = null;
  let wsPingTimer: ReturnType<typeof setInterval> | null = null;
  let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let wsUrl: string | null = null;
  const handlers = new Map<string, StreamEventHandler[]>();

  /** Register a typed event handler. */
  function on<T extends StreamEventType>(
    type: T,
    handler: StreamEventHandler<Extract<StreamEvent, { type: T }>>,
  ): () => void {
    const list = handlers.get(type) ?? [];
    list.push(handler as StreamEventHandler);
    handlers.set(type, list);
    // Return unsubscribe function
    return () => {
      const arr = handlers.get(type);
      if (arr) {
        const idx = arr.indexOf(handler as StreamEventHandler);
        if (idx !== -1) arr.splice(idx, 1);
      }
    };
  }

  /** Register a wildcard handler that receives ALL events. */
  function onAny(handler: StreamEventHandler): () => void {
    return on("*" as StreamEventType, handler);
  }

  /** Dispatch an event to all registered handlers. */
  function emit(ev: StreamEvent) {
    // Type-specific handlers
    const typed = handlers.get(ev.type);
    if (typed) typed.forEach((fn) => fn(ev));
    // Wildcard handlers
    const wildcard = handlers.get("*");
    if (wildcard) wildcard.forEach((fn) => fn(ev));
  }

  /** Close any open connection. */
  function close() {
    if (es) { es.close(); es = null; }
    if (ws) { ws.close(); ws = null; }
    if (wsPingTimer) { clearInterval(wsPingTimer); wsPingTimer = null; }
    if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }
    wsUrl = null;
    connected.value = false;
  }

  /** Open an SSE connection with exponential backoff reconnection. */
  function openSSE(url: string, timeoutMs = 3000): Promise<void> {
    close();
    error.value = null;
    let consecutiveErrors = 0;
    let backoff = SSE_INITIAL_BACKOFF;

    function connect() {
      es = new EventSource(url);

      es.onmessage = (e) => {
        consecutiveErrors = 0;
        backoff = SSE_INITIAL_BACKOFF;
        try {
          emit(JSON.parse(e.data) as StreamEvent);
        } catch { /* heartbeat / non-JSON */ }
      };

      es.onerror = () => {
        consecutiveErrors += 1;
        if (consecutiveErrors >= SSE_MAX_ERRORS) {
          error.value = "SSE 连接断开";
          close();
          return;
        }
        // Exponential backoff reconnection
        if (es) { es.close(); es = null; }
        connected.value = false;
        wsReconnectTimer = setTimeout(() => {
          backoff = Math.min(backoff * 2, SSE_MAX_BACKOFF);
          connect();
        }, backoff);
      };

      es.onopen = () => {
        connected.value = true;
        consecutiveErrors = 0;
        backoff = SSE_INITIAL_BACKOFF;
      };
    }

    connect();

    return new Promise<void>((resolve) => {
      // Resolve once connected or after timeout
      const check = () => {
        if (connected.value) { resolve(); return; }
        setTimeout(check, 100);
      };
      setTimeout(check, 100);
      setTimeout(resolve, timeoutMs);
    });
  }

  /** Start WebSocket heartbeat ping/pong. */
  function startWsHeartbeat() {
    if (wsPingTimer) clearInterval(wsPingTimer);
    wsPingTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, WS_PING_INTERVAL);
  }

  /** Open a WebSocket connection with heartbeat and auto-reconnect. */
  function openWS(url: string, timeoutMs = 800): Promise<void> {
    close();
    error.value = null;
    wsUrl = url;
    let reconnectAttempts = 0;

    function connect() {
      ws = new WebSocket(url);

      ws.onmessage = (e) => {
        reconnectAttempts = 0;
        try {
          const data = JSON.parse(e.data) as StreamEvent;
          // Ignore pong responses
          if ((data as Record<string, unknown>).type !== "pong") {
            emit(data);
          }
        } catch { /* non-JSON */ }
      };

      ws.onclose = (event) => {
        ws = null;
        connected.value = false;
        if (wsPingTimer) { clearInterval(wsPingTimer); wsPingTimer = null; }
        // Auto-reconnect on abnormal closure (not manual close)
        if (event.code !== 1000 && wsUrl) {
          reconnectAttempts++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts - 1), 30_000);
          wsReconnectTimer = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        // onclose will handle reconnection
      };

      ws.onopen = () => {
        connected.value = true;
        reconnectAttempts = 0;
        startWsHeartbeat();
      };
    }

    connect();

    return new Promise<void>((resolve) => {
      const check = () => {
        if (connected.value) { resolve(); return; }
        setTimeout(check, 100);
      };
      setTimeout(check, 100);
      setTimeout(resolve, timeoutMs);
    });
  }

  /** Send data over WebSocket. Only works after openWS(). */
  function send(data: unknown): boolean {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  }

  /** Clear all registered handlers. */
  function offAll() {
    handlers.clear();
  }

  return {
    // State
    connected,
    error,
    // Lifecycle
    openSSE,
    openWS,
    close,
    send,
    // Events
    on,
    onAny,
    offAll,
    emit,
  };
}
