"use client";

import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { helpTexts } from "../lib/help-texts";
import { useAuthStore } from "../stores/auth";

type HelpMarkProps = {
  topic: string;
};

// ビューポート端との余白（px）。これ未満に近づいたら位置を補正する。
const VIEWPORT_PADDING = 8;

type PopoverAdjust = {
  x: number;
  placeAbove: boolean;
};

export function HelpMark({ topic }: HelpMarkProps) {
  const [open, setOpen] = useState(false);
  const [adjust, setAdjust] = useState<PopoverAdjust>({ x: 0, placeAbove: false });
  const helpModeEnabled = useAuthStore((state) => state.helpModeEnabled);
  const text = helpTexts[topic];
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // ポップオーバーが画面端で見切れないよう、アンカー（?ボタン）の位置と
  // ポップオーバーの実寸から水平オフセットと上下配置を計算する。
  // anchor rect と offsetWidth/Height は transform の影響を受けないため、
  // 再オープン時も安定して同じ結果になる。
  const recomputePosition = useCallback(() => {
    const anchor = ref.current;
    const popover = popoverRef.current;
    if (!anchor || !popover) {
      return;
    }

    const anchorRect = anchor.getBoundingClientRect();
    const width = popover.offsetWidth;
    const height = popover.offsetHeight;
    const centerX = anchorRect.left + anchorRect.width / 2;
    const naturalLeft = centerX - width / 2;

    let x = 0;
    const rightLimit = window.innerWidth - VIEWPORT_PADDING;
    if (naturalLeft + width > rightLimit) {
      x = rightLimit - (naturalLeft + width);
    } else if (naturalLeft < VIEWPORT_PADDING) {
      x = VIEWPORT_PADDING - naturalLeft;
    }

    // 下に出すと下端で見切れ、かつ上に十分な余白があるなら上に出す。
    const overflowsBottom = anchorRect.bottom + 8 + height > window.innerHeight - VIEWPORT_PADDING;
    const fitsAbove = anchorRect.top - 8 - height > VIEWPORT_PADDING;
    const placeAbove = overflowsBottom && fitsAbove;

    setAdjust({ x, placeAbove });
  }, []);

  useLayoutEffect(() => {
    if (!open) {
      return;
    }
    recomputePosition();
  }, [open, recomputePosition]);

  useEffect(() => {
    if (!open) {
      return;
    }

    function onPointerDown(event: MouseEvent) {
      if (!ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    function onReflow() {
      recomputePosition();
    }

    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onEscape);
    window.addEventListener("resize", onReflow);
    window.addEventListener("scroll", onReflow, true);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onEscape);
      window.removeEventListener("resize", onReflow);
      window.removeEventListener("scroll", onReflow, true);
    };
  }, [open, recomputePosition]);

  if (!helpModeEnabled || !text) {
    return null;
  }

  return (
    <div className="help-mark relative inline-flex" ref={ref}>
      <button
        aria-controls={id}
        aria-expanded={open}
        aria-label="この項目の説明を表示"
        className="flex h-5 w-5 items-center justify-center rounded-full border border-brand-ocean/30 bg-brand-ocean/10 text-[11px] font-bold text-brand-ocean transition hover:border-brand-ocean hover:bg-brand-ocean hover:text-white"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        ?
      </button>
      {open ? (
        <div
          className={`help-popover absolute left-1/2 z-30 w-64 max-w-[calc(100vw-1rem)] rounded-2xl border border-brand-ink/10 bg-white p-3 text-sm leading-6 text-slate-600 shadow-xl ${
            adjust.placeAbove ? "bottom-full mb-2" : "top-full mt-2"
          }`}
          id={id}
          ref={popoverRef}
          role="tooltip"
          style={{ transform: `translateX(calc(-50% + ${adjust.x}px))` }}
        >
          {text}
        </div>
      ) : null}
    </div>
  );
}
