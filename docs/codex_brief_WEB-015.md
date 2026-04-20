# Codexブリーフィング: WEB-015 下書き一覧画面

**作成日**: 2026-04-20
**担当Issue**: WEB-015（Sprint 2 / 工数: 1.5日）
**依存**: WEB-011（投稿CRUD API）、WEB-007（認証UI）、WEB-014（AppHeader 拡張）
**後続ブロック**: WEB-025（D&D、Sprint 3）

---

## タスク概要

Next.js 15 App Router 上に **`/drafts` 画面** を実装する。`GET /api/posts` を叩き、投稿の一覧をカード形式で表示する。フィルタ（ステータス/プラットフォーム）、ソート、テキスト検索、各カードのアクション（編集/複製/削除）を提供する。決定事項#26-27 のヘルプマーク配置を含む。

---

## 実装基盤（既存）

- **認証**: WEB-007 の `useAuthGuard()`、`apps/web/src/stores/auth.ts`、`api-client.ts`
- **API Client**: `apps/web/src/generated/sdk.gen.ts` に以下が既に生成済み
  - `listPostsApiPostsGet` — WEB-011 で追加
  - `deletePostApiPostsPostIdDelete` — WEB-011 で追加
- **ヘルプ**: `HelpMark`, `HelpModeToggle` コンポーネント + `help-texts.ts`
- **レイアウト**: `AppShell`, `AppHeader` — WEB-014 でナビゲーション追加済み（`/drafts` は非活性状態なので**このIssueで活性化**）
- **Tailwind theme**: `brand` / `x` / `ig` / `yt` / `note` / `line`

---

## スコープ（WEB-015で実装するもの）

### 1. api-client.ts 拡張

`apps/web/src/lib/api-client.ts` に以下を追加:

```typescript
export async function fetchPostList(params?: {
  status?: "draft" | "scheduled" | "publishing" | "published" | "failed" | "archived";
  platform?: "x" | "ig" | "note" | "youtube" | "line";
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}) {
  return withAuthRetry(
    () => listPostsApiPostsGet({ query: params }) as Promise<ClientResult<PostListResponse>>,
  );
}

export async function deletePost(postId: string) {
  return withAuthRetry(
    () => deletePostApiPostsPostIdDelete({ path: { post_id: postId } }) as Promise<ClientResult<unknown>>,
  );
}
```

型は `apps/web/src/generated/types.gen.ts` から import。

### 2. `/drafts` ページ

`apps/web/src/app/drafts/page.tsx` 新規作成。

#### レイアウト
- `AppShell` + `AppHeader` を使用
- `useAuthGuard()` で未認証時は `/login` へ
- ヘッダーの下に:
  - **操作バー**: フィルタ / ソート / 検索 / 新規作成ボタン
  - **投稿カード一覧**（グリッド or リスト、レスポンシブ）
- ローディング / エラー / 空状態の表示

#### フィルタ UI
- **ステータスタブ**: 「すべて / 下書き / 予約済み / 公開済み / 失敗」（モックアップ参照）
  - 各タブに該当件数バッジ
- **プラットフォームフィルタ**: X / IG / YT / note のチェックボックス
- **テキスト検索**: クライアントサイド、content_text に対する部分一致（debounce 300ms）
- **ソート**: 「更新日 新→旧 / 作成日 新→旧 / 予約日時 近→遠」のドロップダウン

#### 投稿カード
- **上部**: プラットフォームバッジ（複数時は複数表示）+ ステータスバッジ
- **中段**: content_text 先頭120文字まで表示（truncate）
- **下段**: 更新日時の相対表示（「3時間前」「昨日」等、自作の簡易関数でOK）
- **アクション**: 「編集」「複製」「削除」（ホバー時に表示）
  - 編集: `/create?id={post_id}`（WEB-016 で対応するが今はプレースホルダリンクでOK）
  - 複製: `POST /api/posts` で同じ content_text を新規作成（status=draft）
  - 削除: 確認ダイアログ → `DELETE /api/posts/{id}`
- status=scheduled のカードには scheduled_at を大きく表示

### 3. カード操作の実装

- **削除**: `window.confirm` ベースの確認（MVP）→ 成功時にカードを除去、失敗時にトースト的なエラーメッセージ
- **複製**: 元の content_text / platforms を使って新規 draft を作成、成功時に一覧を再取得
- **編集**: 現状は `/create?id={post_id}` リンクを出すのみ（WEB-016 で完成）

### 4. ヘルプマーク配置

`help-texts.ts` に追加:
```typescript
"drafts.status_filter": "投稿の状態で絞り込めます。「下書き」は未予約の投稿です",
"drafts.platform_filter": "表示するSNSを絞り込めます",
"drafts.search": "本文の一部を入力すると一致する投稿だけを表示します",
"drafts.sort": "並び替えの基準を変更します",
"drafts.card_actions": "カードにカーソルを合わせると編集・複製・削除のボタンが表示されます",
"drafts.new_post": "新しい投稿を作成します",
```

ヘルプマークを配置する箇所:
- ステータスタブの右隣
- プラットフォームフィルタの右隣
- 検索欄の右隣
- ソートドロップダウンの右隣
- 新規作成ボタンの右隣

### 5. AppHeader のナビゲーション活性化

`AppHeader.tsx` の「下書き」リンクを `/drafts` で活性化。現状は WEB-014 で非活性状態になっているはず。

### 6. 空状態とローディング

- **初期ロード中**: スケルトン or スピナー
- **投稿ゼロ件**: イラスト or メッセージ「まだ下書きがありません。〔新規作成〕から始めましょう」
- **エラー時**: エラーメッセージ + 再読み込みボタン

### 7. ホームページからの誘導

`apps/web/src/app/page.tsx` の CTA リストに「下書きを見る」ボタンを追加（`/drafts` へ遷移）。

### 8. README 更新

`apps/web/README.md` に `/drafts` ページの存在と使い方を追記。

### 9. 動作確認（Codex 側で可能な範囲）

```bash
pnpm install      # サンドボックス失敗時は宣言のみ
pnpm typecheck
pnpm lint
pnpm build
```

ブラウザ動作確認は Claude が実施。

---

## スコープ外（やらないこと）

- ❌ 投稿作成フォーム本体（WEB-016）
- ❌ プレビューパネル（WEB-017）
- ❌ D&D（WEB-025）
- ❌ 新規テストフレームワーク導入（Vitest / Playwright は Sprint 4）
- ❌ 既存 WEB-001〜014 の改変（AppHeader のリンク活性化のみOK）
- ❌ apps/web/src/generated/ の編集

---

## 絶対守るべきこと

- **CLAUDE.md の Codex CLI Usage 節に従う**:
  - サンドボックス制約を検知したら **偽装しない**
  - `packages/` / `apps/*/` への shim 作成禁止
  - install 失敗時は宣言のみで完了報告、実インストールは Claude に委譲
- **axios は使わない**（fetch / @hey-api/client-fetch のみ）
- **既存の pytest 51 件 / pnpm全タスクを壊さない**
- **Next.js 15 / React 19**: `"use client"` / `next/navigation` / Server Actions 不使用
- **Tailwind カスタムテーマは変更しない**（既存 brand / x / ig / yt / note / line を使う）
- **Finder 複製 `* 2.*` を作らない**

---

## 成果物チェックリスト

- [ ] `apps/web/src/app/drafts/page.tsx` 新規作成
- [ ] `apps/web/src/lib/api-client.ts` に `fetchPostList` / `deletePost` 追加
- [ ] `apps/web/src/lib/help-texts.ts` に drafts.* 6項目追加
- [ ] `AppHeader.tsx` で `/drafts` リンク活性化
- [ ] `apps/web/src/app/page.tsx` に CTA 追加
- [ ] カード表示（content / status / platforms / updated_at）
- [ ] ステータスタブ（件数バッジ付き）
- [ ] プラットフォームフィルタ
- [ ] テキスト検索（debounce）
- [ ] ソートドロップダウン
- [ ] 削除（window.confirm + API 呼び出し）
- [ ] 複製（POST /api/posts で新規作成）
- [ ] 編集リンク（`/create?id={id}` プレースホルダ）
- [ ] ヘルプマーク 6箇所配置
- [ ] 空状態・エラー状態・ローディング状態の UI
- [ ] レスポンシブ（モバイル 375px〜 対応）
- [ ] `pnpm typecheck / build / lint` 通過
- [ ] 偽装 packages / shim / Finder複製 一切なし
- [ ] README 更新

---

## コミット指示

- `git add` は明示指定のみ
- `.env` / `apps/web/src/generated/` はコミット対象外
- コミットメッセージ: `feat: WEB-015 下書き一覧画面（フィルタ・ソート・検索・削除・複製）`
- Co-Authored-By 不要（Claude 側で追記）

---

## 補足: 関連設計ドキュメント

- `design/mockup/index.html` — 下書きパネル部分（約460-570行付近が参考）
- `design/design/APP_DESIGN_SPEC.md` 決定事項 #26-27（ヘルプ）

---

## 環境情報

- Next.js 15 + React 19 + TypeScript 5.7 + Tailwind 3.4
- pnpm 9.15.9 / Node 25.2.1 (engines warning 無視可)
- API: http://localhost:8000 / Supabase: http://localhost:54321
- ブラウザ動作確認は Claude が実施、Codex は build/typecheck/lint 通過まで

**重要**: 実装が完了したら、偽装スキャン（`packages/` の workspace 追加、`apps/*/` 直下の shim、Finder複製）を自己確認して完了報告してください。
