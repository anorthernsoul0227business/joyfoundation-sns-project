# Codexブリーフィング: WEB-016 投稿作成画面

**作成日**: 2026-04-20
**担当Issue**: WEB-016（Sprint 2 / 工数: 2日）
**依存**: WEB-011（投稿CRUD）、WEB-012（スケジュール）、WEB-015（下書き一覧の編集リンク）
**後続ブロック**: WEB-017（プレビューパネル）

---

## タスク概要

Next.js 15 App Router で **`/create` 画面** を実装する。新規投稿作成と既存投稿の編集（`/create?id={post_id}`）の両モードをサポートする。`react-hook-form` + `zod` でバリデーション。「下書き保存」「予約して保存」「即時投稿」の3つの送信アクションを提供。

---

## 実装基盤（既存）

- **認証**: `useAuthGuard()`, Zustand store
- **API Client**: `apps/web/src/generated/sdk.gen.ts` に以下が既に生成済み
  - `createPostApiPostsPost` — 新規作成
  - `getPostApiPostsPostIdGet` — 取得
  - `updatePostApiPostsPostIdPatch` — 編集
  - `schedulePostApiPostsPostIdSchedulePost` — 予約
  - `publishNowApiPostsPostIdPublishNowPost` — 即時
- **フォーム依存**: `react-hook-form ^7.53.0`, `@hookform/resolvers ^3.9.0`, `zod ^3.23.8` 導入済み
- **レイアウト**: `AppShell` + `AppHeader`（/create は WEB-014 で非活性、このIssueで活性化）
- **ヘルプ**: `HelpMark`, `help-texts.ts`

---

## スコープ（WEB-016で実装するもの）

### 1. api-client.ts 拡張

`apps/web/src/lib/api-client.ts` に以下を追加:

```typescript
import {
  createPostApiPostsPost,
  getPostApiPostsPostIdGet,
  updatePostApiPostsPostIdPatch,
  schedulePostApiPostsPostIdSchedulePost,
  publishNowApiPostsPostIdPublishNowPost,
} from "../generated/sdk.gen";

export async function createPost(body: PostCreate): Promise<PostResponse>
export async function updatePost(postId: string, body: PostUpdate): Promise<PostResponse>
export async function schedulePost(postId: string, scheduledAt: string): Promise<PostResponse>
export async function publishPostNow(postId: string): Promise<PostResponse>
export async function fetchPostDetail(postId: string): Promise<PostResponse>  // 既存、無ければ追加
```

型は `../generated/types.gen` からimport。

### 2. `/create` ページ

`apps/web/src/app/create/page.tsx` 新規作成。

#### モード判定
- URL クエリ `?id={post_id}` があれば **編集モード**、なければ **新規モード**
- 編集モード時は `fetchPostDetail` で初期値をロード → フォームに prefill
- 編集モードでは `status` の現在値を隠しフィールドに保持（APIの 409 ガードを尊重）

#### フォームフィールド
1. **本文** (`content_text`): textarea、1-10000文字、zod で min(1).max(10000)
2. **投稿先SNS** (`platforms`): チェックボックスグループ (x / ig / youtube / note / line)、最低1つ必須
3. **予約日時** (`scheduled_at`): datetime-local 入力（任意、status=scheduled 時のみ必須）
4. **画像 URL** (`media`): 画像 storage_path を複数追加可能なリスト（+ ボタンで追加、× で削除）
   - MVP 仕様: 実ファイルアップロードは WEB-024 で実装、今は storage_path と mime_type のテキスト入力のみ
   - `image/png`, `image/jpeg`, `image/webp` のラジオ選択で mime_type を指定

#### アクションボタン
- **下書き保存**: `status: "draft"` で POST or PATCH
- **予約して保存**: `status: "scheduled"` + scheduled_at 入力必須（未入力時はエラー表示）。POST の場合は通常通り、PATCH（編集）の場合は `schedulePost(id, scheduledAt)` を別途呼ぶか、PATCH body に含める
- **即時投稿**: 確認ダイアログ → `publishPostNow(post_id)` を呼ぶ（ただし新規作成画面では「まず保存してから」としてDisable、編集モード限定）
- **キャンセル**: `/drafts` へ戻る

#### バリデーション（zod スキーマ）
```typescript
const schema = z.object({
  content_text: z.string().min(1, "本文を入力してください").max(10000),
  platforms: z.array(z.enum(["x", "ig", "youtube", "note", "line"])).min(1, "SNSを1つ以上選択してください"),
  scheduled_at: z.string().optional(),
  media: z.array(z.object({
    storage_path: z.string().min(1),
    mime_type: z.enum(["image/png", "image/jpeg", "image/webp"]),
  })).default([]),
});
```

#### 字数カウンター
- X: 280文字制限、超過時は赤字で警告（送信はブロックしない、ユーザー判断）
- IG: 制限なし（キャプション2200文字の目安を表示）
- content_text の変更にリアルタイム追従

#### エラー表示
- zod バリデーションエラーは各フィールドの下に表示
- API エラーはフォーム上部にトースト的表示
- 送信中はボタン disable + スピナー

### 3. 編集モード特有のロジック

- URL に `?id=xxx` がある場合、`useEffect` で `fetchPostDetail` を呼び、フォームを `reset(data)` で更新
- 既存 status が `published` / `publishing` / `archived` の場合は編集不可（読み取り専用 + メッセージ）
- 送信時:
  - `status` が変わらない場合: `updatePost(id, {content_text, ...})`
  - `status` が `scheduled` になる場合: `updatePost` + `schedulePost` の順で呼ぶ、または PATCH body に `status` と `scheduled_at` を含める（推奨）

### 4. 「新規作成」導線

- `/drafts` から「新規作成」ボタンで `/create` へ
- `/drafts` カードの「編集」リンクで `/create?id={post_id}` へ
- ヘッダーの「投稿作成」リンクを `/create` で活性化

### 5. ヘルプマーク配置

`help-texts.ts` に追加:
```typescript
"create.content_text": "投稿する本文を入力します。SNSごとの文字数制限に注意してください",
"create.platforms": "投稿先のSNSを選択します。複数選択できます",
"create.scheduled_at": "予約投稿の日時を指定します。予約モードで保存するときに必須です",
"create.media": "添付する画像のストレージパスを指定します。実ファイルアップロードは準備中です",
"create.save_draft": "下書きとして保存します。いつでも編集・削除できます",
"create.schedule": "指定した日時に自動投稿されるように予約します",
"create.publish_now": "今すぐ投稿します（編集モードでのみ有効）",
```

ヘルプマーク配置箇所:
- 本文ラベル横
- プラットフォームラベル横
- 予約日時ラベル横
- 画像添付ラベル横
- アクションボタン群の右上（1箇所、使い方ガイド）

### 6. AppHeader のナビゲーション活性化

`/create` リンクを活性化。既存コード（WEB-014で非活性）を修正。

### 7. 空状態とローディング

- 編集モードの初期ロード: スケルトン
- 編集モードで post_id が存在しない: 「投稿が見つかりません」メッセージ + /drafts へ戻るリンク
- published/archived 状態の編集阻止: 「この投稿は公開済みのため編集できません」メッセージ

### 8. レスポンシブ

- デスクトップ: 左にフォーム、右にプラットフォーム別のプレビュー枠（**WEB-017で中身実装**、今は「プレビュー準備中」の枠のみ配置）
- モバイル: 縦積み、プレビューは「プレビューを表示」トグルで出し入れ

### 9. README 更新

`apps/web/README.md` に `/create` の説明を追記。

### 10. 動作確認（Codex 側）

```bash
pnpm typecheck
pnpm lint
pnpm build
```

ブラウザ動作確認は Claude が実施。

---

## スコープ外（やらないこと）

- ❌ プレビュー本体の実装（WEB-017）
- ❌ 実ファイル画像アップロード（WEB-024）
- ❌ AI記事生成連携（Phase 1.5 / WEB-030番台）
- ❌ Vitest / Playwright 導入
- ❌ 既存 WEB-001〜015 改変（AppHeader のリンク活性化のみOK）
- ❌ apps/web/src/generated/ 編集

---

## 絶対守るべきこと

- **CLAUDE.md の Codex CLI Usage 節に従う**: 偽装絶対禁止
- **axios 不使用**（fetch / @hey-api/client-fetch のみ）
- **既存テスト維持**（pytest 51 件、pnpm全タスク）
- **`"use client"` directive を正しく付ける**
- **next/navigation の `useRouter`, `useSearchParams` を使用**（`next/router` 禁止）
- **Server Actions 不使用、全て client-side fetch**
- **Tailwind カスタムテーマは変更しない**
- **Finder 複製 `* 2.*` を作らない**

---

## 成果物チェックリスト

- [ ] `apps/web/src/app/create/page.tsx` 新規作成
- [ ] `apps/web/src/lib/api-client.ts` に 5関数追加（create/update/fetchDetail/schedule/publishNow）
- [ ] `apps/web/src/lib/help-texts.ts` に create.* 7項目追加
- [ ] `AppHeader.tsx` の `/create` リンク活性化
- [ ] 新規 + 編集の2モード動作
- [ ] zod + react-hook-form バリデーション
- [ ] 3つの送信アクション（下書き保存/予約/即時投稿）
- [ ] X/IG の字数カウンター
- [ ] 画像添付のリスト編集UI（ストレージパス入力）
- [ ] 編集モードで published/archived 投稿の保護
- [ ] プレビュー枠のプレースホルダ（WEB-017用）
- [ ] ヘルプマーク 5箇所配置
- [ ] エラー・ローディング・空状態
- [ ] レスポンシブ
- [ ] `pnpm typecheck / build / lint` 通過
- [ ] 偽装 / shim / Finder複製 一切なし

---

## コミット指示

- `git add` は明示指定のみ
- `.env` / `apps/web/src/generated/` はコミット対象外
- コミットメッセージ: `feat: WEB-016 投稿作成画面（新規/編集・zod バリデーション・3送信アクション）`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/mockup/index.html` — 投稿作成UIの参考（600-900行付近）
- `design/design/APP_DESIGN_SPEC.md` 決定事項 #26-27
- `design/design/RELIABILITY_DESIGN.md` — 予約投稿の遷移フロー

---

## 環境情報

- Next.js 15 + React 19 + TypeScript 5.7 + Tailwind 3.4
- pnpm 9.15.9 / Node 25.2.1
- API: http://localhost:8000
- 既存依存: `react-hook-form ^7.53.0`, `@hookform/resolvers ^3.9.0`, `zod ^3.23.8` 導入済み

**重要**: 完了報告時に自己偽装スキャン（packages/ / apps/*/ shim / Finder複製）を実施してください。
