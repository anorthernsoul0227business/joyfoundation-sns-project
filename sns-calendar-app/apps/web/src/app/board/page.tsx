"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArticleDetail } from "../../components/board/ArticleDetail";
import { ArticleList } from "../../components/board/ArticleList";
import {
  FONT_SCALE_PX,
  FONT_SCALE_PX_NARROW,
  FontSizeControl,
  type FontScale,
} from "../../components/board/FontSizeControl";
import { IdeaDock } from "../../components/board/IdeaDock";
import { EventsPanel } from "../../components/board/EventsPanel";
import { GuidePanel } from "../../components/board/GuidePanel";
import { IdeasPanel, SharesPanel } from "../../components/board/SidePanels";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import { useIsNarrow } from "../../hooks/useIsNarrow";
import { signOut, syncSessionFromSupabase } from "../../lib/auth";
import { listArticles, type Article, type ArticleFilter } from "../../lib/board";
import { useAuthStore } from "../../stores/auth";

type Section = "articles" | "ideas" | "events" | "shares" | "guide";

const SECTIONS: { value: Section; label: string; short: string; icon: string }[] = [
  { value: "articles", label: "記事の確認", short: "記事", icon: "📝" },
  { value: "ideas", label: "思いつきメモ", short: "メモ", icon: "💡" },
  { value: "events", label: "イベント", short: "予定", icon: "📅" },
  { value: "shares", label: "資料・お知らせ", short: "資料", icon: "📎" },
  { value: "guide", label: "使い方", short: "使い方", icon: "📖" },
];

const FONT_KEY = "jf-board-font-scale";

function todayJa() {
  return new Intl.DateTimeFormat("ja-JP", {
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date());
}

export default function BoardPage() {
  const router = useRouter();
  const { isReady } = useAuthGuard();
  const user = useAuthStore((s) => s.user);
  const narrow = useIsNarrow();

  const [fontScale, setFontScale] = useState<FontScale>("large");
  const [section, setSection] = useState<Section>("articles");
  const [filter, setFilter] = useState<ArticleFilter>("pending");
  const [articles, setArticles] = useState<Article[]>([]);
  const [pendingCount, setPendingCount] = useState<number | null>(null);
  const [selected, setSelected] = useState<Article | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Supabase 側のセッションを zustand に同期（リロード後も使えるように）
  useEffect(() => {
    void syncSessionFromSupabase();
  }, []);

  // 文字サイズは端末に記憶し、ページ全体の基準サイズ（html の font-size）に反映する
  useEffect(() => {
    const saved = window.localStorage.getItem(FONT_KEY) as FontScale | null;
    if (saved && saved in FONT_SCALE_PX) setFontScale(saved);
  }, []);
  useEffect(() => {
    const root = document.documentElement;
    const table = narrow ? FONT_SCALE_PX_NARROW : FONT_SCALE_PX;
    root.style.fontSize = `${table[fontScale]}px`;
    window.localStorage.setItem(FONT_KEY, fontScale);
    return () => {
      root.style.fontSize = "";
    };
  }, [fontScale, narrow]);

  const reload = useCallback(async () => {
    if (!isReady) return;
    setLoading(true);
    setLoadError(null);
    try {
      const [list, pending] = await Promise.all([
        listArticles(filter),
        filter === "pending" ? null : listArticles("pending"),
      ]);
      setArticles(list);
      setPendingCount((pending ?? list).length);
      setSelected((cur) => {
        if (cur) {
          const still = list.find((a) => a.id === cur.id);
          if (still) return still;
        }
        // 狭い画面では一覧と本文を同時に置けないので、勝手に開かない
        return narrow ? null : list[0] ?? null;
      });
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [filter, isReady, narrow]);

  useEffect(() => {
    void reload();
  }, [reload, reloadKey]);

  function handleUpdated(next: Article) {
    setArticles((prev) => prev.map((a) => (a.id === next.id ? next : a)));
    setSelected(next);
    setReloadKey((k) => k + 1);
  }

  async function handleSignOut() {
    await signOut();
    router.replace("/login");
  }

  if (!isReady || !user) {
    return (
      <main className="flex min-h-[60vh] items-center justify-center text-slate-500">
        読み込んでいます…
      </main>
    );
  }

  const orgId = user.defaultOrgId ?? null;
  // 狭い画面では「一覧」か「本文」のどちらか一方だけを出す
  const showList = !narrow || selected === null;
  const showDetail = !narrow || selected !== null;

  return (
    <main className="flex h-[100dvh] flex-col overflow-hidden bg-brand-sand text-brand-ink">
      {/* 上部バー：今日・文字サイズ・名前・ログアウト */}
      <header className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-slate-200 bg-white px-4 py-2.5 md:gap-x-6 md:px-6 md:py-3">
        <div className="min-w-0">
          <p className="truncate text-[0.72em] text-slate-500 md:text-[0.78em]">
            ジョイファンデーション 共有ボード
          </p>
          <p className="text-[1em] font-semibold md:text-[1.05em]">{todayJa()}</p>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-3 md:gap-5">
          <FontSizeControl value={fontScale} onChange={setFontScale} />
          <span className="hidden text-[0.85em] text-slate-600 md:inline">
            {user.displayName ?? user.email}
          </span>
          <button
            type="button"
            onClick={handleSignOut}
            className="rounded-md border border-slate-200 px-3 py-1.5 text-[0.8em] text-slate-500 transition hover:bg-slate-50"
          >
            ログアウト
          </button>
        </div>
      </header>

      {/* 今日やること */}
      {pendingCount !== null && (
        <div
          className={
            "px-4 py-2 text-[0.9em] md:px-6 md:py-2.5 md:text-[0.95em] " +
            (pendingCount > 0 ? "bg-amber-50 text-amber-900" : "bg-brand-ocean/10 text-brand-ocean")
          }
        >
          {pendingCount > 0 ? (
            <>
              <strong className="mr-2 text-[1.15em]">{pendingCount}件</strong>
              確認をおねがいします。
              <span className="hidden md:inline">左の一覧から記事を選んでください。</span>
            </>
          ) : (
            "確認をお願いする記事はありません。ありがとうございます。"
          )}
        </div>
      )}

      <div className="flex min-h-0 flex-1 flex-col md:grid md:grid-cols-[13rem_minmax(0,1fr)]">
        {/* 機能ナビ：狭い画面では上に横並び、PC では左に縦並び */}
        <nav className="flex shrink-0 gap-1 border-b border-slate-200 bg-white/60 p-2 md:flex-col md:border-b-0 md:border-r md:p-3">
          {SECTIONS.map((s) => {
            const active = section === s.value;
            return (
              <button
                key={s.value}
                type="button"
                aria-current={active ? "page" : undefined}
                onClick={() => setSection(s.value)}
                className={
                  "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-2.5 text-[0.85em] transition md:flex-none md:justify-start md:px-3 md:py-3 md:text-[0.95em] " +
                  (active
                    ? "bg-brand-ink font-semibold text-white"
                    : "text-slate-700 hover:bg-white")
                }
              >
                <span aria-hidden>{s.icon}</span>
                <span className="md:hidden">{s.short}</span>
                <span className="hidden md:inline">{s.label}</span>
                {s.value === "articles" && pendingCount ? (
                  <span
                    className={
                      "rounded-full px-1.5 py-0.5 text-[0.75em] font-semibold md:ml-auto md:px-2 " +
                      (active ? "bg-white/20 text-white" : "bg-amber-100 text-amber-900")
                    }
                  >
                    {pendingCount}
                  </span>
                ) : null}
              </button>
            );
          })}
        </nav>

        {/* セクション本体 */}
        {section === "articles" ? (
          <div className="flex min-h-0 flex-1 flex-col md:grid md:grid-cols-[19rem_minmax(0,1fr)]">
            {showList && (
              <aside className="flex min-h-0 flex-1 flex-col bg-white md:flex-none md:border-r md:border-slate-200">
                {loadError && (
                  <p className="border-b border-rose-100 bg-rose-50 px-4 py-2 text-[0.82em] text-rose-700">
                    {loadError}
                  </p>
                )}
                <ArticleList
                  articles={articles}
                  filter={filter}
                  loading={loading}
                  selectedId={selected?.id ?? null}
                  onFilterChange={setFilter}
                  onSelect={setSelected}
                />
              </aside>
            )}
            {showDetail && (
              <section className="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6 md:py-6">
                {selected ? (
                  <ArticleDetail
                    article={selected}
                    userId={user.id}
                    orgId={orgId}
                    onUpdated={handleUpdated}
                    onBack={narrow ? () => setSelected(null) : undefined}
                  />
                ) : (
                  <p className="px-8 py-16 text-center text-slate-500">
                    {loading ? "読み込んでいます…" : "左の一覧から記事を選ぶと、ここに本文が出ます。"}
                  </p>
                )}
              </section>
            )}
          </div>
        ) : (
          <section className="min-h-0 flex-1 overflow-y-auto px-4 py-5 md:px-6 md:py-6">
            <h2 className="mb-4 text-[1.1em] font-semibold md:text-[1.15em]">
              {SECTIONS.find((s) => s.value === section)?.label}
            </h2>
            {section === "ideas" && <IdeasPanel reloadKey={reloadKey} />}
            {section === "events" && <EventsPanel reloadKey={reloadKey} />}
            {section === "shares" && <SharesPanel reloadKey={reloadKey} />}
            {section === "guide" && <GuidePanel />}
          </section>
        )}
      </div>

      {orgId && (
        <IdeaDock orgId={orgId} userId={user.id} onCreated={() => setReloadKey((k) => k + 1)} />
      )}
    </main>
  );
}
