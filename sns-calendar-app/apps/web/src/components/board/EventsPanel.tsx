"use client";

import { useCallback, useEffect, useState } from "react";
import { AnnounceRuleTable } from "./GuidePanel";
import { ANNOUNCE_NOTES } from "../../lib/rules";
import {
  formatDateJa,
  listEventRuns,
  saveAnnouncePlan,
  PLATFORM_LABEL,
  STATUS_LABEL,
  type EventRun,
} from "../../lib/board";

/** 「9月12日（土）ほか9日」のように、まとめた開催日を短く見せる */
function datesLabel(dates: string[]): string {
  const sorted = [...dates].sort();
  const head = formatDateJa(sorted[0]);
  return sorted.length === 1 ? head : `${head} ほか${sorted.length - 1}日`;
}

function daysUntil(iso: string): number {
  const d = new Date(iso);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  d.setHours(0, 0, 0, 0);
  return Math.round((d.getTime() - today.getTime()) / 86400000);
}

function EventCard({ run, onChanged }: { run: EventRun; onChanged: () => void }) {
  const [from, setFrom] = useState(run.announceFrom ?? "");
  const [note, setNote] = useState(run.announceNote ?? "");
  const [skip, setSkip] = useState(run.announceSkip);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const left = daysUntil([...run.dates].sort()[0]);
  const noImage = run.articles.filter((a) => !a.hasImage);
  const dayBefore = run.articles.filter((a) => a.announce_role === "day_before");

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await saveAnnouncePlan({
        run,
        announceFrom: from || null,
        announceSkip: skip,
        announceNote: note || null,
      });
      setSaved(true);
      onChanged();
      window.setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 text-[0.8em] text-slate-500">
        <span className="font-semibold text-slate-700">{datesLabel(run.dates)}</span>
        <span>あと{left}日</span>
        {run.announceSkip && (
          <span className="rounded bg-slate-200 px-2 py-0.5 font-semibold text-slate-600">
            告知しない
          </span>
        )}
      </div>
      <p className="mt-1 text-[1.05em] font-semibold text-brand-ink">{run.title}</p>
      {(run.venue || run.priceText) && (
        <p className="mt-1 text-[0.88em] text-slate-600">
          {[run.venue, run.priceText].filter(Boolean).join(" ／ ")}
        </p>
      )}

      {/* 告知記事の状況 */}
      <div className="mt-3 rounded bg-brand-sand/50 px-4 py-3">
        {run.articles.length === 0 ? (
          <p className="text-[0.9em] text-slate-600">
            {run.announceSkip
              ? "告知しない設定です。"
              : "告知記事はまだ作られていません。毎朝の処理で作られます。"}
          </p>
        ) : (
          <>
            <p className="mb-2 text-[0.82em] text-slate-500">
              告知 {run.articles.length}本
              {dayBefore.length > 0 && `（うち前日 ${dayBefore.length}本）`}
              {noImage.length > 0 && (
                <span className="ml-2 font-semibold text-amber-800">
                  写真がない記事が{noImage.length}本あります
                </span>
              )}
            </p>
            <ul className="space-y-1 text-[0.85em]">
              {run.articles.map((a) => (
                <li key={a.id} className="flex flex-wrap items-center gap-2">
                  <span className="text-slate-500">
                    {a.scheduled_date ? formatDateJa(a.scheduled_date) : "日付未定"}
                  </span>
                  <span className="font-semibold text-slate-700">
                    {PLATFORM_LABEL[a.platform]}
                  </span>
                  {a.announce_role === "day_before" && (
                    <span className="rounded bg-brand-ocean/10 px-1.5 text-[0.85em] font-semibold text-brand-ocean">
                      前日
                    </span>
                  )}
                  <span className="text-slate-500">{STATUS_LABEL[a.status]}</span>
                  {!a.hasImage && <span className="text-amber-800">写真なし</span>}
                </li>
              ))}
            </ul>
          </>
        )}
      </div>

      {/* 圭一郎さんが決めるところ */}
      <div className="mt-3 grid gap-3 md:grid-cols-[auto_minmax(0,1fr)] md:items-start">
        <label className="text-[0.9em]">
          <span className="mb-1 block text-slate-600">いつから告知しますか</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="rounded border border-slate-300 px-3 py-2 text-[1em] outline-none focus:border-brand-ocean"
          />
          <span className="mt-1 block text-[0.82em] text-slate-500">
            空のままなら、開催日から逆算して決めます
          </span>
        </label>
        <label className="text-[0.9em]">
          <span className="mb-1 block text-slate-600">ご要望があればお書きください</span>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="例：今回は早めに出したい"
            className="w-full rounded border border-slate-300 px-3 py-2 text-[1em] outline-none focus:border-brand-ocean"
          />
        </label>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-[0.9em] text-slate-700">
          <input type="checkbox" checked={skip} onChange={(e) => setSkip(e.target.checked)} />
          この催しは告知しない
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={save}
          className="rounded-md bg-brand-ocean px-5 py-2.5 text-[0.95em] font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
        >
          {busy ? "保存しています…" : "決定"}
        </button>
        {saved && <span className="text-[0.85em] text-brand-ocean">保存しました</span>}
        {error && <span className="text-[0.85em] text-rose-700">{error}</span>}
      </div>
    </li>
  );
}

export function EventsPanel({ reloadKey }: { reloadKey: number }) {
  const [runs, setRuns] = useState<EventRun[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const load = useCallback(() => {
    listEventRuns()
      .then(setRuns)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  useEffect(() => {
    load();
  }, [load, reloadKey, tick]);

  if (error) return <p className="px-6 py-6 text-[0.88em] text-rose-700">{error}</p>;
  if (runs.length === 0) {
    return <p className="px-6 py-10 text-center text-[0.92em] text-slate-500">
      これからのイベントは登録されていません。
    </p>;
  }

  const needDecision = runs.filter((r) => !r.announceSkip && !r.announceFrom);

  return (
    <div className="mx-auto max-w-[46rem]">
      {/* 何も指定しなかったらどうなるかを、毎回目に入る場所に置く */}
      <details className="mb-4 rounded border border-slate-200 bg-white px-5 py-3 shadow-sm">
        <summary className="cursor-pointer list-none text-[0.95em] font-semibold text-brand-ink">
          ▸ 告知の決まり（とくにご指定がなければ、この回数で告知します）
        </summary>
        <div className="pt-3">
          <AnnounceRuleTable />
          <ul className="mt-3 space-y-1.5 text-[0.9em] leading-relaxed text-slate-700">
            {ANNOUNCE_NOTES.map((n) => (
              <li key={n} className="flex gap-2">
                <span aria-hidden className="text-slate-400">
                  ・
                </span>
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </div>
      </details>

      {needDecision.length > 0 && (
        <p className="mb-4 rounded border border-amber-300 bg-amber-50 px-5 py-3 text-[0.95em] text-amber-900">
          <strong>{needDecision.length}件</strong>
          の催しについて、いつから告知するかを決めていただけますか。
          決めていただかなくても開催日から逆算して出しますが、
          ご希望があれば日付を入れてください。
        </p>
      )}
      <ul className="space-y-3">
        {runs.map((run) => (
          <EventCard key={run.runKey} run={run} onChanged={() => setTick((t) => t + 1)} />
        ))}
      </ul>
    </div>
  );
}
