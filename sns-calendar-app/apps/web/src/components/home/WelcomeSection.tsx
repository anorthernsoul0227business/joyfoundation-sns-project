"use client";

import { HelpMark } from "../HelpMark";

type WelcomeSectionProps = {
  displayName: string;
};

function formatToday(): string {
  return new Intl.DateTimeFormat("ja-JP", {
    year: "numeric",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date());
}

export function WelcomeSection({ displayName }: WelcomeSectionProps) {
  return (
    <section className="rounded-[2rem] border border-brand-ink/10 bg-white p-6 shadow-sm sm:p-8">
      <div className="flex items-center gap-2">
        <p className="text-sm font-medium uppercase tracking-[0.28em] text-brand-ocean">
          Home
        </p>
        <HelpMark topic="home.welcome" />
      </div>
      <h1 className="mt-2 text-2xl font-semibold text-brand-ink sm:text-3xl">
        こんにちは、{displayName}さん
      </h1>
      <p className="mt-2 text-sm text-slate-500">
        <span aria-hidden="true" className="mr-2">
          🌿
        </span>
        {formatToday()}
      </p>
    </section>
  );
}
