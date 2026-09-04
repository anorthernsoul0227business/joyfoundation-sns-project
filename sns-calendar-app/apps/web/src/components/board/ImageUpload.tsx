"use client";

import { useRef, useState } from "react";
import { requireSupabaseClient } from "../../lib/supabase";
import type { Attachment } from "../../lib/board";

/** 長辺の上限。これ以上大きくても投稿では使われないため、送る前に縮める */
const MAX_EDGE = 1600;

/**
 * ブラウザ側で画像を縮める。
 *
 * 圭一郎さんが iPhone で撮った写真はそのままだと数MBある。回線と保管量の節約に加え、
 * アップロードの待ち時間を短くする狙い。透過を保ちたい PNG はそのまま送る。
 */
async function shrink(file: File): Promise<Blob> {
  if (file.type === "image/png" && file.size < 1_000_000) return file;

  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, MAX_EDGE / Math.max(bitmap.width, bitmap.height));
  if (scale === 1 && file.size < 1_500_000) return file;

  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) return file;
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/jpeg", 0.85),
  );
  return blob ?? file;
}

export function ImageUpload({
  orgId,
  articleId,
  onUploaded,
}: {
  orgId: string;
  articleId: string;
  onUploaded: (added: Attachment) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  async function upload(file: File) {
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const supabase = requireSupabaseClient();
      const { data: sess } = await supabase.auth.getSession();
      const token = sess.session?.access_token;
      if (!token) throw new Error("ログインし直してください。");

      const blob = await shrink(file);
      const contentType = blob.type || file.type;

      // 同じサイトの API に送り、そこから R2 へ渡す。
      // R2 へ直接送る方式は R2 側の CORS 設定が要るため採らない（2026-09-04）
      const form = new FormData();
      form.append("orgId", orgId);
      form.append("file", new File([blob], file.name, { type: contentType }));

      const res = await fetch("/api/uploads", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });
      const info = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(info.error ?? "写真を追加できませんでした。");

      // 既存の写真の後ろに並べる
      const { count } = await supabase
        .from("attachments")
        .select("id", { count: "exact", head: true })
        .eq("owner_type", "article")
        .eq("owner_id", articleId);

      const { data, error: insertError } = await supabase
        .from("attachments")
        .insert({
          org_id: orgId,
          owner_type: "article",
          owner_id: articleId,
          storage_path: info.storagePath,
          public_url: info.publicUrl,
          mime_type: contentType,
          sort_order: count ?? 0,
          caption: file.name.replace(/\.[^.]+$/, "").slice(0, 60),
        })
        .select("id, owner_type, owner_id, public_url, mime_type, width, height, sort_order, caption")
        .single();
      if (insertError) throw new Error(insertError.message);

      onUploaded(data as Attachment);
      setDone(
        blob.size < file.size
          ? `写真を追加しました（${Math.round(file.size / 1024)}KB → ${Math.round(blob.size / 1024)}KB に縮小）`
          : "写真を追加しました。",
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const f = e.dataTransfer.files?.[0];
          if (f) void upload(f);
        }}
        className={
          "rounded border-2 border-dashed px-5 py-6 text-center transition " +
          (dragging ? "border-brand-ocean bg-brand-ocean/5" : "border-slate-300 bg-white")
        }
      >
        <p className="text-[0.95em] text-slate-600">
          {busy ? "送っています…" : "この記事に使う写真を追加できます"}
        </p>
        <p className="mt-1 hidden text-[0.82em] text-slate-500 md:block">
          ここに写真をドラッグしても追加できます
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={() => inputRef.current?.click()}
          className="mt-3 rounded-md border border-slate-300 bg-white px-6 py-3 text-[0.95em] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
        >
          写真を選ぶ
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void upload(f);
            e.target.value = "";
          }}
        />
      </div>
      {done && <p className="mt-2 text-[0.85em] text-brand-ocean">{done}</p>}
      {error && <p className="mt-2 text-[0.85em] text-rose-700">{error}</p>}
    </div>
  );
}
