"use client";

/**
 * 共有ボードのデータアクセス。
 *
 * supabase/migrations/20260901190000_shared_board.sql のテーブルを
 * ブラウザから直接読み書きする（RLS がユーザーの org で絞る）。
 */
import { requireSupabaseClient } from "./supabase";

// ---- 型（マイグレーションの列と1対1） ------------------------------------

export type Platform = "x" | "ig" | "note" | "youtube" | "line";

export type ArticleStatus =
  | "ai_draft"
  | "needs_check"
  | "staff_ok"
  | "approved"
  | "needs_fix"
  | "revised"
  | "scheduled"
  | "published"
  | "missed";

export interface Article {
  id: string;
  org_id: string;
  article_no: string;
  week: string | null;
  platform: Platform;
  scheduled_date: string | null;
  grade: "A" | "B" | "C" | null;
  source_card_ids: string[];
  title: string;
  body_ai: string;
  body_final: string | null;
  status: ArticleStatus;
  fix_note: string | null;
  /** AI から圭一郎さんへの申し送り（字数のため指示外を変えた、など） */
  revision_note: string | null;
  fix_type: string | null;
  fix_apply: "permanent" | "once" | "none" | null;
  image_reason: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  published_at: string | null;
  /** 本文が触れているイベント開催日。過ぎたら投稿しない */
  event_date: string | null;
  /** 投稿予定の日時 */
  scheduled_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ArticleReview {
  id: string;
  article_id: string;
  reviewer_user_id: string | null;
  decision: "approve" | "request_fix";
  note: string | null;
  created_at: string;
}

export interface Attachment {
  id: string;
  owner_type: "article" | "event" | "share" | "idea";
  owner_id: string;
  public_url: string;
  mime_type: string;
  width: number | null;
  height: number | null;
  sort_order: number;
  caption: string | null;
}

export interface Idea {
  id: string;
  body: string;
  source: "web" | "voice" | "mail" | "line";
  status: "new" | "read" | "used" | "holding";
  linked_article_id: string | null;
  created_at: string;
}

export interface EventItem {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  venue: string | null;
  price_text: string | null;
  url: string | null;
  description: string | null;
  confirmed_by_owner: boolean;
}

export interface Share {
  id: string;
  kind: "notice" | "document" | "link" | "question";
  title: string;
  body: string | null;
  url: string | null;
  answered_at: string | null;
  created_at: string;
}

// ---- 表示用の言葉 ----------------------------------------------------------

export const PLATFORM_LABEL: Record<Platform, string> = {
  x: "X",
  ig: "Instagram",
  note: "note",
  youtube: "YouTube",
  line: "LINE",
};

export const STATUS_LABEL: Record<ArticleStatus, string> = {
  ai_draft: "未確認",
  needs_check: "未確認",
  staff_ok: "未確認",
  approved: "OKしました",
  needs_fix: "直してもらっています",
  revised: "直しました",
  scheduled: "投稿予約",
  published: "投稿済",
  missed: "間に合いませんでした",
};

/** 圭一郎さんの判断を待っている状態 */
export const PENDING_STATUSES: ArticleStatus[] = [
  "ai_draft",
  "needs_check",
  "staff_ok",
  "revised", // AI が直したものの確認も、圭一郎さんの「未対応」に含める
];

export type ArticleFilter = "pending" | "week" | "all";

// ---- 記事 ------------------------------------------------------------------

const ARTICLE_COLUMNS =
  "id, org_id, article_no, week, platform, scheduled_date, grade, source_card_ids, title, " +
  "body_ai, body_final, status, fix_note, revision_note, fix_type, fix_apply, image_reason, reviewed_by, " +
  "reviewed_at, published_at, event_date, scheduled_at, created_at, updated_at";

function isoWeek(d: Date): string {
  // 週次ループと同じ ISO 週表記（例: 2026-W36）
  const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((date.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

export async function listArticles(filter: ArticleFilter): Promise<Article[]> {
  const supabase = requireSupabaseClient();
  let query = supabase
    .from("articles")
    .select(ARTICLE_COLUMNS)
    .order("scheduled_date", { ascending: true, nullsFirst: false })
    .order("created_at", { ascending: false });

  if (filter === "pending") {
    query = query.in("status", PENDING_STATUSES);
  } else if (filter === "week") {
    query = query.eq("week", isoWeek(new Date()));
  } else {
    query = query.limit(200);
  }

  const { data, error } = await query;
  if (error) {
    throw new Error(error.message);
  }
  return (data ?? []) as unknown as Article[];
}

export async function loadArticleDetail(articleId: string): Promise<{
  reviews: ArticleReview[];
  attachments: Attachment[];
}> {
  const supabase = requireSupabaseClient();
  const [reviews, attachments] = await Promise.all([
    supabase
      .from("article_reviews")
      .select("id, article_id, reviewer_user_id, decision, note, created_at")
      .eq("article_id", articleId)
      .order("created_at", { ascending: false }),
    supabase
      .from("attachments")
      .select("id, owner_type, owner_id, public_url, mime_type, width, height, sort_order, caption")
      .eq("owner_type", "article")
      .eq("owner_id", articleId)
      .order("sort_order", { ascending: true }),
  ]);
  if (reviews.error) throw new Error(reviews.error.message);
  if (attachments.error) throw new Error(attachments.error.message);
  return {
    reviews: (reviews.data ?? []) as ArticleReview[],
    attachments: (attachments.data ?? []) as Attachment[],
  };
}

/**
 * 圭一郎さんの判断を記録する。
 *
 * 履歴（article_reviews）を先に書き、次に articles.status を更新する。
 * ブラウザからはトランザクションが張れないため、2つ目が失敗した場合は
 * 履歴だけ残った状態になりうる。その場合は status が古いまま一覧に残るので
 * 再度押せば直る（履歴が重複するだけで実害はない）。
 */
export async function decideArticle(params: {
  article: Article;
  decision: "approve" | "request_fix";
  note: string;
  userId: string;
}): Promise<Article> {
  const { article, decision, note, userId } = params;
  const supabase = requireSupabaseClient();
  const trimmed = note.trim();

  if (decision === "request_fix" && !trimmed) {
    throw new Error("直したいところを書いてください。");
  }

  const { error: reviewError } = await supabase.from("article_reviews").insert({
    org_id: article.org_id,
    article_id: article.id,
    reviewer_user_id: userId,
    decision,
    note: trimmed || null,
    body_snapshot: article.body_final ?? article.body_ai,
  });
  if (reviewError) {
    throw new Error(reviewError.message);
  }

  const now = new Date().toISOString();
  const patch =
    decision === "approve"
      ? {
          status: "approved",
          fix_note: null,
          // 申し送りは承諾された時点で役目を終える
          revision_note: null,
          reviewed_by: userId,
          reviewed_at: now,
        }
      : {
          status: "needs_fix",
          fix_note: trimmed,
          // 直しをやり直すので、前回 AI が直した本文と申し送りは捨てる
          body_final: null,
          revision_note: null,
          reviewed_by: userId,
          reviewed_at: now,
        };

  const { data, error } = await supabase
    .from("articles")
    .update(patch)
    .eq("id", article.id)
    .select(ARTICLE_COLUMNS)
    .single();
  if (error) {
    throw new Error(error.message);
  }
  return data as unknown as Article;
}

// ---- 思いつきメモ ----------------------------------------------------------

export async function listIdeas(): Promise<Idea[]> {
  const supabase = requireSupabaseClient();
  const { data, error } = await supabase
    .from("ideas")
    .select("id, body, source, status, linked_article_id, created_at")
    .order("created_at", { ascending: false })
    .limit(100);
  if (error) throw new Error(error.message);
  return (data ?? []) as Idea[];
}

export async function createIdea(params: { orgId: string; userId: string; body: string }): Promise<Idea> {
  const body = params.body.trim();
  if (!body) {
    throw new Error("何か一言だけでも書いてください。");
  }
  const supabase = requireSupabaseClient();
  const { data, error } = await supabase
    .from("ideas")
    .insert({ org_id: params.orgId, author_user_id: params.userId, body, source: "web" })
    .select("id, body, source, status, linked_article_id, created_at")
    .single();
  if (error) throw new Error(error.message);
  return data as Idea;
}

// ---- イベント・共有（初版は読むだけ） ---------------------------------------

export async function listEvents(): Promise<EventItem[]> {
  const supabase = requireSupabaseClient();
  const since = new Date();
  since.setDate(since.getDate() - 7);
  const { data, error } = await supabase
    .from("events")
    .select("id, title, starts_at, ends_at, all_day, venue, price_text, url, description, confirmed_by_owner")
    .gte("starts_at", since.toISOString())
    .order("starts_at", { ascending: true })
    .limit(100);
  if (error) throw new Error(error.message);
  return (data ?? []) as EventItem[];
}

export async function listShares(): Promise<Share[]> {
  const supabase = requireSupabaseClient();
  const { data, error } = await supabase
    .from("shares")
    .select("id, kind, title, body, url, answered_at, created_at")
    .order("created_at", { ascending: false })
    .limit(100);
  if (error) throw new Error(error.message);
  return (data ?? []) as Share[];
}

// ---- 日付の見せ方 ----------------------------------------------------------

const WEEKDAY = ["日", "月", "火", "水", "木", "金", "土"];

/** "2026-09-03" → "9月3日（水）" */
export function formatDateJa(value: string | null): string {
  if (!value) return "日付未定";
  const d = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return value;
  return `${d.getMonth() + 1}月${d.getDate()}日（${WEEKDAY[d.getDay()]}）`;
}

export function formatDateTimeJa(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${formatDateJa(value)} ${hh}:${mm}`;
}
