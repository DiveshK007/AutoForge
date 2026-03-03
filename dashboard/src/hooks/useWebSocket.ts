'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export type WSEventType =
  | 'workflow_update'
  | 'agent_action'
  | 'activity'
  | 'metrics_snapshot'
  | 'pong'
  | 'connected';

export interface WSMessage {
  event: WSEventType;
  data: Record<string, unknown>;
  timestamp?: string;
}

interface UseWebSocketOptions {
  /** Auto-reconnect on disconnect (default: true) */
  reconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** Max reconnect attempts (default: 10) */
  maxReconnectAttempts?: number;
  /** Event types to listen to (default: all) */
  events?: WSEventType[];
  /** Called on each message */
  onMessage?: (msg: WSMessage) => void;
  /** Called on connection open */
  onOpen?: () => void;
  /** Called on connection close */
  onClose?: () => void;
}

export function useAutoForgeWebSocket(options: UseWebSocketOptions = {}) {
  const {
    reconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
    events,
    onMessage,
    onOpen,
    onClose,
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${WS_BASE}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        reconnectAttempts.current = 0;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data);

          // Backend sends "type" field, normalise to "event" for the hook interface
          const msg: WSMessage = {
            event: raw.event || raw.type,
            data: raw,
            timestamp: raw.timestamp,
          };

          // Filter by event type if specified
          if (events && !events.includes(msg.event)) return;

          // Skip heartbeat / pong noise from triggering re-renders
          if (msg.event === 'pong' || (raw.type === 'heartbeat')) return;

          setLastMessage(msg);
          onMessage?.(msg);
        } catch {
          // Ignore non-JSON messages (e.g. raw pong)
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        onClose?.();

        // Auto-reconnect
        if (reconnect && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current += 1;
          const delay = reconnectDelay * Math.min(reconnectAttempts.current, 5);
          reconnectTimer.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // WebSocket constructor can throw in SSR
    }
  }, [events, maxReconnectAttempts, onClose, onMessage, onOpen, reconnect, reconnectDelay]);

  // Send message
  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
    }
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connected,
    lastMessage,
    send,
    disconnect,
    reconnect: connect,
  };
}
