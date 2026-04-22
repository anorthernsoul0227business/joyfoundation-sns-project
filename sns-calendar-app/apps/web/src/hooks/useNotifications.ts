"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { RealtimeChannel } from "@supabase/supabase-js";
import type { NotificationItem } from "../generated/types.gen";
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../lib/api-client";
import { getSupabaseClient, isSupabaseConfigured } from "../lib/supabase";
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

export function useNotifications(enabled: boolean = true): UseNotificationsReturn {
  const accessToken = useAuthStore((state) => state.session?.accessToken ?? null);
  const [items, setItems] = useState<Array<NotificationItem>>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const channelRef = useRef<RealtimeChannel | null>(null);

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

    refresh();

    const client = getSupabaseClient();
    if (!client || !isSupabaseConfigured()) {
      setIsConnected(false);
      return;
    }

    // Realtime は RLS の SELECT policy を通る。user JWT を渡せば
    // auth.uid() = user_id の通知のみ購読される。
    client.realtime.setAuth(accessToken);

    const channel = client
      .channel("notifications-realtime")
      .on(
        "postgres_changes",
        {
          event: "INSERT",
          schema: "public",
          table: "notifications",
        },
        () => {
          if (!cancelled) {
            refresh();
          }
        },
      )
      .subscribe((status) => {
        if (cancelled) return;
        setIsConnected(status === "SUBSCRIBED");
      });

    channelRef.current = channel;

    return () => {
      cancelled = true;
      const current = channelRef.current;
      channelRef.current = null;
      if (current) {
        client.removeChannel(current);
      }
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
