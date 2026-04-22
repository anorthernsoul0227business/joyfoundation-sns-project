"use client";

import Link from "next/link";
import { useNotifications } from "../hooks/useNotifications";
import { useAuthStore } from "../stores/auth";

const KIND_LABEL: Record<string, string> = {
  post_published: "投稿成功",
  post_failed: "投稿失敗",
  post_partial: "投稿一部失敗",
  system: "システム",
};

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

export function NotificationBell() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const { items, unreadCount, isConnected, markRead } = useNotifications(isAuthenticated);

  if (!isAuthenticated) {
    return null;
  }

  const recent = items.slice(0, 5);

  return (
    <div className="group relative">
      <button
        aria-label="通知を開く"
        className="relative flex h-10 w-10 items-center justify-center rounded-full border border-brand-ink/10 bg-white text-brand-ink transition hover:border-brand-ocean hover:text-brand-ocean"
        type="button"
      >
        <span aria-hidden="true">🔔</span>
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>

      <div className="invisible absolute right-0 top-12 z-50 w-80 rounded-[1.25rem] border border-brand-ink/10 bg-white p-3 text-sm text-slate-700 shadow-lg opacity-0 transition group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100">
        <div className="flex items-center justify-between gap-2 px-1 pb-2">
          <p className="text-xs font-semibold text-brand-ink">通知</p>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
              isConnected ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
            }`}
          >
            {isConnected ? "接続中" : "接続待機"}
          </span>
        </div>

        {recent.length === 0 ? (
          <p className="rounded-2xl bg-brand-sand/40 px-3 py-4 text-xs text-slate-500">
            通知はまだありません。
          </p>
        ) : (
          <ul className="max-h-80 space-y-2 overflow-y-auto">
            {recent.map((item) => (
              <li
                className={`rounded-2xl border px-3 py-2 text-xs leading-5 transition ${
                  item.read_at
                    ? "border-brand-ink/5 bg-brand-sand/20 text-slate-500"
                    : "border-brand-ocean/25 bg-brand-ocean/5 text-brand-ink"
                }`}
                key={item.id}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-brand-ocean">
                    {KIND_LABEL[item.kind] ?? item.kind}
                  </span>
                  <span className="text-[10px] text-slate-400">
                    {formatTime(item.created_at)}
                  </span>
                </div>
                <p className="mt-1 font-semibold text-brand-ink">{item.title}</p>
                {item.read_at === null ? (
                  <button
                    className="mt-1 text-[10px] font-semibold text-brand-ocean transition hover:opacity-80"
                    onClick={() => void markRead(item.id)}
                    type="button"
                  >
                    既読にする
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
        )}

        <Link
          className="mt-2 block rounded-full border border-brand-ink/10 py-1.5 text-center text-xs font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
          href="/notifications"
        >
          すべての通知を見る
        </Link>
      </div>
    </div>
  );
}
