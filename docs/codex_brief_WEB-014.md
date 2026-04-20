# Codexブリーフィング: WEB-014 カレンダー画面（FullCalendar）

**作成日**: 2026-04-20
**担当Issue**: WEB-014（Sprint 2 / 工数: 2日）
**依存**: WEB-013（コミット済 `50b3681`）、WEB-007（認証UI）
**後続ブロック**: WEB-025（D&D実装、Sprint 3）

---

## タスク概要

Next.js 15 App Router 上に FullCalendar で **`/calendar` 画面** を実装する。
WEB-013 で公開した `GET /api/calendar` エンドポイントを叩き、月/週/日ビュー切替・SNS色分け・プラットフォームフィルタを提供する。決定事項#26-27（ミニヘルプ + ヘルプモードトグル）をUIに適用。

D&D（下書き→カレンダー配置）は WEB-025（Sprint 3）で実装。WEB-014 では **カレンダー表示と閲覧操作のみ**。

---

## 現状の実装基盤

- **ログイン/認証** は WEB-007 で完成済み（Zustand store `apps/web/src/stores/auth.ts`、`useAuthGuard`）
- **API Client** は生成済み: `apps/web/src/generated/client.gen.ts` / `sdk.gen.ts` / `types.gen.ts`
  - WEB-013 で生成された `getApiCalendarGet` （関数名は openapi.json を確認）
- **AppHeader / AppShell** は WEB-007 で作成済み、そのまま再利用
- **HelpMark / HelpModeToggle** コンポーネント完成済み
- **Tailwind theme** に brand / x / ig / yt / note カラー定義済み（`packages/config/tailwind`）

---

## スコープ（WEB-014で実装するもの）

### 1. 依存追加

`apps/web/package.json` の `dependencies` に追加:
```
"@fullcalendar/core": "^6.1.15",
"@fullcalendar/react": "^6.1.15",
"@fullcalendar/daygrid": "^6.1.15",
"@fullcalendar/timegrid": "^6.1.15",
"@fullcalendar/interaction": "^6.1.15"
```

**重要**: サンドボックスで `pnpm install` ができない場合は **宣言のみで完了報告**し、
`packages/` 配下への workspace 偽装や fake shim の作成は **絶対禁止**（CLAUDE.md の Codex CLI Usage 参照）。
実インストールは Claude が後で実行します。

### 2. `/calendar` ページ

`apps/web/src/app/calendar/page.tsx` を新規作成:

- **AppShell / AppHeader** を使用（WEB-007 の既存レイアウト）
- `useAuthGuard()` で未認証時は `/login` へリダイレクト
- FullCalendar コンポーネントを配置、以下機能:
  - **月 (dayGridMonth) / 週 (timeGridWeek) / 日 (timeGridDay)** の3ビュー切替
  - 「今日」「前月」「次月」ナビゲーション
  - **SNSフィルタ** (チェックボックス: x / ig / yt / note / line) — デフォルト全チェック
  - イベント表示: タイトル + プラットフォームバッジ色分け
  - イベントクリックで **サイドパネル or モーダル** を開き、content_text / status / platforms / scheduled_at を表示
- カレンダーの可視レンジ (view.activeStart / activeEnd) を拾って `GET /api/calendar?from=...&to=...&platforms[]=...` を呼び出す
- ローディング / エラー表示あり

### 3. カレンダーイベントのスタイル

- `eventClassNames` で各プラットフォーム別の色を当てる
- Tailwind brand カラーベース:
  - `x`: `bg-x text-white`
  - `ig`: `bg-ig text-white`
  - `yt`: `bg-yt text-white`
  - `note`: `bg-note text-white`
  - `line`: `bg-line text-white`
- 複数プラットフォームの場合は先頭プラットフォームの色で、タイトルに `＋N件` を付ける
- status=failed のイベントは赤枠で強調
- status=published はグレーアウト（過去投稿）

### 4. SNS フィルタ UI

- ヘッダー下の操作バーに配置
- FullCalendar の再レンダリングと連動
- 状態は Zustand の新規ストア or React state（迷うなら React state）

### 5. ヘルプマーク配置

決定事項#26-27 に準拠し、以下の箇所にヘルプマークを配置:
- SNSフィルタの右隣（文言: 「投稿する SNS を絞り込めます」）
- ビュー切替ボタンの右隣（文言: 「月/週/日の表示を切り替えます」）
- `「+ 新規投稿」` ボタン（まだ実装しないがプレースホルダー）の右隣（文言: 「新しい投稿を作成します」）

### 6. `apps/web/src/lib/help-texts.ts` 拡張

以下のトピックを追加:
```typescript
"calendar.view_toggle": "月/週/日の表示を切り替えます",
"calendar.platform_filter": "投稿するSNSで絞り込めます。チェックを外すと非表示になります",
"calendar.new_post": "新しい投稿を作成します",
"calendar.event_click": "イベントをクリックすると内容の詳細を確認できます",
```

### 7. ナビゲーション更新

`AppHeader.tsx` に「カレンダー」ナビゲーションリンクを追加（`/calendar` へ）。
既存の下書き / 投稿作成 / AI生成などはまだ画面がないので、カレンダーのみリンク活性化、他はグレーアウトで置いておく。

### 8. ホームからの誘導

`apps/web/src/app/page.tsx` の現在のシンプル表示に「カレンダーを開く」CTA ボタンを追加し、`/calendar` へ遷移できるようにする。

### 9. FullCalendar の ja ロケール

`@fullcalendar/core/locales/ja` を import して `locale="ja"` を設定。曜日表示が日本語になる。

### 10. レスポンシブ

- デスクトップ: フルサイズ
- モバイル: 日ビュー推奨、操作バーは縦並び
- 最低 375px 幅対応（Noto Sans JP の和文レイアウト）

### 11. README 更新

`sns-calendar-app/apps/web/README.md` に `/calendar` ページの存在、FullCalendar 依存、環境変数注意点を追記。

### 12. 動作確認（Codex 側で可能な範囲）

以下が通ること:
```bash
pnpm install                 # サンドボックスで失敗時は宣言のみで報告
pnpm typecheck               # 必須
pnpm lint                    # 必須
pnpm build                   # 必須（ビルドでエラーなく完了すること）
```

**ブラウザ動作確認は Claude が実行する**ので、Codex 側は typecheck/build/lint 完了まででOK。

---

## スコープ外（やらないこと）

- ❌ D&D（下書き→カレンダー配置）— WEB-025 (Sprint 3)
- ❌ 投稿作成フォーム — WEB-016
- ❌ 下書き一覧画面 — WEB-015
- ❌ プレビューパネル — WEB-017
- ❌ 新規テストフレームワーク導入（Playwright/Vitest は Sprint 4）
- ❌ 既存認証フロー改変（WEB-007成果物は維持）
- ❌ apps/web/src/generated/ 編集（自動生成のみ）
- ❌ 新しい packages/* workspace 追加（偽装禁止）

---

## 絶対守るべきこと

- **CLAUDE.md の「Codex CLI Usage」節に従う**:
  - サンドボックス制約を検知したら偽装で回避せず、宣言だけ済ませて Claude に委ねる
  - `packages/` 配下への fake workspace 作成禁止
  - `apps/*/` 直下への npm 公式名と同名 shim 作成禁止
- **axios は使わない**（fetch / @hey-api/client-fetch のみ）
- **既存の WEB-001〜013 成果物を壊さない**（pytest 51 / pnpm全タスク維持）
- **`apps/web/src/generated/` は編集しない**（読み取り専用）
- **Tailwind 設定 (`packages/config/tailwind/index.js`) は変更しない**（brand / x / ig / yt / note / line は既存）
- **Next.js 15 / React 19 の癖**:
  - `"use client"` 必須（FullCalendar や useState 使う page は全て）
  - `next/navigation` のみ使用（`next/router` 禁止）
  - Server Actions 不使用、すべて client fetch で統一

---

## 成果物チェックリスト（Claude レビュー項目）

- [ ] `apps/web/package.json` に FullCalendar 5依存を追加
- [ ] `apps/web/src/app/calendar/page.tsx` を新規作成
- [ ] `useAuthGuard` で保護
- [ ] FullCalendar 月/週/日切替が機能
- [ ] SNSフィルタで表示切替
- [ ] `GET /api/calendar` を可視レンジで呼び出す
- [ ] イベントクリックで詳細表示（モーダル or サイドパネル）
- [ ] Tailwind の brand/x/ig/yt/note/line カラーでプラットフォーム別色分け
- [ ] ja ロケール適用
- [ ] HelpMark を4箇所に配置
- [ ] help-texts.ts に 4 新トピック追加
- [ ] AppHeader にナビゲーションリンク
- [ ] ホームページに CTA ボタン
- [ ] README 更新
- [ ] `pnpm typecheck / build / lint` 全通過
- [ ] 既存 `pnpm openapi:sync` と `poetry run pytest` が影響なし
- [ ] 偽装 packages / shim 一切なし
- [ ] Finder 複製ファイル `* 2.*` なし

---

## コミット指示

- `git add` は明示指定のみ（`git add .` 禁止）
- `.env` / `.DS_Store` / `apps/web/src/generated/` はコミット対象外
- コミットメッセージ: `feat: WEB-014 カレンダー画面（FullCalendar月/週/日 + SNSフィルタ）`
- Co-Authored-By 不要（Claude 側で追記）

---

## 補足: 関連設計ドキュメント

- `design/design/APP_DESIGN_SPEC.md` 決定事項 #1（FullCalendar）、#23（D&D）、#26-27（ヘルプ）
- `design/mockup/index.html` — カレンダー画面の視覚仕様（約180-350行がカレンダー部）
- `design/design/IMPLEMENTATION_PLAN.md` セクション5.2（Sprint 2 詳細）

---

## 補足: 環境情報

- Next.js 15 + React 19
- TypeScript 5.7
- Tailwind CSS 3.4
- pnpm 9.15.9
- Node 25.2.1（engines warning は無視可）
- API: http://localhost:8000（ローカル FastAPI）
- ローカル Supabase 稼働中（認証が必要なため、ログインセッションは Zustand の persist から読まれる前提）

**重要**: Codex 側でブラウザ動作確認はしない。typecheck / build / lint 通過まで。Claude がローカルで `pnpm dev` 起動 + Chrome で目視確認します。
