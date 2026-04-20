"use client";

import { Fragment } from "react";

type PreviewMedia = {
  mime_type: string;
  storage_path: string;
};

type IgPreviewProps = {
  contentText: string;
  displayName: string;
  handle: string;
  mediaPaths: PreviewMedia[];
};

const HASHTAG_PATTERN = /(#[\p{L}\p{N}_-]+)/gu;

function getInitial(label: string) {
  return label.trim().slice(0, 1).toUpperCase() || "U";
}

function renderCaption(text: string) {
  if (!text) {
    return <span className="text-slate-400">ここに Instagram 向けキャプションが表示されます。</span>;
  }

  return text.split(HASHTAG_PATTERN).map((part, index) => {
    if (!part) {
      return null;
    }

    const isHashtag = HASHTAG_PATTERN.test(part);
    HASHTAG_PATTERN.lastIndex = 0;

    return (
      <Fragment key={`${part}-${index}`}>
        <span className={isHashtag ? "font-medium text-sky-600" : ""}>{part}</span>
      </Fragment>
    );
  });
}

export function IgPreview({ contentText, displayName, handle, mediaPaths }: IgPreviewProps) {
  const primaryMedia = mediaPaths[0];
  const extraMediaCount = Math.max(mediaPaths.length - 1, 0);

  return (
    <article className="overflow-hidden rounded-[1.5rem] border border-ig/15 bg-white shadow-sm">
      <div className="border-b border-ig/10 bg-ig/5 px-4 py-3">
        <div className="flex items-center gap-3">
          <div
            aria-label="プロフィール画像"
            className="flex h-10 w-10 items-center justify-center rounded-full bg-ig/15 text-sm font-bold text-ig"
            role="img"
          >
            {getInitial(displayName)}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-brand-ink">{handle}</p>
            <p className="text-xs text-slate-500">Instagram feed post</p>
          </div>
          <span className="text-lg text-slate-400">⋯</span>
        </div>
      </div>

      <div className="p-4">
        {primaryMedia ? (
          <div className="relative overflow-hidden rounded-[1.5rem] border border-brand-ink/10 bg-slate-200">
            <div className="aspect-square bg-gradient-to-br from-ig/20 via-rose-100 to-orange-100">
              <div className="flex h-full w-full items-center justify-center px-6 text-center">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ig">
                    {primaryMedia.mime_type}
                  </p>
                  <p className="text-sm text-slate-600">{primaryMedia.storage_path}</p>
                </div>
              </div>
            </div>
            {extraMediaCount > 0 ? (
              <span className="absolute right-3 top-3 rounded-full bg-black/65 px-2.5 py-1 text-xs font-semibold text-white">
                +{extraMediaCount}
              </span>
            ) : null}
          </div>
        ) : (
          <div className="flex aspect-square items-center justify-center rounded-[1.5rem] border border-dashed border-ig/30 bg-ig/10 px-6 text-center text-sm font-medium text-ig">
            画像未添付
          </div>
        )}

        <div className="mt-4 flex items-center justify-between text-xl text-slate-700">
          <div className="flex items-center gap-3">
            <span aria-hidden="true">♡</span>
            <span aria-hidden="true">💬</span>
            <span aria-hidden="true">✈️</span>
          </div>
          <span aria-hidden="true">🔖</span>
        </div>

        <p className="mt-3 text-sm font-semibold text-brand-ink">いいね数を表示</p>

        <p className="mt-2 text-sm leading-6 text-brand-ink">
          <span className="mr-2 font-semibold">{displayName}</span>
          {renderCaption(contentText)}
        </p>

        <div className="mt-3 flex items-center justify-between text-xs">
          <span className={contentText.length > 2200 ? "font-semibold text-amber-700" : "text-slate-500"}>
            {contentText.length} / 2200 目安
          </span>
          {contentText.length > 2200 ? (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 font-semibold text-amber-700">
              長文です
            </span>
          ) : null}
        </div>
      </div>
    </article>
  );
}
