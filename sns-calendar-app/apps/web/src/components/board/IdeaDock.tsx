"use client";

import { useState } from "react";
import { createIdea } from "../../lib/board";

/** 画面右下に常駐する「思いついたことを書く」入口 */
export function IdeaDock({
  orgId,
  userId,
  onCreated,
}: {
  orgId: string;
  userId: string;
  onCreated: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setMessage(null);
    try {
      await createIdea({ orgId, userId, body });
      setBody("");
      setMessage("メモを送りました。");
      onCreated();
      window.setTimeout(() => {
        setMessage(null);
        setOpen(false);
      }, 1500);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {!open && (
        <div className="fixed bottom-4 right-4 z-30 md:bottom-6 md:right-6">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="rounded-full bg-brand-ink px-4 py-3 text-[0.9em] font-semibold text-white shadow-lg transition hover:opacity-90 md:px-6 md:py-4 md:text-[1em]"
          >
            💡<span className="hidden md:inline"> 思いついたことを書く</span>
            <span className="md:hidden"> メモ</span>
          </button>
        </div>
      )}
      {open && (
        <div className="fixed inset-x-3 bottom-3 z-30 rounded-lg border border-slate-200 bg-white p-4 shadow-2xl md:inset-x-auto md:bottom-6 md:right-6 md:w-[min(26rem,calc(100vw-3rem))] md:p-5">
          <h3 className="text-[1em] font-semibold text-brand-ink">思いつきメモ</h3>
          <p className="mb-3 text-[0.82em] text-slate-500">一行でも大丈夫です。あとで康二郎さんが形にします。</p>
          <textarea
            autoFocus
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={4}
            placeholder="例：ハワイの話、そろそろ出してもいい頃かもしれない"
            className="w-full rounded border border-slate-200 bg-brand-sand/40 px-3 py-2.5 text-[0.98em] leading-relaxed outline-none focus:border-brand-ocean focus:bg-white"
          />
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              disabled={busy || body.trim() === ""}
              onClick={submit}
              className="rounded-md bg-brand-ocean px-5 py-2.5 font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
            >
              {busy ? "送っています…" : "送る"}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-md border border-slate-200 px-4 py-2.5 text-slate-500 transition hover:bg-slate-50"
            >
              閉じる
            </button>
            {message && <span className="ml-auto text-[0.82em] text-brand-ocean">{message}</span>}
          </div>
        </div>
      )}
    </>
  );
}
