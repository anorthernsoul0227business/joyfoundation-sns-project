"use client";

import { ANNOUNCE_NOTES, ANNOUNCE_RULES, GUIDE } from "../../lib/rules";

export function AnnounceRuleTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[30rem] border-collapse text-[0.88em]">
        <thead>
          <tr className="border-b border-slate-300 text-left text-slate-600">
            <th className="py-2 pr-3 font-semibold">開催まで</th>
            <th className="py-2 pr-3 font-semibold">X</th>
            <th className="py-2 pr-3 font-semibold">Instagram</th>
            <th className="py-2 font-semibold">note</th>
          </tr>
        </thead>
        <tbody>
          {ANNOUNCE_RULES.map((r) => (
            <tr key={r.when} className="border-b border-slate-200 align-top">
              <td className="py-2 pr-3 font-semibold text-brand-ink">{r.when}</td>
              <td className="py-2 pr-3 text-slate-700">{r.x}</td>
              <td className="py-2 pr-3 text-slate-700">{r.ig}</td>
              <td className="py-2 text-slate-700">{r.note}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function GuidePanel() {
  return (
    <div className="mx-auto max-w-[46rem]">
      <p className="mb-4 rounded border border-slate-200 bg-white px-5 py-3 text-[0.92em] text-slate-600">
        更新の記録は「🔎 やること」の中にまとめました。
      </p>
      <div className="space-y-4">
        {GUIDE.map((section) => (
          <section
            key={section.title}
            className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm"
          >
            <h3 className="mb-3 text-[1.08em] font-semibold text-brand-ink">{section.title}</h3>
            <div className="space-y-3">
              {section.items.map((item, i) => (
                <div key={i}>
                  {item.heading && (
                    <p className="text-[0.92em] font-semibold text-slate-700">{item.heading}</p>
                  )}
                  <p className="whitespace-pre-wrap text-[0.94em] leading-relaxed text-slate-700">
                    {item.body}
                  </p>
                </div>
              ))}
            </div>
          </section>
        ))}

        <section className="rounded border border-slate-200 bg-white px-5 py-4 shadow-sm">
          <h3 className="mb-1 text-[1.08em] font-semibold text-brand-ink">
            イベントの告知の決まり
          </h3>
          <p className="mb-3 text-[0.9em] text-slate-600">
            とくにご指定がなければ、開催までの日数に応じてこの回数で告知します。
          </p>
          <AnnounceRuleTable />
          <ul className="mt-3 space-y-1.5 text-[0.9em] leading-relaxed text-slate-700">
            {ANNOUNCE_NOTES.map((n) => (
              <li key={n} className="flex gap-2">
                <span aria-hidden className="text-slate-400">
                  ・
                </span>
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  );
}
