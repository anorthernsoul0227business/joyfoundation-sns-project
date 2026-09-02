"use client";

import { useEffect, useState } from "react";
import {
  formatDateJa,
  formatDateTimeJa,
  listEvents,
  listIdeas,
  listShares,
  type EventItem,
  type Idea,
  type Share,
} from "../../lib/board";

function useList<T>(loader: () => Promise<T[]>, reloadKey: number) {
  const [items, setItems] = useState<T[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    loader()
      .then((d) => {
        if (!cancelled) setItems(d);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
    // loader は定数関数なので依存に含めない
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey]);
  return { items, error };
}

function Empty({ text }: { text: string }) {
  return <p className="px-6 py-10 text-center text-[0.92em] text-slate-500">{text}</p>;
}

function Err({ text }: { text: string }) {
  return <p className="px-6 py-6 text-[0.88em] text-rose-700">{text}</p>;
}

const IDEA_STATUS: Record<Idea["status"], string> = {
  new: "届いています",
  read: "読みました",
  used: "記事にしました",
  holding: "あたためています",
};

export function IdeasPanel({ reloadKey }: { reloadKey: number }) {
  const { items, error } = useList<Idea>(listIdeas, reloadKey);
  if (error) return <Err text={error} />;
  if (items.length === 0) return <Empty text="まだメモはありません。右下のボタンから書けます。" />;
  return (
    <ul className="mx-auto max-w-[44rem] space-y-3">
      {items.map((i) => (
        <li key={i.id} className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <p className="whitespace-pre-wrap text-[0.98em] leading-relaxed text-brand-ink">{i.body}</p>
          <p className="mt-2 text-[0.78em] text-slate-500">
            {formatDateTimeJa(i.created_at)} ・ {IDEA_STATUS[i.status]}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function EventsPanel({ reloadKey }: { reloadKey: number }) {
  const { items, error } = useList<EventItem>(listEvents, reloadKey);
  if (error) return <Err text={error} />;
  if (items.length === 0) return <Empty text="これからのイベントは登録されていません。" />;
  return (
    <ul className="mx-auto max-w-[44rem] space-y-3">
      {items.map((ev) => (
        <li key={ev.id} className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2 text-[0.8em] text-slate-500">
            <span className="font-semibold text-slate-700">{formatDateJa(ev.starts_at)}</span>
            {!ev.all_day && <span>{formatDateTimeJa(ev.starts_at).split(" ")[1]}〜</span>}
            {ev.confirmed_by_owner ? (
              <span className="rounded bg-brand-ocean/10 px-2 py-0.5 text-[0.85em] font-semibold text-brand-ocean">確認ずみ</span>
            ) : (
              <span className="rounded bg-amber-50 px-2 py-0.5 text-[0.85em] font-semibold text-amber-800">未確認</span>
            )}
          </div>
          <p className="mt-1 text-[1.02em] font-semibold text-brand-ink">{ev.title}</p>
          {(ev.venue || ev.price_text) && (
            <p className="mt-1 text-[0.88em] text-slate-600">
              {[ev.venue, ev.price_text].filter(Boolean).join(" ／ ")}
            </p>
          )}
          {ev.description && (
            <p className="mt-2 whitespace-pre-wrap text-[0.9em] leading-relaxed text-slate-700">{ev.description}</p>
          )}
        </li>
      ))}
    </ul>
  );
}

const SHARE_KIND: Record<Share["kind"], string> = {
  notice: "お知らせ",
  document: "資料",
  link: "リンク",
  question: "質問",
};

export function SharesPanel({ reloadKey }: { reloadKey: number }) {
  const { items, error } = useList<Share>(listShares, reloadKey);
  if (error) return <Err text={error} />;
  if (items.length === 0) return <Empty text="共有された資料・お知らせはまだありません。" />;
  return (
    <ul className="mx-auto max-w-[44rem] space-y-3">
      {items.map((s) => (
        <li key={s.id} className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <div className="flex flex-wrap items-center gap-2 text-[0.8em] text-slate-500">
            <span className="rounded bg-slate-100 px-2 py-0.5 font-semibold text-slate-600">{SHARE_KIND[s.kind]}</span>
            <span>{formatDateTimeJa(s.created_at)}</span>
            {s.kind === "question" && !s.answered_at && (
              <span className="rounded bg-amber-50 px-2 py-0.5 font-semibold text-amber-800">お返事待ち</span>
            )}
          </div>
          <p className="mt-1 text-[1.02em] font-semibold text-brand-ink">{s.title}</p>
          {s.body && <p className="mt-2 whitespace-pre-wrap text-[0.9em] leading-relaxed text-slate-700">{s.body}</p>}
          {s.url && (
            <a
              href={s.url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-[0.9em] font-semibold text-brand-ocean underline"
            >
              開く
            </a>
          )}
        </li>
      ))}
    </ul>
  );
}
