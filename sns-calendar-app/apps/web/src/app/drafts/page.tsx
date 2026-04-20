"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { PostListResponse, PostResponse } from "../../generated/types.gen";
import { HelpMark } from "../../components/HelpMark";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import { createPost, deletePost, fetchPostList } from "../../lib/api-client";

type PlatformValue = "x" | "ig" | "note" | "youtube" | "line";
type StatusValue = PostResponse["status"];
type StatusTab = "all" | "draft" | "scheduled" | "published" | "failed";
type SortValue = "updated_desc" | "created_desc" | "scheduled_asc";

const PLATFORM_OPTIONS: Array<{ label: string; shortLabel: string; value: PlatformValue }> = [
  { label: "X", shortLabel: "X", value: "x" },
  { label: "Instagram", shortLabel: "IG", value: "ig" },
  { label: "YouTube", shortLabel: "YT", value: "youtube" },
  { label: "note", shortLabel: "note", value: "note" },
  { label: "LINE", shortLabel: "LINE", value: "line" },
];

const PLATFORM_STYLES: Record<PlatformValue, string> = {
  x: "bg-x text-white",
  ig: "bg-ig text-white",
  line: "bg-line text-white",
  note: "bg-note text-white",
  youtube: "bg-yt text-white",
};

const STATUS_LABELS: Record<StatusValue, string> = {
  archived: "アーカイブ",
  draft: "下書き",
  failed: "失敗",
  published: "公開済み",
  publishing: "公開中",
  scheduled: "予約済み",
};

const STATUS_STYLES: Record<StatusValue, string> = {
  archived: "bg-slate-100 text-slate-500",
  draft: "bg-brand-sand text-brand-ink",
  failed: "bg-rose-100 text-rose-700",
  published: "bg-emerald-100 text-emerald-700",
  publishing: "bg-amber-100 text-amber-700",
  scheduled: "bg-brand-ocean/10 text-brand-ocean",
};

const STATUS_TABS: Array<{ value: StatusTab; label: string }> = [
  { value: "all", label: "すべて" },
  { value: "draft", label: "下書き" },
  { value: "scheduled", label: "予約済み" },
  { value: "published", label: "公開済み" },
  { value: "failed", label: "失敗" },
];

const DEFAULT_PLATFORMS = PLATFORM_OPTIONS.map((option) => option.value);

function getPostPlatforms(post: PostResponse) {
  return Array.from(new Set((post.targets ?? []).map((target) => target.platform)));
}

function truncateText(text: string, maxLength: number) {
  return text.length <= maxLength ? text : `${text.slice(0, maxLength)}...`;
}

function formatRelativeTime(value: string) {
  const target = new Date(value);
  const diffMs = target.getTime() - Date.now();
  const diffMinutes = Math.round(diffMs / (1000 * 60));
  const absMinutes = Math.abs(diffMinutes);

  if (absMinutes < 1) {
    return "たった今";
  }

  if (absMinutes < 60) {
    return diffMinutes > 0 ? `${absMinutes}分後` : `${absMinutes}分前`;
  }

  const diffHours = Math.round(absMinutes / 60);
  if (diffHours < 24) {
    return diffMinutes > 0 ? `${diffHours}時間後` : `${diffHours}時間前`;
  }

  if (diffHours < 48) {
    return diffMinutes > 0 ? "明日" : "昨日";
  }

  const diffDays = Math.round(diffHours / 24);
  if (diffDays < 7) {
    return diffMinutes > 0 ? `${diffDays}日後` : `${diffDays}日前`;
  }

  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(target);
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未設定";
  }

  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function sortPosts(posts: Array<PostResponse>, sortValue: SortValue) {
  const sorted = [...posts];

  sorted.sort((left, right) => {
    if (sortValue === "updated_desc") {
      return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
    }

    if (sortValue === "created_desc") {
      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
    }

    const leftScheduled = left.scheduled_at ? new Date(left.scheduled_at).getTime() : Number.MAX_SAFE_INTEGER;
    const rightScheduled = right.scheduled_at
      ? new Date(right.scheduled_at).getTime()
      : Number.MAX_SAFE_INTEGER;

    if (leftScheduled !== rightScheduled) {
      return leftScheduled - rightScheduled;
    }

    return new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime();
  });

  return sorted;
}

export default function DraftsPage() {
  const { isReady } = useAuthGuard();
  const [posts, setPosts] = useState<Array<PostResponse>>([]);
  const [total, setTotal] = useState(0);
  const [statusTab, setStatusTab] = useState<StatusTab>("all");
  const [selectedPlatforms, setSelectedPlatforms] =
    useState<Array<PlatformValue>>(DEFAULT_PLATFORMS);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sortValue, setSortValue] = useState<SortValue>("updated_desc");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [pendingPostId, setPendingPostId] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim().toLowerCase());
    }, 300);

    return () => {
      window.clearTimeout(timer);
    };
  }, [searchInput]);

  useEffect(() => {
    if (!actionMessage) {
      return;
    }

    const timer = window.setTimeout(() => {
      setActionMessage(null);
    }, 4000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [actionMessage]);

  useEffect(() => {
    if (!isReady) {
      return;
    }

    let active = true;

    setIsLoading(true);
    setErrorMessage(null);

    fetchPostList({ limit: 200, offset: 0 })
      .then((response: PostListResponse) => {
        if (!active) {
          return;
        }

        setPosts(response.items);
        setTotal(response.total);
        setIsLoaded(true);
      })
      .catch(() => {
        if (!active) {
          return;
        }

        setErrorMessage("下書き一覧の取得に失敗しました。時間をおいて再試行してください。");
        setIsLoaded(true);
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [isReady, reloadKey]);

  const counts = useMemo(() => {
    const base = {
      all: posts.length,
      draft: 0,
      failed: 0,
      published: 0,
      scheduled: 0,
    };

    posts.forEach((post) => {
      if (post.status === "draft") {
        base.draft += 1;
      }
      if (post.status === "scheduled") {
        base.scheduled += 1;
      }
      if (post.status === "published") {
        base.published += 1;
      }
      if (post.status === "failed") {
        base.failed += 1;
      }
    });

    return base;
  }, [posts]);

  const visiblePosts = useMemo(() => {
    const filtered = posts.filter((post) => {
      if (statusTab !== "all" && post.status !== statusTab) {
        return false;
      }

      const platforms = getPostPlatforms(post);
      if (
        selectedPlatforms.length > 0 &&
        platforms.length > 0 &&
        !platforms.some((platform) => selectedPlatforms.includes(platform))
      ) {
        return false;
      }

      if (selectedPlatforms.length === 0) {
        return false;
      }

      if (!debouncedSearch) {
        return true;
      }

      return post.content_text.toLowerCase().includes(debouncedSearch);
    });

    return sortPosts(filtered, sortValue);
  }, [debouncedSearch, posts, selectedPlatforms, sortValue, statusTab]);

  function reloadList() {
    setReloadKey((current) => current + 1);
  }

  function togglePlatform(platform: PlatformValue) {
    setSelectedPlatforms((current) =>
      current.includes(platform)
        ? current.filter((item) => item !== platform)
        : [...current, platform],
    );
  }

  async function handleDelete(post: PostResponse) {
    const confirmed = window.confirm("この投稿を削除しますか？この操作は取り消せません。");
    if (!confirmed) {
      return;
    }

    setPendingPostId(post.id);
    setActionMessage(null);

    try {
      await deletePost(post.id);
      setPosts((current) => current.filter((item) => item.id !== post.id));
      setTotal((current) => Math.max(current - 1, 0));
      setActionMessage("投稿を削除しました。");
    } catch {
      setActionMessage("削除に失敗しました。もう一度お試しください。");
    } finally {
      setPendingPostId(null);
    }
  }

  async function handleDuplicate(post: PostResponse) {
    setPendingPostId(post.id);
    setActionMessage(null);

    try {
      await createPost({
        content_text: post.content_text,
        platforms: getPostPlatforms(post),
        status: "draft",
      });
      reloadList();
      setActionMessage("投稿を複製しました。");
    } catch {
      setActionMessage("複製に失敗しました。もう一度お試しください。");
    } finally {
      setPendingPostId(null);
    }
  }

  if (!isReady) {
    return (
      <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-brand-sand px-6">
        <div className="rounded-3xl border border-brand-ink/10 bg-white px-6 py-4 text-sm text-slate-500 shadow-sm">
          下書き一覧を準備しています...
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-7xl">
        <section className="rounded-[2rem] border border-brand-ink/10 bg-white/90 p-5 shadow-xl shadow-brand-ink/5 sm:p-6">
          <div className="flex flex-col gap-4 border-b border-brand-ink/10 pb-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.28em] text-brand-ocean">
                  Draft Library
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-brand-ink">下書き一覧</h1>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                  作成済みの投稿を見直し、SNS ごとに絞り込みながら編集、複製、削除できます。
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <Link
                  className="inline-flex items-center rounded-full bg-brand-ocean px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                  href="/create"
                >
                  新規作成
                </Link>
                <HelpMark topic="drafts.new_post" />
              </div>
            </div>

            <div className="grid gap-4 xl:grid-cols-[1.3fr_1fr_1fr_auto]">
              <div className="rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/35 p-4">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-brand-ink">ステータス</p>
                  <HelpMark topic="drafts.status_filter" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {STATUS_TABS.map((tab) => (
                    <button
                      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
                        statusTab === tab.value
                          ? "border-brand-ocean bg-brand-ocean text-white"
                          : "border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean hover:text-brand-ocean"
                      }`}
                      key={tab.value}
                      onClick={() => setStatusTab(tab.value)}
                      type="button"
                    >
                      <span>{tab.label}</span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          statusTab === tab.value
                            ? "bg-white/20 text-white"
                            : "bg-brand-sand text-slate-500"
                        }`}
                      >
                        {counts[tab.value]}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/35 p-4">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-brand-ink">プラットフォーム</p>
                  <HelpMark topic="drafts.platform_filter" />
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {PLATFORM_OPTIONS.map((option) => {
                    const checked = selectedPlatforms.includes(option.value);

                    return (
                      <label
                        className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium transition ${
                          checked
                            ? "border-transparent bg-brand-ink text-white"
                            : "border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean hover:text-brand-ocean"
                        }`}
                        key={option.value}
                      >
                        <input
                          checked={checked}
                          className="sr-only"
                          onChange={() => togglePlatform(option.value)}
                          type="checkbox"
                        />
                        <span>{option.shortLabel}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/35 p-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-semibold text-brand-ink" htmlFor="draft-search">
                    検索
                  </label>
                  <HelpMark topic="drafts.search" />
                </div>
                <input
                  className="mt-3 w-full rounded-2xl border border-brand-ink/10 bg-white px-4 py-3 text-sm text-brand-ink outline-none transition focus:border-brand-ocean"
                  id="draft-search"
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="本文を検索"
                  type="search"
                  value={searchInput}
                />
              </div>

              <div className="rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/35 p-4">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-semibold text-brand-ink" htmlFor="draft-sort">
                    並び替え
                  </label>
                  <HelpMark topic="drafts.sort" />
                </div>
                <select
                  className="mt-3 w-full rounded-2xl border border-brand-ink/10 bg-white px-4 py-3 text-sm text-brand-ink outline-none transition focus:border-brand-ocean"
                  id="draft-sort"
                  onChange={(event) => setSortValue(event.target.value as SortValue)}
                  value={sortValue}
                >
                  <option value="updated_desc">更新日 新→旧</option>
                  <option value="created_desc">作成日 新→旧</option>
                  <option value="scheduled_asc">予約日時 近→遠</option>
                </select>
              </div>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-brand-ink/10 bg-brand-sand/30 px-4 py-3 text-sm text-slate-600">
            <div className="flex items-center gap-2">
              <span>
                表示中 {visiblePosts.length} 件 / 全 {total} 件
              </span>
              <HelpMark topic="drafts.card_actions" />
            </div>
            {actionMessage ? (
              <p className="text-sm font-medium text-brand-ocean">{actionMessage}</p>
            ) : null}
          </div>

          {errorMessage ? (
            <div className="mt-6 rounded-[1.5rem] border border-rose-200 bg-rose-50 px-5 py-6">
              <p className="text-base font-semibold text-rose-700">一覧を読み込めませんでした</p>
              <p className="mt-2 text-sm text-rose-600">{errorMessage}</p>
              <button
                className="mt-4 rounded-full bg-rose-600 px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90"
                onClick={reloadList}
                type="button"
              >
                再読み込み
              </button>
            </div>
          ) : null}

          {!errorMessage && isLoading && !isLoaded ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div
                  className="animate-pulse rounded-[1.5rem] border border-brand-ink/10 bg-white p-5"
                  key={index}
                >
                  <div className="flex gap-2">
                    <div className="h-6 w-12 rounded-full bg-brand-sand" />
                    <div className="h-6 w-16 rounded-full bg-brand-sand" />
                  </div>
                  <div className="mt-5 h-4 w-5/6 rounded bg-brand-sand" />
                  <div className="mt-2 h-4 w-full rounded bg-brand-sand" />
                  <div className="mt-2 h-4 w-4/5 rounded bg-brand-sand" />
                  <div className="mt-6 h-4 w-24 rounded bg-brand-sand" />
                </div>
              ))}
            </div>
          ) : null}

          {!errorMessage && !isLoading && visiblePosts.length === 0 ? (
            <div className="mt-6 rounded-[1.75rem] border border-dashed border-brand-ink/15 bg-brand-sand/40 px-6 py-12 text-center">
              <p className="text-lg font-semibold text-brand-ink">
                {posts.length === 0
                  ? "まだ下書きがありません。〔新規作成〕から始めましょう"
                  : "条件に一致する投稿がありません。"}
              </p>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                {posts.length === 0
                  ? "最初の投稿を作成すると、この画面で状態ごとに管理できます。"
                  : "ステータス、SNS、検索条件を見直してください。"}
              </p>
              <div className="mt-6">
                <Link
                  className="inline-flex items-center rounded-full bg-brand-ocean px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                  href="/create"
                >
                  新規作成へ
                </Link>
              </div>
            </div>
          ) : null}

          {!errorMessage && visiblePosts.length > 0 ? (
            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {visiblePosts.map((post) => {
                const platforms = getPostPlatforms(post);
                const isPending = pendingPostId === post.id;

                return (
                  <article
                    className="group rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-lg"
                    key={post.id}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="flex flex-wrap gap-2">
                        {platforms.length > 0 ? (
                          platforms.map((platform) => (
                            <span
                              className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${PLATFORM_STYLES[platform]}`}
                              key={platform}
                            >
                              {
                                PLATFORM_OPTIONS.find((option) => option.value === platform)
                                  ?.shortLabel
                              }
                            </span>
                          ))
                        ) : (
                          <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-500">
                            未設定
                          </span>
                        )}
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${STATUS_STYLES[post.status]}`}
                        >
                          {STATUS_LABELS[post.status]}
                        </span>
                      </div>

                      <div className="flex items-center gap-2 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
                        <Link
                          className="rounded-full border border-brand-ink/10 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                          href={`/create?id=${post.id}`}
                        >
                          編集
                        </Link>
                        <button
                          className="rounded-full border border-brand-ink/10 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isPending}
                          onClick={() => handleDuplicate(post)}
                          type="button"
                        >
                          複製
                        </button>
                        <button
                          className="rounded-full border border-rose-200 px-3 py-1.5 text-xs font-medium text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isPending}
                          onClick={() => handleDelete(post)}
                          type="button"
                        >
                          削除
                        </button>
                      </div>
                    </div>

                    {post.status === "scheduled" ? (
                      <div className="mt-5 rounded-[1.25rem] bg-brand-ocean/8 px-4 py-3">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-ocean">
                          Scheduled For
                        </p>
                        <p className="mt-2 text-lg font-semibold text-brand-ink">
                          {formatDateTime(post.scheduled_at)}
                        </p>
                      </div>
                    ) : null}

                    <div className="mt-5">
                      <p className="text-sm leading-7 text-slate-700">
                        {truncateText(post.content_text, 120)}
                      </p>
                    </div>

                    <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-brand-ink/10 pt-4 text-xs text-slate-500">
                      <span>更新: {formatRelativeTime(post.updated_at)}</span>
                      <span>作成: {formatDateTime(post.created_at)}</span>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : null}
        </section>
      </div>
    </main>
  );
}
