"use client";

export type FontScale = "normal" | "large" | "xlarge";

/** PC の基準文字サイズ（html の font-size に入れる） */
export const FONT_SCALE_PX: Record<FontScale, number> = {
  normal: 17,
  large: 19,
  xlarge: 22,
};

/**
 * iPhone など幅の狭い画面用。同じ px を使うと 1rem が大きすぎて
 * 枠が画面からはみ出すため、ひとまわり小さい値にする。
 */
export const FONT_SCALE_PX_NARROW: Record<FontScale, number> = {
  normal: 14,
  large: 16,
  xlarge: 18,
};

const OPTIONS: { value: FontScale; label: string; short: string }[] = [
  { value: "normal", label: "標準", short: "小" },
  { value: "large", label: "大きく", short: "中" },
  { value: "xlarge", label: "もっと大きく", short: "大" },
];

export function FontSizeControl({
  value,
  onChange,
}: {
  value: FontScale;
  onChange: (next: FontScale) => void;
}) {
  return (
    <div className="flex items-center gap-1.5 text-[0.8em] text-slate-500 md:gap-2">
      <span className="hidden md:inline">文字の大きさ</span>
      <span className="md:hidden" aria-hidden>
        文字
      </span>
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          aria-pressed={value === opt.value}
          aria-label={`文字の大きさ：${opt.label}`}
          onClick={() => onChange(opt.value)}
          className={
            "rounded-full border px-3 py-1 transition " +
            (value === opt.value
              ? "border-brand-ocean bg-brand-ocean/10 font-semibold text-brand-ocean"
              : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")
          }
        >
          <span className="hidden md:inline">{opt.label}</span>
          <span className="md:hidden">{opt.short}</span>
        </button>
      ))}
    </div>
  );
}
