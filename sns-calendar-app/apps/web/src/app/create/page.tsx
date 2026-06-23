"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type DragEvent, Suspense, useEffect, useRef, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import type { PostCreate, PostResponse, PostUpdate } from "../../generated/types.gen";
import { DriveImagePicker } from "../../components/DriveImagePicker";
import { HelpMark } from "../../components/HelpMark";
import { PreviewPanel } from "../../components/preview/PreviewPanel";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import {
  ApiError,
  createPost,
  fetchPostDetail,
  publishPostNow,
  schedulePost,
  updatePost,
  uploadMedia,
} from "../../lib/api-client";
import { useAuthStore } from "../../stores/auth";

type PlatformValue = "x" | "ig" | "youtube" | "note" | "line";
type EditableStatus = "draft" | "scheduled";
type SubmitAction = "draft" | "schedule" | "publish";
type LoadState = "idle" | "loading" | "ready" | "not-found" | "error";

const platformEnum = z.enum(["x", "ig", "youtube", "note", "line"]);
const mediaEnum = z.enum(["image/png", "image/jpeg", "image/webp"]);

const createSchema = z.object({
  content_text: z
    .string()
    .min(1, "本文を入力してください")
    .max(10000, "本文は10000文字以内で入力してください"),
  platforms: z
    .array(platformEnum)
    .min(1, "SNSを1つ以上選択してください"),
  scheduled_at: z.string().optional(),
  media: z
    .array(
      z.object({
        storage_path: z.string().min(1, "画像URLを入力してください"),
        mime_type: mediaEnum,
      }),
    )
    .default([]),
});

type CreateFormValues = z.infer<typeof createSchema>;

const PLATFORM_OPTIONS: Array<{
  value: PlatformValue;
  label: string;
  shortLabel: string;
  hint: string;
  className: string;
}> = [
  {
    value: "x",
    label: "X",
    shortLabel: "X",
    hint: "280文字目安",
    className: "border-x/20 bg-x/5 text-x",
  },
  {
    value: "ig",
    label: "Instagram",
    shortLabel: "IG",
    hint: "2200文字目安",
    className: "border-ig/20 bg-ig/5 text-ig",
  },
  {
    value: "youtube",
    label: "YouTube",
    shortLabel: "YT",
    hint: "説明欄用",
    className: "border-yt/20 bg-yt/5 text-yt",
  },
  {
    value: "note",
    label: "note",
    shortLabel: "note",
    hint: "長文向け",
    className: "border-note/20 bg-note/5 text-note",
  },
  {
    value: "line",
    label: "LINE",
    shortLabel: "LINE",
    hint: "短文配信",
    className: "border-line/20 bg-line/5 text-line",
  },
];

const NON_EDITABLE_STATUSES = new Set<PostResponse["status"]>([
  "published",
  "publishing",
  "archived",
]);
const EMPTY_PLATFORMS: Array<PlatformValue> = [];
const EMPTY_MEDIA: Array<CreateFormValues["media"][number]> = [];

function toDatetimeLocal(value?: string | null) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const offset = date.getTimezoneOffset();
  const localDate = new Date(date.getTime() - offset * 60_000);
  return localDate.toISOString().slice(0, 16);
}

function toIsoString(value?: string) {
  if (!value) {
    return undefined;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }

  return date.toISOString();
}

function mapPostToFormValues(post: PostResponse): CreateFormValues {
  return {
    content_text: post.content_text,
    platforms: Array.from(new Set((post.targets ?? []).map((target) => target.platform))),
    scheduled_at: toDatetimeLocal(post.scheduled_at),
    media: (post.media ?? []).map((item) => ({
      storage_path: item.storage_path,
      mime_type:
        item.mime_type === "image/png" ||
        item.mime_type === "image/jpeg" ||
        item.mime_type === "image/webp"
          ? item.mime_type
          : "image/png",
    })),
  };
}

function buildCreatePayload(values: CreateFormValues, status: EditableStatus): PostCreate {
  return {
    content_text: values.content_text,
    media: values.media.map((item, index) => ({
      ...item,
      sort_order: index,
    })),
    platforms: values.platforms,
    scheduled_at: status === "scheduled" ? toIsoString(values.scheduled_at) : undefined,
    status,
  };
}

function getActionErrorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    return error.message || fallback;
  }

  return fallback;
}

function LoadingSkeleton() {
  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-7xl animate-pulse">
        <div className="rounded-[2rem] border border-brand-ink/10 bg-white/90 p-6 shadow-xl shadow-brand-ink/5">
          <div className="h-5 w-32 rounded bg-brand-sand" />
          <div className="mt-4 h-10 w-72 rounded bg-brand-sand" />
          <div className="mt-3 h-4 w-full max-w-2xl rounded bg-brand-sand" />
          <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_20rem]">
            <div className="space-y-4">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  className="rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/40 p-5"
                  key={index}
                >
                  <div className="h-4 w-28 rounded bg-brand-sand" />
                  <div className="mt-4 h-24 rounded-3xl bg-white" />
                </div>
              ))}
            </div>
            <div className="rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/40 p-5">
              <div className="h-4 w-24 rounded bg-brand-sand" />
              <div className="mt-4 h-64 rounded-3xl bg-white" />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

function toPreviewHandle(email?: string | null) {
  if (!email) {
    return "sns_calendar";
  }

  return (
    email
      .split("@")[0]
      ?.toLowerCase()
      .replace(/[^a-z0-9_]+/g, "_")
      .replace(/^_+|_+$/g, "") || "sns_calendar"
  );
}

function CreatePageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isReady } = useAuthGuard();
  const user = useAuthStore((state) => state.user);
  const postId = searchParams.get("id")?.trim() || null;
  const isEditMode = Boolean(postId);
  const [loadState, setLoadState] = useState<LoadState>(isEditMode ? "loading" : "ready");
  const [loadMessage, setLoadMessage] = useState<string | null>(null);
  const [apiMessage, setApiMessage] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<SubmitAction | null>(null);
  const [postDetail, setPostDetail] = useState<PostResponse | null>(null);
  const [currentStatus, setCurrentStatus] = useState<PostResponse["status"]>("draft");
  const [previewVisible, setPreviewVisible] = useState(false);

  const form = useForm<CreateFormValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      content_text: "",
      media: [],
      platforms: [],
      scheduled_at: "",
    },
  });

  const {
    control,
    formState: { errors, isSubmitting, isDirty },
    handleSubmit,
    register,
    reset,
    setError,
    watch,
  } = form;

  const { fields, append, remove } = useFieldArray({
    control,
    name: "media",
  });

  const [mediaUploadState, setMediaUploadState] = useState<{
    isUploading: boolean;
    error: string | null;
  }>({ isUploading: false, error: null });
  const [isDraggingMedia, setIsDraggingMedia] = useState(false);
  const [drivePickerOpen, setDrivePickerOpen] = useState(false);
  // dragenter / dragleave は子要素を跨ぐたびに発火するため、深さをカウントして
  // ゾーン全体から本当に離れたときだけハイライトを解除する。
  const dragDepthRef = useRef(0);

  const handleMediaUpload = async (
    files: FileList | File[] | null,
    options: { autoResizeIg: boolean },
  ) => {
    if (!files || files.length === 0) {
      return;
    }
    setMediaUploadState({ isUploading: true, error: null });
    try {
      const fileList = Array.from(files);
      const response = await uploadMedia(fileList, {
        autoResizeIg: options.autoResizeIg,
      });
      for (const item of response.media) {
        const mime = (item.mime_type ?? "image/jpeg") as
          | "image/png"
          | "image/jpeg"
          | "image/webp";
        append({
          storage_path: item.public_url,
          mime_type: mediaEnum.options.includes(mime) ? mime : "image/jpeg",
        });
      }
      setMediaUploadState({ isUploading: false, error: null });
    } catch (uploadError) {
      const message =
        uploadError instanceof ApiError
          ? uploadError.message
          : "画像アップロードに失敗しました";
      setMediaUploadState({ isUploading: false, error: message });
    }
  };

  const mediaDropDisabled = () => isReadonly || mediaUploadState.isUploading;

  const handleMediaDragOver = (event: DragEvent<HTMLDivElement>) => {
    if (mediaDropDisabled()) {
      return;
    }
    // drop を許可するには dragover で preventDefault が必須。
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  };

  const handleMediaDragEnter = (event: DragEvent<HTMLDivElement>) => {
    if (mediaDropDisabled()) {
      return;
    }
    event.preventDefault();
    dragDepthRef.current += 1;
    setIsDraggingMedia(true);
  };

  const handleMediaDragLeave = (event: DragEvent<HTMLDivElement>) => {
    if (mediaDropDisabled()) {
      return;
    }
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setIsDraggingMedia(false);
    }
  };

  const handleMediaDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    dragDepthRef.current = 0;
    setIsDraggingMedia(false);
    if (mediaDropDisabled()) {
      return;
    }
    const images = Array.from(event.dataTransfer.files).filter((file) =>
      file.type.startsWith("image/"),
    );
    if (images.length === 0) {
      setMediaUploadState({
        isUploading: false,
        error: "画像ファイル（JPEG / PNG / WebP）をドロップしてください",
      });
      return;
    }
    void handleMediaUpload(images, { autoResizeIg: false });
  };

  const watchedPlatforms = watch("platforms");
  const watchedMedia = watch("media");
  const contentText = watch("content_text") ?? "";
  const selectedPlatforms = watchedPlatforms ?? EMPTY_PLATFORMS;
  const scheduledAt = watch("scheduled_at") ?? "";
  const media = watchedMedia ?? EMPTY_MEDIA;
  const previewDisplayName = user?.displayName || user?.email || "SNS Calendar";
  const previewHandle = toPreviewHandle(user?.email);

  const isReadonly = postDetail ? NON_EDITABLE_STATUSES.has(postDetail.status) : false;
  const xCount = contentText.length;
  const igCount = contentText.length;
  const isXOverLimit = selectedPlatforms.includes("x") && xCount > 280;

  useEffect(() => {
    if (!isReady) {
      return;
    }

    if (!isEditMode || !postId) {
      setLoadState("ready");
      setPostDetail(null);
      setCurrentStatus("draft");
      reset({
        content_text: "",
        media: [],
        platforms: [],
        scheduled_at: "",
      });
      return;
    }

    let active = true;

    setLoadState("loading");
    setLoadMessage(null);
    setApiMessage(null);

    fetchPostDetail(postId)
      .then((post) => {
        if (!active) {
          return;
        }

        setPostDetail(post);
        setCurrentStatus(post.status);
        reset(mapPostToFormValues(post));
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }

        if (error instanceof ApiError && error.status === 404) {
          setLoadState("not-found");
          setLoadMessage("指定された投稿は見つかりませんでした。");
          return;
        }

        setLoadState("error");
        setLoadMessage("投稿の読み込みに失敗しました。時間をおいて再試行してください。");
      });

    return () => {
      active = false;
    };
  }, [isEditMode, isReady, postId, reset]);

  useEffect(() => {
    if (!apiMessage) {
      return;
    }

    const timer = window.setTimeout(() => {
      setApiMessage(null);
    }, 5000);

    return () => {
      window.clearTimeout(timer);
    };
  }, [apiMessage]);

  async function saveDraft(values: CreateFormValues) {
    if (!isEditMode || !postId) {
      await createPost(buildCreatePayload(values, "draft"));
      return;
    }

    const body: PostUpdate = {
      content_text: values.content_text,
      scheduled_at: null,
      status: "draft",
      platforms: values.platforms,
      media: values.media,
    };

    const updated = await updatePost(postId, body);
    setPostDetail(updated);
    setCurrentStatus(updated.status);
  }

  async function saveScheduled(values: CreateFormValues) {
    if (!values.scheduled_at) {
      setError("scheduled_at", {
        message: "予約日時を入力してください",
        type: "manual",
      });
      return;
    }

    const scheduledAtIso = toIsoString(values.scheduled_at);
    if (!scheduledAtIso) {
      setError("scheduled_at", {
        message: "予約日時の形式が正しくありません",
        type: "manual",
      });
      return;
    }

    if (!isEditMode || !postId) {
      await createPost(buildCreatePayload(values, "scheduled"));
      return;
    }

    await updatePost(postId, {
      content_text: values.content_text,
      platforms: values.platforms,
      media: values.media,
    });
    const scheduled = await schedulePost(postId, scheduledAtIso);
    setPostDetail(scheduled);
    setCurrentStatus(scheduled.status);
  }

  async function publishNow(values: CreateFormValues) {
    if (!isEditMode || !postId) {
      return false;
    }

    const confirmed = window.confirm("この内容で即時投稿しますか？");
    if (!confirmed) {
      return false;
    }

    await updatePost(postId, {
      content_text: values.content_text,
      platforms: values.platforms,
      media: values.media,
    });
    const published = await publishPostNow(postId);
    setPostDetail(published);
    setCurrentStatus(published.status);
    return true;
  }

  async function runAction(action: SubmitAction, values: CreateFormValues) {
    setPendingAction(action);
    setApiMessage(null);

    try {
      if (action === "draft") {
        await saveDraft(values);
        router.push("/drafts");
        return;
      }

      if (action === "schedule") {
        await saveScheduled(values);
        router.push("/drafts");
        return;
      }

      const published = await publishNow(values);
      if (!published) {
        return;
      }
      router.push("/drafts");
    } catch (error: unknown) {
      const fallback =
        action === "draft"
          ? "下書き保存に失敗しました。"
          : action === "schedule"
            ? "予約保存に失敗しました。"
            : "即時投稿に失敗しました。";
      setApiMessage(getActionErrorMessage(error, fallback));
    } finally {
      setPendingAction(null);
    }
  }

  function triggerAction(action: SubmitAction) {
    void handleSubmit(async (values) => {
      await runAction(action, values);
    })();
  }

  if (!isReady || loadState === "loading") {
    return <LoadingSkeleton />;
  }

  if (loadState === "not-found") {
    return (
      <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-3xl rounded-[2rem] border border-brand-ink/10 bg-white/90 p-8 text-center shadow-xl shadow-brand-ink/5">
          <p className="text-sm font-medium uppercase tracking-[0.28em] text-brand-ocean">
            Create Post
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-brand-ink">投稿が見つかりません</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">{loadMessage}</p>
          <div className="mt-6 flex justify-center">
            <Link
              className="inline-flex items-center rounded-full bg-brand-ocean px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
              href="/drafts"
            >
              下書き一覧へ戻る
            </Link>
          </div>
        </div>
      </main>
    );
  }

  if (loadState === "error") {
    return (
      <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-6 sm:px-6 sm:py-8">
        <div className="mx-auto max-w-3xl rounded-[2rem] border border-rose-200 bg-white/90 p-8 text-center shadow-xl shadow-brand-ink/5">
          <p className="text-sm font-medium uppercase tracking-[0.28em] text-rose-600">
            Create Post
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-rose-700">読み込みに失敗しました</h1>
          <p className="mt-4 text-sm leading-6 text-rose-600">{loadMessage}</p>
          <div className="mt-6 flex justify-center">
            <Link
              className="inline-flex items-center rounded-full bg-rose-600 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
              href="/drafts"
            >
              下書き一覧へ戻る
            </Link>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-7xl">
        <section className="rounded-[2rem] border border-brand-ink/10 bg-white/90 p-5 shadow-xl shadow-brand-ink/5 sm:p-6">
          <div className="flex flex-col gap-4 border-b border-brand-ink/10 pb-6">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.28em] text-brand-ocean">
                  Create Post
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-brand-ink">
                  {isEditMode ? "投稿を編集" : "投稿を作成"}
                </h1>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
                  本文、投稿先、予約日時、画像ストレージパスをまとめて設定します。
                  X の文字数超過は警告のみで、保存自体は継続できます。
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-3 xl:justify-end">
                <HelpMark
                  topic={
                    pendingAction === "publish"
                      ? "create.publish_now"
                      : pendingAction === "schedule"
                        ? "create.schedule"
                        : "create.save_draft"
                  }
                />
                <button
                  className="inline-flex items-center rounded-full border border-brand-ink/10 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand-ocean hover:text-brand-ocean disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isSubmitting || isReadonly}
                  onClick={() => triggerAction("draft")}
                  type="button"
                >
                  {pendingAction === "draft" ? (
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-ocean" />
                  ) : null}
                  下書き保存
                </button>
                <button
                  className="inline-flex items-center rounded-full bg-brand-ocean px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isSubmitting || isReadonly}
                  onClick={() => triggerAction("schedule")}
                  type="button"
                >
                  {pendingAction === "schedule" ? (
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  ) : null}
                  予約して保存
                </button>
                <button
                  className="inline-flex items-center rounded-full border border-amber-300 bg-amber-50 px-5 py-3 text-sm font-semibold text-amber-700 transition hover:bg-amber-100 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={isSubmitting || isReadonly || !isEditMode}
                  onClick={() => triggerAction("publish")}
                  type="button"
                >
                  {pendingAction === "publish" ? (
                    <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-amber-300 border-t-amber-700" />
                  ) : null}
                  即時投稿
                </button>
                <Link
                  className="inline-flex items-center rounded-full border border-brand-ink/10 px-5 py-3 text-sm font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                  href="/drafts"
                >
                  キャンセル
                </Link>
              </div>
            </div>

            {isEditMode ? (
              <div className="flex flex-wrap items-center gap-3 rounded-[1.25rem] border border-brand-ink/10 bg-brand-sand/35 px-4 py-3 text-sm text-slate-600">
                <span className="font-semibold text-brand-ink">編集モード</span>
                <span>Post ID: {postId}</span>
                <span>現在の状態: {currentStatus}</span>
                <input readOnly type="hidden" value={currentStatus} />
              </div>
            ) : null}

            {isReadonly ? (
              <div className="rounded-[1.5rem] border border-amber-200 bg-amber-50 px-5 py-4">
                <p className="text-sm font-semibold text-amber-800">
                  この投稿は公開済みのため編集できません
                </p>
                <p className="mt-2 text-sm leading-6 text-amber-700">
                  `published` / `publishing` / `archived` 状態の投稿は読み取り専用です。
                  内容確認のみ行い、一覧に戻ってください。
                </p>
              </div>
            ) : null}

            {apiMessage ? (
              <div className="rounded-[1.25rem] border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
                {apiMessage}
              </div>
            ) : null}
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.25fr)_22rem]">
            <form className="space-y-4" onSubmit={(event) => event.preventDefault()}>
              <section className="rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-semibold text-brand-ink" htmlFor="content_text">
                    本文
                  </label>
                  <HelpMark topic="create.content_text" />
                </div>
                <textarea
                  className="mt-4 min-h-56 w-full rounded-[1.5rem] border border-brand-ink/10 bg-brand-sand/20 px-4 py-4 text-sm leading-7 text-brand-ink outline-none transition focus:border-brand-ocean disabled:cursor-not-allowed disabled:opacity-70"
                  disabled={isReadonly}
                  id="content_text"
                  placeholder="投稿テキストを入力してください"
                  {...register("content_text")}
                />
                {errors.content_text ? (
                  <p className="mt-2 text-sm text-rose-600">{errors.content_text.message}</p>
                ) : null}

                <div className="mt-4 rounded-[1.25rem] border border-brand-ink/10 bg-brand-sand/35 p-4">
                  <div className="flex flex-wrap items-center gap-3 text-sm">
                    <span
                      className={`inline-flex rounded-full px-3 py-1.5 font-semibold ${
                        isXOverLimit
                          ? "bg-rose-100 text-rose-700"
                          : selectedPlatforms.includes("x")
                            ? "bg-x/10 text-x"
                            : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      X {xCount} / 280
                    </span>
                    <span
                      className={`inline-flex rounded-full px-3 py-1.5 font-semibold ${
                        selectedPlatforms.includes("ig")
                          ? "bg-ig/10 text-ig"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      IG {igCount} / 2200 目安
                    </span>
                  </div>
                  {isXOverLimit ? (
                    <p className="mt-3 text-sm text-rose-600">
                      X の目安 280 文字を超えています。保存は可能ですが、投稿前に短縮を検討してください。
                    </p>
                  ) : null}
                </div>
              </section>

              <section className="rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-brand-ink">投稿先SNS</p>
                  <HelpMark topic="create.platforms" />
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                  {PLATFORM_OPTIONS.map((option) => {
                    const checked = selectedPlatforms.includes(option.value);

                    return (
                      <label
                        className={`flex cursor-pointer items-start gap-3 rounded-[1.25rem] border px-4 py-3 transition ${
                          checked
                            ? `${option.className} border-current`
                            : "border-brand-ink/10 bg-brand-sand/20 text-slate-600 hover:border-brand-ocean"
                        } ${isReadonly ? "cursor-not-allowed opacity-70" : ""}`}
                        key={option.value}
                      >
                        <input
                          className="mt-1 h-4 w-4"
                          disabled={isReadonly}
                          type="checkbox"
                          value={option.value}
                          {...register("platforms")}
                        />
                        <span className="min-w-0">
                          <span className="block text-sm font-semibold">{option.label}</span>
                          <span className="block text-xs text-slate-500">{option.hint}</span>
                        </span>
                      </label>
                    );
                  })}
                </div>
                {errors.platforms ? (
                  <p className="mt-2 text-sm text-rose-600">{errors.platforms.message}</p>
                ) : null}
              </section>

              <section className="rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-sm">
                <div className="flex items-center gap-2">
                  <label className="text-sm font-semibold text-brand-ink" htmlFor="scheduled_at">
                    予約日時
                  </label>
                  <HelpMark topic="create.scheduled_at" />
                </div>
                <input
                  className="mt-4 w-full rounded-[1.25rem] border border-brand-ink/10 bg-brand-sand/20 px-4 py-3 text-sm text-brand-ink outline-none transition focus:border-brand-ocean disabled:cursor-not-allowed disabled:opacity-70"
                  disabled={isReadonly}
                  id="scheduled_at"
                  type="datetime-local"
                  {...register("scheduled_at")}
                />
                {errors.scheduled_at ? (
                  <p className="mt-2 text-sm text-rose-600">{errors.scheduled_at.message}</p>
                ) : null}
                <p className="mt-3 text-sm leading-6 text-slate-500">
                  予約して保存を押すときだけ必須です。下書き保存では空のままでも問題ありません。
                </p>
              </section>

              <section className="rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold text-brand-ink">画像 URL</p>
                    <HelpMark topic="create.media" />
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <label
                      className={`inline-flex cursor-pointer items-center rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean ${
                        isReadonly || mediaUploadState.isUploading
                          ? "cursor-not-allowed opacity-50"
                          : ""
                      }`}
                    >
                      {mediaUploadState.isUploading ? "アップロード中…" : "画像をアップロード"}
                      <input
                        accept="image/jpeg,image/png,image/webp"
                        className="hidden"
                        disabled={isReadonly || mediaUploadState.isUploading}
                        multiple
                        onChange={(event) => {
                          void handleMediaUpload(event.target.files, { autoResizeIg: false });
                          event.target.value = "";
                        }}
                        type="file"
                      />
                    </label>
                    <label
                      className={`inline-flex cursor-pointer items-center rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean ${
                        isReadonly || mediaUploadState.isUploading
                          ? "cursor-not-allowed opacity-50"
                          : ""
                      }`}
                      title="Instagram 用に 1080x1350 白余白パディングしてアップロードします"
                    >
                      IG向けリサイズ
                      <input
                        accept="image/jpeg,image/png,image/webp"
                        className="hidden"
                        disabled={isReadonly || mediaUploadState.isUploading}
                        multiple
                        onChange={(event) => {
                          void handleMediaUpload(event.target.files, { autoResizeIg: true });
                          event.target.value = "";
                        }}
                        type="file"
                      />
                    </label>
                    <button
                      className="inline-flex items-center rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={isReadonly}
                      onClick={() => setDrivePickerOpen(true)}
                      type="button"
                    >
                      Drive から選ぶ
                    </button>
                    <button
                      className="inline-flex items-center rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean disabled:cursor-not-allowed disabled:opacity-50"
                      disabled={isReadonly}
                      onClick={() =>
                        append({
                          mime_type: "image/png",
                          storage_path: "",
                        })
                      }
                      type="button"
                    >
                      + URL 手入力
                    </button>
                  </div>
                </div>
                {mediaUploadState.error ? (
                  <p className="mt-3 text-sm text-rose-600">{mediaUploadState.error}</p>
                ) : null}

                <DriveImagePicker
                  onClose={() => setDrivePickerOpen(false)}
                  onImported={(item) => {
                    const mime = (item.mime_type ?? "image/jpeg") as
                      | "image/png"
                      | "image/jpeg"
                      | "image/webp";
                    append({
                      storage_path: item.public_url,
                      mime_type: mediaEnum.options.includes(mime) ? mime : "image/jpeg",
                    });
                  }}
                  open={drivePickerOpen}
                />

                <div
                  className={`mt-4 space-y-3 rounded-[1.25rem] transition ${
                    isDraggingMedia
                      ? "outline-dashed outline-2 outline-offset-4 outline-brand-ocean/60"
                      : ""
                  }`}
                  onDragEnter={handleMediaDragEnter}
                  onDragLeave={handleMediaDragLeave}
                  onDragOver={handleMediaDragOver}
                  onDrop={handleMediaDrop}
                >
                  {fields.length === 0 ? (
                    <div
                      className={`rounded-[1.25rem] border border-dashed px-4 py-6 text-sm transition ${
                        isDraggingMedia
                          ? "border-brand-ocean bg-brand-ocean/5 text-brand-ocean"
                          : "border-brand-ink/15 bg-brand-sand/25 text-slate-500"
                      }`}
                    >
                      {isDraggingMedia
                        ? "ここに画像をドロップしてアップロード"
                        : "画像をここにドラッグ&ドロップ、または上のボタンからアップロードできます。URL を手入力することも可能です。"}
                    </div>
                  ) : null}

                  {fields.map((field, index) => (
                    <div
                      className="rounded-[1.25rem] border border-brand-ink/10 bg-brand-sand/20 p-4"
                      key={field.id}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-brand-ink">画像 {index + 1}</p>
                        <button
                          className="rounded-full border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-600 transition hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
                          disabled={isReadonly}
                          onClick={() => remove(index)}
                          type="button"
                        >
                          削除
                        </button>
                      </div>

                      <div className="mt-4">
                        <label
                          className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500"
                          htmlFor={`media-path-${index}`}
                        >
                          storage_path
                        </label>
                        <input
                          className="mt-2 w-full rounded-[1rem] border border-brand-ink/10 bg-white px-4 py-3 text-sm text-brand-ink outline-none transition focus:border-brand-ocean disabled:cursor-not-allowed disabled:opacity-70"
                          disabled={isReadonly}
                          id={`media-path-${index}`}
                          placeholder="uploads/posts/example.png"
                          {...register(`media.${index}.storage_path`)}
                        />
                        {errors.media?.[index]?.storage_path ? (
                          <p className="mt-2 text-sm text-rose-600">
                            {errors.media[index]?.storage_path?.message}
                          </p>
                        ) : null}
                      </div>

                      <div className="mt-4">
                        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                          mime_type
                        </span>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {(["image/png", "image/jpeg", "image/webp"] as const).map((mime) => (
                            <label
                              className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm transition ${
                                media[index]?.mime_type === mime
                                  ? "border-brand-ocean bg-brand-ocean/10 text-brand-ocean"
                                  : "border-brand-ink/10 bg-white text-slate-600"
                              } ${isReadonly ? "cursor-not-allowed opacity-70" : ""}`}
                              key={mime}
                            >
                              <input
                                className="h-4 w-4"
                                disabled={isReadonly}
                                type="radio"
                                value={mime}
                                {...register(`media.${index}.mime_type`)}
                              />
                              <span>{mime}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            </form>

            <aside className="space-y-4">
              <button
                className="inline-flex w-full items-center justify-center rounded-full border border-brand-ink/10 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-brand-ocean hover:text-brand-ocean xl:hidden"
                onClick={() => setPreviewVisible((current) => !current)}
                type="button"
              >
                {previewVisible ? "プレビューを閉じる" : "プレビューを表示"}
              </button>

              <div className={`${previewVisible ? "block" : "hidden"} xl:block`}>
                <PreviewPanel
                  contentText={contentText}
                  displayName={previewDisplayName}
                  handle={previewHandle}
                  isDirty={isDirty}
                  mediaPaths={media}
                  scheduledAt={scheduledAt}
                  selectedPlatforms={selectedPlatforms}
                />
              </div>
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}

export default function CreatePage() {
  return (
    <Suspense fallback={<LoadingSkeleton />}>
      <CreatePageContent />
    </Suspense>
  );
}
