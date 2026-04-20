# SNS Calendar App

WEB-002 時点のモノレポです。Turborepo + pnpm で `apps/web` と `apps/api` をまとめ、FastAPI の OpenAPI スキーマから TypeScript クライアントを生成する型安全パイプラインを構成しています。

## 前提

- Node.js 20.x
- pnpm 9.x
- Python 3.11
- Poetry

## セットアップ

```bash
cd sns-calendar-app
pnpm install
cd apps/api && poetry install
cd ../..
```

## 開発

```bash
pnpm dev
```

- Web: `http://localhost:3000`
- API: `http://localhost:8000`

## 検証

```bash
pnpm build
pnpm typecheck
pnpm lint
cd apps/api && poetry run pytest
```

## Supabase 設定

### 初回セットアップ

1. 依存をインストール
   ```bash
   cd apps/api && poetry install
   ```

2. 環境変数を設定
   ```bash
   cp .env.example .env
   # .env を開いて SUPABASE_SERVICE_ROLE_KEY に値を設定
   # （Supabase Dashboard → Settings → API Keys → Secret keys → Reveal）
   ```

3. ローカルで Supabase を起動
   ```bash
   supabase start
   ```

4. ローカル管理 UI にアクセス
   ```text
   Studio: http://localhost:54323
   ```

### リモート接続の切替

`.env` の `SUPABASE_URL` とキー類を切り替えて利用します。

### マイグレーション

`supabase/migrations/` は Pure Supabase migrations（SQL）で管理します。Alembic / SQLAlchemy は使いません。

1. ローカル Supabase の状態確認
   ```bash
   supabase status
   ```
2. 未起動ならローカル Supabase を起動
   ```bash
   supabase start
   ```
3. マイグレーションを再適用して確認
   ```bash
   supabase db reset
   ```

### マイグレーション追加ワークフロー

1. `supabase/migrations/` に `YYYYMMDDHHMMSS_description.sql` を追加します。
2. ローカルで `supabase db reset` を実行して、最初から適用できることを確認します。
3. 必要に応じて `supabase db dump --db-url "postgresql://postgres:postgres@127.0.0.1:54322/postgres" --schema public -f /tmp/schema_dump.sql` で生成スキーマを確認します。
4. API テストと既存の `pnpm typecheck && pnpm build && pnpm lint` を通して既存成果物に影響がないことを確認します。

### RLS 動作確認

1. ローカル Supabase を起動した状態で `supabase db reset` を実行します。
2. Supabase Studio (`http://localhost:54323`) の Table Editor から対象テーブルを開き、Policies タブで `organizations` / `org_members` / `users` のポリシーを確認します。
3. CLI で確認する場合は `psql "postgresql://postgres:postgres@127.0.0.1:54322/postgres" -c "SELECT schemaname, tablename, policyname FROM pg_policies WHERE schemaname='public' ORDER BY tablename, policyname;"` を実行します。
4. API 側の RLS 回帰確認は、ローカル専用の環境変数を一時指定して `cd apps/api && SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_ANON_KEY=... SUPABASE_SERVICE_ROLE_KEY=... poetry run pytest -v` で実行します。

### RLS トラブルシューティング

- フロントエンドや通常ユーザー権限の確認に `SUPABASE_SERVICE_ROLE_KEY` を使わないでください。service role は RLS をバイパスするため、ポリシー検証になりません。
- `.env` は本番接続用として扱い、ローカル検証用の URL / キーはコマンド実行時の一時環境変数で渡します。

### リモート反映

リモートへ反映する場合は `supabase db push` を使います。ただし WEB-004 の作業では本番リモートへの push は実行しません。

## Docker Compose（Redis + Celery）

WEB-008 で `docker-compose.yml` に Redis + FastAPI + Celery worker + Celery beat を配置しました。ローカル開発で Celery タスクを動かす際に利用します。

### 初回ビルドと起動

```bash
docker compose build
docker compose up -d redis
docker compose up -d celery-worker celery-beat
# FastAPI もコンテナで動かす場合は
# docker compose up -d api
```

### 環境変数

`docker-compose.yml` は `${SUPABASE_URL}` などをホスト環境から読み込みます。`.env`（sns-calendar-app 直下）を用意して `docker compose --env-file .env up` で読み込ませるのが簡単です。

### 状態確認

```bash
docker compose ps
docker logs sns-calendar-celery-worker --tail 50
docker logs sns-calendar-celery-beat --tail 20
```

Celery beat は毎分 `app.tasks.scheduled_posts.check_scheduled_posts` を発火します（WEB-008 ではヘルスビート相当。実投稿ロジックは Sprint 3 以降の WEB-022 で実装）。

### 停止・クリーンアップ

```bash
docker compose stop
docker compose down
docker compose down -v
```

### Docker credential helper 不在時の回避

Docker Desktop 4.30+ の一部構成で `docker-credential-desktop` が PATH に無いと `docker compose pull` が失敗します。暫定対応として `~/.docker/config.json` の `credsStore` キーを削除（`{"auths":{}}` に置換）してください。

## OpenAPI

- スキーマのみ再生成: `pnpm openapi:gen-schema`
- クライアントのみ再生成: `pnpm openapi:gen-client`
- エンドツーエンド同期: `pnpm openapi:sync`

## OpenAPI 同期ワークフロー

- FastAPI の Pydantic スキーマや `response_model` を変更したら `pnpm openapi:sync` を実行します。
- `pnpm openapi:sync` は `apps/api/openapi.json` を再生成し、その内容から `apps/web/src/generated/` に TS クライアントを再生成します。
- `apps/web/src/generated/` は生成物なので Git には含めません。ビルドと型検査は生成済みクライアントを参照して検証します。

## pre-commit

- `.pre-commit-config.yaml` は Python 側のスキーマ変更時に `openapi.json` を再生成し、`openapi.json` が変わった場合に TS クライアント生成を走らせます。
- 初回だけ手元で `pre-commit install` を実行してください。フック自体はリポジトリに含めていますが、自動インストールはしません。

## CI/CD（GitHub Actions）

`.github/workflows/ci.yml` が PR と main への push で走ります。3 ジョブ構成:

| ジョブ | 役割 | 主要ステップ |
|---|---|---|
| **frontend** | Next.js 品質ゲート | `pnpm typecheck` / `pnpm lint` / `pnpm build` + axios サプライチェーン監査 |
| **backend** | FastAPI 品質ゲート | `poetry run ruff check` / `poetry run pytest` |
| **openapi-schema-sync** | 契約整合性 | `pnpm openapi:gen-schema` 後に `git diff --exit-code` で生成漏れ検出 |

### サプライチェーン監査

`ci.yml` の `Security audit (axios supply-chain)` ステップが `pnpm-lock.yaml` を grep し、既知の悪意あるバージョン（`axios@1.14.1` / `axios@0.30.4` / `plain-crypto-js@4.2.x`）を検出したら fail します。

### Dependabot

`.github/dependabot.yml` で毎週 (npm/pip) と毎月 (GitHub Actions / Docker) の自動更新 PR を受け付けます。axios のサプライチェーン攻撃バージョンは `ignore` 指定で PR 提案対象から外しています。

### ローカルでの再現

```bash
# Backend
cd apps/api && poetry run ruff check . && poetry run pytest

# Frontend
pnpm typecheck && pnpm build && pnpm lint

# OpenAPI 整合性
pnpm openapi:gen-schema && git diff --exit-code -- apps/api/openapi.json
```

### リモートリポジトリ化時の注意

現状 `.github/` は `sns-calendar-app/` 配下にあります。将来 `sns-calendar-app` を独立 Git リポジトリとして切り出す前提の配置です。`joyfoundation_project/` 全体を単一リポジトリとして GitHub に push する場合は、`.github/` をリポジトリルートに移動するか、Actions のパスを調整してください。
