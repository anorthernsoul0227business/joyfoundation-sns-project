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
