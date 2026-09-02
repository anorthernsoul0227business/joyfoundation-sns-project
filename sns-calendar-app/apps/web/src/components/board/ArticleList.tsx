"use client";

import { formatDateJa, PLATFORM_LABEL, type Article, type ArticleFilter } from "../../lib/board";
import { StatusBadge } from "./StatusBadge";

const FILTERS: { value: ArticleFilter; label: string }[] = [
  { value: "pending", label: "未対応だけ" },
  { value: "week", label: "今週" },
  { value: "all", label: "すべて" },
];

export function ArticleList({
  articles,
  filter,
  loading,
  selectedId,
  onFilterChange,
  onSelect,
}: {
  articles: Article[];
  filter: ArticleFilter;
  loading: boolean;
  selectedId: string | null;
  onFilterChange: (next: ArticleFilter) => void;
  onSelect: (article: Article) => void;
}) {
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

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && articles.length === 0 ? (
          <p className="px-4 py-6 text-[0.9em] text-slate-500">読み込んでいます…</p>
        ) : articles.length === 0 ? (
          <div className="px-4 py-8 text-center text-[0.9em] text-slate-500">
            {filter === "pending" ? (
              <>
                <p className="text-[1.4em]">✓</p>
                <p className="mt-1">確認をお願いする記事はありません。</p>
              </>
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
                <div className="mb-1 flex items-center gap-2 text-[0.75em] text-slate-500">
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
