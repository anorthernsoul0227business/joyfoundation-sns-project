"use client";

import { useEffect, useState } from "react";
import {
  announceState,
  approveBy,
  decideArticle,
  formatDateJa,
  loadArticleDetail,
  PENDING_STATUSES,
  PLATFORM_LABEL,
  STATUS_LABEL,
  type Article,
  type Attachment,
} from "../../lib/board";

/**
 * カレンダーの横で、記事をその場で読んで判断するための小窓。
 *
 * 2026-09-30 康二郎さん: カレンダーから記事を開くと確認ページに移ってしまい、
 * カレンダーに戻りにくい。カレンダーを見たまま確認できるようにする。
 */
export function ArticlePeek({
  article,
  userId,
  onUpdated,
  onClose,
  onOpenFull,
}: {
  article: Article;
  userId: string;
  onUpdated: (a: Article) => void;
  onClose: () => void;
  onOpenFull: () => void;
}) {
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [busy, setBusy] = useState<"approve" | "request_fix" | null>(null);
  const [fixOpen, setFixOpen] = useState(false);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setFixOpen(false);
    setNote("");
    setError(null);
    setDone(null);
    loadArticleDetail(article.id)
      .then((d) => {
        if (!cancelled) setAttachments(d.attachments);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [article.id]);

  const body = article.body_final ?? article.body_ai;
  const pending = PENDING_STATUSES.includes(article.status);
  const by = approveBy(article);

  async function decide(decision: "approve" | "request_fix") {
    setBusy(decision);
    setError(null);
    try {
      const next = await decideArticle({ article, decision, note, userId });
      onUpdated(next);
      setDone(
        decision === "approve"
          ? `OKを受け付けました。${formatDateJa(next.scheduled_date)}に投稿されます。`
          : "康二郎さんに届きました。直したものをまたお見せします。",
      );
      setFixOpen(false);
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <aside className="rounded border border-slate-200 bg-white shadow-sm">
      <div className="flex items-start gap-2 border-b border-slate-200 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="flex flex-wrap items-center gap-2 text-[0.78em] text-slate-500">
            <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono font-semibold text-slate-700">
              {article.article_no}
            </span>
            <span className="font-semibold text-slate-600">
              {PLATFORM_LABEL[article.platform]}
            </span>
            <span>{STATUS_LABEL[article.status]}</span>
          </p>
          <p className="mt-1 text-[1em] font-semibold text-brand-ink">{article.title}</p>
          {article.scheduled_date && (
            <p className="mt-1 text-[0.82em] text-slate-500">
              {formatDateJa(article.scheduled_date)}に投稿
              {announceState(article) === "waiting" && by && (
                <span className="ml-1 font-semibold text-amber-800">
                  （{formatDateJa(by)}までに承認を）
                </span>
              )}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="閉じる"
          className="shrink-0 rounded px-2 py-1 text-[1.1em] text-slate-400 transition hover:bg-slate-100"
        >
          ×
        </button>
      </div>

      <div className="max-h-[22rem] overflow-y-auto px-4 py-3">
        <p className="whitespace-pre-wrap break-words text-[0.95em] leading-[1.9] text-brand-ink">
          {body}
        </p>
        {attachments.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {attachments.map((at) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={at.id}
                src={at.public_url}
                alt={at.caption ?? ""}
                className="max-h-32 rounded object-contain"
                loading="lazy"
              />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 px-4 py-3">
        {done ? (
          <p className="rounded bg-brand-ocean/10 px-3 py-2 text-[0.9em] font-semibold text-brand-ocean">
            {done}
          </p>
        ) : pending ? (
          <>
            <div className="flex flex-col gap-2 md:flex-row">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => decide("approve")}
                className="w-full rounded-md bg-brand-ocean px-5 py-3 text-[0.98em] font-semibold text-white transition hover:brightness-110 disabled:opacity-60 md:w-auto"
              >
                {busy === "approve" ? "送っています…" : "このまま出す"}
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => setFixOpen((v) => !v)}
                className="w-full rounded-md border border-amber-700 bg-white px-5 py-3 text-[0.98em] font-semibold text-amber-800 transition hover:bg-amber-50 disabled:opacity-60 md:w-auto"
              >
                直したいところがある
              </button>
            </div>
            {fixOpen && (
              <div className="mt-2">
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={3}
                  placeholder="気になったところを、ふだんの言葉でお書きください。"
                  className="w-full rounded border border-slate-200 bg-brand-sand/40 px-3 py-2 text-[0.95em] outline-none focus:border-brand-ocean focus:bg-white"
                />
                <button
                  type="button"
                  disabled={busy !== null || note.trim() === ""}
                  onClick={() => decide("request_fix")}
                  className="mt-2 w-full rounded-md bg-brand-ink px-5 py-2.5 font-semibold text-white transition hover:opacity-90 disabled:opacity-50 md:w-auto"
                >
                  {busy === "request_fix" ? "送っています…" : "これで送る"}
                </button>
              </div>
            )}
          </>
        ) : (
          <p className="text-[0.9em] text-slate-600">
            この記事は「{STATUS_LABEL[article.status]}」です。
          </p>
        )}

        <button
          type="button"
          onClick={onOpenFull}
          className="mt-3 text-[0.85em] text-slate-500 underline transition hover:text-slate-700"
        >
          記事の画面でくわしく見る
        </button>
        {error && <p className="mt-2 text-[0.85em] text-rose-700">{error}</p>}
      </div>
    </aside>
  );
}
