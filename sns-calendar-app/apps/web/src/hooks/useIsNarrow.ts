"use client";

import { useEffect, useState } from "react";

/**
 * iPhone のような狭い画面かどうか。Tailwind の md（768px）と同じ境目にしてある。
 *
 * 見た目そのものは CSS のレスポンシブ指定で切り替える。この hook は
 * 「一覧と本文のどちらを出すか」など、振る舞いを変えるところだけに使う。
 */
export function useIsNarrow(): boolean {
  const [narrow, setNarrow] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const apply = () => setNarrow(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  return narrow;
}
