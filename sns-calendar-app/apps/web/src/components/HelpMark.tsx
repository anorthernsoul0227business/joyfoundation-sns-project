"use client";

import { useEffect, useId, useRef, useState } from "react";
import { helpTexts } from "../lib/help-texts";
import { useAuthStore } from "../stores/auth";

type HelpMarkProps = {
  topic: string;
};

export function HelpMark({ topic }: HelpMarkProps) {
  const [open, setOpen] = useState(false);
  const helpModeEnabled = useAuthStore((state) => state.helpModeEnabled);
  const text = helpTexts[topic];
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);

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

    window.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onEscape);
    return () => {
      window.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onEscape);
    };
  }, [open]);

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
          className="help-popover absolute left-1/2 top-full z-30 mt-2 w-64 -translate-x-1/2 rounded-2xl border border-brand-ink/10 bg-white p-3 text-sm leading-6 text-slate-600 shadow-xl"
          id={id}
          role="tooltip"
        >
          {text}
        </div>
      ) : null}
    </div>
  );
}
