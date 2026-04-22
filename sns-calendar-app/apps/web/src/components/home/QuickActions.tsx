"use client";

import Link from "next/link";

const ACTIONS: Array<{
  href: string;
  title: string;
  description: string;
  accent: string;
}> = [
  {
    href: "/create",
    title: "投稿を作る",
    description: "新しい投稿を書いて下書き保存または予約",
    accent: "bg-brand-ocean text-white",
  },
  {
    href: "/drafts",
    title: "下書き",
    description: "保存した下書きを一覧・編集",
    accent: "bg-white text-brand-ink",
  },
  {
    href: "/settings/sns",
    title: "設定",
    description: "SNS アカウントの接続・切断",
    accent: "bg-white text-brand-ink",
  },
];

export function QuickActions() {
  return (
    <section className="grid gap-3 sm:grid-cols-3">
      {ACTIONS.map((action) => (
        <Link
          className={`flex flex-col gap-1 rounded-[1.5rem] border border-brand-ink/10 px-5 py-4 shadow-sm transition hover:-translate-y-0.5 hover:border-brand-ocean hover:shadow-md ${action.accent}`}
          href={action.href}
          key={action.href}
        >
          <span className="text-base font-semibold">{action.title}</span>
          <span
            className={`text-xs leading-5 ${
              action.accent.includes("text-white") ? "text-white/80" : "text-slate-500"
            }`}
          >
            {action.description}
          </span>
        </Link>
      ))}
    </section>
  );
}
