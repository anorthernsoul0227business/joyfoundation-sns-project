"use client";

import { PLATFORM_LABEL, type Article, type Platform } from "../../lib/board";

/** カレンダーに出す媒体。チェックが付いているものだけを表示する */
export const FILTERABLE: Platform[] = ["x", "ig", "note"];

const TONE: Record<string, string> = {
  x: "bg-slate-800",
  ig: "bg-rose-600",
  note: "bg-emerald-700",
};

/**
 * 媒体の絞り込み。
 *
 * 2026-09-30 康二郎さん: すべて合わせたカレンダーも、媒体ごとの分割も見たい。
 * チェックが付いている媒体を表示する、という形にした。
 */
export function PlatformFilter({
  value,
  onChange,
  counts,
}: {
  value: Set<Platform>;
  onChange: (next: Set<Platform>) => void;
  counts?: Record<string, number>;
}) {
  const allOn = FILTERABLE.every((p) => value.has(p));

  function toggle(p: Platform) {
    const next = new Set(value);
    if (next.has(p)) {
      // 全部外すと何も見えなくなるので、最後の1つは外させない
      if (next.size === 1) return;
      next.delete(p);
    } else {
      next.add(p);
    }
    onChange(next);
  }

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <span className="text-[0.82em] text-slate-500">見る媒体</span>
      {FILTERABLE.map((p) => {
        const on = value.has(p);
        return (
          <button
            key={p}
            type="button"
            role="checkbox"
            aria-checked={on}
            onClick={() => toggle(p)}
            className={
              "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[0.85em] transition " +
              (on
                ? "border-brand-ink bg-white font-semibold text-brand-ink"
                : "border-slate-200 bg-slate-50 text-slate-400")
            }
          >
            <span
              className={
                "flex h-4 w-4 items-center justify-center rounded text-[0.7em] text-white " +
                (on ? TONE[p] : "bg-slate-300")
              }
              aria-hidden
            >
              {on ? "✓" : ""}
            </span>
            {PLATFORM_LABEL[p]}
            {counts && <span className="text-[0.85em] text-slate-400">{counts[p] ?? 0}</span>}
          </button>
        );
      })}
      <button
        type="button"
        onClick={() => onChange(new Set(allOn ? ["x" as Platform] : FILTERABLE))}
        className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[0.82em] text-slate-600 transition hover:bg-slate-50"
      >
        {allOn ? "Xだけにする" : "すべて見る"}
      </button>
    </div>
  );
}

/** チェックの付いた媒体だけに絞る */
export function filterByPlatform(list: Article[], on: Set<Platform>): Article[] {
  return list.filter((a) => on.has(a.platform));
}
