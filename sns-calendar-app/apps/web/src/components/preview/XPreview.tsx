"use client";

type PreviewMedia = {
  mime_type: string;
  storage_path: string;
};

type XPreviewProps = {
  contentText: string;
  displayName: string;
  handle: string;
  mediaPaths: PreviewMedia[];
  scheduledAt?: string;
};

function formatScheduledAt(value?: string) {
  if (!value) {
    return "Now";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Now";
  }

  return `Scheduled for ${date.toLocaleString("ja-JP", {
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    month: "numeric",
  })}`;
}

function getInitial(label: string) {
  return label.trim().slice(0, 1).toUpperCase() || "U";
}

export function XPreview({ contentText, displayName, handle, mediaPaths, scheduledAt }: XPreviewProps) {
  const hasText = contentText.trim().length > 0;
  const visibleMedia = mediaPaths.slice(0, 4);
  const overflowText = contentText.slice(280);
  const safeText = hasText ? contentText : "ここに X 向け本文が表示されます。";

  return (
    <article className="rounded-[1.5rem] border border-x/15 bg-white shadow-sm">
      <div className="border-b border-x/10 bg-x/5 px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-x">X Preview</p>
            <p className="mt-1 text-xs text-slate-500">{formatScheduledAt(scheduledAt)}</p>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              contentText.length > 280 ? "bg-rose-100 text-rose-700" : "bg-white text-slate-600"
            }`}
          >
            {contentText.length} / 280
          </span>
        </div>
      </div>

      <div className={`p-4 ${contentText.length > 280 ? "bg-rose-50/60" : ""}`}>
        <div className="flex items-start gap-3">
          <div
            aria-label="プロフィール画像"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-x/15 text-sm font-bold text-x"
            role="img"
          >
            {getInitial(displayName)}
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className="text-sm font-semibold text-brand-ink">{displayName}</span>
              <span className="text-sm text-slate-500">@{handle}</span>
              <span className="text-sm text-slate-400">·</span>
              <span className="text-sm text-slate-400">Just now</span>
            </div>

            <div className="mt-3 whitespace-pre-wrap text-sm leading-6 text-brand-ink">
              <span className={hasText ? "" : "text-slate-400"}>{safeText.slice(0, 280)}</span>
              {overflowText ? <span className="text-rose-600">{overflowText}</span> : null}
            </div>

            {visibleMedia.length > 0 ? (
              <div
                className={`mt-4 grid gap-2 ${
                  visibleMedia.length === 1 ? "grid-cols-1" : "grid-cols-2"
                }`}
              >
                {visibleMedia.map((item, index) => (
                  <div
                    className={`relative overflow-hidden rounded-[1.25rem] border border-brand-ink/10 bg-slate-200 ${
                      visibleMedia.length === 1 ? "aspect-[16/10]" : "aspect-square"
                    }`}
                    key={`${item.storage_path}-${index}`}
                  >
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-200 via-slate-100 to-slate-200 text-center text-xs text-slate-500">
                      <div className="space-y-2 px-4">
                        <p className="font-semibold text-slate-600">{item.mime_type}</p>
                        <p className="line-clamp-2 break-all">{item.storage_path}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}

            <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
              <span>💬 返信</span>
              <span>🔁 リポスト</span>
              <span>❤️ いいね</span>
              <span>📤 共有</span>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}
