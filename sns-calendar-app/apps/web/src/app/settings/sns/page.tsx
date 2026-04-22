"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HelpMark } from "../../../components/HelpMark";
import { useAuthGuard } from "../../../hooks/useAuthGuard";
import {
  ApiError,
  connectSnsAccount,
  disconnectSnsAccount,
  fetchSnsAccounts,
} from "../../../lib/api-client";
import type { SnsAccountListResponse, SnsAccountSafe } from "../../../generated/types.gen";

type Platform = "x" | "ig";
type BannerState =
  | {
      kind: "success";
      platform: Platform;
      handle: string;
    }
  | {
      kind: "error";
      reason: string;
    };

const PLATFORM_META: Record<
  Platform,
  {
    accentClass: string;
    buttonClass: string;
    emptyLabel: string;
    title: string;
  }
> = {
  x: {
    accentClass: "bg-x text-white",
    buttonClass: "bg-x text-white hover:opacity-90",
    emptyLabel: "X アカウントは未接続です。",
    title: "X",
  },
  ig: {
    accentClass: "bg-ig text-white",
    buttonClass: "bg-ig text-white hover:opacity-90",
    emptyLabel: "Instagram アカウントは未接続です。",
    title: "Instagram",
  },
};

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatExpiry(value?: string | null) {
  if (!value) {
    return null;
  }

  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(value));
}

function getBannerMessage(banner: BannerState) {
  if (banner.kind === "success") {
    const platformLabel = banner.platform === "x" ? "X" : "Instagram";
    return `✅ @${banner.handle} を ${platformLabel} に接続しました`;
  }

  return `⚠️ 接続に失敗しました: ${banner.reason}`;
}

function getRequestErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message || fallback;
  }

  return fallback;
}

function PlatformCard({
  accounts,
  busyAction,
  isLoaded,
  isLoading,
  onConnect,
  onDisconnect,
  platform,
}: {
  accounts: Array<SnsAccountSafe>;
  busyAction: string | null;
  isLoaded: boolean;
  isLoading: boolean;
  onConnect: (platform: Platform) => void;
  onDisconnect: (account: SnsAccountSafe) => void;
  platform: Platform;
}) {
  const meta = PLATFORM_META[platform];

  return (
    <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-6 shadow-lg shadow-brand-ink/5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-3">
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] ${meta.accentClass}`}
          >
            {meta.title}
          </span>
          <div>
            <h2 className="text-2xl font-semibold text-brand-ink">{meta.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              接続済みアカウントは、公開ジョブの送信先として利用されます。
            </p>
          </div>
        </div>

        <button
          className={`inline-flex items-center rounded-full px-5 py-3 text-sm font-semibold transition ${meta.buttonClass}`}
          disabled={busyAction === `connect:${platform}`}
          onClick={() => onConnect(platform)}
          type="button"
        >
          {busyAction === `connect:${platform}` ? "接続準備中..." : "接続する"}
        </button>
      </div>

      <div className="mt-6">
        {isLoading && !isLoaded ? (
          <div className="rounded-2xl border border-dashed border-brand-ink/10 bg-brand-sand/40 px-5 py-6 text-sm text-slate-500">
            接続済みアカウントを読み込んでいます...
          </div>
        ) : accounts.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-brand-ink/10 bg-brand-sand/40 px-5 py-6 text-sm text-slate-500">
            {meta.emptyLabel}
          </div>
        ) : (
          <div className="space-y-4">
            {accounts.map((account) => {
              const expiresAt = formatExpiry(account.expires_at);

              return (
                <article
                  className="rounded-2xl border border-brand-ink/10 bg-brand-sand/35 p-5"
                  key={account.id}
                >
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="text-lg font-semibold text-brand-ink">@{account.handle}</p>
                        {account.is_active ? (
                          <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-700">
                            接続中
                          </span>
                        ) : (
                          <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-700">
                            無効
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-slate-600">
                        {account.display_name || "表示名未設定"}
                      </p>
                      <div className="space-y-1 text-sm text-slate-500">
                        <p>接続日時: {formatDateTime(account.created_at)}</p>
                        {expiresAt ? <p>{expiresAt} まで有効</p> : null}
                      </div>
                    </div>

                    <button
                      className="rounded-full border border-rose-200 px-4 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-60"
                      disabled={busyAction === `disconnect:${account.id}`}
                      onClick={() => onDisconnect(account)}
                      type="button"
                    >
                      {busyAction === `disconnect:${account.id}` ? "切断中..." : "切断"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function SnsAccountsSettingsPageContent() {
  const { isReady } = useAuthGuard();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [accounts, setAccounts] = useState<Array<SnsAccountSafe>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [banner, setBanner] = useState<BannerState | null>(null);

  const accountsByPlatform = useMemo(() => {
    return {
      ig: accounts.filter((account) => account.platform === "ig"),
      x: accounts.filter((account) => account.platform === "x"),
    };
  }, [accounts]);

  async function loadAccounts() {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response: SnsAccountListResponse = await fetchSnsAccounts();
      setAccounts(response.accounts);
      setIsLoaded(true);
    } catch (error) {
      setErrorMessage(
        getRequestErrorMessage(
          error,
          "SNSアカウントの取得に失敗しました。時間をおいて再試行してください。",
        ),
      );
      setIsLoaded(true);
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    if (!isReady) {
      return;
    }

    void loadAccounts();
  }, [isReady]);

  useEffect(() => {
    const connected = searchParams.get("connected");
    const handle = searchParams.get("handle");
    const error = searchParams.get("error");

    if (connected && handle && (connected === "x" || connected === "ig")) {
      setBanner({
        handle,
        kind: "success",
        platform: connected,
      });
      return;
    }

    if (error) {
      setBanner({
        kind: "error",
        reason: error,
      });
      return;
    }

    setBanner(null);
  }, [searchParams]);

  async function handleConnect(platform: Platform) {
    setBusyAction(`connect:${platform}`);
    setErrorMessage(null);

    try {
      const response = await connectSnsAccount(platform);
      window.location.href = response.authorization_url;
    } catch (error) {
      setErrorMessage(
        getRequestErrorMessage(
          error,
          `${PLATFORM_META[platform].title} の接続開始に失敗しました。`,
        ),
      );
      setBusyAction(null);
    }
  }

  async function handleDisconnect(account: SnsAccountSafe) {
    const confirmed = window.confirm(
      `@${account.handle} の接続を解除します。公開ジョブからこのアカウントを利用できなくなります。`,
    );

    if (!confirmed) {
      return;
    }

    setBusyAction(`disconnect:${account.id}`);
    setErrorMessage(null);

    try {
      await disconnectSnsAccount(account.id);
      await loadAccounts();
    } catch (error) {
      setErrorMessage(
        getRequestErrorMessage(error, `@${account.handle} の切断に失敗しました。`),
      );
    } finally {
      setBusyAction(null);
    }
  }

  function handleDismissBanner() {
    setBanner(null);
    router.replace("/settings/sns");
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-6 py-10">
      <div className="mx-auto max-w-6xl space-y-6">
        <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-8 shadow-xl shadow-brand-ink/5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <p className="text-sm font-semibold uppercase tracking-[0.28em] text-brand-ocean">
                  Settings
                </p>
                <HelpMark topic="settings.sns" />
              </div>
              <div>
                <h1 className="text-3xl font-semibold text-brand-ink">SNSアカウント連携</h1>
                <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
                  X と Instagram のアカウントを接続すると、投稿キューから自動投稿できるようになります。
                </p>
              </div>
            </div>
          </div>
        </section>

        {banner ? (
          <section
            className={`flex flex-wrap items-start justify-between gap-4 rounded-[1.75rem] border px-6 py-5 shadow-sm ${
              banner.kind === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-rose-200 bg-rose-50 text-rose-700"
            }`}
          >
            <p className="text-sm font-medium">{getBannerMessage(banner)}</p>
            <button
              className="rounded-full border border-current/20 px-4 py-2 text-sm font-medium transition hover:bg-white/60"
              onClick={handleDismissBanner}
              type="button"
            >
              閉じる
            </button>
          </section>
        ) : null}

        {errorMessage ? (
          <section className="rounded-[1.75rem] border border-rose-200 bg-rose-50 px-6 py-5 text-sm text-rose-700 shadow-sm">
            {errorMessage}
          </section>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-2">
          <PlatformCard
            accounts={accountsByPlatform.x}
            busyAction={busyAction}
            isLoaded={isLoaded}
            isLoading={isLoading}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            platform="x"
          />
          <PlatformCard
            accounts={accountsByPlatform.ig}
            busyAction={busyAction}
            isLoaded={isLoaded}
            isLoading={isLoading}
            onConnect={handleConnect}
            onDisconnect={handleDisconnect}
            platform="ig"
          />
        </div>
      </div>
    </main>
  );
}

export default function SnsAccountsSettingsPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-6 py-10">
          <div className="mx-auto max-w-6xl rounded-[2rem] border border-brand-ink/10 bg-white px-6 py-4 text-sm text-slate-500 shadow-sm">
            設定画面を読み込んでいます...
          </div>
        </main>
      }
    >
      <SnsAccountsSettingsPageContent />
    </Suspense>
  );
}
