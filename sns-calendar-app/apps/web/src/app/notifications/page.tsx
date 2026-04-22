"use client";

import { useState } from "react";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import { useNotifications } from "../../hooks/useNotifications";

const KIND_LABEL: Record<string, string> = {
  post_published: "投稿成功",
  post_failed: "投稿失敗",
  post_partial: "投稿一部失敗",
  system: "システム",
};

const KIND_BADGE: Record<string, string> = {
  post_published: "bg-emerald-100 text-emerald-700",
  post_failed: "bg-rose-100 text-rose-700",
  post_partial: "bg-amber-100 text-amber-700",
  system: "bg-slate-100 text-slate-700",
};

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function NotificationsPage() {
  const { isReady } = useAuthGuard();
  const {
    items,
    unreadCount,
    isLoading,
    errorMessage,
    isConnected,
    markRead,
    markAllRead,
    refresh,
  } = useNotifications(isReady);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  if (!isReady) {
    return (
      <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-brand-sand px-6">
        <div className="rounded-3xl border border-brand-ink/10 bg-white px-6 py-4 text-sm text-slate-500 shadow-sm">
          認証状態を確認しています…
        </div>
      </main>
    );
  }

  const visible = filter === "unread" ? items.filter((item) => item.read_at === null) : items;

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-8 sm:px-6 sm:py-12">
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.28em] text-brand-ocean">
                Notifications
              </p>
              <h1 className="mt-1 text-2xl font-semibold text-brand-ink">通知履歴</h1>
              <p className="mt-1 text-xs text-slate-500">
                未読 {unreadCount} 件 ・ {isConnected ? "リアルタイム接続中" : "接続待機中"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  filter === "all"
                    ? "border-brand-ocean bg-brand-ocean text-white"
                    : "border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean"
                }`}
                onClick={() => setFilter("all")}
                type="button"
              >
                すべて
              </button>
              <button
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition ${
                  filter === "unread"
                    ? "border-brand-ocean bg-brand-ocean text-white"
                    : "border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean"
                }`}
                onClick={() => setFilter("unread")}
                type="button"
              >
                未読のみ
              </button>
              <button
                className="rounded-full border border-brand-ink/10 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                onClick={() => void refresh()}
                type="button"
              >
                再読込
              </button>
              <button
                className="rounded-full border border-brand-ink/10 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                disabled={unreadCount === 0}
                onClick={() => void markAllRead()}
                type="button"
              >
                全件既読
              </button>
            </div>
          </div>

          {errorMessage ? (
            <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </p>
          ) : null}

          {isLoading ? (
            <p className="mt-4 rounded-2xl bg-brand-sand/40 px-4 py-3 text-sm text-slate-500">
              読み込み中…
            </p>
          ) : null}

          {!isLoading && visible.length === 0 ? (
            <div className="mt-4 rounded-[1.5rem] border border-dashed border-brand-ink/15 bg-brand-sand/30 px-4 py-6 text-sm leading-6 text-slate-500">
              {filter === "unread" ? "未読の通知はありません。" : "通知はまだありません。"}
            </div>
          ) : null}

          {visible.length > 0 ? (
            <ul className="mt-4 space-y-3">
              {visible.map((item) => (
                <li
                  className={`rounded-2xl border px-4 py-3 transition ${
                    item.read_at
                      ? "border-brand-ink/10 bg-brand-sand/20 text-slate-600"
                      : "border-brand-ocean/30 bg-brand-ocean/5 text-brand-ink"
                  }`}
                  key={item.id}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          KIND_BADGE[item.kind] ?? "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {KIND_LABEL[item.kind] ?? item.kind}
                      </span>
                      <span className="text-xs text-slate-500">
                        {formatDateTime(item.created_at)}
                      </span>
                    </div>
                    {item.read_at === null ? (
                      <button
                        className="text-xs font-semibold text-brand-ocean transition hover:opacity-80"
                        onClick={() => void markRead(item.id)}
                        type="button"
                      >
                        既読にする
                      </button>
                    ) : null}
                  </div>
                  <p className="mt-2 text-sm font-semibold text-brand-ink">{item.title}</p>
                  {item.body ? (
                    <pre className="mt-2 whitespace-pre-wrap break-words text-xs leading-6 text-slate-600">
                      {item.body}
                    </pre>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      </div>
    </main>
  );
}
