/**
 * useWebSocket — React hook for real-time messaging.
 *
 * This hook is a thin wrapper around the singleton `wsClient` that:
 * 1. Exposes the current connection status (isConnected).
 * 2. Provides a `sendMessage` convenience function.
 * 3. Provides an `onMessage` subscription for `message:new` events.
 *
 * Connection lifecycle (auto-connect / auto-disconnect) is managed
 * centrally in AuthContext, so this hook only needs to surface
 * the client's state to consuming components.
 *
 * @module hooks/useWebSocket
 */

import { useEffect, useState, useCallback } from 'react';
import { wsClient } from '../services/websocket.ts';
import { MessageOut, MessageType } from '../types.ts';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UseWebSocketResult {
  /** Whether the WebSocket is currently in the OPEN state. */
  isConnected: boolean;

  /**
   * Send a chat message over the WebSocket.
   * @returns true if the message was queued to the socket, false if
   *          the connection is not open.
   */
  sendMessage: (content: string, conversationId: string, type?: MessageType) => boolean;

  /**
   * Subscribe to incoming message:new events.
   * @param callback - Called with the MessageOut payload when a new
   *                   message arrives from another user.
   * @returns An unsubscribe function.
   */
  onMessage: (callback: (message: MessageOut) => void) => () => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Consume the global WebSocket client in a React component.
 *
 * Usage in MessageCenter.tsx:
 *   const { isConnected, sendMessage, onMessage } = useWebSocket();
 *   useEffect(() => { return onMessage((msg) => appendToMessageList(msg)); }, [onMessage]);
 */
export function useWebSocket(): UseWebSocketResult {
  const [isConnected, setIsConnected] = useState<boolean>(wsClient.connected);

  // Track connection state changes via the onConnectionChange listener.
  // The listener is immediately invoked with the current state, so
  // the initial useState value is just a fallback until the effect runs.
  useEffect(() => {
    const unsub = wsClient.onConnectionChange((connected: boolean) => {
      setIsConnected(connected);
    });
    return unsub;
  }, []);

  /** Send a chat message via the WebSocket client. */
  const sendMessage = useCallback(
    (content: string, conversationId: string, type: MessageType = MessageType.Text): boolean => {
      if (!wsClient.connected) return false;
      wsClient.send('message:send', { conversation_id: conversationId, type, content });
      return true;
    },
    []
  );

  /** Subscribe to incoming messages. Returns an unsubscribe function. */
  const onMessage = useCallback(
    (callback: (message: MessageOut) => void): (() => void) => {
      return wsClient.on('message:new', (data: any) => {
        callback(data as MessageOut);
      });
    },
    []
  );

  return { isConnected, sendMessage, onMessage };
}

export default useWebSocket;
