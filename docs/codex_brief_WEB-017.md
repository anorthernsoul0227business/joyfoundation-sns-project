# Codexブリーフィング: WEB-017 プレビューパネル（X/IG切替）

**作成日**: 2026-04-20
**担当Issue**: WEB-017（Sprint 2 / 工数: 1日）
**依存**: WEB-016（投稿作成画面）
**Sprint 2 最後の Issue**

---

## タスク概要

WEB-016 で配置した `/create` ページのプレビュー枠（プレースホルダ）を **実プレビュー UI** に置き換える。X / Instagram のフィード表示を模倣し、フォーム入力にリアルタイムで追従する。タブで切替可能。

---

## 既存コード位置

- **ファイル**: `apps/web/src/app/create/page.tsx`
- **置換対象**: 800-874行付近（「プレビュー準備中」のプレースホルダブロック全体）
- **既存利用可能なフォーム値**:
  - `contentText` (string) — 本文
  - `selectedPlatformLabels` / `platforms` — 選択中SNS
  - `scheduledAt` (string) — 予約日時
  - `fields` (画像配列、`useFieldArray` 由来)
  - `isDirty` (boolean) — 未保存フラグ
  - `isEditMode` (boolean) — 編集モード判定
- **未使用だが画面で必要になりそうな値**: `defaultDisplayName` 等（`useAuthStore` で取得可能）

---

## スコープ（WEB-017で実装するもの）

### 1. プレビューコンポーネント分離

肥大化を避けるため、以下のコンポーネントを新規作成して `/create/page.tsx` から分離:

```
apps/web/src/components/preview/
├── PreviewPanel.tsx       # コンテナ（タブ + 切替）
├── XPreview.tsx           # X (Twitter) 風カード
├── IgPreview.tsx          # Instagram 風カード
└── usePreviewMeta.ts      # 投稿者の display_name / avatar 等を取得（オプション）
```

各サブコンポーネントは Props で `content_text`, `mediaPaths`, `displayName`, `handle` を受け取る純粋表示コンポーネント。

### 2. PreviewPanel の構造

```tsx
type Tab = "x" | "ig";

type PreviewPanelProps = {
  contentText: string;
  selectedPlatforms: Platform[];   // 選択中SNS（タブ自動切替に利用）
  mediaPaths: { storage_path: string; mime_type: string }[];
  displayName: string;
  isDirty: boolean;
};
```

- 上部にタブ（X / IG）。選択中SNSに応じてデフォルトタブを決定（X 選択 → X、IG のみ選択 → IG、両方選択 → X 優先）
- タブ切替で表示を切り替え
- 選択されていないSNSのタブはグレーアウト＋クリックすると半透明プレビュー（「このSNSは未選択です」）
- リアルタイム反映（フォーム値の変更で再描画）

### 3. XPreview コンポーネント

X のタイムラインカード相当を Tailwind で再現:

- ヘッダー: アバター丸 + display_name + `@handle` + 「Just now」
- 本文: `content_text` を改行保持で表示（`whitespace-pre-wrap`）
- 文字数: 280字超は赤字 / 280以下は通常色
- 画像: 添付があれば最大4枚を 2x2 グリッド or 1枚なら全幅
  - `storage_path` を image src として使用（実画像はないので `bg-slate-200` のスケルトン表示でOK、ただし MIME type をラベル表示）
- アクションバー: 返信 / リポスト / いいね / 共有 アイコン（lucide-react を新規導入してもよいが、emoji or fa-* class でもOK）
- 投稿時刻: `scheduledAt` があれば「Scheduled for 4/22 18:00」、なければ「Now」

X の brand color (`bg-x` / `text-x`) を活かし、ヘッダー背景に薄く使う。Tailwind theme は既存のものをそのまま利用。

### 4. IgPreview コンポーネント

Instagram の投稿カード相当:

- 上部バー: アバター + ハンドル + … メニュー
- メイン: 画像（1:1 正方形、複数なら横スクロール風 or 1枚目のみ）
  - 画像未添付なら brand カラーのスケルトン枠 + 「画像未添付」
- アクション行: ハート / コメント / 紙飛行機 / ブックマーク
- いいね数（ダミー: 「いいね数を表示」）
- キャプション: ヘッダーに display_name、続けて `content_text`（先頭部分のみ強調）
- ハッシュタグ: 本文中の `#xxx` を青色で強調表示（簡易な regex で）

IG brand color (`bg-ig` / `text-ig`) を活かす。

### 5. リアルタイム反映

`/create/page.tsx` の `useForm` の `watch()` で値を取得しているので、それを Props に渡せば自動で再描画される。`watch("content_text")` で本文を、`watch("media")` で画像配列を取得して PreviewPanel に渡す。

### 6. ヘルプマーク追加

`help-texts.ts` に追加:
```typescript
"create.preview_tabs": "プレビューを X / Instagram で切替できます。選択していないSNSのタブはグレーで表示されます",
"create.preview_realtime": "本文や画像を変更するとリアルタイムでプレビューが更新されます",
```

PreviewPanel タブ右側に1箇所、プレビュー上部に1箇所。

### 7. レスポンシブ

- デスクトップ (xl ブレイクポイント以上): 右サイドにスティッキー表示（既存の枠と同じ位置）
- モバイル: 「プレビューを表示」トグルで開閉（既存の `previewVisible` ロジックを継続使用）

### 8. アクセシビリティ

- タブ: `role="tab"` + `aria-selected` 属性
- タブパネル: `role="tabpanel"` + `aria-labelledby`
- アバターの代替テキスト: `alt="プロフィール画像"`

### 9. 文字数オーバーフローの視覚警告

- X タブで content_text が 280 を超えたら本文背景に薄い赤、超過分は赤色テキスト
- IG タブは 2200 文字目安、超えても警告のみ

### 10. README 更新

`apps/web/README.md` の `/create` の説明にプレビュー機能を追記。

### 11. 動作確認

```bash
pnpm typecheck
pnpm lint
pnpm build
```

ブラウザ動作確認は Claude が実施。

---

## スコープ外（やらないこと）

- ❌ note / YouTube / LINE のプレビュー実装（X/IG のみ）
- ❌ 実画像レンダリング（storage_path がローカルなので画像表示不可、スケルトンで妥協）
- ❌ 投稿API送信ロジック改変（WEB-016 で完成済）
- ❌ apps/web/src/generated/ の編集
- ❌ 新規 NPM 依存追加（lucide-react 等は不要、Tailwind + emoji or font-awesome class で十分）
- ❌ 既存 WEB-001〜016 の改変（ただし `/create/page.tsx` のプレビュー枠は置換OK）

---

## 絶対守るべきこと

- **CLAUDE.md の Codex CLI Usage 節に従う**: 偽装絶対禁止
- **axios 不使用**
- **既存テスト維持**（pytest 51 件、pnpm 全タスク）
- **`"use client"` 必須**
- **next/navigation のみ使用**
- **Tailwind カスタムテーマは変更しない**（既存 `bg-x` / `bg-ig` / `text-x` / `text-ig` を使用）
- **Finder 複製 `* 2.*` を作らない**

---

## 成果物チェックリスト

- [ ] `apps/web/src/components/preview/PreviewPanel.tsx` 新規作成
- [ ] `apps/web/src/components/preview/XPreview.tsx` 新規作成
- [ ] `apps/web/src/components/preview/IgPreview.tsx` 新規作成
- [ ] `apps/web/src/app/create/page.tsx` のプレースホルダ部分を `<PreviewPanel />` で置換
- [ ] フォーム値の変更でリアルタイム反映
- [ ] X タブ: ヘッダー / 本文 / 画像枠 / アクションバー / 文字数
- [ ] IG タブ: 上部バー / メイン画像枠 / アクション / キャプション / ハッシュタグ強調
- [ ] タブ切替（aria-* 属性付与）
- [ ] 選択外 SNS のタブはグレーアウト
- [ ] X 280字超過の視覚警告
- [ ] HelpMark 2箇所追加、help-texts に create.preview_* 追加
- [ ] レスポンシブ（デスクトップsticky、モバイル トグル）
- [ ] `pnpm typecheck / build / lint` 通過
- [ ] 偽装 / shim / Finder複製 一切なし
- [ ] README 更新

---

## コミット指示

- `git add` は明示指定のみ
- `.env` / `apps/web/src/generated/` はコミット対象外
- コミットメッセージ: `feat: WEB-017 プレビューパネル（X/IG リアルタイム表示・タブ切替）`
- Co-Authored-By 不要

---

## 補足: 関連設計ドキュメント

- `design/mockup/index.html` の preview 部分（750-900行付近）

---

## 環境情報

- Next.js 15 + React 19 + TypeScript 5.7 + Tailwind 3.4
- pnpm 9.15.9 / Node 25.2.1
- `react-hook-form` 既導入（`watch` で値監視可）

**重要**: 完了報告時に偽装スキャンの自己確認を実施してください。
