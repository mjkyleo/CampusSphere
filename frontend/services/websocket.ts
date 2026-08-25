/**
 * Singleton WebSocket client for real-time messaging.
 *
 * Features:
 * - Connects to `ws://{host}/ws?token=<jwt>&since=<iso>` (goes through Express proxy)
 * - 30-second heartbeat ping to keep the connection alive
 * - Exponential backoff reconnection (1s → 2s → 4s → ... → max 30s)
 * - `since` parameter sent on reconnect for server-side message compensation
 * - Event-based pub/sub: register listeners via `on(event, handler)`
 * - Connection state listeners for reactive UI updates
 */

/** Handler invoked when a WebSocket event is received. */
type WsEventHandler = (data: any) => void;

/** Listener invoked when the connection state changes. */
type ConnectionListener = (connected: boolean) => void;

const HEARTBEAT_INTERVAL_MS = 30_000; // 30 seconds
const MAX_RECONNECT_DELAY_MS = 30_000; // cap at 30s
const BASE_RECONNECT_DELAY_MS = 1_000; // start at 1s

class WebSocketClient {
  private ws: WebSocket | null = null;
  private token: string | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private shouldReconnect = false;
  /** Timestamp of the last received message — sent as `since` on reconnect. */
  private lastMessageAt: string | null = null;
  /** Map of event name → set of handlers. */
  private listeners: Map<string, Set<WsEventHandler>> = new Map();
  /** Listeners for connection state changes. */
  private connectionListeners: Set<ConnectionListener> = new Set();

  /** Whether the underlying socket is in the OPEN state. */
  get connected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Establish a WebSocket connection using the provided JWT access token.
   *
   * If a connection is already open with the same token, this is a no-op.
   * Any existing connection is cleanly torn down before opening a new one.
   */
  connect(token: string): void {
    if (!token) return;

    // Already connected with the same token — nothing to do
    if (this.ws && this.ws.readyState === WebSocket.OPEN && this.token === token) {
      return;
    }

    // Tear down any existing connection (stops timers, removes handlers)
    this.disconnectInternal();

    this.token = token;
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.openSocket();
  }

  /** Gracefully close the connection and stop all background timers. */
  disconnect(): void {
    this.shouldReconnect = false;
    this.token = null;
    this.disconnectInternal();
  }

  /**
   * Send a message to the server.
   *
   * The payload is `{ event, ...data }` to match the backend protocol.
   * No-op if the socket is not open.
   */
  send(event: string, data: Record<string, unknown> = {}): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ event, ...data }));
    }
  }

  /**
   * Register a handler for a specific event.
   * @returns An unsubscribe function that removes the handler.
   */
  on(event: string, handler: WsEventHandler): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);

    return () => {
      const handlers = this.listeners.get(event);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.listeners.delete(event);
        }
      }
    };
  }

  /**
   * Register a listener for connection state changes.
   * The listener is immediately called with the current state.
   * @returns An unsubscribe function.
   */
  onConnectionChange(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    // Immediately notify of the current state
    listener(this.connected);
    return () => {
      this.connectionListeners.delete(listener);
    };
  }

  // ------------------------------------------------------------------
  // Private implementation
  // ------------------------------------------------------------------

  /** Tear down socket + timers without touching `shouldReconnect`/`token`. */
  private disconnectInternal(): void {
    this.stopHeartbeat();
    this.clearReconnectTimer();
    if (this.ws) {
      // Remove handlers so onclose doesn't trigger reconnect logic
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.onopen = null;
      try {
        this.ws.close();
      } catch {
        // Ignore errors during close
      }
      this.ws = null;
    }
    this.reconnectAttempts = 0;
  }

  /** Open a new WebSocket connection using the current token. */
  private openSocket(): void {
    if (!this.token) return;

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const params = new URLSearchParams();
    params.set('token', this.token);
    // On reconnect, include `since` so the backend can replay missed messages
    if (this.lastMessageAt) {
      params.set('since', this.lastMessageAt);
    }
    const url = `${proto}://${window.location.host}/ws?${params.toString()}`;

    try {
      this.ws = new WebSocket(url);
    } catch {
      // Constructor failed (e.g., invalid URL) — schedule a retry
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
      this.notifyConnection();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data as string);
        const eventName: string | undefined = payload?.event;
        if (!eventName) return;

        // Track latest message timestamp for reconnection compensation
        if (eventName === 'message:new' && payload.data?.created_at) {
          this.lastMessageAt = payload.data.created_at as string;
        }

        // Dispatch to all registered listeners for this event
        const handlers = this.listeners.get(eventName);
        if (handlers) {
          handlers.forEach((handler) => handler(payload.data));
        }
      } catch {
        // Non-JSON message — ignore
      }
    };

    this.ws.onclose = () => {
      this.stopHeartbeat();
      this.ws = null;
      this.notifyConnection();
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // Errors are handled by the onclose handler which triggers reconnect.
      // No action needed here.
    };
  }

  /** Start the 30-second heartbeat interval. */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send('ping', {});
    }, HEARTBEAT_INTERVAL_MS);
  }

  /** Stop the heartbeat interval. */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /** Clear any pending reconnect timer. */
  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  /**
   * Schedule a reconnect with exponential backoff.
   * Delay = base * 2^attempts, capped at max.
   */
  private scheduleReconnect(): void {
    this.clearReconnectTimer();

    const delay = Math.min(
      BASE_RECONNECT_DELAY_MS * Math.pow(2, this.reconnectAttempts),
      MAX_RECONNECT_DELAY_MS
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      if (this.shouldReconnect && this.token) {
        this.openSocket();
      }
    }, delay);
  }

  /** Notify all connection-state listeners of the current state. */
  private notifyConnection(): void {
    const isConnected = this.connected;
    this.connectionListeners.forEach((listener) => listener(isConnected));
  }
}

/** Singleton instance shared across the entire app. */
export const wsClient = new WebSocketClient();
