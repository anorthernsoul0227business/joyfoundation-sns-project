"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  fetchDriveThumbnailBlob,
  importDriveImage,
  listDriveImages,
} from "../lib/api-client";
import type { DriveListResponse, MediaUploadItem } from "../generated/types.gen";

type DriveImagePickerProps = {
  open: boolean;
  onClose: () => void;
  onImported: (item: MediaUploadItem) => void;
};

type Crumb = { id?: string; name: string };

const ROOT_CRUMB: Crumb = { name: "共有フォルダ" };

// 認証必須のサムネイルを Bearer 付きで取得し object URL 化する小コンポーネント。
function DriveThumb({ fileId, alt }: { fileId: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let revoked = false;
    let objectUrl: string | null = null;
    setUrl(null);
    setFailed(false);
    fetchDriveThumbnailBlob(fileId)
      .then((blob) => {
        if (revoked) {
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => {
        if (!revoked) {
          setFailed(true);
        }
      });
    return () => {
      revoked = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [fileId]);

  if (failed) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-slate-100 text-xs text-slate-400">
        読み込み失敗
      </div>
    );
  }
  if (!url) {
    return <div className="h-full w-full animate-pulse bg-slate-200" />;
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img alt={alt} className="h-full w-full object-cover" src={url} />;
}

export function DriveImagePicker({ open, onClose, onImported }: DriveImagePickerProps) {
  const [stack, setStack] = useState<Crumb[]>([ROOT_CRUMB]);
  const [listing, setListing] = useState<DriveListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [autoResizeIg, setAutoResizeIg] = useState(false);
  const [importingId, setImportingId] = useState<string | null>(null);
  const [addedIds, setAddedIds] = useState<Set<string>>(new Set());

  const load = useCallback(async (folderId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await listDriveImages(folderId);
      setListing(result);
    } catch (err) {
      setListing(null);
      setError(
        err instanceof ApiError ? err.message : "Drive の読み込みに失敗しました",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // モーダルを開いたタイミングで初期化し、現在フォルダを読み込む。
  useEffect(() => {
    if (!open) {
      return;
    }
    setStack([ROOT_CRUMB]);
    setAddedIds(new Set());
    void load(undefined);
  }, [open, load]);

  if (!open) {
    return null;
  }

  const openFolder = (folder: { id: string; name: string }) => {
    setStack((prev) => [...prev, { id: folder.id, name: folder.name }]);
    void load(folder.id);
  };

  const goToCrumb = (index: number) => {
    const next = stack.slice(0, index + 1);
    setStack(next);
    void load(next[next.length - 1]?.id);
  };

  const handleImport = async (fileId: string) => {
    if (importingId) {
      return;
    }
    setImportingId(fileId);
    setError(null);
    try {
      const item = await importDriveImage(fileId, autoResizeIg);
      onImported(item);
      setAddedIds((prev) => new Set(prev).add(fileId));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "画像の取り込みに失敗しました",
      );
    } finally {
      setImportingId(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        aria-label="Google Drive から画像を選択"
        aria-modal="true"
        className="flex max-h-[85vh] w-full max-w-3xl flex-col overflow-hidden rounded-[1.5rem] bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="flex items-center justify-between gap-3 border-b border-brand-ink/10 px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-brand-ink">Google Drive から選ぶ</p>
            <nav className="mt-1 flex flex-wrap items-center gap-1 text-xs text-slate-500">
              {stack.map((crumb, index) => (
                <span className="flex items-center gap-1" key={`${crumb.id ?? "root"}-${index}`}>
                  {index > 0 ? <span>/</span> : null}
                  <button
                    className="rounded px-1 py-0.5 transition hover:text-brand-ocean"
                    onClick={() => goToCrumb(index)}
                    type="button"
                  >
                    {crumb.name}
                  </button>
                </span>
              ))}
            </nav>
          </div>
          <button
            aria-label="閉じる"
            className="rounded-full border border-brand-ink/10 px-3 py-1.5 text-sm font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
            onClick={onClose}
            type="button"
          >
            閉じる
          </button>
        </div>

        <label className="flex items-center gap-2 border-b border-brand-ink/10 px-5 py-3 text-sm text-slate-600">
          <input
            checked={autoResizeIg}
            onChange={(event) => setAutoResizeIg(event.target.checked)}
            type="checkbox"
          />
          Instagram 用に 4:5 へリサイズして取り込む
        </label>

        {error ? (
          <p className="border-b border-rose-100 bg-rose-50 px-5 py-3 text-sm text-rose-600">
            {error}
          </p>
        ) : null}

        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <p className="py-10 text-center text-sm text-slate-500">読み込み中…</p>
          ) : !listing ? (
            <p className="py-10 text-center text-sm text-slate-500">
              表示できる項目がありません
            </p>
          ) : (
            <div className="space-y-5">
              {listing.folders.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {listing.folders.map((folder) => (
                    <button
                      className="inline-flex items-center gap-2 rounded-[1rem] border border-brand-ink/10 bg-brand-sand/30 px-4 py-2 text-sm font-semibold text-brand-ink transition hover:border-brand-ocean hover:text-brand-ocean"
                      key={folder.id}
                      onClick={() => openFolder(folder)}
                      type="button"
                    >
                      📁 {folder.name}
                    </button>
                  ))}
                </div>
              ) : null}

              {listing.images.length > 0 ? (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                  {listing.images.map((image) => {
                    const isAdded = addedIds.has(image.id);
                    const isImporting = importingId === image.id;
                    return (
                      <button
                        className={`group relative aspect-square overflow-hidden rounded-[1rem] border transition ${
                          isAdded
                            ? "border-brand-ocean ring-2 ring-brand-ocean/40"
                            : "border-brand-ink/10 hover:border-brand-ocean"
                        } ${importingId && !isImporting ? "opacity-60" : ""}`}
                        disabled={Boolean(importingId)}
                        key={image.id}
                        onClick={() => void handleImport(image.id)}
                        title={image.name}
                        type="button"
                      >
                        <DriveThumb alt={image.name} fileId={image.id} />
                        {isImporting ? (
                          <span className="absolute inset-0 flex items-center justify-center bg-white/70 text-xs font-semibold text-brand-ocean">
                            取り込み中…
                          </span>
                        ) : null}
                        {isAdded && !isImporting ? (
                          <span className="absolute right-2 top-2 rounded-full bg-brand-ocean px-2 py-0.5 text-xs font-semibold text-white">
                            追加済み
                          </span>
                        ) : null}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p className="py-6 text-center text-sm text-slate-500">
                  このフォルダに画像はありません
                </p>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-brand-ink/10 px-5 py-3 text-right">
          <button
            className="rounded-full bg-brand-ocean px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-ocean/90"
            onClick={onClose}
            type="button"
          >
            完了
          </button>
        </div>
      </div>
    </div>
  );
}
