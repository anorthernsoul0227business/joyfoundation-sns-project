"use client";

import Link from "next/link";
import type { CalendarEvent } from "../../generated/types.gen";
import { HelpMark } from "../HelpMark";

type PlatformValue = "x" | "ig" | "youtube" | "note" | "line";

const PLATFORM_LABELS: Record<PlatformValue, string> = {
  x: "X",
  ig: "IG",
  youtube: "YT",
  note: "note",
  line: "LINE",
};

const PLATFORM_BADGE: Record<PlatformValue, string> = {
  x: "bg-x text-white",
  ig: "bg-ig text-white",
  youtube: "bg-yt text-white",
  note: "bg-note text-white",
  line: "bg-line text-white",
};

type TodaysPostsSectionProps = {
  events: Array<CalendarEvent>;
  isLoading: boolean;
  errorMessage: string | null;
};

function formatEventTime(value: string): string {
  const date = new Date(value);
  return new Intl.DateTimeFormat("ja-JP", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function truncate(text: string, length = 100): string {
  const trimmed = text.trim();
  if (trimmed.length <= length) {
    return trimmed;
  }
  return `${trimmed.slice(0, length)}…`;
}

export function TodaysPostsSection({ events, isLoading, errorMessage }: TodaysPostsSectionProps) {
  const sorted = [...events].sort((a, b) => a.start.localeCompare(b.start));

  return (
    <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-brand-ink">今日・明日の予約</h2>
          <HelpMark topic="home.todays_posts" />
        </div>
        <Link
          className="text-xs font-semibold text-brand-ocean transition hover:opacity-80"
          href="/calendar"
        >
          カレンダー →
        </Link>
      </div>

      {errorMessage ? (
        <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {errorMessage}
        </p>
      ) : null}

      {isLoading ? (
        <p className="mt-4 rounded-2xl bg-brand-sand/40 px-4 py-3 text-sm text-slate-500">
          予約を確認しています…
        </p>
      ) : null}

      {!isLoading && !errorMessage && sorted.length === 0 ? (
        <div className="mt-4 rounded-[1.5rem] border border-dashed border-brand-ink/15 bg-brand-sand/30 px-4 py-6 text-sm leading-6 text-slate-500">
          本日と明日に予約済みの投稿はありません。
          <Link
            className="ml-2 font-semibold text-brand-ocean transition hover:opacity-80"
            href="/calendar"
          >
            カレンダーから予約する
          </Link>
        </div>
      ) : null}

      {!isLoading && sorted.length > 0 ? (
        <ul className="mt-4 space-y-3">
          {sorted.map((event) => {
            const platforms = (event.platforms ?? []) as Array<PlatformValue>;
            return (
              <li
                className="rounded-2xl border border-brand-ink/10 bg-brand-sand/20 px-4 py-3 text-sm text-slate-700"
                key={event.id}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-semibold text-brand-ocean">
                    {formatEventTime(event.start)}
                  </span>
                  {platforms.map((platform) => (
                    <span
                      className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${PLATFORM_BADGE[platform]}`}
                      key={platform}
                    >
                      {PLATFORM_LABELS[platform]}
                    </span>
                  ))}
                </div>
                <p className="mt-1.5 text-sm leading-6 text-brand-ink">
                  {truncate(event.title, 100)}
                </p>
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
