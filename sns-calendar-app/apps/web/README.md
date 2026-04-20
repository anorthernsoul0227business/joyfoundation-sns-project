# SNS Calendar Web

Next.js 15 / React 19 ベースのフロントエンドです。WEB-016 時点ではログイン、サインアップ、認証状態の永続化、ヘルプモード UI に加え、`/calendar` の FullCalendar ベース予約投稿カレンダー、`/drafts` の下書き一覧、`/create` の投稿作成・編集画面を実装しています。

## 開発起動

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# API
cd apps/api
SUPABASE_URL=http://127.0.0.1:54321 \
SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH \
SUPABASE_SERVICE_ROLE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz \
poetry run uvicorn app.main:app --reload

# Web
cd ../web
pnpm install
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 pnpm dev
```

## 環境変数

- `NEXT_PUBLIC_API_BASE_URL`: FastAPI のベース URL。未指定時は `http://localhost:8000`

## カレンダー画面

- `@fullcalendar/react` / `@fullcalendar/daygrid` / `@fullcalendar/timegrid` / `@fullcalendar/interaction` / `@fullcalendar/core` を利用します。
- `/calendar` は認証必須です。`useAuthGuard` が未認証状態を検知すると `/login?redirect=/calendar` に遷移します。
- カレンダーは `GET /api/calendar?from=...&to=...&platforms[]=...` を使って可視レンジ単位で再取得します。
- イベントクリック時は `GET /api/posts/{post_id}` で投稿本文を取得し、右側パネルに表示します。
- ローカル API を使うため、`NEXT_PUBLIC_API_BASE_URL` が FastAPI に向いていることを確認してください。

## 下書き一覧画面

- `/drafts` は認証必須です。`useAuthGuard` が未認証状態を検知すると `/login?redirect=/drafts` に遷移します。
- `GET /api/posts` を使って投稿一覧を取得し、ステータス、SNS、検索、ソートで絞り込みできます。
- 検索は `content_text` に対する 300ms debounce のクライアントサイド部分一致です。
- カードでは編集、複製、削除を操作できます。複製は `POST /api/posts`、削除は `DELETE /api/posts/{id}` を使います。
- `status=scheduled` の投稿は予約日時を強調表示します。

## 投稿作成画面

- `/create` は認証必須です。`/create?id={post_id}` で編集モード、クエリなしで新規作成モードになります。
- `react-hook-form` + `zod` で本文、投稿先SNS、予約日時、画像ストレージパスの入力をバリデーションします。
- 送信アクションは「下書き保存」「予約して保存」「即時投稿」の3種類です。即時投稿は編集モードのみ有効です。
- 編集モードでは `GET /api/posts/{id}` で初期値を取得し、公開済み・投稿中・アーカイブ済みの投稿は読み取り専用で表示します。
- 右側のプレビュー枠は X / Instagram のリアルタイムプレビューです。モバイルでは既存トグルで開閉し、未選択SNSのタブは半透明表示になります。
- X は 280 文字超過を強調表示し、Instagram はハッシュタグ強調と 2200 文字目安の警告を表示します。

## 認証フロー概要

1. `/login` または `/signup` から FastAPI 認証 API を呼び出します。
2. 返却された `access_token` / `refresh_token` / ユーザー情報を Zustand persist で `localStorage` に保存します。
3. 保護ページでは `useAuthGuard` が期限切れを含む未認証状態を検知し、`/login?redirect=...` へ移動します。
4. 認証 API が `401` を返した場合、`refresh_token` で 1 回だけ再試行し、失敗時はストアをクリアしてログイン画面へ戻します。
5. ヘルプモードはストアで保持し、`body.help-off` クラスと同期して `HelpMark` の表示を切り替えます。
