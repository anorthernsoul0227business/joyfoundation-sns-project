"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import timeGridPlugin from "@fullcalendar/timegrid";
import jaLocale from "@fullcalendar/core/locales/ja";
import type {
  DatesSetArg,
  EventClickArg,
  EventContentArg,
} from "@fullcalendar/core";
import type { CalendarEvent, PostResponse } from "../../generated/types.gen";
import { HelpMark } from "../../components/HelpMark";
import { useAuthGuard } from "../../hooks/useAuthGuard";
import { fetchCalendarEvents, fetchPostDetail } from "../../lib/api-client";

type CalendarView = "dayGridMonth" | "timeGridWeek" | "timeGridDay";
type PlatformValue = "x" | "ig" | "youtube" | "note" | "line";
type CalendarRange = {
  from: string;
  to: string;
};

const PLATFORM_OPTIONS: Array<{ label: string; shortLabel: string; value: PlatformValue }> = [
  { label: "X", shortLabel: "X", value: "x" },
  { label: "Instagram", shortLabel: "IG", value: "ig" },
  { label: "YouTube", shortLabel: "YT", value: "youtube" },
  { label: "note", shortLabel: "note", value: "note" },
  { label: "LINE", shortLabel: "LINE", value: "line" },
];

const PLATFORM_STYLES: Record<
  PlatformValue,
  {
    badgeClass: string;
    eventClass: string;
    label: string;
  }
> = {
  x: {
    badgeClass: "bg-x text-white",
    eventClass: "bg-x text-white",
    label: "X",
  },
  ig: {
    badgeClass: "bg-ig text-white",
    eventClass: "bg-ig text-white",
    label: "Instagram",
  },
  youtube: {
    badgeClass: "bg-yt text-white",
    eventClass: "bg-yt text-white",
    label: "YouTube",
  },
  note: {
    badgeClass: "bg-note text-white",
    eventClass: "bg-note text-white",
    label: "note",
  },
  line: {
    badgeClass: "bg-line text-white",
    eventClass: "bg-line text-white",
    label: "LINE",
  },
};

const STATUS_LABELS: Record<CalendarEvent["status"], string> = {
  archived: "アーカイブ",
  draft: "下書き",
  failed: "失敗",
  published: "投稿済み",
  publishing: "投稿中",
  scheduled: "予約済み",
};

const DEFAULT_PLATFORMS = PLATFORM_OPTIONS.map((platform) => platform.value);

function getPlatformClass(platforms: Array<PlatformValue>) {
  return PLATFORM_STYLES[platforms[0] ?? "x"];
}

function formatEventTitle(title: string, platforms: Array<PlatformValue>) {
  if (platforms.length <= 1) {
    return title;
  }

  return `${title} +${platforms.length - 1}件`;
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "未設定";
  }

  return new Intl.DateTimeFormat("ja-JP", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function getPostPlatforms(post: PostResponse | null) {
  if (!post?.targets?.length) {
    return [];
  }

  return Array.from(new Set(post.targets.map((target) => target.platform)));
}

export default function CalendarPage() {
  const { isReady } = useAuthGuard();
  const calendarRef = useRef<FullCalendar | null>(null);
  const [initialView, setInitialView] = useState<CalendarView | null>(null);
  const [currentTitle, setCurrentTitle] = useState("");
  const [currentView, setCurrentView] = useState<CalendarView>("dayGridMonth");
  const [selectedPlatforms, setSelectedPlatforms] =
    useState<Array<PlatformValue>>(DEFAULT_PLATFORMS);
  const [visibleRange, setVisibleRange] = useState<CalendarRange | null>(null);
  const [calendarEvents, setCalendarEvents] = useState<Array<CalendarEvent>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [selectedPost, setSelectedPost] = useState<PostResponse | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    setInitialView(window.innerWidth < 640 ? "timeGridDay" : "dayGridMonth");
  }, []);

  useEffect(() => {
    if (!isReady || !visibleRange) {
      return;
    }

    if (selectedPlatforms.length === 0) {
      setCalendarEvents([]);
      setErrorMessage(null);
      return;
    }

    let active = true;

    setIsLoading(true);
    setErrorMessage(null);

    fetchCalendarEvents({
      from: visibleRange.from,
      to: visibleRange.to,
      platforms: selectedPlatforms,
    })
      .then((response) => {
        if (!active) {
          return;
        }

        setCalendarEvents(response.events);
      })
      .catch(() => {
        if (!active) {
          return;
        }

        setErrorMessage("カレンダーの取得に失敗しました。時間をおいて再試行してください。");
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [isReady, selectedPlatforms, visibleRange]);

  useEffect(() => {
    if (!selectedEventId) {
      return;
    }

    let active = true;

    setDetailLoading(true);
    setDetailError(null);

    fetchPostDetail(selectedEventId)
      .then((post) => {
        if (active) {
          setSelectedPost(post);
        }
      })
      .catch(() => {
        if (active) {
          setDetailError("投稿詳細の取得に失敗しました。");
        }
      })
      .finally(() => {
        if (active) {
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedEventId]);

  function handleDatesSet(arg: DatesSetArg) {
    setCurrentTitle(arg.view.title);
    setCurrentView(arg.view.type as CalendarView);
    setVisibleRange({
      from: arg.view.activeStart.toISOString(),
      to: arg.view.activeEnd.toISOString(),
    });
  }

  function handleTogglePlatform(platform: PlatformValue) {
    setSelectedPost(null);
    setSelectedEventId(null);
    setSelectedPlatforms((current) =>
      current.includes(platform)
        ? current.filter((item) => item !== platform)
        : [...current, platform],
    );
  }

  function handleChangeView(view: CalendarView) {
    calendarRef.current?.getApi().changeView(view);
  }

  function handleEventClick(arg: EventClickArg) {
    setSelectedEventId(arg.event.id);
    setSelectedPost(null);
  }

  function renderEventContent(arg: EventContentArg) {
    const platforms = (arg.event.extendedProps.platforms ?? []) as Array<PlatformValue>;
    const platformStyle = getPlatformClass(platforms);

    return (
      <div className="min-w-0">
        <div className="flex items-center gap-1.5">
          {arg.timeText ? <span className="text-[10px] font-semibold">{arg.timeText}</span> : null}
          <span
            className={`inline-flex rounded-full px-1.5 py-0.5 text-[10px] font-semibold ${platformStyle.badgeClass}`}
          >
            {platformStyle.label}
          </span>
        </div>
        <p className="mt-1 truncate text-[11px] font-semibold">
          {formatEventTitle(arg.event.title, platforms)}
        </p>
      </div>
    );
  }

  function getEventClassNames(arg: EventContentArg) {
    const platforms = (arg.event.extendedProps.platforms ?? []) as Array<PlatformValue>;
    const status = arg.event.extendedProps.status as CalendarEvent["status"];
    const platformClass = getPlatformClass(platforms);
    const classNames = [
      "calendar-event-chip",
      platformClass.eventClass,
      "border-transparent",
      "shadow-sm",
    ];

    if (status === "failed") {
      classNames.push("border-2", "border-rose-500");
    }

    if (status === "published") {
      classNames.push("opacity-60", "grayscale");
    }

    return classNames;
  }

  if (!isReady || !initialView) {
    return (
      <main className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-brand-sand px-6">
        <div className="rounded-3xl border border-brand-ink/10 bg-white px-6 py-4 text-sm text-slate-500 shadow-sm">
          カレンダーを準備しています...
        </div>
      </main>
    );
  }

  const detailPlatforms = getPostPlatforms(selectedPost);

  return (
    <main className="min-h-[calc(100vh-4rem)] bg-brand-sand px-4 py-6 sm:px-6 sm:py-8">
      <div className="mx-auto max-w-7xl">
        <div className="rounded-[2rem] border border-brand-ink/10 bg-white/90 p-5 shadow-xl shadow-brand-ink/5 sm:p-6">
          <div className="flex flex-col gap-4 border-b border-brand-ink/10 pb-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.28em] text-brand-ocean">
                  Posting Calendar
                </p>
                <h1 className="mt-2 text-3xl font-semibold text-brand-ink">{currentTitle}</h1>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  予約済み・投稿済みの予定を SNS ごとに確認できます。ドラッグ配置は次の
                  Sprint で追加予定です。
                </p>
              </div>

              <div className="flex flex-col gap-3 sm:items-end">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    className="rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                    onClick={() => calendarRef.current?.getApi().prev()}
                    type="button"
                  >
                    前へ
                  </button>
                  <button
                    className="rounded-full border border-brand-ocean bg-brand-ocean px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
                    onClick={() => calendarRef.current?.getApi().today()}
                    type="button"
                  >
                    今日
                  </button>
                  <button
                    className="rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                    onClick={() => calendarRef.current?.getApi().next()}
                    type="button"
                  >
                    次へ
                  </button>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <button
                    className="cursor-not-allowed rounded-full border border-brand-ink/10 bg-slate-100 px-4 py-2 text-sm font-medium text-slate-400"
                    disabled
                    type="button"
                  >
                    + 新規投稿
                  </button>
                  <HelpMark topic="calendar.new_post" />
                  <Link
                    className="rounded-full border border-brand-ink/10 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-brand-ocean hover:text-brand-ocean"
                    href="/"
                  >
                    ホームへ戻る
                  </Link>
                </div>
              </div>
            </div>

            <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-brand-ink">SNS フィルタ</p>
                  <HelpMark topic="calendar.platform_filter" />
                </div>
                <div className="flex flex-wrap gap-2">
                  {PLATFORM_OPTIONS.map((platform) => {
                    const checked = selectedPlatforms.includes(platform.value);
                    const styles = PLATFORM_STYLES[platform.value];

                    return (
                      <label
                        className={`inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-2 text-sm font-medium transition ${
                          checked
                            ? "border-transparent bg-brand-ink text-white"
                            : "border-brand-ink/10 bg-white text-slate-500 hover:border-brand-ocean hover:text-brand-ocean"
                        }`}
                        key={platform.value}
                      >
                        <input
                          checked={checked}
                          className="sr-only"
                          onChange={() => handleTogglePlatform(platform.value)}
                          type="checkbox"
                        />
                        <span
                          className={`inline-flex min-w-10 justify-center rounded-full px-2 py-0.5 text-xs font-semibold ${styles.badgeClass}`}
                        >
                          {platform.shortLabel}
                        </span>
                        {platform.label}
                      </label>
                    );
                  })}
                </div>
              </div>

              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-brand-ink">表示切替</p>
                  <HelpMark topic="calendar.view_toggle" />
                </div>
                <div className="flex flex-wrap gap-2">
                  {[
                    { label: "月", value: "dayGridMonth" },
                    { label: "週", value: "timeGridWeek" },
                    { label: "日", value: "timeGridDay" },
                  ].map((view) => (
                    <button
                      className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                        currentView === view.value
                          ? "bg-brand-ocean text-white"
                          : "border border-brand-ink/10 bg-white text-slate-600 hover:border-brand-ocean hover:text-brand-ocean"
                      }`}
                      key={view.value}
                      onClick={() => handleChangeView(view.value as CalendarView)}
                      type="button"
                    >
                      {view.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
            <section className="space-y-4">
              {errorMessage ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {errorMessage}
                </div>
              ) : null}
              {selectedPlatforms.length === 0 ? (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                  表示する SNS を 1 つ以上選択してください。
                </div>
              ) : null}

              <div className="calendar-shell overflow-hidden rounded-[1.5rem] border border-brand-ink/10 bg-[#fcfaf6] p-3 shadow-inner shadow-brand-ink/5 sm:p-4">
                {isLoading ? (
                  <div className="mb-3 rounded-2xl bg-white/80 px-4 py-3 text-sm text-slate-500">
                    表示範囲の投稿予定を読み込んでいます...
                  </div>
                ) : null}

                <FullCalendar
                  allDaySlot={false}
                  datesSet={handleDatesSet}
                  dayMaxEvents={3}
                  eventClassNames={getEventClassNames}
                  eventClick={handleEventClick}
                  eventContent={renderEventContent}
                  events={calendarEvents.map((event) => ({
                    id: event.id,
                    start: event.start,
                    title: event.title,
                    extendedProps: {
                      platforms: (event.platforms ?? []) as Array<PlatformValue>,
                      status: event.status,
                    },
                  }))}
                  expandRows
                  headerToolbar={false}
                  height="auto"
                  initialView={initialView}
                  locale={jaLocale}
                  moreLinkClassNames="text-brand-ocean"
                  nowIndicator
                  plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
                  ref={calendarRef}
                  slotMaxTime="24:00:00"
                  slotMinTime="06:00:00"
                  stickyHeaderDates
                />
              </div>

              <div className="flex flex-wrap items-center gap-4 rounded-2xl border border-brand-ink/10 bg-white px-4 py-3 text-xs text-slate-500">
                {PLATFORM_OPTIONS.map((platform) => (
                  <span className="inline-flex items-center gap-2" key={platform.value}>
                    <span
                      className={`inline-flex h-2.5 w-2.5 rounded-full ${PLATFORM_STYLES[platform.value].badgeClass}`}
                    />
                    {platform.label}
                  </span>
                ))}
                <span className="text-slate-400">失敗した投稿は赤枠、投稿済みは淡色表示です。</span>
              </div>
            </section>

            <aside className="rounded-[1.5rem] border border-brand-ink/10 bg-white p-5 shadow-lg shadow-brand-ink/5 xl:sticky xl:top-24 xl:h-fit">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-semibold text-brand-ink">投稿詳細</h2>
                <HelpMark topic="calendar.event_click" />
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                カレンダー上のイベントをクリックすると、投稿本文と配信状態を確認できます。
              </p>

              {detailLoading ? (
                <div className="mt-6 rounded-2xl bg-brand-sand/60 px-4 py-4 text-sm text-slate-500">
                  詳細を読み込んでいます...
                </div>
              ) : null}

              {detailError ? (
                <div className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {detailError}
                </div>
              ) : null}

              {!detailLoading && !detailError && !selectedPost ? (
                <div className="mt-6 rounded-[1.5rem] border border-dashed border-brand-ink/15 bg-brand-sand/40 px-4 py-6 text-sm leading-6 text-slate-500">
                  右側のパネルには、選択した投稿の本文・予約時刻・配信先 SNS を表示します。
                </div>
              ) : null}

              {selectedPost ? (
                <div className="mt-6 space-y-5">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand-ocean">
                      Status
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="rounded-full bg-brand-sand px-3 py-1 text-sm font-medium text-brand-ink">
                        {STATUS_LABELS[selectedPost.status]}
                      </span>
                      {detailPlatforms.map((platform) => (
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold ${PLATFORM_STYLES[platform].badgeClass}`}
                          key={platform}
                        >
                          {PLATFORM_STYLES[platform].label}
                        </span>
                      ))}
                    </div>
                  </div>

                  <dl className="space-y-4 text-sm text-slate-600">
                    <div>
                      <dt className="font-medium text-brand-ink">予約時刻</dt>
                      <dd className="mt-1">{formatDateTime(selectedPost.scheduled_at)}</dd>
                    </div>
                    <div>
                      <dt className="font-medium text-brand-ink">更新日時</dt>
                      <dd className="mt-1">{formatDateTime(selectedPost.updated_at)}</dd>
                    </div>
                  </dl>

                  <div>
                    <p className="text-sm font-medium text-brand-ink">投稿本文</p>
                    <div className="mt-2 rounded-[1.25rem] bg-brand-sand/50 px-4 py-4 text-sm leading-7 text-slate-700">
                      <p className="whitespace-pre-wrap break-words">{selectedPost.content_text}</p>
                    </div>
                  </div>
                </div>
              ) : null}
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}
