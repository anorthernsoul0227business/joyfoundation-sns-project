"use client";

import Link from "next/link";
import type { SnsAccountSafe } from "../../generated/types.gen";

type SystemStatusBannerProps = {
  accounts: Array<SnsAccountSafe> | null;
  isLoading: boolean;
};

const REQUIRED_PLATFORMS: Array<{ key: "x" | "ig"; label: string }> = [
  { key: "x", label: "X" },
  { key: "ig", label: "Instagram" },
];

export function SystemStatusBanner({ accounts, isLoading }: SystemStatusBannerProps) {
  if (isLoading || accounts === null) {
    return null;
  }

  const missing = REQUIRED_PLATFORMS.filter(
    ({ key }) => !accounts.some((account) => account.platform === key && account.is_active),
  );

  if (missing.length === 0) {
    return null;
  }

  const labels = missing.map(({ label }) => label).join(" / ");

  return (
    <section className="rounded-[1.5rem] border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-800">
      <p className="font-semibold">SNS アカウント未接続</p>
      <p className="mt-1 text-xs leading-5">
        {labels} が未接続です。設定から連携すると、予約時刻に自動投稿できるようになります。
      </p>
      <Link
        className="mt-2 inline-flex items-center rounded-full border border-amber-300 bg-white px-4 py-1.5 text-xs font-semibold text-amber-800 transition hover:bg-amber-100"
        href="/settings/sns"
      >
        設定画面へ →
      </Link>
    </section>
  );
}
