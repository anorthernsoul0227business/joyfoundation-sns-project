# SNS Calendar App

WEB-001 向けのモノレポ初期構成です。Turborepo + pnpm で `apps/web` と `apps/api` をまとめ、OpenAPI 型安全パイプラインの土台だけを用意しています。

## 前提

- Node.js 20.x
- pnpm 9.x
- Python 3.11
- Poetry

## セットアップ

```bash
cd sns-calendar-app
pnpm install
cd apps/api
poetry install
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
cd apps/api && poetry install && poetry run pytest
```

## OpenAPI

- FastAPI スキーマ出力: `cd apps/api && poetry run python scripts/generate_openapi.py`
- TypeScript クライアント生成: `cd apps/web && pnpm generate:api-client`

