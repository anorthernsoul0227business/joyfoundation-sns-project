"use client";

import { useEffect, useState } from "react";
import {
  decideArticle,
  editArticleBody,
  formatDateJa,
  formatDateTimeJa,
  loadArticleDetail,
  PENDING_STATUSES,
  PLATFORM_LABEL,
  type Article,
  type ArticleReview,
  type Attachment,
} from "../../lib/board";
import { requireSupabaseClient } from "../../lib/supabase";
import { BodyDiff } from "./BodyDiff";
import { ImageUpload } from "./ImageUpload";
import { StatusBadge } from "./StatusBadge";

const GRADE_LABEL: Record<"A" | "B" | "C", string> = {
  A: "A：確認済みの資料の言いかえのみ",
  B: "B：新しい組み合わせ・解釈を含む",
  C: "C：新しい数値・ニュース・医療的な表現を含む",
};

export function ArticleDetail({
  article,
  userId,
  orgId,
  onUpdated,
  onBack,
}: {
  article: Article;
  userId: string;
  orgId: string | null;
  onUpdated: (next: Article) => void;
  /** 狭い画面のときだけ渡す。一覧に戻る */
  onBack?: () => void;
}) {
  const [reviews, setReviews] = useState<ArticleReview[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [fixOpen, setFixOpen] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "request_fix" | "edit" | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setFixOpen(false);
    setNote("");
    setEditOpen(false);
    setError(null);
    setDone(null);
    loadArticleDetail(article.id)
      .then((d) => {
        if (cancelled) return;
        setReviews(d.reviews);
        setAttachments(d.attachments);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [article.id]);

  const pending = PENDING_STATUSES.includes(article.status);
  const isRevised = article.status === "revised" && article.body_final !== null;
  const body = article.body_final ?? article.body_ai;
  const [showDiff, setShowDiff] = useState(true);
  const charCount = body.replace(/\s/g, "").length;

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

  /** 写真を記事から外す。保管してある実体も一緒に消える */
  async function removeImage(at: Attachment) {
    if (!window.confirm("この写真を消しますか。")) return;
    setRemoving(at.id);
    setError(null);
    try {
      const supabase = requireSupabaseClient();
      const { data: sess } = await supabase.auth.getSession();
      const res = await fetch("/api/uploads", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${sess.session?.access_token ?? ""}`,
        },
        body: JSON.stringify({ attachmentId: at.id }),
      });
      const info = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(info.error ?? "写真を消せませんでした。");
      setAttachments((prev) => prev.filter((x) => x.id !== at.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRemoving(null);
    }
  }

  async function saveEdit() {
    setBusy("edit");
    setError(null);
    try {
      const next = await editArticleBody({ article, body: draft, userId });
      onUpdated(next);
      setDone("直した内容で承ります。ありがとうございます。");
      setEditOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const overLimit =
    article.platform === "x" && draft.replace(/\s/g, "").length > 140;

  return (
    <div className="mx-auto max-w-[44rem]">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="mb-3 -ml-1 rounded-md px-2 py-1.5 text-[0.9em] font-semibold text-brand-ocean transition hover:bg-brand-ocean/10"
        >
          ← 一覧にもどる
        </button>
      )}
      <h1 className="mb-1 text-[1.3em] font-semibold leading-snug text-brand-ink">
        {PLATFORM_LABEL[article.platform]}
        {article.scheduled_at
          ? ` ／ ${formatDateTimeJa(article.scheduled_at)}に投稿します`
          : article.status === "missed"
            ? " ／ 投稿は見送りました"
            : " ／ 投稿日はこれから決まります"}
      </h1>
      <p className="mb-6 flex flex-wrap items-center gap-3 text-[0.82em] text-slate-500">
        <span>記事番号 {article.article_no}</span>
        <StatusBadge status={article.status} />
      </p>

      {article.event_date && (
        <div className="mb-4 rounded border border-brand-ocean/30 bg-brand-ocean/5 px-5 py-3 text-[0.92em] text-brand-ocean">
          <strong>{formatDateJa(article.event_date)}</strong>のイベントの記事です。
          {article.scheduled_at
            ? "開催日より前に投稿されます。"
            : "開催日に間に合うように投稿日を決めます。"}
        </div>
      )}

      {article.status === "missed" && (
        <div className="mb-4 rounded border border-slate-300 bg-slate-100 px-5 py-4 text-[0.95em] text-slate-700">
          <div className="mb-1 font-semibold">この記事は投稿を見送りました</div>
          <p>
            {article.event_date ? `${formatDateJa(article.event_date)}の` : ""}
            開催日までに投稿できる日が取れませんでした。
            日が過ぎてからの告知は出さないようにしています。
          </p>
        </div>
      )}

      {article.status === "needs_owner_input" && article.revision_note && (
        <div className="mb-4 rounded border-2 border-amber-400 bg-amber-50 px-5 py-4">
          <div className="mb-1 text-[0.8em] font-semibold tracking-wider text-amber-900">
            確認させてください
          </div>
          <p className="whitespace-pre-wrap text-[1em] leading-relaxed text-amber-900">
            {article.revision_note}
          </p>
          <p className="mt-2 text-[0.85em] text-amber-800">
            下の「直したいところがある」に、あらためてお書きいただけますか。
            そのままでよければ「このまま出す」でも大丈夫です。
          </p>
        </div>
      )}

      {isRevised && article.revision_note && (
        <div className="mb-4 rounded border-2 border-amber-300 bg-amber-50 px-5 py-4">
          <div className="mb-1 text-[0.8em] font-semibold tracking-wider text-amber-900">
            お尋ねしたいことがあります
          </div>
          <p className="whitespace-pre-wrap text-[1em] leading-relaxed text-amber-900">
            {article.revision_note}
          </p>
          <p className="mt-2 text-[0.85em] text-amber-800">
            これでよければ下の「このまま出す」を、違うときは「直したいところがある」をお使いください。
          </p>
        </div>
      )}

      {isRevised ? (
        <>
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              type="button"
              aria-pressed={showDiff}
              onClick={() => setShowDiff(true)}
              className={
                "rounded-full border px-4 py-1.5 text-[0.85em] transition " +
                (showDiff
                  ? "border-brand-ink bg-brand-ink text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")
              }
            >
              直したところ
            </button>
            <button
              type="button"
              aria-pressed={!showDiff}
              onClick={() => setShowDiff(false)}
              className={
                "rounded-full border px-4 py-1.5 text-[0.85em] transition " +
                (!showDiff
                  ? "border-brand-ink bg-brand-ink text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")
              }
            >
              直したあとの全文
            </button>
          </div>
          {showDiff ? (
            <BodyDiff before={article.body_ai} after={body} />
          ) : (
            <div className="whitespace-pre-wrap break-words rounded border border-slate-200 bg-white px-4 py-5 text-[1.02em] leading-[1.95] shadow-sm md:px-8 md:py-7 md:leading-[2.05]">
              {body}
            </div>
          )}
        </>
      ) : (
        <div className="whitespace-pre-wrap break-words rounded border border-slate-200 bg-white px-4 py-5 text-[1.02em] leading-[1.95] shadow-sm md:px-8 md:py-7 md:leading-[2.05]">
          {body}
        </div>
      )}

      <div className="mt-5 rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div className="mb-2 text-[0.78em] tracking-wider text-slate-500">いっしょに出す写真</div>
        {attachments.length > 0 ? (
          <div className="flex flex-wrap gap-3">
            {attachments.map((at) => (
              <figure key={at.id} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={at.public_url}
                  alt={at.caption ?? ""}
                  className="max-h-60 max-w-full rounded object-contain"
                  loading="lazy"
                />
                <button
                  type="button"
                  disabled={removing !== null}
                  onClick={() => void removeImage(at)}
                  aria-label="この写真を消す"
                  className="absolute right-1.5 top-1.5 rounded-full bg-white/90 px-3 py-1.5 text-[0.8em] font-semibold text-rose-700 shadow transition hover:bg-white disabled:opacity-50"
                >
                  {removing === at.id ? "消しています…" : "消す"}
                </button>
              </figure>
            ))}
          </div>
        ) : (
          <p className="text-[0.9em] text-slate-500">まだ写真はありません。</p>
        )}
        {orgId && (
          <ImageUpload
            orgId={orgId}
            articleId={article.id}
            onUploaded={(added) => setAttachments((prev) => [...prev, added])}
          />
        )}
      </div>

      {isRevised && (
        <p className="mt-4 text-[0.85em] text-slate-500">
          ご指示にそって直しました。よろしければ「このまま出す」をお願いします。
        </p>
      )}

      {article.status === "needs_fix" && article.fix_note && (
        <div className="mt-5 rounded border border-rose-200 bg-rose-50 px-5 py-4 text-[0.92em] text-rose-900">
          <div className="mb-1 text-[0.8em] font-semibold tracking-wider">お書きいただいた直したいところ</div>
          <p className="whitespace-pre-wrap">{article.fix_note}</p>
        </div>
      )}

      <details className="mt-5 rounded border border-slate-200 bg-white">
        <summary className="cursor-pointer list-none px-5 py-3 text-[0.88em] text-slate-600">
          ▸ くわしい情報（ふだんは見なくて大丈夫です）
        </summary>
        <dl className="grid grid-cols-1 gap-x-4 gap-y-1 px-5 pb-5 pt-1 text-[0.88em] md:grid-cols-[8.5rem_minmax(0,1fr)] md:gap-y-2">
          {article.source_card_ids.length > 0 && (
            <>
              <dt className="mt-2 text-slate-500 md:mt-0">もとにした資料</dt>
              <dd className="break-words text-slate-700">{article.source_card_ids.join("、")}</dd>
            </>
          )}
          {article.image_reason && (
            <>
              <dt className="mt-2 text-slate-500 md:mt-0">写真を選んだ理由</dt>
              <dd className="break-words text-slate-700">{article.image_reason}</dd>
            </>
          )}
          {article.grade && (
            <>
              <dt className="mt-2 text-slate-500 md:mt-0">分級</dt>
              <dd className="text-slate-700">{GRADE_LABEL[article.grade]}</dd>
            </>
          )}
          <dt className="mt-2 text-slate-500 md:mt-0">文字数</dt>
          <dd className="text-slate-700">{charCount}文字</dd>
          <dt className="mt-2 text-slate-500 md:mt-0">作成</dt>
          <dd className="text-slate-700">{formatDateTimeJa(article.created_at)}</dd>
          {reviews.length > 0 && (
            <>
              <dt className="mt-2 text-slate-500 md:mt-0">これまでのやりとり</dt>
              <dd className="text-slate-700">
                <ul className="space-y-1">
                  {reviews.map((r) => (
                    <li key={r.id}>
                      {formatDateTimeJa(r.created_at)}：
                      {r.decision === "approve" ? "OK" : "直したいところあり"}
                      {r.note ? `（${r.note}）` : ""}
                    </li>
                  ))}
                </ul>
              </dd>
            </>
          )}
        </dl>
      </details>

      <section className="mt-6 rounded border border-slate-200 bg-white px-4 py-5 shadow-sm md:mt-7 md:px-7 md:py-6">
        <h2 className="mb-4 text-[0.72em] font-semibold tracking-[0.14em] text-slate-500">どうしますか</h2>

        {done ? (
          <p className="rounded bg-brand-ocean/10 px-4 py-3 text-[0.98em] font-semibold text-brand-ocean">{done}</p>
        ) : !pending ? (
          <p className="text-[0.92em] text-slate-600">
            この記事は「{article.status === "needs_fix" ? "直しています。しばらくお待ちください" : "確認ずみ"}」です。
            変えたいときは康二郎さんにお知らせください。
          </p>
        ) : (
          <>
            <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:gap-4">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => decide("approve")}
                className="w-full rounded-md bg-brand-ocean px-8 py-4 text-[1.05em] font-semibold text-white transition hover:brightness-110 disabled:opacity-60 md:w-auto md:min-w-[13rem]"
              >
                {busy === "approve" ? "送っています…" : "このまま出す"}
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => setFixOpen((v) => !v)}
                aria-expanded={fixOpen}
                className="w-full rounded-md border border-amber-700 bg-white px-8 py-4 text-[1.05em] font-semibold text-amber-800 transition hover:bg-amber-50 disabled:opacity-60 md:w-auto md:min-w-[13rem]"
              >
                直したいところがある
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => {
                  setDraft(body);
                  setEditOpen((v) => !v);
                  setFixOpen(false);
                }}
                aria-expanded={editOpen}
                className="w-full rounded-md border border-slate-300 bg-white px-8 py-4 text-[1.05em] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60 md:w-auto md:min-w-[13rem]"
              >
                自分で直す
              </button>
            </div>

            {editOpen && (
              <div className="mt-4">
                <p className="mb-2 text-[0.82em] text-slate-500">
                  本文をそのまま書き換えてください。直したら「これで出す」を押すと、
                  その文で投稿します。
                </p>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={16}
                  className="w-full rounded border border-slate-200 bg-white px-4 py-3 text-[0.98em] leading-[1.9] text-brand-ink outline-none focus:border-brand-ocean"
                />
                <div className="mt-2 flex flex-wrap items-center gap-3 text-[0.82em]">
                  <span className={overLimit ? "font-semibold text-rose-700" : "text-slate-500"}>
                    {draft.replace(/\s/g, "").length}文字
                    {article.platform === "x" && "（Xは140文字まで）"}
                  </span>
                  {overLimit && (
                    <span className="text-rose-700">
                      140文字を超えています。このままでは投稿できません。
                    </span>
                  )}
                </div>
                <button
                  type="button"
                  disabled={busy !== null || draft.trim() === "" || overLimit}
                  onClick={saveEdit}
                  className="mt-3 w-full rounded-md bg-brand-ocean px-6 py-3 font-semibold text-white transition hover:brightness-110 disabled:opacity-50 md:w-auto"
                >
                  {busy === "edit" ? "送っています…" : "これで出す"}
                </button>
              </div>
            )}

            {fixOpen && (
              <div className="mt-4">
                <p className="mb-2 text-[0.82em] text-slate-500">
                  気になったところだけ、ふつうの言葉でお書きください。分類や記号は不要です。
                </p>
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={5}
                  placeholder={"例：「治すものではありません」は、もう少しやわらかく言いたい。\n例：9名だと少なく見えるので、人数は書かないでほしい。"}
                  className="w-full rounded border border-slate-200 bg-brand-sand/40 px-4 py-3 text-[0.98em] leading-relaxed text-brand-ink outline-none focus:border-brand-ocean focus:bg-white"
                />
                <button
                  type="button"
                  disabled={busy !== null || note.trim() === ""}
                  onClick={() => decide("request_fix")}
                  className="mt-3 w-full rounded-md bg-brand-ink px-6 py-3 font-semibold text-white transition hover:opacity-90 disabled:opacity-50 md:w-auto"
                >
                  {busy === "request_fix" ? "送っています…" : "これで送る"}
                </button>
              </div>
            )}
          </>
        )}

        {error && <p className="mt-3 text-[0.88em] text-rose-700">{error}</p>}
      </section>
    </div>
  );
}
