"use client";

import { useEffect, useId, useMemo, useState } from "react";
import { HelpMark } from "../HelpMark";
import { IgPreview } from "./IgPreview";
import { XPreview } from "./XPreview";

export type PreviewPlatform = "x" | "ig" | "youtube" | "note" | "line";

type PreviewMedia = {
  mime_type: string;
  storage_path: string;
};

type Tab = "x" | "ig";

type PreviewPanelProps = {
  contentText: string;
  displayName: string;
  handle: string;
  isDirty: boolean;
  mediaPaths: PreviewMedia[];
  scheduledAt?: string;
  selectedPlatforms: PreviewPlatform[];
};

function getPreferredTab(platforms: PreviewPlatform[]): Tab {
  if (platforms.includes("x")) {
    return "x";
  }

  if (platforms.includes("ig")) {
    return "ig";
  }

  return "x";
}

const TAB_META: Record<Tab, { label: string; inactiveMessage: string }> = {
  ig: { label: "Instagram", inactiveMessage: "このSNSは未選択です" },
  x: { label: "X", inactiveMessage: "このSNSは未選択です" },
};

export function PreviewPanel({
  contentText,
  displayName,
  handle,
  isDirty,
  mediaPaths,
  scheduledAt,
  selectedPlatforms,
}: PreviewPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>(() => getPreferredTab(selectedPlatforms));
  const tablistId = useId();
  const selectedPreviewPlatforms = selectedPlatforms.filter(
    (platform): platform is Tab => platform === "x" || platform === "ig",
  );
  const hasPreviewTarget = selectedPreviewPlatforms.length > 0;
  const preferredTab = useMemo(() => getPreferredTab(selectedPlatforms), [selectedPlatforms]);

  useEffect(() => {
    if (!selectedPreviewPlatforms.includes(activeTab)) {
      setActiveTab(preferredTab);
    }
  }, [activeTab, preferredTab, selectedPreviewPlatforms]);

  const isTabSelected = selectedPreviewPlatforms.includes(activeTab);
  const panelId = `${tablistId}-${activeTab}-panel`;

  return (
    <div className="rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-sm xl:sticky xl:top-24">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-ocean">Preview</p>
          <h2 className="mt-3 text-xl font-semibold text-brand-ink">投稿プレビュー</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            本文と画像の入力内容を X / Instagram 形式でリアルタイム表示します。
          </p>
        </div>
        <HelpMark topic="create.preview_realtime" />
      </div>

      <div className="mt-5 rounded-[1.25rem] border border-brand-ink/10 bg-brand-sand/25 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">対象SNS</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {hasPreviewTarget ? (
                selectedPreviewPlatforms.map((platform) => (
                  <span
                    className={`inline-flex rounded-full px-3 py-1.5 text-xs font-semibold ${
                      platform === "x" ? "bg-x/10 text-x" : "bg-ig/10 text-ig"
                    }`}
                    key={platform}
                  >
                    {TAB_META[platform].label}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-500">X / Instagram 未選択</span>
              )}
            </div>
          </div>
          <HelpMark topic="create.preview_tabs" />
        </div>
      </div>

      <div className="mt-4 overflow-hidden rounded-[1.25rem] border border-brand-ink/10 bg-brand-sand/15">
        <div aria-label="プレビュー切替" className="flex border-b border-brand-ink/10" role="tablist">
          {(["x", "ig"] as const).map((tab) => {
            const enabled = selectedPreviewPlatforms.includes(tab);
            const selected = activeTab === tab;

            return (
              <button
                aria-controls={`${tablistId}-${tab}-panel`}
                aria-selected={selected}
                className={`flex-1 px-4 py-3 text-sm font-semibold transition ${
                  selected
                    ? tab === "x"
                      ? "bg-white text-x"
                      : "bg-white text-ig"
                    : enabled
                      ? "bg-brand-sand/20 text-slate-500 hover:bg-white"
                      : "bg-slate-100 text-slate-400"
                }`}
                id={`${tablistId}-${tab}-tab`}
                key={tab}
                onClick={() => setActiveTab(tab)}
                role="tab"
                type="button"
              >
                {TAB_META[tab].label}
              </button>
            );
          })}
        </div>

        <div
          aria-labelledby={`${tablistId}-${activeTab}-tab`}
          className="relative p-4"
          id={panelId}
          role="tabpanel"
        >
          <div className={isTabSelected ? "" : "pointer-events-none opacity-45"}>
            {activeTab === "x" ? (
              <XPreview
                contentText={contentText}
                displayName={displayName}
                handle={handle}
                mediaPaths={mediaPaths}
                scheduledAt={scheduledAt}
              />
            ) : (
              <IgPreview
                contentText={contentText}
                displayName={displayName}
                handle={handle}
                mediaPaths={mediaPaths}
              />
            )}
          </div>

          {!isTabSelected ? (
            <div className="absolute inset-x-10 top-1/2 -translate-y-1/2 rounded-[1.25rem] border border-brand-ink/10 bg-white/95 px-4 py-3 text-center shadow-lg">
              <p className="text-sm font-semibold text-brand-ink">{TAB_META[activeTab].inactiveMessage}</p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                投稿先のSNSで {TAB_META[activeTab].label} を選択すると実プレビューとして有効化されます。
              </p>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-[1.25rem] border border-brand-ink/10 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">入力サマリー</p>
          <dl className="mt-3 space-y-2 text-sm text-slate-600">
            <div className="flex items-start justify-between gap-3">
              <dt className="font-medium text-brand-ink">本文</dt>
              <dd>{contentText.length} 文字</dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="font-medium text-brand-ink">画像</dt>
              <dd>{mediaPaths.length} 件</dd>
            </div>
            <div className="flex items-start justify-between gap-3">
              <dt className="font-medium text-brand-ink">予約日時</dt>
              <dd>{scheduledAt || "Now"}</dd>
            </div>
          </dl>
        </div>

        <div className="rounded-[1.25rem] border border-brand-ink/10 bg-white p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">状態</p>
          <div className="mt-3 space-y-2 text-sm">
            <p className={isDirty ? "font-medium text-amber-700" : "text-emerald-700"}>
              {isDirty ? "未保存の変更があります" : "最新の保存内容と一致しています"}
            </p>
            <p className="text-slate-500">
              X は 280 文字、Instagram は 2200 文字を目安に確認してください。
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
