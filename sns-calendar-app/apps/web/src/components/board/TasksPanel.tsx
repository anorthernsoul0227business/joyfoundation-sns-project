"use client";

import { useCallback, useEffect, useState } from "react";
import { CHANGELOG } from "../../lib/changelog";
import {
  decideTask,
  formatDateJa,
  formatDateTimeJa,
  listTasks,
  TASK_KIND_LABEL,
  TASK_SOURCE_LABEL,
  TASK_STATUS_LABEL,
  type Task,
} from "../../lib/board";

const TONE: Record<Task["status"], string> = {
  open: "bg-slate-100 text-slate-600",
  proposed: "bg-amber-100 text-amber-900",
  approved: "bg-brand-ocean/10 text-brand-ocean",
  done: "bg-emerald-100 text-emerald-800",
  rejected: "bg-rose-50 text-rose-700",
  dismissed: "bg-slate-100 text-slate-500",
};

function TaskCard({
  task,
  userId,
  onChanged,
}: {
  task: Task;
  userId: string;
  onChanged: (next: Task) => void;
}) {
  const [open, setOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const waiting = task.status === "proposed";

  async function decide(approve: boolean) {
    setBusy(approve ? "approve" : "reject");
    setError(null);
    try {
      onChanged(await decideTask({ task, approve, note, userId }));
      setRejectOpen(false);
      setNote("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <li className="rounded border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start gap-3 px-5 py-4 text-left transition hover:bg-slate-50"
      >
        <span className="mt-0.5 text-slate-400" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
        <span className="min-w-0 flex-1">
          <span className="mb-1 flex flex-wrap items-center gap-2 text-[0.78em]">
            <span className={`rounded px-2 py-0.5 font-semibold ${TONE[task.status]}`}>
              {TASK_STATUS_LABEL[task.status]}
            </span>
            <span className="text-slate-500">{TASK_SOURCE_LABEL[task.source]}</span>
            <span className="text-slate-400">{formatDateJa(task.created_at)}</span>
          </span>
          <span className="block text-[1.02em] font-semibold text-brand-ink">{task.title}</span>
        </span>
      </button>

      {open && (
        <div className="border-t border-slate-200 px-5 py-4">
          {task.detail && (
            <div className="mb-3">
              <div className="mb-1 text-[0.78em] font-semibold tracking-wider text-slate-500">
                もとになった内容
              </div>
              <p className="whitespace-pre-wrap text-[0.92em] leading-relaxed text-slate-700">
                {task.detail}
              </p>
            </div>
          )}

          {task.proposal && (
            <div className="rounded border-2 border-amber-300 bg-amber-50 px-5 py-4">
              <div className="mb-1 text-[0.8em] font-semibold tracking-wider text-amber-900">
                こう直そうと思います
              </div>
              {task.proposal_kind && (
                <p className="mb-2 text-[0.85em] font-semibold text-amber-900">
                  {TASK_KIND_LABEL[task.proposal_kind]}
                </p>
              )}
              <p className="whitespace-pre-wrap text-[0.95em] leading-relaxed text-amber-900">
                {task.proposal}
              </p>
            </div>
          )}

          {task.result_note && (
            <p className="mt-3 rounded bg-emerald-50 px-4 py-3 text-[0.92em] text-emerald-900">
              {task.result_note}
              {task.done_at && (
                <span className="ml-2 text-[0.85em] text-emerald-700">
                  （{formatDateTimeJa(task.done_at)}）
                </span>
              )}
            </p>
          )}

          {task.decision_note && task.status === "rejected" && (
            <p className="mt-3 rounded bg-rose-50 px-4 py-3 text-[0.92em] text-rose-900">
              いただいたご指摘：{task.decision_note}
              <span className="mt-1 block text-[0.85em]">
                これをふまえて、あらためて案を考えます。
              </span>
            </p>
          )}

          {waiting && (
            <div className="mt-4">
              <div className="flex flex-col gap-3 md:flex-row">
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => decide(true)}
                  className="w-full rounded-md bg-brand-ocean px-8 py-3.5 text-[1em] font-semibold text-white transition hover:brightness-110 disabled:opacity-60 md:w-auto"
                >
                  {busy === "approve" ? "送っています…" : "これでお願いします"}
                </button>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => setRejectOpen((v) => !v)}
                  aria-expanded={rejectOpen}
                  className="w-full rounded-md border border-slate-300 bg-white px-8 py-3.5 text-[1em] font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60 md:w-auto"
                >
                  そうではありません
                </button>
              </div>

              {rejectOpen && (
                <div className="mt-3">
                  <p className="mb-2 text-[0.85em] text-slate-500">
                    どこが違うかをお書きください。それをふまえて考え直します。
                  </p>
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    rows={3}
                    className="w-full rounded border border-slate-200 bg-brand-sand/40 px-4 py-3 text-[0.98em] leading-relaxed outline-none focus:border-brand-ocean focus:bg-white"
                  />
                  <button
                    type="button"
                    disabled={busy !== null || note.trim() === ""}
                    onClick={() => decide(false)}
                    className="mt-2 w-full rounded-md bg-brand-ink px-6 py-3 font-semibold text-white transition hover:opacity-90 disabled:opacity-50 md:w-auto"
                  >
                    {busy === "reject" ? "送っています…" : "これで送る"}
                  </button>
                </div>
              )}
            </div>
          )}

          {error && <p className="mt-3 text-[0.88em] text-rose-700">{error}</p>}
        </div>
      )}
    </li>
  );
}

export function TasksPanel({ userId, reloadKey }: { userId: string; reloadKey: number }) {
  const [tab, setTab] = useState<"todo" | "done">("todo");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTasks(await listTasks(true));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, reloadKey]);

  const todo = tasks.filter((t) => ["open", "proposed", "approved", "rejected"].includes(t.status));
  const done = tasks.filter((t) => ["done", "dismissed"].includes(t.status));
  const waiting = todo.filter((t) => t.status === "proposed").length;

  return (
    <div className="mx-auto max-w-[46rem]">
      <div className="mb-4 flex flex-wrap gap-2">
        {([
          ["todo", `やること${todo.length > 0 ? `（${todo.length}）` : ""}`],
          ["done", "終わったこと・更新の記録"],
        ] as const).map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={tab === value}
            onClick={() => setTab(value)}
            className={
              "rounded-full border px-4 py-2 text-[0.9em] transition " +
              (tab === value
                ? "border-brand-ink bg-brand-ink font-semibold text-white"
                : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50")
            }
          >
            {label}
          </button>
        ))}
      </div>

      {error && (
        <p className="mb-3 rounded border border-rose-200 bg-rose-50 px-4 py-2 text-[0.88em] text-rose-700">
          {error}
        </p>
      )}

      {tab === "todo" ? (
        <>
          {waiting > 0 && (
            <p className="mb-4 rounded border border-amber-300 bg-amber-50 px-5 py-3 text-[0.95em] text-amber-900">
              <strong>{waiting}件</strong>
              について、こう直そうという案があります。押して中身をご覧いただき、
              よければ「これでお願いします」を押してください。
            </p>
          )}
          {todo.length === 0 ? (
            <p className="rounded border border-slate-200 bg-white px-5 py-10 text-center text-[0.95em] text-slate-500">
              {loading ? "読み込んでいます…" : "いまやることはありません。"}
            </p>
          ) : (
            <ul className="space-y-3">
              {todo.map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  userId={userId}
                  onChanged={(next) =>
                    setTasks((prev) => prev.map((x) => (x.id === next.id ? next : x)))
                  }
                />
              ))}
            </ul>
          )}
        </>
      ) : (
        <div className="space-y-6">
          {done.length > 0 && (
            <section>
              <h3 className="mb-2 text-[1.05em] font-semibold text-brand-ink">
                やり終えたこと
              </h3>
              <ul className="space-y-3">
                {done.map((t) => (
                  <TaskCard
                    key={t.id}
                    task={t}
                    userId={userId}
                    onChanged={(next) =>
                      setTasks((prev) => prev.map((x) => (x.id === next.id ? next : x)))
                    }
                  />
                ))}
              </ul>
            </section>
          )}
          <section>
            <h3 className="mb-2 text-[1.05em] font-semibold text-brand-ink">画面の更新</h3>
            <ul className="space-y-3">
              {CHANGELOG.map((c, i) => (
                <li key={i} className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
                  <p className="text-[0.8em] text-slate-500">{formatDateJa(c.date)}</p>
                  <p className="mt-1 text-[1.02em] font-semibold text-brand-ink">{c.title}</p>
                  <p className="mt-1 text-[0.94em] leading-relaxed text-slate-700">{c.body}</p>
                  {c.from && (
                    <p className="mt-2 rounded bg-brand-sand/60 px-4 py-2 text-[0.88em] text-slate-600">
                      きっかけ：「{c.from}」
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}
