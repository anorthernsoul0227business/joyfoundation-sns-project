# Codexブリーフィング: WEB-001 モノレポ初期構成

**作成日**: 2026-04-17
**担当Issue**: WEB-001（Sprint 1 / 工数: 1日）
**依存**: なし
**後続ブロック**: WEB-002（OpenAPI自動生成）、WEB-003（Supabase）、WEB-008（docker-compose）、WEB-009（CI/CD）

---

## タスク概要

SNS投稿管理Webアプリの**モノレポ骨格**を初期化する。Turborepo + pnpm をベースに、`apps/web`（Next.js 15）と `apps/api`（FastAPI）の2アプリ + `packages/*` の共有モジュール構造を立ち上げる。

**この段階では「動くハロー・ワールド」まで。認証・DB接続・ビジネスロジックは含めない。**

---

## 前提: プロジェクト全体像

- **プロダクト**: サウンドヒーリング協会/ジョイファンデーションのSNS投稿を一元管理するWebアプリ
- **対応SNS**: X, Instagram, note, YouTube（Phase 1はX・IGのみ）
- **主要機能**: カレンダー型UI・D&D投稿予約・AI記事生成・自動投稿・品質評価
- **規模**: 30 Issue / 4 Sprint / 7-8週間 / MVPコスト $5-15/月
- **既存資産**: `sns-auto-poster/`（Python投稿スクリプト群、Sprint 3で移植予定）

---

## 技術スタック（確定事項）

| 層 | 採用技術 | 根拠 |
|---|---|---|
| モノレポ | **Turborepo + pnpm** | Vercel親和性、キャッシュ性能、2言語対応 |
| フロントエンド | **Next.js 15 (App Router) + TypeScript + Tailwind CSS** | shadcn/uiベースのデザインシステム |
| 状態管理 | **Zustand** | 軽量、Serverコンポーネント親和性 |
| バックエンド | **FastAPI + Python 3.11+** | 既存Python資産再利用 |
| DB/Auth | **Supabase (Postgres + Auth + RLS)** | MVP速度優先 |
| ジョブ | **Celery + Redis** | 既存Python資産 |
| 型安全 | **OpenAPI自動生成 (@hey-api/openapi-ts)** | Pydantic → TS型自動同期 |
| バリデーション | **zod** | フロント・バックエンド共有 |
| カレンダー | **FullCalendar + dnd-kit** | Sprint 2以降 |
| デプロイ | **Vercel (web) + Railway (api) + Supabase + Cloudflare R2** | Sprint 4 |

---

## スコープ（WEB-001で実装するもの）

### 必須成果物

1. **ルート設定**
   - `package.json`（private: true, workspacesはpnpm側で管理）
   - `pnpm-workspace.yaml`
   - `turbo.json`（パイプライン定義: build/lint/typecheck/dev/generate:api-client）
   - `.gitignore`（Node + Python + 各種ローカル設定）
   - `.nvmrc` or `engines`でNode 20.x指定
   - `README.md`（セットアップ手順）

2. **apps/web**（Next.js 15 App Router骨格）
   ```
   apps/web/
   ├── src/
   │   ├── app/
   │   │   ├── layout.tsx
   │   │   ├── page.tsx             # 「Hello SNS Calendar」最小ページ
   │   │   └── globals.css
   │   ├── components/              # 空 or .gitkeep
   │   ├── hooks/                   # 空 or .gitkeep
   │   ├── stores/                  # 空 or .gitkeep
   │   ├── lib/                     # 空 or .gitkeep
   │   └── generated/               # 空 or .gitkeep (WEB-002で埋まる)
   ├── next.config.ts
   ├── tailwind.config.ts
   ├── postcss.config.mjs
   ├── tsconfig.json                # packages/config/typescriptを継承
   ├── .eslintrc.json               # packages/config/eslintを継承
   └── package.json
   ```
   - Tailwind導入済み（mockup設定のbrandカラーに後で拡張できる骨格）
   - `pnpm dev` で http://localhost:3000 に起動

3. **apps/api**（FastAPI骨格）
   ```
   apps/api/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py                  # FastAPIインスタンス + /health エンドポイント
   │   ├── config.py                # pydantic-settings（環境変数）
   │   ├── api/                     # 空ルーター置き場 (.gitkeep)
   │   ├── models/                  # .gitkeep
   │   ├── schemas/                 # .gitkeep
   │   ├── services/                # .gitkeep
   │   └── core/                    # .gitkeep
   ├── scripts/
   │   └── generate_openapi.py      # WEB-002で実装 → 今はスタブでOK
   ├── tests/
   │   └── test_health.py           # /health の最小テスト
   ├── pyproject.toml               # Poetry or uv（Poetry推奨）
   ├── .python-version              # 3.11
   └── README.md
   ```
   - `/health` エンドポイント: `{"status": "ok"}` を返すだけ
   - `poetry run uvicorn app.main:app --reload` で http://localhost:8000 に起動
   - `pytest tests/` で health test が通る

4. **packages/shared-types**（zodスキーマ共有パッケージ）
   - `package.json`（name: `@sns-calendar/shared-types`）
   - 最小限のプレースホルダexport（`src/index.ts`で `export const VERSION = '0.1.0'`）
   - Sprint 2以降でpost/calendar/sns-accountスキーマを追加

5. **packages/ui**（デザインシステム骨格）
   - shadcn/ui 初期化（`components.json`）
   - Buttonコンポーネントのみ先行配置（`src/button.tsx`）
   - `package.json`（name: `@sns-calendar/ui`）

6. **packages/config**（共通設定）
   - `eslint/index.js`（Next.js + TypeScript推奨設定）
   - `typescript/base.json`, `typescript/nextjs.json`
   - `tailwind/index.js`（brandカラー等の共通テーマ）

7. **docker-compose.yml**（スタブのみ、WEB-008で完成）
   - Redisサービス定義
   - Celery worker定義はコメントアウトでプレースホルダ

8. **動作確認コマンド（全て成功すること）**
   ```bash
   pnpm install                     # 依存解決
   pnpm dev                         # web + api が並行起動
   pnpm build                       # web ビルド成功
   pnpm typecheck                   # TypeScript エラー 0
   pnpm lint                        # Lint エラー 0
   cd apps/api && poetry install && poetry run pytest  # API テスト成功
   ```

### やらないこと（スコープ外）

- ❌ 認証機能（Supabase Auth統合はWEB-006）
- ❌ DBモデル・Alembicマイグレーション（WEB-004）
- ❌ OpenAPI自動生成の実装（WEB-002 — ここではディレクトリと空スクリプトだけ）
- ❌ 投稿機能・AI生成（Sprint 2-3）
- ❌ CI/CDワークフローファイル（WEB-009）
- ❌ Vercel/Railwayデプロイ設定（WEB-029）
- ❌ ビジネスロジックの先取り実装（「ついでに投稿作成画面も…」は禁止）

---

## ディレクトリ構造（確定版・全体）

参考のため全体像を記載。WEB-001では太字部分の骨格だけ作る。

```
sns-calendar-app/
├── **turbo.json**
├── **pnpm-workspace.yaml**
├── **package.json**
├── .github/workflows/         # WEB-009で作成
├── **apps/**
│   ├── **web/**               # Next.js骨格まで
│   └── **api/**               # FastAPI骨格 + /health まで
├── **packages/**
│   ├── **shared-types/**      # zod用プレースホルダ
│   ├── **ui/**                # shadcn/ui初期化 + Button のみ
│   └── **config/**            # eslint/ts/tailwind共通設定
├── **docker-compose.yml**     # Redisのみ稼働、Celeryはコメントアウト
└── **README.md**              # セットアップ手順
```

---

## 設計制約・重要な注意点

### セキュリティ
- **axios v1.14.1, v0.30.4 は絶対に使わない**（2026-03-30のサプライチェーン攻撃パッケージ）
- `npm install` / `pnpm install` 後はlockfileでaxiosのバージョンを確認
- 安全バージョン: axios v1.13.x系（使う場合）
- 代替: `fetch` 標準APIまたは `@hey-api/client-fetch`（OpenAPIクライアント側で使用予定）

### 依存バージョン指針
- Node.js: 20.x LTS
- pnpm: 9.x
- Python: 3.11
- Next.js: 15.x
- FastAPI: 0.110+
- Turborepo: 2.x

### Phase 2を見据えた設計
- **マルチテナント（org_id方式）をDB設計時に仕込む予定**（WEB-004で対応、今回は不要）
- **英語展開が夏頃**（i18n骨格はPhase 1.5で追加、今回は不要）

### コーディング規約
- コミットメッセージ: `<タイプ>: <概要>` （feat/fix/docs/refactor/test/chore）
- Co-Authored-By付与必須
- 不要な抽象化・将来機能の先取り禁止

---

## 成果物チェックリスト（レビュー項目）

Codex納品後、以下をClaude側で検証:

- [ ] `sns-calendar-app/` ディレクトリが新規作成されている（プロジェクトルート直下）
- [ ] 確定版ディレクトリ構造と完全一致
- [ ] `pnpm install` が成功する
- [ ] `pnpm dev` でweb(:3000) + api(:8000)が同時起動
- [ ] web: トップページに「Hello SNS Calendar」等が表示される
- [ ] api: `curl http://localhost:8000/health` が `{"status":"ok"}`
- [ ] `pnpm build` 成功
- [ ] `pnpm typecheck` エラー0
- [ ] `pnpm lint` エラー0
- [ ] `apps/api` でpytest成功
- [ ] axios悪意バージョンが含まれていない（lockfile grep）
- [ ] スコープ外の実装が混入していない
- [ ] READMEにセットアップ手順が記載されている

---

## 補足: 関連設計ドキュメント

Codexは以下を参照して良い（コピー可能な範囲はコピーして使う）:

- `design/design/IMPLEMENTATION_PLAN.md` — 実装計画全体（特にセクション1-2）
- `design/design/APP_DESIGN_SPEC.md` — 全体仕様と決定事項
- `design/design/PLATFORM_MATRIX.md` — SNS別機能マトリクス
- `design/mockup/index.html` — UIモックアップ（参考用、この段階ではUIは最小）

---

## 完了基準

1. 上記チェックリストが全て通る
2. `git status` で `sns-calendar-app/` 配下に新規ファイルが追加されている
3. 初回コミット `feat: WEB-001 モノレポ初期構成` が作成されている

**納品フォーマット**: PR or パッチファイル or 直接コミット（方針は別途指示）
