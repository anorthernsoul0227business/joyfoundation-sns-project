"use client";

import { PENDING_STATUSES, STATUS_LABEL, type ArticleStatus } from "../../lib/board";

export function StatusBadge({ status }: { status: ArticleStatus }) {
  const pending = PENDING_STATUSES.includes(status);
  // 「直しました」は確認を促したいので、他の未対応より目立たせる
  // 聞き返しは返事が要る。放っておくと止まるので一番目立たせる
  const tone = status === "needs_owner_input"
    ? "bg-amber-200 text-amber-900"
    : status === "revised"
    ? "bg-emerald-100 text-emerald-800"
    : pending
    ? "bg-amber-50 text-amber-800"
    : status === "approved" || status === "scheduled"
      ? "bg-brand-ocean/10 text-brand-ocean"
      : status === "needs_fix"
        ? "bg-rose-50 text-rose-700"
        : status === "missed"
          ? "bg-slate-200 text-slate-600"
        : "bg-slate-100 text-slate-500";
  return (
    <span className={`whitespace-nowrap rounded px-2 py-0.5 text-[0.7em] font-semibold ${tone}`}>
      {STATUS_LABEL[status]}
    </span>
  );
}
