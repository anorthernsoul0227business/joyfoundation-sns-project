# Codexブリーフィング: WEB-002 OpenAPI自動生成パイプライン

**作成日**: 2026-04-17
**担当Issue**: WEB-002（Sprint 1 / 工数: 1日）
**依存**: WEB-001（コミット済: `ac03b27`）
**後続ブロック**: WEB-011（投稿CRUD API）以降の型安全な実装全般

---

## タスク概要

WEB-001 で構築したモノレポに対し、**FastAPI（Pydantic）のスキーマを起点にTypeScript型を自動生成するパイプライン**を構築する。これにより、バックエンドで型を変更するとフロントエンドの型も自動追従し、二言語構成の最大リスク「グルーコードの型ズレ」を排除する。

---

## ゴール（完成形）

```
FastAPI Pydantic Models
  ↓  poetry run python scripts/generate_openapi.py
apps/api/openapi.json
  ↓  pnpm generate:api-client
apps/web/src/generated/
  ├── client/         ← API呼び出し関数
  ├── types.gen.ts    ← リクエスト/レスポンス型
  └── index.ts        ← 再エクスポート
```

**1コマンドでEnd-to-Endの型同期が動く状態**まで。

---

## 前提コードベース（WEB-001の成果物）

- **WEB-001ブランチ**: `sprint-1/WEB-002` は `sprint-1/WEB-001` から派生済み
- 作業ディレクトリ: `/Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app`
- 既存ファイル（変更対象）:
  - `apps/api/scripts/generate_openapi.py` — 最小実装済み（スキーマ書き出しのみ）
  - `apps/web/openapi-ts.config.ts` — v0.66+ plugin形式で設定済み
  - `apps/api/app/main.py` — `/health` のみ定義
  - `apps/api/app/schemas/` — 空（.gitkeep のみ）
  - `apps/web/src/generated/` — 空（.gitkeep のみ）
  - `apps/web/package.json` — `generate:api-client` スクリプト既定義
  - `turbo.json` — `generate:api-client` タスク定義済み
- **既存のビルド/テストは全て通る状態**（WEB-001レビュー済み）

---

## スコープ（WEB-002で実装するもの）

### 1. サンプルPydanticスキーマ追加（動作検証用）

`apps/api/app/schemas/health.py`:
```python
from pydantic import BaseModel
from typing import Literal

class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
```

`apps/api/app/main.py` の `/health` をこのスキーマで返すようにリファクタ（response_model指定）。
pytestも `version` フィールドの検証を追加。

### 2. OpenAPIスキーマ出力スクリプトの完成

`apps/api/scripts/generate_openapi.py`:
- 既存の最小実装を拡張
- `app.openapi()` を呼び出して `apps/api/openapi.json` に整形JSONで書き出し
- 書き出し成功時にログ出力
- 終了コード: 成功0 / エラー時1

### 3. フロントエンド側クライアント生成

- `apps/web/openapi-ts.config.ts` は既に v0.66+ 形式で設定済み。そのまま動く想定
- `pnpm --filter @sns-calendar/web generate:api-client` を実行
- `apps/web/src/generated/` に型・クライアントが出力される
- **出力ファイルは `.gitignore` に追加**（生成物なので）

### 4. 生成物を呼び出すサンプルコード

`apps/web/src/app/page.tsx` を軽く書き換え、生成されたクライアントを import して型を使うサンプルを追加（ビルド時検証になる）:
```tsx
import type { HealthResponse } from "../generated";

const dummy: HealthResponse = { status: "ok", version: "0.1.0" };
// この行がビルド時に型チェックされることで、パイプラインが機能している証拠になる
```

### 5. pnpm ワークフローの追加

ルート `package.json` に以下スクリプトを追加:
```json
{
  "scripts": {
    "openapi:gen-schema": "cd apps/api && poetry run python scripts/generate_openapi.py",
    "openapi:gen-client": "pnpm --filter @sns-calendar/web generate:api-client",
    "openapi:sync": "pnpm openapi:gen-schema && pnpm openapi:gen-client"
  }
}
```

### 6. pre-commitフック設定

`sns-calendar-app/.pre-commit-config.yaml` 新規作成:
- Pythonスキーマ変更を検知して openapi.json 再生成
- openapi.json 変更を検知してTS型再生成
- 実装は IMPLEMENTATION_PLAN.md セクション 2.5 を参考

**注意**: pre-commitのインストール自体はドキュメント記載のみでよい（`pre-commit install` は手動実行）。

### 7. CIでの整合性チェック

`.github/workflows/openapi-check.yml` 新規作成:
- PR時に実行
- `pnpm openapi:sync` を走らせて、生成物と commit 内容に差分が出たら fail
- 「スキーマ変更したけどTS型を再生成し忘れた」PRを検出

### 8. ドキュメント更新

`sns-calendar-app/README.md` に OpenAPI 同期ワークフロー章を追加:
- いつ `pnpm openapi:sync` を走らせるか
- pre-commitフックが何をするか
- CIで何が検証されるか

---

## やらないこと（スコープ外）

- ❌ 認証・投稿・カレンダー等の実APIルーター実装（Sprint 2以降）
- ❌ watchdog等のファイル監視による自動同期（IMPLEMENTATION_PLAN.md 2.4は将来課題）
- ❌ DB接続・マイグレーション（WEB-004）
- ❌ Supabaseクライアント（WEB-003）
- ❌ 既存 `/health` 以外の新規エンドポイント
- ❌ CI全体（`ci.yml`）の構築（WEB-009）— OpenAPI整合性チェックのみ先行

---

## 必須検証コマンド（全て成功すること）

```bash
cd sns-calendar-app

# 1. スキーマ出力
pnpm openapi:gen-schema
test -f apps/api/openapi.json
grep -q "HealthResponse" apps/api/openapi.json

# 2. TSクライアント生成
pnpm openapi:gen-client
test -d apps/web/src/generated
ls apps/web/src/generated | grep -E "(types|client|index)"

# 3. 型が使えることの確認
pnpm typecheck
pnpm build

# 4. API側テスト（versionフィールド追加含む）
cd apps/api && poetry run pytest

# 5. 一括同期コマンド
cd .. && pnpm openapi:sync

# 6. pre-commit設定ファイル存在確認
test -f .pre-commit-config.yaml

# 7. CIワークフロー存在確認
test -f .github/workflows/openapi-check.yml
```

---

## 絶対守るべきこと

- **WEB-001で構築済みのモノレポ構造を壊さない**
- **既存の動作確認コマンド（`pnpm build`, `pnpm typecheck`, `pnpm lint`, `poetry run pytest`）が引き続き通る**
- axiosは導入しない（@hey-api/client-fetch 既導入）
- スコープ外の実装禁止
- `apps/web/src/generated/` は .gitignore に追加（ビルド生成物）

---

## 成果物チェックリスト（レビュー項目）

Codex納品後、Claude側で検証:

- [ ] `apps/api/app/schemas/health.py` が追加されている
- [ ] `/health` エンドポイントが response_model で型指定されている
- [ ] `apps/api/scripts/generate_openapi.py` が `openapi.json` を書き出す
- [ ] 書き出された `openapi.json` に `HealthResponse` スキーマが含まれる
- [ ] `pnpm openapi:gen-client` で `apps/web/src/generated/` が生成される
- [ ] 生成物は `.gitignore` に含まれる（コミットされない）
- [ ] `apps/web/src/app/page.tsx` で生成型を import する実例が含まれる
- [ ] `pnpm openapi:sync` が End-to-End で動く
- [ ] `.pre-commit-config.yaml` が設置されている
- [ ] `.github/workflows/openapi-check.yml` が設置されている
- [ ] 既存の `pnpm build / typecheck / lint / pytest` が全て通る
- [ ] README に同期ワークフロー章が追加されている
- [ ] スコープ外の実装が混入していない

---

## 完了基準

1. 上記チェックリストが全て通る
2. 必須検証コマンドが全て成功
3. 作業ブランチ `sprint-1/WEB-002` に以下2つのコミットを作成（分離推奨）:
   - `feat: WEB-002 OpenAPI型安全パイプライン` — スクリプト・設定・サンプル
   - `chore: WEB-002 pre-commit & CI 整合性チェック` — pre-commit / CI
   - ※まとめて1コミットでも可
4. コミット前に `git add` は明示指定（`git add .` 禁止、`apps/web/src/generated/` を除外する）

---

## 補足: 関連設計ドキュメント

- `design/design/IMPLEMENTATION_PLAN.md` セクション2（必読）
- `design/design/APP_DESIGN_SPEC.md` 決定事項#21（型安全パイプライン方針）
- `docs/codex_brief_WEB-001.md` — 前段の構成前提

---

## 検証時に Claude が引き継ぐこと（Codex側は気にしなくてよい）

- `pnpm openapi:sync` の実行
- 生成されたクライアントを使った簡単な動作確認
- pre-commit の手動実行確認
- 最終コミット形状のレビュー
