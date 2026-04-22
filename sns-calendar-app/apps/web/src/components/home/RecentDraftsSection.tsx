"use client";

import Link from "next/link";
import type { PostResponse } from "../../generated/types.gen";
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

type RecentDraftsSectionProps = {
  drafts: Array<PostResponse>;
  isLoading: boolean;
  errorMessage: string | null;
};

function truncate(text: string, length = 80): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return "(本文なし)";
  }
  if (trimmed.length <= length) {
    return trimmed;
  }
  return `${trimmed.slice(0, length)}…`;
}

function extractPlatforms(post: PostResponse): Array<PlatformValue> {
  const targets = post.targets ?? [];
  return Array.from(new Set(targets.map((target) => target.platform as PlatformValue)));
}

export function RecentDraftsSection({
  drafts,
  isLoading,
  errorMessage,
}: RecentDraftsSectionProps) {
  const recent = drafts.slice(0, 3);

  return (
    <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-semibold text-brand-ink">最近の下書き</h2>
          <HelpMark topic="home.recent_drafts" />
        </div>
        <Link
          className="text-xs font-semibold text-brand-ocean transition hover:opacity-80"
          href="/drafts"
        >
          もっと見る →
        </Link>
      </div>

      {errorMessage ? (
        <p className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {errorMessage}
        </p>
      ) : null}

      {isLoading ? (
        <p className="mt-4 rounded-2xl bg-brand-sand/40 px-4 py-3 text-sm text-slate-500">
          下書きを読み込んでいます…
        </p>
      ) : null}

      {!isLoading && !errorMessage && recent.length === 0 ? (
        <div className="mt-4 rounded-[1.5rem] border border-dashed border-brand-ink/15 bg-brand-sand/30 px-4 py-6 text-sm leading-6 text-slate-500">
          下書きはまだありません。
          <Link
            className="ml-2 font-semibold text-brand-ocean transition hover:opacity-80"
            href="/create"
          >
            新規投稿を作る
          </Link>
        </div>
      ) : null}

      {recent.length > 0 ? (
        <div className="-mx-2 mt-4 flex gap-3 overflow-x-auto px-2 pb-2">
          {recent.map((draft) => {
            const platforms = extractPlatforms(draft);
            return (
              <Link
                className="flex w-64 shrink-0 flex-col gap-2 rounded-2xl border border-brand-ink/10 bg-brand-sand/20 px-4 py-3 text-left text-sm text-slate-700 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-ocean hover:shadow-md"
                href={`/create?id=${draft.id}`}
                key={draft.id}
              >
                <div className="flex flex-wrap gap-1">
                  {platforms.length === 0 ? (
                    <span className="rounded-full border border-brand-ink/10 px-1.5 py-0.5 text-[10px] font-semibold text-slate-500">
                      未設定
                    </span>
                  ) : (
                    platforms.map((platform) => (
                      <span
                        className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${PLATFORM_BADGE[platform]}`}
                        key={platform}
                      >
                        {PLATFORM_LABELS[platform]}
                      </span>
                    ))
                  )}
                </div>
                <p className="line-clamp-4 whitespace-pre-wrap text-xs leading-5 text-brand-ink">
                  {truncate(draft.content_text, 120)}
                </p>
              </Link>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
