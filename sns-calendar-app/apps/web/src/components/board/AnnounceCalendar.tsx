"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArticlePeek } from "./ArticlePeek";
import { FILTERABLE, PlatformFilter, filterByPlatform } from "./PlatformFilter";
import { useIsNarrow } from "../../hooks/useIsNarrow";
import {
  announceState,
  approveBy,
  formatDateJa,
  listAnnounceArticles,
  listEventsBetween,
  PLATFORM_LABEL,
  type Article,
  type EventItem,
  type Platform,
} from "../../lib/board";

const WEEKDAYS = ["日", "月", "火", "水", "木", "金", "土"];

/**
 * 告知の状態ごとの見た目。
 *
 * 2026-09-30 康二郎さんの設計: 圭一郎さんはこのカレンダーを見て、
 * 投稿希望日の前日までに承認すればよい。そのため
 * 「まだ承認していない（＝要対応）」を一番目立たせる。
 */
const STATE_STYLE: Record<string, { chip: string; label: string }> = {
  waiting: { chip: "bg-amber-400 text-amber-950 ring-1 ring-amber-600", label: "承認まち" },
  fixed: { chip: "bg-brand-ocean text-white", label: "決まりました" },
  done: { chip: "bg-slate-300 text-slate-600", label: "投稿ずみ" },
  missed: { chip: "bg-rose-200 text-rose-800 line-through", label: "間に合いませんでした" },
};

// 2026-09-30 康二郎さん: 実際に催しが行われる日も出す。ほかと違う分かりやすい色で。
// 告知は amber（承認まち）/ ocean / slate / rose を使っているので、紫にした
const EVENT_CHIP = "bg-violet-600 text-white ring-1 ring-violet-800";

function ymd(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function AnnounceCalendar({
  reloadKey,
  userId,
  onSelectArticle,
}: {
  reloadKey: number;
  userId: string;
  /** 記事の画面へ移りたいときだけ使う。ふだんは横のプレビューで済ませる */
  onSelectArticle: (a: Article) => void;
}) {
  // 2026-09-30 康二郎さん: カレンダーから記事を開くと確認ページに移ってしまい、
  // 戻りにくい。カレンダーを見たまま横で読めるようにする
  const [peek, setPeek] = useState<Article | null>(null);
  const [shown, setShown] = useState<Set<Platform>>(() => new Set(FILTERABLE));
  const narrow = useIsNarrow();
  const [month, setMonth] = useState(() => {
    const d = new Date();
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });
  const [articles, setArticles] = useState<Article[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [showEvents, setShowEvents] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const from = new Date(month.getFullYear(), month.getMonth(), -7);
      const to = new Date(month.getFullYear(), month.getMonth() + 1, 14);
      const [as, es] = await Promise.all([
        listAnnounceArticles(from, to),
        listEventsBetween(from, to),
      ]);
      setArticles(as);
      setEvents(es);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [month]);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const visible = useMemo(() => filterByPlatform(articles, shown), [articles, shown]);

  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const a of articles) c[a.platform] = (c[a.platform] ?? 0) + 1;
    return c;
  }, [articles]);

  const byDay = useMemo(() => {
    const map = new Map<string, Article[]>();
    for (const a of visible) {
      if (!a.scheduled_date) continue;
      const list = map.get(a.scheduled_date) ?? [];
      list.push(a);
      map.set(a.scheduled_date, list);
    }
    return map;
  }, [visible]);

  // 終日の催しは starts_at が 0時(JST)。端末の時刻で日付に直す
  const eventsByDay = useMemo(() => {
    const map = new Map<string, EventItem[]>();
    if (!showEvents) return map;
    for (const e of events) {
      const key = ymd(new Date(e.starts_at));
      const list = map.get(key) ?? [];
      list.push(e);
      map.set(key, list);
    }
    return map;
  }, [events, showEvents]);

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
  const waiting = visible.filter(
    (a) => announceState(a) === "waiting" && (a.scheduled_date ?? "") >= today,
  );

  function Chip({ a }: { a: Article }) {
    const st = announceState(a);
    const by = approveBy(a);
    const late = st === "waiting" && by !== null && by < today;
    return (
      <button
        type="button"
        onClick={() => setPeek(a)}
        title={`${a.article_no}／${PLATFORM_LABEL[a.platform]}／${STATE_STYLE[st].label}${
          st === "waiting" && by ? `／${formatDateJa(by)}までに承認` : ""
        }`}
        className={
          "block w-full truncate rounded px-1.5 py-0.5 text-left text-[0.72em] transition hover:opacity-80 " +
          STATE_STYLE[st].chip
        }
      >
        {late && "⚠ "}
        {PLATFORM_LABEL[a.platform]} {a.title || a.article_no}
      </button>
    );
  }

  function EventChip({ e }: { e: EventItem }) {
    const at = new Date(e.starts_at);
    const time = e.all_day ? "終日" : `${at.getHours()}:${String(at.getMinutes()).padStart(2, "0")}`;
    return (
      <div
        title={`${e.title}／${time}${e.venue ? `／${e.venue}` : ""}`}
        className={"truncate rounded px-1.5 py-0.5 text-[0.72em] font-semibold " + EVENT_CHIP}
      >
        ● {e.title}
      </div>
    );
  }

  return (
    <div className={peek ? "mx-auto max-w-[70rem]" : "mx-auto max-w-[52rem]"}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-[0.9em] transition hover:bg-slate-50 md:px-4"
        >
          ←<span className="hidden md:inline"> 前の月</span>
        </button>
        <span className="text-[1.15em] font-semibold text-brand-ink">
          {month.getFullYear()}年{month.getMonth() + 1}月
        </span>
        <button
          type="button"
          onClick={() => setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))}
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-[0.9em] transition hover:bg-slate-50 md:px-4"
        >
          <span className="hidden md:inline">次の月 </span>→
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
          {loading
            ? "読み込んでいます…"
            : `この月の告知 ${visible.length}件` +
              (showEvents ? ` ／ 催し ${events.length}件` : "")}
        </span>
      </div>

      <p className="mb-3 rounded border border-amber-300 bg-amber-50 px-5 py-3 text-[0.93em] leading-relaxed text-amber-900">
        <strong className="mr-1">使い方</strong>
        黄色い帯が「まだ承認していない記事」です。
        <strong>その日の前日までに「このまま出す」を押していただければ</strong>
        、書かれている日に投稿されます。
        押していただけなかった場合は、承認の翌日以降に自動でずらします。
        {waiting.length > 0 && (
          <span className="mt-1 block">
            いま承認をお待ちしているのは <strong>{waiting.length}件</strong> です。
          </span>
        )}
      </p>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="[&>div]:mb-0">
          <PlatformFilter value={shown} onChange={setShown} counts={counts} />
        </div>
        <button
          type="button"
          role="checkbox"
          aria-checked={showEvents}
          onClick={() => setShowEvents((v) => !v)}
          className={
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[0.85em] transition " +
            (showEvents
              ? "border-violet-700 bg-white font-semibold text-violet-800"
              : "border-slate-200 bg-slate-50 text-slate-400")
          }
        >
          <span
            className={
              "flex h-4 w-4 items-center justify-center rounded text-[0.7em] text-white " +
              (showEvents ? "bg-violet-600" : "bg-slate-300")
            }
            aria-hidden
          >
            {showEvents ? "✓" : ""}
          </span>
          催しの日
          <span className="text-[0.85em] text-slate-400">{events.length}</span>
        </button>
      </div>

      <div className="mb-2 flex flex-wrap items-center gap-3 text-[0.8em] text-slate-600">
        {showEvents && (
          <span className="flex items-center gap-1.5">
            <span className={`inline-block h-3 w-6 rounded ${EVENT_CHIP}`} />
            催しの日
          </span>
        )}
        {(["waiting", "fixed", "done", "missed"] as const).map((k) => (
          <span key={k} className="flex items-center gap-1.5">
            <span className={`inline-block h-3 w-6 rounded ${STATE_STYLE[k].chip}`} />
            {STATE_STYLE[k].label}
          </span>
        ))}
      </div>

      {error && (
        <p className="mb-3 rounded border border-rose-200 bg-rose-50 px-4 py-2 text-[0.88em] text-rose-700">
          {error}
        </p>
      )}

      {withPeek(
        <>
      {narrow ? (
        <ul className="space-y-2">
          {cells
            .filter(
              (d) =>
                d.getMonth() === thisMonth &&
                ((byDay.get(ymd(d)) ?? []).length > 0 ||
                  (eventsByDay.get(ymd(d)) ?? []).length > 0),
            )
            .map((d) => {
              const key = ymd(d);
              return (
                <li
                  key={key}
                  className={
                    "rounded border bg-white px-4 py-3 shadow-sm " +
                    (key === today ? "border-brand-ocean" : "border-slate-200")
                  }
                >
                  <p className="mb-2 text-[0.9em] font-semibold text-slate-700">
                    {d.getMonth() + 1}月{d.getDate()}日（{WEEKDAYS[d.getDay()]}）
                    {key === today && " 今日"}
                  </p>
                  <div className="space-y-1.5">
                    {(eventsByDay.get(key) ?? []).map((e) => (
                      <EventChip key={e.id} e={e} />
                    ))}
                    {(byDay.get(key) ?? []).map((a) => (
                      <Chip key={a.id} a={a} />
                    ))}
                  </div>
                </li>
              );
            })}
          {visible.length === 0 && eventsByDay.size === 0 && (
            <li className="rounded border border-slate-200 bg-white px-5 py-8 text-center text-[0.92em] text-slate-500">
              この月の告知はありません。
            </li>
          )}
        </ul>
      ) : (
        <div className="grid grid-cols-7 gap-px rounded border border-slate-200 bg-slate-200">
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
                  {(eventsByDay.get(key) ?? []).map((e) => (
                    <EventChip key={e.id} e={e} />
                  ))}
                  {items.map((a) => (
                    <Chip key={a.id} a={a} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
        </>,
      )}

      <p className="mt-3 text-[0.85em] text-slate-500">
        押すと、右（携帯では下）に記事が出ます。投稿はお昼の12時です。
      </p>
    </div>
  );

  function withPeek(cal: React.ReactNode) {
    if (!peek) return cal;
    return (
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
        <div className="min-w-0">{cal}</div>
        <ArticlePeek
          article={peek}
          userId={userId}
          onUpdated={(next) => {
            setPeek(next);
            setArticles((prev) => prev.map((x) => (x.id === next.id ? next : x)));
          }}
          onClose={() => setPeek(null)}
          onOpenFull={() => onSelectArticle(peek)}
        />
      </div>
    );
  }
}
