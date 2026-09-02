"use client";

import { useMemo } from "react";

/**
 * 直す前と直した後の差分を、文単位で色分けして見せる。
 *
 * 2026-09-02: はじめ文字単位で差分を取っていたが、変わった文字が飛び飛びに
 * 色付くため読みにくかった。「1文ごと消して、修正も文ごと見せる」方が
 * 分かりやすいという指摘を受けて、文単位に変更した。
 */
type Part = { text: string; kind: "same" | "added" | "removed" };

/**
 * 文に切る。「。！？」の後（閉じ括弧と続く改行を含む）か、空行で区切る。
 *
 * Instagram の本文は読みやすさのために一文の途中で改行を入れている。
 * 単独の改行で切ると「私たちは、音に合わせて」のような断片になってしまうため、
 * 文中の改行では切らない。
 */
function splitSentences(text: string): string[] {
  return (text.match(/[\s\S]*?(?:[。！？]+[」』）】]*\n*|\n{2,}|$)/g) ?? []).filter(
    (s) => s !== "",
  );
}

function diffSentences(before: string, after: string): Part[] {
  const a = splitSentences(before);
  const b = splitSentences(after);

  // 文の数は多くても数十なので、そのまま最長共通部分列を取る
  const dp: number[][] = Array.from({ length: a.length + 1 }, () =>
    new Array<number>(b.length + 1).fill(0),
  );
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const parts: Part[] = [];
  const push = (text: string, kind: Part["kind"]) => {
    const last = parts[parts.length - 1];
    // 同じ種類が続くときはまとめる。ただし消した文と足した文の間は分けたまま
    if (last && last.kind === kind) last.text += text;
    else parts.push({ text, kind });
  };

  let i = 0;
  let j = 0;
  while (i < a.length && j < b.length) {
    if (a[i] === b[j]) {
      push(a[i], "same");
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      push(a[i], "removed");
      i++;
    } else {
      push(b[j], "added");
      j++;
    }
  }
  while (i < a.length) push(a[i++], "removed");
  while (j < b.length) push(b[j++], "added");
  return parts;
}

export function BodyDiff({ before, after }: { before: string; after: string }) {
  const parts = useMemo(() => diffSentences(before, after), [before, after]);
  const changed = parts.some((p) => p.kind !== "same");

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.78em] text-slate-500">
        <span className="rounded bg-rose-100 px-1.5 py-0.5 text-rose-800 line-through">前の文</span>
        <span>を消して</span>
        <span className="rounded bg-emerald-100 px-1.5 py-0.5 text-emerald-900">新しい文</span>
        <span>にしました</span>
      </div>
      <div className="rounded border border-slate-200 bg-white px-4 py-5 text-[1.02em] leading-[2.1] shadow-sm md:px-8 md:py-7 md:leading-[2.2]">
        {!changed ? (
          <span className="text-slate-500">変わったところはありません。</span>
        ) : (
          parts.map((p, i) =>
            p.kind === "same" ? (
              <span key={i} className="whitespace-pre-wrap break-words">
                {p.text}
              </span>
            ) : (
              <span
                key={i}
                className={
                  "my-0.5 inline whitespace-pre-wrap break-words rounded px-1 py-0.5 decoration-rose-400 " +
                  (p.kind === "removed"
                    ? "bg-rose-100 text-rose-800 line-through"
                    : "bg-emerald-100 font-medium text-emerald-900")
                }
              >
                {p.text}
              </span>
            ),
          )
        )}
      </div>
    </div>
  );
}
