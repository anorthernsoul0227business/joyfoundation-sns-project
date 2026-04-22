"use client";

import { useEffect, useState } from "react";
import type { CalendarEvent, PostResponse, SnsAccountSafe } from "../generated/types.gen";
import { QuickActions } from "../components/home/QuickActions";
import { RecentDraftsSection } from "../components/home/RecentDraftsSection";
import { SystemStatusBanner } from "../components/home/SystemStatusBanner";
import { TodaysPostsSection } from "../components/home/TodaysPostsSection";
import { WelcomeSection } from "../components/home/WelcomeSection";
import { useAuthGuard } from "../hooks/useAuthGuard";
import { useAuthStore } from "../stores/auth";
import {
  fetchCalendarEvents,
  fetchCurrentUser,
  fetchPostList,
  fetchSnsAccounts,
} from "../lib/api-client";

const ALL_PLATFORMS: Array<"x" | "ig" | "youtube" | "note" | "line"> = [
  "x",
  "ig",
  "youtube",
  "note",
  "line",
];

function getTodayAndTomorrowRange(): { from: string; to: string } {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const end = new Date(start);
  end.setDate(end.getDate() + 2);
  return {
    from: start.toISOString(),
    to: end.toISOString(),
  };
}

export default function HomePage() {
  const { isReady } = useAuthGuard();
  const user = useAuthStore((state) => state.user);
  const session = useAuthStore((state) => state.session);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [todaysEvents, setTodaysEvents] = useState<Array<CalendarEvent>>([]);
  const [todaysLoading, setTodaysLoading] = useState(false);
  const [todaysError, setTodaysError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Array<PostResponse>>([]);
  const [draftsLoading, setDraftsLoading] = useState(false);
  const [draftsError, setDraftsError] = useState<string | null>(null);
  const [snsAccounts, setSnsAccounts] = useState<Array<SnsAccountSafe> | null>(null);
  const [snsLoading, setSnsLoading] = useState(false);

  useEffect(() => {
    if (!isReady) {
      return;
    }
    fetchCurrentUser().catch(() => {
      setRefreshError("プロフィールの再取得に失敗しました。");
    });
  }, [isReady]);

  useEffect(() => {
    if (!isReady) {
      return;
    }
    let active = true;

    setTodaysLoading(true);
    setTodaysError(null);
    const range = getTodayAndTomorrowRange();
    fetchCalendarEvents({
      from: range.from,
      to: range.to,
      platforms: ALL_PLATFORMS,
    })
      .then((response) => {
        if (!active) return;
        setTodaysEvents(
          response.events.filter(
            (event) => event.status === "scheduled" || event.status === "publishing",
          ),
        );
      })
      .catch(() => {
        if (!active) return;
        setTodaysError("予約投稿の取得に失敗しました。");
      })
      .finally(() => {
        if (active) setTodaysLoading(false);
      });

    setDraftsLoading(true);
    setDraftsError(null);
    fetchPostList({ status: "draft" })
      .then((response) => {
        if (!active) return;
        setDrafts(response.items);
      })
      .catch(() => {
        if (!active) return;
        setDraftsError("下書きの取得に失敗しました。");
      })
      .finally(() => {
        if (active) setDraftsLoading(false);
      });

    setSnsLoading(true);
    fetchSnsAccounts()
      .then((response) => {
        if (!active) return;
        setSnsAccounts(response.accounts);
      })
      .catch(() => {
        if (!active) return;
        setSnsAccounts([]);
      })
      .finally(() => {
        if (active) setSnsLoading(false);
      });

    return () => {
      active = false;
    };
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
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-8 sm:px-6 sm:py-12">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <WelcomeSection displayName={user.displayName || user.email} />
        <QuickActions />
        <SystemStatusBanner accounts={snsAccounts} isLoading={snsLoading} />
        <TodaysPostsSection
          errorMessage={todaysError}
          events={todaysEvents}
          isLoading={todaysLoading}
        />
        <RecentDraftsSection
          drafts={drafts}
          errorMessage={draftsError}
          isLoading={draftsLoading}
        />
        {refreshError ? (
          <p className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {refreshError}
          </p>
        ) : null}
      </div>
    </main>
  );
}
