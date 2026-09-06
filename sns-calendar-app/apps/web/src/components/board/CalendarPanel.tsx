"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  calendarDate,
  listCalendarArticles,
  PLATFORM_LABEL,
  STATUS_LABEL,
  type Article,
} from "../../lib/board";

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

/** 媒体ごとの色。並べたときに一目で見分けられるようにする */
const PLATFORM_TONE: Record<string, string> = {
  x: "bg-slate-800 text-white",
  ig: "bg-rose-600 text-white",
  note: "bg-emerald-700 text-white",
  youtube: "bg-red-700 text-white",
  line: "bg-lime-700 text-white",
};

function ymd(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function CalendarPanel({
  reloadKey,
  onSelectArticle,
}: {
  reloadKey: number;
  onSelectArticle: (a: Article) => void;
}) {
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [articles, setArticles] = useState<Article[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 前後の月にはみ出した週も表示するので、少し広めに取る
      const from = new Date(month.getFullYear(), month.getMonth(), -7);
      const to = new Date(month.getFullYear(), month.getMonth() + 1, 14);
      setArticles(await listCalendarArticles(from, to));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const byDay = useMemo(() => {
    const map = new Map<string, Article[]>();
    for (const a of articles) {
      const key = calendarDate(a);
      if (!key) continue;
      const list = map.get(key) ?? [];
      list.push(a);
      map.set(key, list);
    }
    for (const list of map.values()) {
      list.sort((x, y) => x.platform.localeCompare(y.platform));
    }
    return map;
  }, [articles]);

  // 月の初日を含む週の日曜から、6週間ぶんを並べる
  const cells = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1);
    const start = new Date(first);
    start.setDate(1 - first.getDay());
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      return d;
    });
  }, [month]);

  const today = ymd(new Date());
  const thisMonth = month.getMonth();
  const total = articles.filter((a) => {
    const k = calendarDate(a);
    return k && new Date(k).getMonth() === thisMonth;
  }).length;

  return (
    <div className="mx-auto max-w-[52rem]">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-[0.9em] transition hover:bg-slate-50"
        >
          ← 前の月
        </button>
        <span className="text-[1.15em] font-semibold text-brand-ink">
          {month.getFullYear()}年{month.getMonth() + 1}月
        </span>
        <button
          type="button"
          onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-[0.9em] transition hover:bg-slate-50"
        >
          次の月 →
        </button>
        <button
          type="button"
          onClick={() => {
            const d = new Date();
            setMonth(new Date(d.getFullYear(), d.getMonth(), 1));
          }}
          className="rounded-md border border-slate-300 bg-white px-4 py-2 text-[0.9em] text-slate-600 transition hover:bg-slate-50"
        >
          今月
        </button>
        <span className="text-[0.85em] text-slate-500">
          {loading ? "読み込んでいます…" : `この月の投稿 ${total}件`}
        </span>
      </div>

      {error && (
        <p className="mb-3 rounded border border-rose-200 bg-rose-50 px-4 py-2 text-[0.88em] text-rose-700">
          {error}
        </p>
      )}

      <div className="mb-2 flex flex-wrap items-center gap-3 text-[0.8em] text-slate-500">
        {Object.entries(PLATFORM_LABEL).map(([key, label]) =>
          key === "youtube" || key === "line" ? null : (
            <span key={key} className="flex items-center gap-1.5">
              <span className={`inline-block h-3 w-3 rounded ${PLATFORM_TONE[key]}`} />
              {label}
            </span>
          ),
        )}
        <span>薄い色は投稿ずみ</span>
      </div>

      <div className="overflow-x-auto">
        <div className="grid min-w-[34rem] grid-cols-7 gap-px rounded border border-slate-200 bg-slate-200">
          {WEEKDAYS.map((w, i) => (
            <div
              key={w}
              className={
                "bg-white px-2 py-1.5 text-center text-[0.8em] font-semibold " +
                (i === 0 ? "text-rose-600" : i === 6 ? "text-blue-600" : "text-slate-600")
              }
            >
              {w}
            </div>
          ))}
          {cells.map((d) => {
            const key = ymd(d);
            const items = byDay.get(key) ?? [];
            const inMonth = d.getMonth() === thisMonth;
            return (
              <div
                key={key}
                className={
                  "min-h-[5.5rem] px-1.5 py-1 " +
                  (inMonth ? "bg-white" : "bg-slate-50") +
                  (key === today ? " ring-2 ring-inset ring-brand-ocean" : "")
                }
              >
                <div
                  className={
                    "mb-1 text-[0.78em] " +
                    (key === today
                      ? "font-bold text-brand-ocean"
                      : inMonth
                        ? "text-slate-600"
                        : "text-slate-400")
                  }
                >
                  {d.getDate()}
                </div>
                <div className="space-y-0.5">
                  {items.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => onSelectArticle(a)}
                      title={`${PLATFORM_LABEL[a.platform]}／${STATUS_LABEL[a.status]}／${a.title}`}
                      className={
                        "block w-full truncate rounded px-1.5 py-0.5 text-left text-[0.72em] transition hover:opacity-80 " +
                        PLATFORM_TONE[a.platform] +
                        (a.status === "published" ? " opacity-50" : "")
                      }
                    >
                      {a.title || PLATFORM_LABEL[a.platform]}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <p className="mt-3 text-[0.85em] text-slate-500">
        帯を押すと、その記事を開きます。投稿はお昼の12時です。
      </p>
    </div>
  );
}
