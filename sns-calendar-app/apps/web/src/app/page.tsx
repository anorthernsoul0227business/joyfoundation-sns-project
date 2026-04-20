"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { VERSION } from "@sns-calendar/shared-types";
import { Button } from "@sns-calendar/ui";
import { fetchCurrentUser } from "../lib/api-client";
import { useAuthGuard } from "../hooks/useAuthGuard";
import { useAuthStore } from "../stores/auth";

export default function HomePage() {
  const { isReady } = useAuthGuard();
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.session);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  useEffect(() => {
    if (!isReady) {
      return;
    }

    fetchCurrentUser().catch(() => {
      setRefreshError("プロフィールの再取得に失敗しました。");
    });
  }, [isReady]);

  if (!isReady || !user || !session) {
    return (
      <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-brand-sand px-6">
        <div className="rounded-3xl border border-brand-ink/10 bg-white px-6 py-4 text-sm text-slate-500 shadow-sm">
          認証状態を確認しています...
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-6 py-12">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-10 shadow-xl shadow-brand-ink/5">
          <p className="text-sm font-medium uppercase tracking-[0.3em] text-brand-ocean">
            Authenticated Home
          </p>
          <h1 className="mt-4 text-4xl font-semibold text-brand-ink">
            こんにちは、{user.displayName || user.email}
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">
            認証フローに続き、Sprint 2 では予約投稿のカレンダー閲覧画面が利用できます。
            月・週・日ビューを切り替えながら、SNS ごとの投稿予定を確認できます。
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-brand-ocean/15 bg-brand-sand/50 p-5">
              <p className="text-sm font-medium text-brand-ocean">Shared types version</p>
              <p className="mt-2 font-mono text-lg text-brand-ink">{VERSION}</p>
            </div>
            <div className="rounded-2xl border border-brand-ocean/15 bg-brand-sand/50 p-5">
              <p className="text-sm font-medium text-brand-ocean">Session expires at</p>
              <p className="mt-2 font-mono text-lg text-brand-ink">
                {new Date(session.expiresAt * 1000).toLocaleString("ja-JP")}
              </p>
            </div>
          </div>

          {refreshError ? <p className="mt-6 text-sm text-rose-600">{refreshError}</p> : null}

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              className="inline-flex items-center rounded-full bg-brand-ocean px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
              href="/calendar"
            >
              カレンダーを開く
            </Link>
            <Link
              className="inline-flex items-center rounded-full border border-brand-ink/10 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand-ocean hover:text-brand-ocean"
              href="/drafts"
            >
              下書きを見る
            </Link>
            <Button className="rounded-full px-5 py-3" type="button">
              UI Package Button
            </Button>
          </div>
        </section>

        <aside className="rounded-[2rem] border border-brand-ink/10 bg-white/80 p-8 shadow-lg shadow-brand-ink/5">
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-ocean">
            Session Summary
          </p>
          <dl className="mt-6 space-y-5 text-sm text-slate-600">
            <div>
              <dt className="font-medium text-brand-ink">Email</dt>
              <dd className="mt-1">{user.email}</dd>
            </div>
            <div>
              <dt className="font-medium text-brand-ink">Display name</dt>
              <dd className="mt-1">{user.displayName || "未設定"}</dd>
            </div>
            <div>
              <dt className="font-medium text-brand-ink">UI mode</dt>
              <dd className="mt-1">{user.uiMode}</dd>
            </div>
            <div>
              <dt className="font-medium text-brand-ink">Help mode</dt>
              <dd className="mt-1">{user.helpModeEnabled ? "ON" : "OFF"}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </main>
  );
}
