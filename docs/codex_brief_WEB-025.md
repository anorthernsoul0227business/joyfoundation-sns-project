# Codexブリーフィング: WEB-025 D&D実装（サイドバー下書き → カレンダー）

**作成日**: 2026-04-21
**担当Issue**: WEB-025（Sprint 3 / 工数: 1.5日）
**依存**: WEB-014（カレンダー画面 FullCalendar）、WEB-015（下書き一覧画面）
**参考**: `design/design/IMPLEMENTATION_PLAN.md` セクション 4（FullCalendar + dnd-kit 統合設計）
**後続**: WEB-026（ホーム画面から類似操作）

---

## タスク概要

カレンダー画面のサイドバーに **下書き一覧** を表示し、カレンダーのスロットに **D&D で配置** できるようにする。ドロップで `POST /api/posts/{id}/schedule` を呼び、成功時に FullCalendar にイベントが追加される。

**採用方針**: IMPLEMENTATION_PLAN.md セクション 4.5 の **FullCalendar公式Draggableのみ**（Phase 1 はdnd-kit併用しない。シンプル優先）。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| D&D ライブラリ | **FullCalendar `interaction` plugin の Draggable** | 既存 FC と相性が良い、追加依存最小 |
| サイドバー | カレンダー画面 (`/calendar`) 左端に固定幅パネル | shadcn/ui パターン |
| 下書きソース | `GET /api/posts?status=draft` | WEB-011 既存API |
| ドロップ時 | 日付スロットへ drop → `PATCH /api/posts/{id}` で `scheduled_at` 更新 + `POST /api/posts/{id}/schedule` | WEB-012 API |
| 楽観更新 | drop 直後にイベントをカレンダーに追加、APIエラー時はロールバック | UX 向上 |
| 時刻 | デフォルト 12:00 JST 固定（後続で編集可能） | Phase 1 簡素化 |
| プラットフォーム | 下書きに紐付く `post_targets.platform` をイベントで表示 | 色分け既存ロジック流用 |

---

## スコープ

### 1. サイドバー追加（`apps/web/src/app/calendar/page.tsx` 更新）

既存の FullCalendar レイアウトに左 300px のサイドバーを追加。

```tsx
<div className="flex gap-4">
  <aside className="w-80 shrink-0">
    <DraftsSidebar drafts={drafts} onRefresh={refetchDrafts} />
  </aside>
  <main className="flex-1">
    <FullCalendar {...calendarOptions} />
  </main>
</div>
```

### 2. 新規コンポーネント: `DraftsSidebar`

`apps/web/src/components/calendar/DraftsSidebar.tsx`:
- `draft` リストを取得（`fetchPostList({ status: "draft" })`）
- 各カードは `data-event` 属性付き（FullCalendar 用）
- `FullCalendar.Draggable` コンストラクタでサイドバー要素を受け渡す
- 検索ボックス + プラットフォームフィルタ（WEB-015 と重複する最小版）
- カードに「カレンダーへドラッグ」アイコン表示

```tsx
import { Draggable } from "@fullcalendar/interaction";

const containerRef = useRef<HTMLDivElement>(null);
useEffect(() => {
  if (!containerRef.current) return;
  const draggable = new Draggable(containerRef.current, {
    itemSelector: "[data-draft-id]",
    eventData: (el) => {
      const id = el.getAttribute("data-draft-id");
      const title = el.getAttribute("data-draft-title") ?? "下書き";
      return { id, title, extendedProps: { draftId: id } };
    },
  });
  return () => draggable.destroy();
}, []);
```

### 3. FullCalendar オプション更新

`apps/web/src/app/calendar/page.tsx` の `calendarOptions` に追加:

```tsx
{
  editable: true,
  droppable: true,
  drop: async (info) => {
    const draftId = info.draggedEl.getAttribute("data-draft-id");
    if (!draftId) return;
    const scheduledAt = combineDateWithDefaultTime(info.date);  // YYYY-MM-DDT12:00:00+09:00
    try {
      await schedulePost(draftId, scheduledAt);
      await refetchCalendar();
      await refetchDrafts();
    } catch (err) {
      // エラーバナー表示
    }
  },
  eventReceive: (info) => {
    // 楽観更新後の整合
  },
}
```

### 4. api-client 追加

`apps/web/src/lib/api-client.ts` に:
- `schedulePost(postId, scheduledAt): Promise<PostResponse>` — 既にあれば再利用、無ければ `PATCH /api/posts/{id}` + `POST /schedule` の 2 ステップラッパー
- 既存の `fetchPostList` を `{ status: "draft" }` フィルタ対応に拡張（既存実装に依存）

### 5. 既存カレンダーイベント表示との整合

`PostResponse → EventInput` 変換関数を再利用 / 拡張。`draftId` からカレンダーイベントへの変換キーマップが同じであることを確認。

### 6. ヘルプ追加

`help-texts.ts` に:
```typescript
"calendar.drafts_sidebar": "下書きをここからカレンダーへドラッグすると予約できます。時刻は12:00で配置されます（後で編集可能）。",
```

### 7. 動作確認チェックリスト（Claude 側で実施）

- [ ] `/calendar` 左サイドバーに下書き3件以上表示
- [ ] ドラッグしてカレンダーの日付にドロップ
- [ ] カレンダーにイベント表示、サイドバーから当該下書きが消える
- [ ] 下書き一覧画面 (`/drafts`) でも scheduled ステータス化
- [ ] APIエラー時に alert/banner で表示
- [ ] ドロップ時刻は 12:00 JST
- [ ] 既存のカレンダー移動・削除が壊れていない

---

## スコープ外

- ❌ 時刻指定モーダル（ドロップ後に時刻選択）。Phase 2
- ❌ 複数投稿一括ドラッグ
- ❌ カレンダーから下書きへ戻すドラッグ（Phase 2）
- ❌ dnd-kit 併用（IMPLEMENTATION_PLAN.md セクション 4.5 に従い Phase 1 は不採用）
- ❌ AI 生成下書きとの統合（別 Issue）
- ❌ モバイル D&D（Phase 2）
- ❌ キーボード操作での予約（a11y Phase 2）

---

## 必須検証コマンド

```bash
cd sns-calendar-app
pnpm typecheck
pnpm lint
pnpm build
```

`@fullcalendar/interaction` は既に `apps/web/package.json` にある想定。無ければ `pnpm --filter @sns-calendar/web add @fullcalendar/interaction`。

---

## 絶対守るべきこと

- **`apps/web/src/generated/` は手動編集禁止**
- **`next.config.ts` 変更禁止**
- **既存 /calendar /drafts 画面の挙動を壊さない**
- **Tailwind 既存 brand colors のみ使用**
- **Finder複製禁止 / 偽装禁止**
- **@fullcalendar/interaction を正規 npm からインストール**（偽装NG）
- **既存 API を変更しない**（フロント配線のみ）

---

## 成果物チェックリスト

- [ ] `apps/web/src/components/calendar/DraftsSidebar.tsx` 新規
- [ ] `apps/web/src/app/calendar/page.tsx` サイドバー追加 + FC options 更新
- [ ] `apps/web/src/lib/api-client.ts` に schedulePost ラッパー（無ければ）
- [ ] `apps/web/src/lib/help-texts.ts` に calendar.drafts_sidebar 追加
- [ ] `apps/web/package.json` に `@fullcalendar/interaction` 確認/追加
- [ ] `pnpm typecheck` / `pnpm lint` / `pnpm build` 成功
- [ ] 手動動作確認7項目パス（Claude 側）
- [ ] スコープ外実装混入なし

## コミット指示

- コミットメッセージ: `feat: WEB-025 D&D実装（下書き→カレンダー配置）`
- Co-Authored-By 不要
