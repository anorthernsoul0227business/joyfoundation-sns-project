"use client";

import { Draggable } from "@fullcalendar/interaction";
import { useEffect, useMemo, useRef, useState } from "react";
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

const PLATFORM_FILTERS: Array<PlatformValue> = ["x", "ig", "youtube", "note", "line"];

type DraftsSidebarProps = {
  drafts: Array<PostResponse>;
  isLoading: boolean;
  errorMessage: string | null;
  onRefresh: () => void;
};

function extractPlatforms(draft: PostResponse): Array<PlatformValue> {
  const targets = draft.targets ?? [];
  const unique = new Set<PlatformValue>();
  for (const target of targets) {
    unique.add(target.platform as PlatformValue);
  }
  return Array.from(unique);
}

function truncate(text: string, length = 60): string {
  const trimmed = text.trim();
  if (!trimmed) {
    return "(本文なし)";
  }
  if (trimmed.length <= length) {
    return trimmed;
  }
  return `${trimmed.slice(0, length)}…`;
}

export function DraftsSidebar({
  drafts,
  isLoading,
  errorMessage,
  onRefresh,
}: DraftsSidebarProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [query, setQuery] = useState("");
  const [platformFilter, setPlatformFilter] = useState<PlatformValue | "all">("all");

  useEffect(() => {
    if (!containerRef.current) {
      return;
    }
    const draggable = new Draggable(containerRef.current, {
      itemSelector: "[data-draft-id]",
      eventData: (el) => {
        const id = el.getAttribute("data-draft-id") ?? undefined;
        const title = el.getAttribute("data-draft-title") ?? "下書き";
        const rawPlatforms = el.getAttribute("data-draft-platforms") ?? "";
        const platforms = rawPlatforms
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean);
        return {
          id,
          title,
          extendedProps: {
            draftId: id,
            platforms,
            status: "draft",
          },
        };
      },
    });
    return () => {
      draggable.destroy();
    };
  }, []);

  const filteredDrafts = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return drafts.filter((draft) => {
      if (normalizedQuery && !draft.content_text.toLowerCase().includes(normalizedQuery)) {
        return false;
      }
      if (platformFilter === "all") {
        return true;
      }
      return extractPlatforms(draft).includes(platformFilter);
    });
  }, [drafts, query, platformFilter]);

  return (
    <section className="flex h-full min-w-0 flex-col gap-3 rounded-[1.5rem] border border-brand-ink/10 bg-white p-4 shadow-sm">
      <header className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-brand-ink">下書き</h2>
          <HelpMark topic="calendar.drafts_sidebar" />
        </div>
        <button
          className="rounded-full border border-brand-ink/10 px-2.5 py-1 text-xs font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
          onClick={onRefresh}
          type="button"
        >
          再読込
        </button>
      </header>

      <input
        className="w-full rounded-full border border-brand-ink/10 bg-brand-sand/30 px-3 py-2 text-xs text-slate-700 outline-none transition focus:border-brand-ocean"
        onChange={(event) => setQuery(event.target.value)}
        placeholder="本文で検索"
        type="search"
        value={query}
      />

      <div className="flex flex-wrap gap-1">
        <button
          className={`rounded-full border px-2 py-1 text-[10px] font-semibold transition ${
            platformFilter === "all"
              ? "border-brand-ocean bg-brand-ocean text-white"
              : "border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean"
          }`}
          onClick={() => setPlatformFilter("all")}
          type="button"
        >
          全て
        </button>
        {PLATFORM_FILTERS.map((platform) => (
          <button
            className={`rounded-full border px-2 py-1 text-[10px] font-semibold transition ${
              platformFilter === platform
                ? `${PLATFORM_BADGE[platform]} border-transparent`
                : "border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean"
            }`}
            key={platform}
            onClick={() => setPlatformFilter(platform)}
            type="button"
          >
            {PLATFORM_LABELS[platform]}
          </button>
        ))}
      </div>

      {errorMessage ? (
        <p className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {errorMessage}
        </p>
      ) : null}

      <div
        className="flex min-h-[200px] flex-1 flex-col gap-2 overflow-y-auto"
        ref={containerRef}
      >
        {isLoading ? (
          <p className="rounded-2xl bg-brand-sand/40 px-3 py-2 text-xs text-slate-500">
            下書きを読み込んでいます…
          </p>
        ) : null}
        {!isLoading && filteredDrafts.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-brand-ink/15 bg-brand-sand/30 px-3 py-4 text-xs leading-5 text-slate-500">
            表示できる下書きはありません。
          </p>
        ) : null}

        {filteredDrafts.map((draft) => {
          const platforms = extractPlatforms(draft);
          return (
            <article
              className="cursor-grab rounded-2xl border border-brand-ink/10 bg-brand-sand/20 px-3 py-2.5 text-left text-sm text-slate-700 shadow-sm transition hover:border-brand-ocean active:cursor-grabbing"
              data-draft-id={draft.id}
              data-draft-platforms={platforms.join(",")}
              data-draft-title={truncate(draft.content_text, 30)}
              key={draft.id}
              title="カレンダーにドラッグして予約"
            >
              <div className="flex flex-wrap items-center gap-1">
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
              <p className="mt-1.5 line-clamp-3 whitespace-pre-wrap text-xs leading-5 text-brand-ink">
                {truncate(draft.content_text, 120)}
              </p>
            </article>
          );
        })}
      </div>
    </section>
  );
}
