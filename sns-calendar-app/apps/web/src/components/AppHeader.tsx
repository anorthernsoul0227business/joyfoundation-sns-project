"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { HelpModeToggle } from "./HelpModeToggle";
import { NotificationBell } from "./NotificationBell";
import { logout } from "../lib/api-client";
import { useAuthStore } from "../stores/auth";

const navItems = [
  { href: "/calendar", label: "カレンダー", enabled: true },
  { href: "/drafts", label: "下書き", enabled: true },
  { href: "/create", label: "投稿作成", enabled: true },
  { href: "#", label: "AI生成", enabled: false },
  { href: "/settings/sns", label: "設定", enabled: true },
];

function isActivePath(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

function getInitial(label?: string | null) {
  if (!label) {
    return "U";
  }

  return label.slice(0, 1).toUpperCase();
}

export function AppHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated());
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  async function handleLogout() {
    await logout();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b border-brand-ink/10 bg-white/90 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <div className="flex items-center gap-6">
          <Link className="flex items-center gap-3" href="/">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-brand-ocean text-lg font-bold text-white">
              S
            </span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand-ocean">
                SNS Calendar
              </p>
              <p className="text-sm text-slate-500">
                {isAuthPage ? "Sign in to continue" : "Planning workspace"}
              </p>
            </div>
          </Link>

          {!isAuthPage ? (
            <nav aria-label="グローバルナビゲーション" className="flex flex-wrap items-center gap-2">
              {navItems.map((item) =>
                item.enabled ? (
                  <Link
                    className={`rounded-full px-3 py-2 text-sm font-medium transition ${
                      isActivePath(pathname, item.href)
                        ? "bg-brand-ocean text-white"
                        : "text-slate-600 hover:bg-brand-sand hover:text-brand-ocean"
                    }`}
                    href={item.href}
                    key={item.label}
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span
                    aria-disabled="true"
                    className="cursor-not-allowed rounded-full px-3 py-2 text-sm font-medium text-slate-300"
                    key={item.label}
                  >
                    {item.label}
                  </span>
                ),
              )}
            </nav>
          ) : null}
        </div>

        <div className="flex items-center gap-3">
          {isAuthenticated && !isAuthPage ? <NotificationBell /> : null}
          <HelpModeToggle />
          {isAuthenticated && user ? (
            <>
              <div className="hidden items-center gap-3 rounded-full border border-brand-ink/10 bg-brand-sand/80 px-3 py-1.5 sm:flex">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-ocean/15 text-sm font-bold text-brand-ocean">
                  {getInitial(user.displayName || user.email)}
                </span>
                <div className="text-sm">
                  <p className="font-medium text-brand-ink">
                    {user.displayName || user.email}
                  </p>
                  <p className="text-xs text-slate-500">{user.email}</p>
                </div>
              </div>
              {!isAuthPage ? (
                <button
                  className="rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                  onClick={handleLogout}
                  type="button"
                >
                  ログアウト
                </button>
              ) : null}
            </>
          ) : isAuthPage ? null : (
            <div className="flex items-center gap-2">
              <Link
                className="rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                href="/login"
              >
                ログイン
              </Link>
              <Link
                className="rounded-full bg-brand-ocean px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                href="/signup"
              >
                新規登録
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
