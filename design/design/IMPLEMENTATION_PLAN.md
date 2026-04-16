# Phase 1 実装計画（Codex壁打ち R5 結果）

**作成日**: 2026-04-16
**関連**: APP_DESIGN_SPEC.md / 旧 phase1_implementation_plan.md（Google Sheets版）からWebアプリ版への移行

---

## 前提と総評

- 旧Phase 1（Google Sheets + GitHub Actions）は稼働中。本ドキュメントは**Webアプリ版 Phase 1**の実装計画。
- Postiz（OSS SNSスケジューラ）のアーキテクチャを参考にしつつ、FastAPI + Next.jsの二言語構成に最適化。
- **Turborepoモノレポ**で型安全性を確保（OpenAPI自動生成 → TypeScriptクライアント）。
- 最大のリスクは「二言語のグルーコード」。OpenAPI自動生成パイプラインを初日に構築することで緩和。

---

## 1. モノレポ構成

### 1.1 ディレクトリ構造（確定版）

```
sns-calendar-app/
├── turbo.json                        # Turborepoパイプライン定義
├── pnpm-workspace.yaml               # pnpmワークスペース定義
├── package.json                      # ルートpackage.json
├── .github/
│   └── workflows/
│       ├── ci.yml                    # PR時: lint + test + typecheck
│       ├── deploy-frontend.yml       # Vercelデプロイ
│       └── deploy-backend.yml        # Railwayデプロイ
│
├── apps/
│   ├── web/                          # Next.js 15 (App Router)
│   │   ├── src/
│   │   │   ├── app/                  # App Router ページ
│   │   │   ├── components/           # UIコンポーネント
│   │   │   ├── hooks/                # カスタムフック
│   │   │   ├── stores/               # Zustand ステート管理
│   │   │   ├── lib/                  # ユーティリティ
│   │   │   └── generated/            # OpenAPI自動生成クライアント
│   │   ├── next.config.ts
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   │
│   └── api/                          # FastAPI
│       ├── app/
│       │   ├── main.py               # FastAPIアプリ + OpenAPIスキーマ
│       │   ├── config.py             # 設定（環境変数）
│       │   ├── models/               # SQLAlchemy モデル
│       │   ├── schemas/              # Pydantic スキーマ
│       │   ├── api/                  # ルーター
│       │   │   ├── auth.py
│       │   │   ├── posts.py
│       │   │   ├── calendar.py
│       │   │   ├── sns_accounts.py
│       │   │   ├── media.py
│       │   │   ├── generate.py
│       │   │   └── notifications.py
│       │   ├── services/
│       │   │   ├── publisher/        # 投稿実行（既存スクリプト移植）
│       │   │   │   ├── base.py
│       │   │   │   ├── x_publisher.py
│       │   │   │   ├── ig_publisher.py
│       │   │   │   └── note_publisher.py
│       │   │   ├── ai_generator/     # AI記事生成
│       │   │   ├── scheduler.py      # Celeryタスク定義
│       │   │   ├── notifier.py       # 通知
│       │   │   └── media_processor.py
│       │   ├── core/
│       │   │   ├── security.py       # JWT認証
│       │   │   ├── database.py       # DB接続
│       │   │   └── supabase.py       # Supabaseクライアント
│       │   └── tasks/
│       │       └── celery_tasks.py
│       ├── alembic/                  # DBマイグレーション
│       ├── scripts/
│       │   └── generate_openapi.py   # OpenAPIスキーマ出力
│       ├── pyproject.toml
│       ├── Dockerfile
│       └── requirements.txt
│
├── packages/
│   ├── shared-types/                 # zodスキーマ（フロント・バックエンド共有）
│   │   ├── src/
│   │   │   ├── post.ts
│   │   │   ├── calendar.ts
│   │   │   ├── sns-account.ts
│   │   │   └── index.ts
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── ui/                           # デザインシステム（shadcn/uiベース）
│   │   ├── src/
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── calendar-event.tsx
│   │   │   └── index.ts
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── config/                       # 共通設定
│       ├── eslint/
│       ├── typescript/
│       └── tailwind/
│
├── docker-compose.yml                # ローカル開発（Redis + Celery worker）
└── README.md
```

### 1.2 Turborepo パイプライン定義

```json
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "globalDependencies": ["**/.env.*local"],
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": [".next/**", "!.next/cache/**", "dist/**"]
    },
    "lint": {
      "dependsOn": ["^build"]
    },
    "typecheck": {
      "dependsOn": ["^build"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "generate:api-client": {
      "dependsOn": ["^build"],
      "outputs": ["apps/web/src/generated/**"]
    }
  }
}
```

### 1.3 pnpmワークスペース

```yaml
# pnpm-workspace.yaml
packages:
  - "apps/*"
  - "packages/*"
```

---

## 2. OpenAPI型安全パイプライン

### 2.1 フロー

```
FastAPI Pydantic Models
  ↓  python scripts/generate_openapi.py
openapi.json (apps/api/openapi.json)
  ↓  @hey-api/openapi-ts
TypeScript Client (apps/web/src/generated/)
  ├── schemas.gen.ts   ← Pydanticモデル → TS型
  ├── types.gen.ts     ← リクエスト/レスポンス型
  └── services.gen.ts  ← API呼び出し関数
```

### 2.2 バックエンド側: スキーマ出力スクリプト

```python
# apps/api/scripts/generate_openapi.py
import json
from pathlib import Path
from app.main import app

def main():
    schema = app.openapi()
    output = Path(__file__).parent.parent / "openapi.json"
    output.write_text(json.dumps(schema, indent=2))
    print(f"OpenAPI schema written to {output}")

if __name__ == "__main__":
    main()
```

### 2.3 フロントエンド側: クライアント生成

```typescript
// apps/web/openapi-ts.config.ts
import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  client: '@hey-api/client-fetch',
  input: '../api/openapi.json',
  output: 'src/generated',
});
```

```json
// apps/web/package.json scripts
{
  "scripts": {
    "generate:api-client": "openapi-ts",
    "dev": "next dev",
    "build": "next build"
  }
}
```

### 2.4 開発時の自動同期

```python
# apps/api/watcher.py — ファイル変更時に自動再生成
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess, time

class SchemaRegenHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_run = 0

    def on_modified(self, event):
        if event.src_path.endswith(('.py',)) and time.time() - self.last_run > 2:
            self.last_run = time.time()
            subprocess.run(["python", "scripts/generate_openapi.py"])

# watchdog起動 → openapi.json変更 → フロント側chokidarが検知 → クライアント再生成
```

### 2.5 pre-commitフック

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: generate-openapi-schema
      name: Regenerate OpenAPI schema
      entry: sh -c 'cd apps/api && python scripts/generate_openapi.py'
      language: system
      files: 'apps/api/app/(schemas|api)/.*\.py$'
    - id: generate-api-client
      name: Regenerate API client
      entry: sh -c 'cd apps/web && pnpm generate:api-client'
      language: system
      files: 'apps/api/openapi\.json$'
```

---

## 3. インフラ / DevOps 設計

### 3.1 環境構成

```
                ┌─────────────┐
                │   Vercel     │ ← apps/web (Next.js)
                │  (Frontend)  │   Preview Deploy: PR毎
                └──────┬──────┘
                       │ HTTPS
                       ▼
                ┌─────────────┐
                │   Railway    │ ← apps/api (FastAPI)
                │  (Backend)   │   + Celery worker
                │  + Redis     │   + Redis（Railway addon）
                └──────┬──────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
     ┌──────────┐ ┌────────┐ ┌──────────┐
     │ Supabase │ │  R2    │ │ External │
     │ (Auth+DB)│ │(画像)  │ │ APIs     │
     └──────────┘ └────────┘ │ X/IG/YT  │
                              └──────────┘
```

### 3.2 環境別構成

| 環境 | Frontend | Backend | DB | 用途 |
|---|---|---|---|---|
| **Local** | `next dev` (localhost:3000) | `uvicorn` (localhost:8000) | Supabase CLI (localhost:54321) | 開発 |
| **Preview** | Vercel Preview (PR毎URL) | Railway PR環境 | Supabase staging | PRレビュー |
| **Production** | Vercel Production | Railway Production | Supabase Production | 本番 |

### 3.3 ローカル開発環境

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  celery-worker:
    build: ./apps/api
    command: celery -A app.tasks.celery_tasks worker --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_SERVICE_ROLE_KEY=${SUPABASE_SERVICE_ROLE_KEY}
    depends_on:
      - redis
    volumes:
      - ./apps/api:/app

  celery-beat:
    build: ./apps/api
    command: celery -A app.tasks.celery_tasks beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./apps/api:/app
```

```bash
# 開発起動コマンド（ルートから）
pnpm dev          # Next.js + FastAPI 同時起動（Turborepo）
docker compose up  # Redis + Celery worker/beat
supabase start     # Supabase CLI（ローカルDB）
```

### 3.4 CI/CD パイプライン

```yaml
# .github/workflows/ci.yml
name: CI
on:
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: 'pnpm' }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }

      # Frontend
      - run: pnpm install
      - run: pnpm turbo lint typecheck --filter=web

      # Backend
      - run: pip install -r apps/api/requirements.txt
      - run: cd apps/api && python -m pytest
      - run: cd apps/api && ruff check .

      # OpenAPI整合性チェック
      - run: cd apps/api && python scripts/generate_openapi.py
      - run: git diff --exit-code apps/api/openapi.json  # 差分があればfail
```

```yaml
# .github/workflows/deploy-frontend.yml
name: Deploy Frontend
on:
  push:
    branches: [main]
    paths: ['apps/web/**', 'packages/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          vercel-args: '--prod'
```

### 3.5 コスト試算（月額）

| サービス | プラン | 月額 | 備考 |
|---|---|---|---|
| Vercel | Hobby→Pro | $0→$20 | MVP期間はHobbyで十分 |
| Railway | Starter | ~$5-15 | 従量課金、FastAPI + Redis + Celery |
| Supabase | Free→Pro | $0→$25 | 500MBまで無料、Pro以降は$25 |
| Cloudflare R2 | Free tier | $0 | 10GB/月まで無料 |
| GitHub Actions | Free | $0 | 2,000分/月まで無料 |
| **合計（MVP期間）** | | **~$5-15** | Railway従量課金のみ |
| **合計（PMF後）** | | **~$60-80** | 全サービスPro移行時 |

---

## 4. FullCalendar + dnd-kit 統合設計

### 4.1 アーキテクチャ概要

```
┌─ dnd-kit DndContext ──────────────────────────────────────┐
│                                                            │
│  ┌─ Sidebar (dnd-kit Draggable) ──┐  ┌─ Calendar ──────┐ │
│  │                                 │  │                  │ │
│  │  DraftCard (draggable)          │  │  FullCalendar    │ │
│  │  DraftCard (draggable)          │  │  droppable=true  │ │
│  │  DraftCard (draggable)          │  │                  │ │
│  │                                 │  │  EventCard       │ │
│  └─────────────────────────────────┘  │  EventCard       │ │
│                                       │  (FC内部D&D)     │ │
│  ┌─ DragOverlay ──────────────────┐  └──────────────────┘ │
│  │ ドラッグ中のプレビュー表示     │                        │
│  └─────────────────────────────────┘                       │
└────────────────────────────────────────────────────────────┘
```

**2つのD&Dシステムの共存:**
1. **FullCalendar内部**: カレンダー上のイベント移動（日時変更）→ FC公式 interaction plugin
2. **外部→カレンダー**: サイドバー下書き → カレンダーへドロップ → dnd-kit + FC `ThirdPartyDraggable`

### 4.2 実装パターン

```tsx
// components/calendar/CalendarView.tsx
'use client';

import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin, { ThirdPartyDraggable } from '@fullcalendar/interaction';
import { useEffect, useRef } from 'react';

export function CalendarView() {
  const calendarRef = useRef<FullCalendar>(null);

  // FullCalendar内部のイベント移動
  const handleEventDrop = async (info: EventDropArg) => {
    // PATCH /api/posts/:id/reschedule
    await reschedulePost(info.event.extendedProps.postId, info.event.start);
  };

  // 外部からのドロップ（dnd-kit経由）
  const handleEventReceive = async (info: EventReceiveArg) => {
    const draftId = info.event.extendedProps.draftId;
    const scheduledAt = info.event.start;
    
    // POST /api/posts/:id/schedule
    await schedulePost(draftId, scheduledAt);
  };

  return (
    <FullCalendar
      ref={calendarRef}
      plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
      initialView="dayGridMonth"
      editable={true}           // カレンダー内D&D有効
      droppable={true}          // 外部ドロップ受け入れ
      eventDrop={handleEventDrop}
      eventReceive={handleEventReceive}
      events={calendarEvents}
      headerToolbar={{
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay',
      }}
      locale="ja"
      timeZone="Asia/Tokyo"
      eventContent={renderEventContent}  // カスタムイベント表示
    />
  );
}

// カスタムイベントレンダラー（SNSごとの色分け）
function renderEventContent(eventInfo: EventContentArg) {
  const platform = eventInfo.event.extendedProps.platform;
  const colorMap = { x: 'bg-x/10 text-x', instagram: 'bg-ig/10 text-ig' };

  return (
    <div className={`px-1.5 py-0.5 rounded text-[10px] truncate ${colorMap[platform]}`}>
      <PlatformIcon platform={platform} />
      {eventInfo.timeText} {eventInfo.event.title}
    </div>
  );
}
```

### 4.3 サイドバー下書きパネル（dnd-kit）

```tsx
// components/calendar/DraftsSidebar.tsx
'use client';

import {
  DndContext,
  DragOverlay,
  useSensor,
  useSensors,
  PointerSensor,
} from '@dnd-kit/core';
import { useDraggable } from '@dnd-kit/core';

export function DraftsSidebar({ drafts }: { drafts: Draft[] }) {
  const [activeDraft, setActiveDraft] = useState<Draft | null>(null);
  const sensors = useSensors(useSensor(PointerSensor, {
    activationConstraint: { distance: 8 },  // 8px移動でドラッグ開始
  }));

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(event) => {
        const draft = drafts.find(d => d.id === event.active.id);
        setActiveDraft(draft ?? null);
      }}
      onDragEnd={() => setActiveDraft(null)}
    >
      <div className="w-72 bg-white rounded-xl border">
        <h3 className="px-4 py-3 font-semibold text-sm border-b">
          下書き ({drafts.length}件)
        </h3>
        <div className="p-3 space-y-2">
          {drafts.map(draft => (
            <DraggableDraftCard key={draft.id} draft={draft} />
          ))}
        </div>
      </div>

      {/* ドラッグ中のオーバーレイ */}
      <DragOverlay>
        {activeDraft && <DraftCardPreview draft={activeDraft} />}
      </DragOverlay>
    </DndContext>
  );
}

function DraggableDraftCard({ draft }: { draft: Draft }) {
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: draft.id,
    data: {
      // FullCalendarのThirdPartyDraggableに渡すイベントデータ
      event: {
        title: draft.title,
        duration: '01:00',
        extendedProps: { draftId: draft.id, platform: draft.platform },
        create: true,
      },
    },
  });

  return (
    <div ref={setNodeRef} {...listeners} {...attributes}
      className="post-card bg-white border rounded-lg p-3 cursor-grab"
    >
      <span className="text-xs font-medium">{draft.title}</span>
      <PlatformBadges platforms={draft.platforms} />
    </div>
  );
}
```

### 4.4 dnd-kit → FullCalendar ブリッジ

```tsx
// hooks/useCalendarDndBridge.ts
import { ThirdPartyDraggable } from '@fullcalendar/interaction';
import { useEffect } from 'react';

/**
 * dnd-kitのドラッグイベントをFullCalendarのThirdPartyDraggableに変換
 * 
 * 方式: dnd-kitのDragOverlay表示時に、同じDOM要素を
 * ThirdPartyDraggableとして登録し、FCのドロップ検知に乗せる
 */
export function useCalendarDndBridge(sidebarRef: RefObject<HTMLElement>) {
  useEffect(() => {
    if (!sidebarRef.current) return;

    const draggable = new ThirdPartyDraggable(sidebarRef.current, {
      itemSelector: '.post-card',
      mirrorSelector: '.dnd-kit-overlay',
      eventData: (eventEl) => {
        // data-*属性からイベントデータを取得
        return {
          title: eventEl.dataset.title,
          duration: '01:00',
          extendedProps: {
            draftId: eventEl.dataset.draftId,
            platform: eventEl.dataset.platform,
          },
          create: true,
        };
      },
    });

    return () => draggable.destroy();
  }, [sidebarRef]);
}
```

### 4.5 代替案: FullCalendar公式Draggableのみ使用

```
検討結果: FullCalendar公式Draggableのみで十分な可能性あり。

FullCalendar v6のDraggable APIは外部要素のD&Dを公式サポート。
dnd-kitが追加で必要になるのは以下のケースのみ:
  - サイドバー内での下書き並べ替え
  - 下書きパネル → ゴミ箱へのD&D
  - モバイル向けタッチD&D（FCのタッチ対応が不十分な場合）

推奨: Phase 1はFC公式Draggableのみで実装。
      D&D UXに不足を感じたらPhase 1.5でdnd-kitを追加導入。
```

---

## 5. Issue分割（GitHub Issue化 — Webアプリ版）

### 5.1 Sprint 1: 基盤構築（2週間）

| Issue | タイトル | 工数 | 依存 |
|---|---|---|---|
| WEB-001 | モノレポ初期構成（Turborepo + pnpm + apps/web + apps/api） | 1日 | - |
| WEB-002 | OpenAPI自動生成パイプライン構築 | 1日 | WEB-001 |
| WEB-003 | Supabase プロジェクト作成 + ローカルCLI設定 | 0.5日 | WEB-001 |
| WEB-004 | DBスキーマ作成（Alembicマイグレーション: users, organizations, org_members） | 1日 | WEB-003 |
| WEB-005 | RLSポリシー適用（RLS_DESIGN.md準拠） | 1日 | WEB-004 |
| WEB-006 | 認証API実装（signup, login, logout, refresh） | 1.5日 | WEB-004 |
| WEB-007 | ログイン/サインアップ画面実装 | 1.5日 | WEB-006 |
| WEB-008 | docker-compose（Redis + Celery） | 0.5日 | WEB-001 |
| WEB-009 | CI/CD基盤（GitHub Actions: lint + test + OpenAPI整合性チェック） | 1日 | WEB-002 |

### 5.2 Sprint 2: コア機能（2週間）

| Issue | タイトル | 工数 | 依存 |
|---|---|---|---|
| WEB-010 | DBスキーマ追加（posts, post_targets, post_media, sns_accounts） | 1日 | WEB-005 |
| WEB-011 | 投稿CRUD API（POST/GET/PATCH/DELETE /api/posts） | 2日 | WEB-010 |
| WEB-012 | スケジュールAPI（schedule, reschedule, unschedule, publish-now） | 1日 | WEB-011 |
| WEB-013 | カレンダーAPI（GET /api/calendar?from=&to=&platforms[]=） | 1日 | WEB-011 |
| WEB-014 | カレンダー画面実装（FullCalendar月/週/日 + SNS色分け） | 2日 | WEB-013 |
| WEB-015 | 下書き一覧画面実装（フィルタ/ソート/検索） | 1.5日 | WEB-011 |
| WEB-016 | 投稿作成画面実装（テキストエディタ + 画像アップロード） | 2日 | WEB-011 |
| WEB-017 | プレビューパネル（X/IG切替プレビュー） | 1日 | WEB-016 |

### 5.3 Sprint 3: SNS連携 + 投稿実行（2週間）

| Issue | タイトル | 工数 | 依存 |
|---|---|---|---|
| WEB-018 | SNSアカウント連携API（OAuth: X, IG） | 2日 | WEB-010 |
| WEB-019 | SNSアカウント設定画面 | 1日 | WEB-018 |
| WEB-020 | X投稿Publisher実装（既存x_auto_poster移植） | 1.5日 | WEB-018 |
| WEB-021 | IG投稿Publisher実装（既存ig_auto_poster移植） | 1.5日 | WEB-018 |
| WEB-022 | Celery予約投稿タスク（check_scheduled_posts + publish_post） | 2日 | WEB-020, WEB-021 |
| WEB-023 | 投稿結果通知（メール通知: notifier.py移植） | 1日 | WEB-022 |
| WEB-024 | 画像自動変換（media_processor: R2アップロード + リサイズ） | 1.5日 | WEB-016 |
| WEB-025 | D&D実装（サイドバー下書き → カレンダー配置） | 1.5日 | WEB-014, WEB-015 |

### 5.4 Sprint 4: 統合 + テスト（1-2週間）

| Issue | タイトル | 工数 | 依存 |
|---|---|---|---|
| WEB-026 | ホーム画面（シンプルモード）実装 | 1.5日 | WEB-013 |
| WEB-027 | 通知画面 + WebSocket（投稿成功/失敗リアルタイム） | 1.5日 | WEB-023 |
| WEB-028 | E2Eテスト（投稿作成→予約→自動投稿→通知） | 2日 | WEB-022 |
| WEB-029 | Vercel + Railway本番デプロイ | 1日 | WEB-009 |
| WEB-030 | 内部運用開始（自社アカウントで実運用テスト） | 継続 | WEB-029 |

### 5.5 クリティカルパス

```
WEB-001 → WEB-002 → WEB-003 → WEB-004 → WEB-005
                                    ↓
              WEB-006 → WEB-007 → WEB-010 → WEB-011 → WEB-012
                                                ↓
                                    WEB-013 → WEB-014 → WEB-025
                                                ↓
                              WEB-018 → WEB-020/021 → WEB-022 → WEB-028
```

**最短パス: WEB-001 → ... → WEB-028 = 約7-8週間**

---

## 6. 開発順序の最適化

### 6.1 並行開発が可能な組み合わせ

```
Week 1-2: 基盤
  ├── [開発者A] WEB-001〜003 モノレポ + Supabase
  └── [開発者B] WEB-008〜009 Docker + CI/CD

Week 3-4: コア機能
  ├── [バックエンド] WEB-010〜013 API実装
  └── [フロントエンド] WEB-014〜017 UI実装（モックデータで先行）

Week 5-6: SNS連携
  ├── [バックエンド] WEB-018, 020〜023 Publisher + Celery
  └── [フロントエンド] WEB-019, 024〜025 設定画面 + D&D

Week 7-8: 統合
  └── [全員] WEB-026〜030 統合テスト + デプロイ
```

### 6.2 1人開発の場合の優先順位

1人で開発する場合は**バックエンドAPI → フロントエンドUI**の順序が効率的:
- APIが先に完成していればフロントエンドはOpenAPI生成クライアントで型安全に開発可能
- フロントエンドをモックデータで先行すると、API完成後に接続時の修正が発生しやすい

---

## 7. 決定事項まとめ

| # | 項目 | 決定 | 理由 |
|---|---|---|---|
| 1 | モノレポツール | **Turborepo + pnpm** | Vercelとの親和性、キャッシュ性能、2言語対応 |
| 2 | 型安全パイプライン | **OpenAPI自動生成 (@hey-api/openapi-ts)** | Pydantic → TS型の自動同期。pre-commitフックで整合性保証 |
| 3 | ローカル開発 | **docker-compose (Redis+Celery) + Supabase CLI** | 本番に近い環境をローカルで再現 |
| 4 | CI/CD | **GitHub Actions → Vercel + Railway** | 無料枠活用、PR毎プレビュー |
| 5 | カレンダーD&D | **Phase 1: FC公式Draggableのみ** | dnd-kitは必要に応じてPhase 1.5で追加 |
| 6 | Issue管理 | **30 Issue、4 Sprint（7-8週間）** | クリティカルパスを明確化 |
| 7 | コスト | **MVP期間: ~$5-15/月** | Railway従量課金のみ。PMF後は~$60-80/月 |

---

## 8. 優先アクション（今すぐやること）

| # | アクション | 工数 |
|---|---|---|
| 1 | GitHubリポジトリ作成 `sns-calendar-app` | 10分 |
| 2 | Turborepo + pnpmモノレポ初期化 | 30分 |
| 3 | apps/web (Next.js 15) + apps/api (FastAPI) スキャフォールド | 1時間 |
| 4 | OpenAPI自動生成パイプライン構築 | 1時間 |
| 5 | Supabaseプロジェクト作成 + ローカルCLI設定 | 30分 |
| 6 | docker-compose（Redis + Celery）作成 | 30分 |
| 7 | GitHub Issues 30件を一括起票 | 1時間 |
