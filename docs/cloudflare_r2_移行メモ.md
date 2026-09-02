# Cloudflare R2：共有ボードの画像置き場にするための準備

2026-09-02 調査。康二郎さんの方針「なるべくシステムには Cloudflare を使っていく」に沿って、
記事画像の保存先を Google Drive から R2 に寄せる。

## いま分かっていること

**すでに稼働中**。バケット `shc-sns-temp-images`（オブジェクト15件 / 28.7MB）。
名前は "temp" だが、実際は一時ファイルと永続ファイルが**プレフィックスで分かれて**入っている。

| プレフィックス | 件数 | 用途 | 性質 |
|---|---|---|---|
| `event-images/` | 7 | イベントのチラシ・ポスター | 永続 |
| `post-media/{org_id}/YYYY/MM/DD/{uuid}.{ext}` | 5 | 旧 FastAPI がアップロードした記事画像 | 永続 |
| `ig-temp/` | 1 | Instagram 投稿の一時画像 | 投稿後に削除 |
| `weekly/` | 1 | 週次ループが 2026-08-17 に上げたもの | 検証の名残 |
| `test/` | 1 | 疎通確認 | 不要 |

`post-media/` の org_id は現在の organizations の ID と一致している。
**共有ボードの画像アップロードは、この命名規則をそのまま引き継げる。**

### バケットを分ける必要は無い（前言の訂正）
「一時と永続を混ぜると掃除で事故る」と言ったが、`ig_auto_poster.py` の
`delete_from_r2(object_key)` は**自分が上げたキーだけを名指しで消す**。
プレフィックス一括削除はしていないので、今の分け方で足りる。

## 唯一の障害：公開URL（r2.dev）が 403

`R2_PUBLIC_URL` は `pub-….r2.dev` 形式。**2026-09-02 時点で 403**。
2026-08-17 にも同じ状態が記録されている（`image_picker.py` のコメント）。
このため共有ボードのプレビューは Drive のサムネイルURLを使っている。

Instagram 投稿は成功しているので、投稿経路は別の方法（Drive の lh3 URL への
フォールバック）で動いている可能性が高い。**要確認**。

### 康二郎さんにお願いしたい設定（Cloudflare ダッシュボード）

いまの R2 トークンは対象バケットの Object 読み書きのみで、
`ListBuckets` も**公開設定の変更もできない**（AccessDenied を確認済み）。
以下はダッシュボードからの操作が必要。

1. **R2 → `shc-sns-temp-images` → Settings → Public access**
   - `r2.dev subdomain` が Disabled なら Enable する（これだけで直る可能性がある）
   - ただし r2.dev は**本番非推奨**（レート制限あり、Cloudflare のキャッシュが効かない）
2. **できればカスタムドメインを割り当てる**（本番はこちらが本筋）
   - Settings → Custom Domains → Connect Domain
   - 例 `img.<所有ドメイン>`。Cloudflare で DNS を管理しているドメインが要る
   - 割り当て後、`R2_PUBLIC_URL` をそのドメインに書き換える（.env 3箇所）
3. 設定後にこのコマンドで確認できる:
   `python3 -c "import os,urllib.request;..."`（`docs/r2_setup.md` 参照）

## 実装の段取り（公開URLが直ったあと）

1. Next.js に Route Handler を1本置き、R2 への**署名付きアップロードURL**を発行する
   （ブラウザから R2 へ直接 PUT。Vercel の実行時間制限を受けない）
2. ブラウザ側で長辺 1600px にリサイズしてから送る
3. アップロード完了後、`attachments` に INSERT
   （`storage_path` = オブジェクトキー、`public_url` = 公開URL）
4. キーの規則は既存を踏襲: `post-media/{org_id}/{YYYY/MM/DD}/{uuid}.{ext}`
5. Drive 経由の既存経路は当面残す（過去26枚の画像が Drive にあるため）

## 参考：ホスティングを Cloudflare にする案

Next.js は `@opennextjs/cloudflare` で Workers 上でも動くが、設定と検証に手間がかかる。
Vercel 側はプロジェクトもルートディレクトリ設定も既にあるため、まず Vercel で公開し、
必要が出てから移行を検討する。移行は後からでもできる。
