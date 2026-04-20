"use client";

import type { ReactNode } from "react";
import Link from "next/link";

type AuthCardProps = {
  alternateHref: string;
  alternateLabel: string;
  alternateText: string;
  children: ReactNode;
  description: string;
  eyebrow: string;
  title: string;
};

export function AuthCard({
  alternateHref,
  alternateLabel,
  alternateText,
  children,
  description,
  eyebrow,
  title,
}: AuthCardProps) {
  return (
    <main className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-brand-sand px-6 py-12">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(15,118,110,0.16),_transparent_38%),radial-gradient(circle_at_bottom_right,_rgba(255,255,255,0.96),_transparent_44%)]" />
      <div className="relative mx-auto grid max-w-6xl gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <section className="max-w-xl">
          <p className="text-sm font-semibold uppercase tracking-[0.32em] text-brand-ocean">
            {eyebrow}
          </p>
          <h1 className="mt-4 text-4xl font-semibold leading-tight text-brand-ink sm:text-5xl">
            {title}
          </h1>
          <p className="mt-5 text-base leading-7 text-slate-600">{description}</p>
          <div className="mt-8 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/70 bg-white/70 p-4 shadow-sm backdrop-blur">
              投稿計画をまとめて管理し、次の制作ステップへ最短で戻れます。
            </div>
            <div className="rounded-2xl border border-white/70 bg-white/70 p-4 shadow-sm backdrop-blur">
              ヘルプモードで各入力項目の意図をその場で確認できます。
            </div>
          </div>
        </section>

        <section className="rounded-[2rem] border border-white/70 bg-white/95 p-8 shadow-2xl shadow-brand-ink/10 backdrop-blur sm:p-10">
          {children}
          <p className="mt-6 text-sm text-slate-500">
            {alternateText}{" "}
            <Link className="font-semibold text-brand-ocean hover:underline" href={alternateHref}>
              {alternateLabel}
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}
