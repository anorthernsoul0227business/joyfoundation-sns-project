#!/usr/bin/env python3
"""イベント告知の日取りを決める。

2026-09-04 康二郎さんと決めた方針:
  ・開催までの日数で回数を変える
  ・X と Instagram は「前日」に必ず投稿する（他の予定と重なっても優先する）
  ・告知開始日は圭一郎さんが決められる。指定があればそちらを優先する

同じ催しが複数回開かれる場合は 1 つの告知にまとめる（series_run_key の単位）。
1公演ごとに告知すると、9月だけで毎日3〜4回投稿になってしまうため。
"""
from __future__ import annotations

import datetime as dt

# 開催までの日数 → 媒体ごとの「何日前に出すか」
# 前日(1)は必ず入れる。X と Instagram は前日を落とさない
PLAN: list[tuple[int, dict[str, list[int]]]] = [
    (30, {"x": [30, 14, 3, 1], "ig": [21, 5, 1], "note": [14]}),
    (14, {"x": [14, 3, 1],     "ig": [7, 1],     "note": [10]}),
    (7,  {"x": [3, 1],         "ig": [5, 1],     "note": []}),
    (0,  {"x": [0, 1],         "ig": [1],        "note": []}),  # 0 は「できるだけ早く」
]

def role_for(lead: int) -> str:
    if lead == 1:
        return "day_before"
    if lead >= 21:
        return "early"
    if lead >= 7:
        return "middle"
    return "late"   # lead == 0（できるだけ早く）もここ


def plan_for(event_date: dt.date, today: dt.date,
             announce_from: dt.date | None = None) -> list[tuple[dt.date, str, str]]:
    """告知の (投稿日, 媒体, 役割) を返す。

    announce_from が指定されていれば、その日より前には出さない。
    圭一郎さんが「この公演は2か月前から」と決めた場合にそれを尊重する。
    """
    days = (event_date - today).days
    if days < 0:
        return []

    table = next(t for threshold, t in PLAN if days >= threshold)

    out: list[tuple[dt.date, str, str]] = []
    for platform, leads in table.items():
        for lead in leads:
            # lead == 0 は「できるだけ早く」。次に投稿できる日に置く
            when = today + dt.timedelta(days=1) if lead == 0 else event_date - dt.timedelta(days=lead)

            # 過ぎた日には出せない。開催当日・開催後にも出さない
            # （「明日やります」と当日に言っても意味がない）
            if when <= today or when >= event_date:
                continue

            # 開始日より前には出さない。ただし前日だけは必ず出す
            if announce_from and when < announce_from and role_for(lead) != "day_before":
                continue

            out.append((when, platform, role_for(lead)))

    # 同じ日・同じ媒体が重なることがある（開催が近いと「できるだけ早く」と
    # 「前日」が同じ日になる）。前日を残して1本にまとめる
    best: dict[tuple[dt.date, str], str] = {}
    for when, platform, role in out:
        cur = best.get((when, platform))
        if cur is None or role == "day_before":
            best[(when, platform)] = role
    out = [(w, p, r) for (w, p), r in best.items()]

    out.sort(key=lambda x: (x[0], x[1]))
    return out


def describe(event_date: dt.date, today: dt.date,
             announce_from: dt.date | None = None) -> str:
    """人に見せる要約。イベント画面の説明に使う。"""
    rows = plan_for(event_date, today, announce_from)
    if not rows:
        return "告知の予定はありません"
    label = {"x": "X", "ig": "Instagram", "note": "note"}
    parts = [f"{d.month}/{d.day} {label.get(p, p)}" + ("（前日）" if r == "day_before" else "")
             for d, p, r in rows]
    return " ／ ".join(parts)
