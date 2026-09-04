#!/usr/bin/env python3
"""Vercel へ本番デプロイする（CLI を使わない）。

2026-09-04: `vercel deploy` が "User not found" で失敗するようになった。
チームスコープのトークンでは /v2/user を引けず、CLI がその前段で止まる。
API は正常に応答するので、必要な手順（ファイル登録 → デプロイ作成 → 完了待ち）
だけを直接叩く。

    set -a; source ~/.config/jf/vercel.env; set +a
    /usr/bin/python3 deploy/vercel_deploy.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "sns-calendar-app"
PROJECT = "shc-sns-calendar-web"
TEAM = "team_ZiXbwLEjoVtClh8P0v7SqH0j"
API = "https://api.vercel.com"

# アップロードしないもの。ビルド成果物・依存・秘密は送らない
SKIP_DIRS = {"node_modules", ".next", ".git", ".vercel", ".turbo",
             "playwright-report", "test-results", ".pnpm-store"}


def token() -> str:
    t = os.getenv("VERCEL_TOKEN", "")
    if not t:
        sys.exit("VERCEL_TOKEN がありません（~/.config/jf/vercel.env）")
    return t


def call(method: str, path: str, body=None, raw: bytes | None = None, extra: dict | None = None):
    url = f"{API}{path}{'&' if '?' in path else '?'}teamId={TEAM}"
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token()}")
    if raw is None and body is not None:
        req.add_header("Content-Type", "application/json")
    for k, v in (extra or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            out = r.read().decode()
            return json.loads(out) if out.strip() else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} {path}: {e.read().decode()[:300]}") from e


def collect() -> list[tuple[str, Path]]:
    """git が管理しているファイルを送る。.gitignore の判断をそのまま使える。"""
    out = subprocess.run(["git", "ls-files"], cwd=APP, capture_output=True, text=True, check=True)
    files = []
    for rel in out.stdout.splitlines():
        if not rel.strip():
            continue
        if any(part in SKIP_DIRS for part in Path(rel).parts):
            continue
        p = APP / rel
        if p.is_file():
            files.append((rel, p))
    return files


def main() -> int:
    files = collect()
    print(f"送るファイル: {len(files)}件")

    manifest = []
    uploaded = 0
    for rel, p in files:
        blob = p.read_bytes()
        sha = hashlib.sha1(blob).hexdigest()
        manifest.append({"file": rel, "sha": sha, "size": len(blob)})
        # 同じ内容が既に登録されていれば再送されない（Vercel 側で重複排除）
        call("POST", "/v2/files", raw=blob,
             extra={"x-vercel-digest": sha, "Content-Type": "application/octet-stream"})
        uploaded += 1
        if uploaded % 40 == 0:
            print(f"  {uploaded}/{len(files)}")

    print("デプロイを作成します")
    # forceNew=1 でビルドキャッシュを使わせない。
    # キャッシュを復元すると pnpm install が「Already up-to-date」で終わり、
    # node_modules が揃わないまま next を見つけられずに落ちる（2026-09-04）
    dep = call("POST", "/v13/deployments?forceNew=1&skipAutoDetectionConfirmation=1", body={
        "name": PROJECT,
        "project": PROJECT,
        "target": "production",
        "files": manifest,
        # projectSettings は渡さない。渡すとプロジェクト側の設定を上書きし、
        # rootDirectory（apps/web）が既定に戻ってビルドが落ちる。
        # 成功しているデプロイの projectSettings にも rootDirectory は入っておらず、
        # プロジェクト設定を継承するのが正しい（2026-09-04 に実機で確認）
    })
    dep_id, url = dep["id"], dep.get("url")
    print(f"  {dep_id}  https://{url}")

    for _ in range(120):
        st = call("GET", f"/v13/deployments/{dep_id}")
        state = st.get("readyState") or st.get("status")
        if state in ("READY", "ERROR", "CANCELED"):
            print("結果:", state)
            return 0 if state == "READY" else 1
        time.sleep(10)
    print("時間内に完了しませんでした")
    return 1


if __name__ == "__main__":
    sys.exit(main())
