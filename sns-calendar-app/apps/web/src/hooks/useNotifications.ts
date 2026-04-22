"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { NotificationItem } from "../generated/types.gen";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../lib/api-client";
import { useAuthStore } from "../stores/auth";

type UseNotificationsReturn = {
  items: Array<NotificationItem>;
  unreadCount: number;
  isLoading: boolean;
  errorMessage: string | null;
  isConnected: boolean;
  refresh: () => Promise<void>;
  markRead: (id: string) => Promise<void>;
  markAllRead: () => Promise<void>;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const MIN_RECONNECT_MS = 1000;
const MAX_RECONNECT_MS = 30000;

function buildWsUrl(token: string): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/ws/notifications?token=${encodeURIComponent(token)}`;
}

export function useNotifications(enabled: boolean = true): UseNotificationsReturn {
  const accessToken = useAuthStore((state) => state.session?.accessToken ?? null);
  const [items, setItems] = useState<Array<NotificationItem>>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled || !accessToken) {
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetchNotifications({ limit: 50 });
      setItems(response.items);
      setUnreadCount(response.unread_count);
    } catch {
      setErrorMessage("通知の取得に失敗しました。");
    } finally {
      setIsLoading(false);
    }
  }, [enabled, accessToken]);

  const markRead = useCallback(async (id: string) => {
    try {
      await markNotificationRead(id);
      setItems((current) =>
        current.map((item) =>
          item.id === id && item.read_at === null
            ? { ...item, read_at: new Date().toISOString() }
            : item,
        ),
      );
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch {
      setErrorMessage("既読処理に失敗しました。");
    }
  }, []);

  const markAllRead = useCallback(async () => {
    try {
      await markAllNotificationsRead();
      const now = new Date().toISOString();
      setItems((current) =>
        current.map((item) => (item.read_at ? item : { ...item, read_at: now })),
      );
      setUnreadCount(0);
    } catch {
      setErrorMessage("全件既読処理に失敗しました。");
    }
  }, []);

  useEffect(() => {
    if (!enabled || !accessToken) {
      return;
    }
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      let socket: WebSocket;
      try {
        socket = new WebSocket(buildWsUrl(accessToken));
      } catch {
        scheduleReconnect();
        return;
      }
      socketRef.current = socket;

      socket.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data?.type === "notification") {
            refresh();
          }
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        setIsConnected(false);
        socketRef.current = null;
        if (!cancelled) {
          scheduleReconnect();
        }
      };

      socket.onerror = () => {
        // handled via onclose
      };
    };

    const scheduleReconnect = () => {
      if (cancelled) return;
      const attempt = reconnectAttemptsRef.current;
      const delay = Math.min(MIN_RECONNECT_MS * 2 ** attempt, MAX_RECONNECT_MS);
      reconnectAttemptsRef.current = attempt + 1;
      reconnectTimerRef.current = window.setTimeout(connect, delay);
    };

    refresh();
    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }
      socketRef.current?.close();
    };
  }, [enabled, accessToken, refresh]);

  return {
    items,
    unreadCount,
    isLoading,
    errorMessage,
    isConnected,
    refresh,
    markRead,
    markAllRead,
  };
}
