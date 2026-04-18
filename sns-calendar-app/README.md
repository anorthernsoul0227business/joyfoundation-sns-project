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

## CI 整合性チェック

- `.github/workflows/openapi-check.yml` は Pull Request ごとに `pnpm openapi:sync` を実行します。
- 実行後に `git diff --exit-code -- apps/api/openapi.json` で OpenAPI スキーマの再生成漏れを検出します。
- `apps/web/src/generated/` はコミット対象外のため、CI では生成コマンドが成功することをもって整合性を確認します。
