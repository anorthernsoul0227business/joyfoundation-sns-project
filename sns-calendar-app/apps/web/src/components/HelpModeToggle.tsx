"use client";

import { useAuthStore } from "../stores/auth";

export function HelpModeToggle() {
  const helpModeEnabled = useAuthStore((state) => state.helpModeEnabled);
  const toggleHelpMode = useAuthStore((state) => state.toggleHelpMode);

  return (
    <button
      aria-pressed={helpModeEnabled}
      className={`help-toggle inline-flex items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium transition ${
        helpModeEnabled
          ? "border-brand-ocean bg-brand-ocean text-white"
          : "border-brand-ink/10 bg-white text-slate-500"
      }`}
      onClick={toggleHelpMode}
      type="button"
    >
      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-white/20 text-xs font-bold">
        ?
      </span>
      {helpModeEnabled ? "ヘルプ ON" : "ヘルプ OFF"}
    </button>
  );
}
