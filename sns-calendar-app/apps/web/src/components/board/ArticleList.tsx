"use client";

import { useEffect, useState } from "react";
import {
  formatDateJa,
  PLATFORM_LABEL,
  type Article,
  type ArticleFilter,
  type CalendarScope,
  type Platform,
} from "../../lib/board";
import { FILTERABLE, PlatformFilter } from "./PlatformFilter";
import { StatusBadge } from "./StatusBadge";

// 開いているか閉じているかは端末に覚えておく。
// 2026-09-30 康二郎さん: 絞り込みは開いたり閉じたりできるようにしてほしい
const OPEN_KEY = "jf-board-filters-open";

const FILTERS: { value: ArticleFilter; label: string }[] = [
  { value: "pending", label: "未対応だけ" },
  { value: "approved", label: "OKした記事" },
  { value: "week", label: "今週" },
  { value: "all", label: "すべて" },
  { value: "discarded", label: "出さないもの" },
];

// 2026-09-30 康二郎さん: 記事の確認ページもイベントと通常記事を分けて見たい。
// 投稿予定カレンダーと同じ3分割・同じ文言にしてある
const SCOPES: { value: CalendarScope; label: string }[] = [
  { value: "all", label: "すべての記事" },
  { value: "normal", label: "イベント以外" },
  { value: "event", label: "イベント記事" },
];

export function ArticleList({
  articles,
  filter,
  scope,
  platforms,
  scopeCounts,
  platformCounts,
  loading,
  selectedId,
  onFilterChange,
  onScopeChange,
  onPlatformsChange,
  onSelect,
}: {
  articles: Article[];
  filter: ArticleFilter;
  scope: CalendarScope;
  platforms: Set<Platform>;
  /** 絞り込む前の件数。選ぶ前に「イベント記事が何件あるか」が分かるように */
  scopeCounts: Record<CalendarScope, number>;
  platformCounts: Record<string, number>;
  loading: boolean;
  selectedId: string | null;
  onFilterChange: (next: ArticleFilter) => void;
  onScopeChange: (next: CalendarScope) => void;
  onPlatformsChange: (next: Set<Platform>) => void;
  onSelect: (article: Article) => void;
}) {
  const narrowed = scope !== "all" || platforms.size < FILTERABLE.length;

  // 最初は開いておく。閉じたままだと「イベント以外だけ見る」ができることに
  // 気づけないため。一度閉じたら次からは閉じたまま
  const [open, setOpen] = useState(true);
  useEffect(() => {
    const saved = window.localStorage.getItem(OPEN_KEY);
    if (saved !== null) setOpen(saved === "1");
  }, []);

  function toggleOpen() {
    const next = !open;
    setOpen(next);
    window.localStorage.setItem(OPEN_KEY, next ? "1" : "0");
  }

  // 閉じているときは、いま何で絞っているかを一行で見せる。
  // 閉じたせいで「なぜこの件数なのか」が分からなくなると困る
  const summary = narrowed
    ? [
        SCOPES.find((s) => s.value === scope)?.label,
        platforms.size < FILTERABLE.length
          ? FILTERABLE.filter((p) => platforms.has(p))
              .map((p) => PLATFORM_LABEL[p])
              .join("・")
          : null,
      ]
        .filter(Boolean)
        .join(" / ")
    : "すべての記事・すべての媒体";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex flex-wrap gap-1.5 border-b border-slate-200 px-3 py-2.5">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            type="button"
            aria-pressed={filter === f.value}
            onClick={() => onFilterChange(f.value)}
            className={
              "rounded-full border px-3 py-1 text-[0.78em] transition " +
              (filter === f.value
                ? "border-brand-ink bg-brand-ink text-white"
                : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")
            }
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="border-b border-slate-200 bg-slate-50/70">
        <button
          type="button"
          onClick={toggleOpen}
          aria-expanded={open}
          aria-controls="article-filters"
          className="flex w-full items-center gap-2 px-3 py-2 text-left transition hover:bg-slate-100/70"
        >
          <span aria-hidden className="text-[0.7em] text-slate-400">
            {open ? "▼" : "▶"}
          </span>
          <span className="text-[0.8em] font-semibold text-slate-600">絞り込み</span>
          {!open && (
            <span
              className={
                "min-w-0 flex-1 truncate text-[0.78em] " +
                (narrowed ? "font-semibold text-brand-ink" : "text-slate-400")
              }
            >
              {summary}
            </span>
          )}
          {!open && narrowed && (
            <span className="shrink-0 rounded-full bg-brand-ocean/15 px-2 py-0.5 text-[0.7em] font-semibold text-brand-ink">
              {articles.length}件
            </span>
          )}
        </button>

        {open && (
          <div id="article-filters" className="px-3 pb-2.5">
            <div className="flex gap-1" role="tablist" aria-label="記事の種類">
              {SCOPES.map((s) => (
                <button
                  key={s.value}
                  type="button"
                  role="tab"
                  aria-selected={scope === s.value}
                  onClick={() => onScopeChange(s.value)}
                  className={
                    "flex-1 rounded-lg border px-2 py-1.5 text-[0.78em] transition " +
                    (scope === s.value
                      ? "border-brand-ocean bg-white font-semibold text-brand-ink shadow-sm"
                      : "border-transparent text-slate-500 hover:bg-white/70")
                  }
                >
                  {s.label}
                  <span className="ml-1 text-[0.85em] text-slate-400">{scopeCounts[s.value]}</span>
                </button>
              ))}
            </div>
            <div className="mt-2 [&>div]:mb-0">
              <PlatformFilter
                value={platforms}
                onChange={onPlatformsChange}
                counts={platformCounts}
              />
            </div>
            {narrowed && (
              <button
                type="button"
                onClick={() => {
                  onScopeChange("all");
                  onPlatformsChange(new Set(FILTERABLE));
                }}
                className="mt-2 text-[0.78em] text-brand-ink underline underline-offset-2"
              >
                絞り込みを外す
              </button>
            )}
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && articles.length === 0 ? (
          <p className="px-4 py-6 text-[0.9em] text-slate-500">読み込んでいます…</p>
        ) : articles.length === 0 ? (
          <div className="px-4 py-8 text-center text-[0.9em] text-slate-500">
            {narrowed ? (
              // 絞り込みのせいで空なのか、本当に無いのかが分からないと迷う
              <>
                <p>この絞り込みでは記事がありません。</p>
                <p className="mt-1 text-[0.9em]">
                  「すべての記事」に戻すか、見る媒体を増やしてみてください。
                </p>
              </>
            ) : filter === "pending" ? (
              <>
                <p className="text-[1.4em]">✓</p>
                <p className="mt-1">確認をお願いする記事はありません。</p>
              </>
            ) : filter === "approved" ? (
              <p>OKした記事はまだありません。</p>
            ) : (
              <p>記事がありません。</p>
            )}
          </div>
        ) : (
          articles.map((a) => {
            const on = a.id === selectedId;
            return (
              <button
                key={a.id}
                type="button"
                onClick={() => onSelect(a)}
                aria-current={on ? "true" : undefined}
                className={
                  "block w-full min-w-0 border-b border-slate-200 px-4 py-3.5 text-left transition " +
                  (on ? "bg-brand-ocean/10 shadow-[inset_3px_0_0_#0f766e]" : "hover:bg-slate-50")
                }
              >
                <div className="mb-1 flex flex-wrap items-center gap-2 text-[0.75em] text-slate-500">
                  {/* 2026-09-30: メールから来たとき、どれが指定された記事か
                      分かるように番号を出す */}
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono font-semibold text-slate-700">
                    {a.article_no}
                  </span>
                  <span className="font-semibold text-slate-600">{PLATFORM_LABEL[a.platform]}</span>
                  <span>
                    ・
                    {a.scheduled_at
                      ? `${formatDateJa(a.scheduled_at)}に投稿`
                      : a.event_date
                        ? `${formatDateJa(a.event_date)}のイベント`
                        : "日付未定"}
                  </span>
                  <StatusBadge status={a.status} />
                </div>
                <div className="line-clamp-2 text-[0.92em] leading-relaxed text-brand-ink">
                  {a.title || a.body_ai.split("\n")[0] || "（タイトルなし）"}
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
