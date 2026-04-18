# Codexブリーフィング: WEB-006 認証API実装

**作成日**: 2026-04-18
**担当Issue**: WEB-006（Sprint 1 / 工数: 1.5日）
**依存**: WEB-004（コミット済 `a21735e`）、WEB-005（コミット済 `5df3491`）
**後続ブロック**: WEB-007（ログイン画面）、Sprint 2以降の保護済みAPI全般

---

## タスク概要

FastAPI 側に **認証API（signup/login/logout/refresh/me）** と **JWT検証Dependency** を実装する。Supabase Auth をラップしつつ、アプリケーション側で一貫したAPI契約を提供し、将来の認証プロバイダ変更に備える（決定事項#2: Auth境界を抽象化）。

---

## 設計方針

### アーキテクチャ選択: **Thin FastAPI Wrapper + JWT Verification**

| 理由 | 詳細 |
|---|---|
| API の一貫性 | フロントエンドは全てFastAPI経由（Supabaseは内部実装詳細） |
| 抽象化 | 決定事項#2: Supabase Auth 依存をサービス境界に閉じ込める |
| 拡張可能性 | 将来: メール送信前の検証、ログイン監査、MFA 統合等 |
| 認可の統一 | 保護済みエンドポイントは全て `get_current_user` dependency を使う |

### JWT検証の実装方式

**採用**: **Supabase JWT Secret を使った HS256 検証（PyJWT）**
- 理由: Supabase はデフォルト HS256、JWT シークレットが環境変数で取得可能
- JWKS方式（RS256）はSupabase Proプラン以上の機能、Phase 1では不要
- 検証失敗時は 401 Unauthorized
- Supabase client をトークンごとにインスタンス化するのは重いため、JWT はローカル検証 + 必要に応じて service_role で profile 参照

---

## スコープ（WEB-006で実装するもの）

### 1. 環境変数追加

`.env.example` に追加:
```bash
# Supabase JWT verification
SUPABASE_JWT_SECRET=your-local-jwt-secret  # Settings → JWT Keys から取得
```

`apps/api/app/config.py` の Settings に追加:
```python
supabase_jwt_secret: Optional[SecretStr] = Field(
    default=None,
    validation_alias="SUPABASE_JWT_SECRET"
)
```

### 2. Pydantic Schemas

`apps/api/app/schemas/auth.py` 新規作成:
```python
from pydantic import BaseModel, EmailStr, SecretStr, Field
from typing import Optional


class SignupRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=8)
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: Optional[str] = None
    ui_mode: str = "simple"
    help_mode_enabled: bool = True
    default_org_id: Optional[str] = None


class SessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
```

**備考**: `EmailStr` を使うため `pydantic[email]` が必要 → `pyproject.toml` に追加

### 3. JWT 検証 Dependency

`apps/api/app/core/security.py` 新規作成:
```python
"""JWT authentication dependencies."""
from typing import Annotated, Optional
import jwt
from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.config import get_settings


class CurrentUser(BaseModel):
    id: str
    email: str
    role: str  # authenticated, anon, service_role


def _extract_bearer_token(authorization: str) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization.split(" ", 1)[1]


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> CurrentUser:
    """Verify JWT and return current user.
    
    Usage:
        @router.get("/protected")
        def protected(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings()
    if settings.supabase_jwt_secret is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase JWT secret is not configured",
        )
    
    token = _extract_bearer_token(authorization)
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret.get_secret_value(),
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return CurrentUser(
        id=payload["sub"],
        email=payload.get("email", ""),
        role=payload.get("role", "authenticated"),
    )
```

### 4. Auth Router

`apps/api/app/api/auth.py` 新規作成:

- `POST /api/auth/signup`: Supabase `sign_up()` 呼び出し → SessionResponse 返却
- `POST /api/auth/login`: Supabase `sign_in_with_password()` → SessionResponse
- `POST /api/auth/logout`: `get_current_user` dependency、session 破棄 → MessageResponse
- `POST /api/auth/refresh`: Supabase `refresh_session()` → SessionResponse
- `GET /api/auth/me`: `get_current_user` dependency、profile 取得（`public.users` からservice_role で）→ UserResponse

**重要**:
- Supabase Auth API呼び出しは `get_anon_client()` を使う（ユーザー操作なので service_role 不使用）
- `/me` の profile 取得のみ service_role で行う（RLS バイパス、内部操作）
- エラーは Supabase のエラーを FastAPI HTTPException にマッピング

### 5. main.py 更新

`apps/api/app/main.py` に router を登録:
```python
from app.api import auth

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
```

### 6. 依存追加

`apps/api/pyproject.toml`:
```toml
pyjwt = "^2.9.0"
pydantic = {extras = ["email"], version = "^2.9.0"}  # EmailStr対応
```

**注意**: pydantic-settings 経由で pydantic が既に入っているが、`email` extra が必要

### 7. テスト

`apps/api/tests/test_auth.py` 新規作成:

テストケース（ローカル Supabase のみ実行）:
- ✅ 正常な signup → 201 + SessionResponse 返却 + public.users にプロファイル作成される
- ✅ 重複 email signup → 400 or 409
- ✅ 弱いパスワード → 422（Pydantic validation）
- ✅ 正常 login → SessionResponse
- ✅ 間違いパスワード → 401
- ✅ Bearer なし `/api/auth/me` → 401
- ✅ 有効な Bearer `/api/auth/me` → UserResponse
- ✅ 無効な Bearer `/api/auth/me` → 401
- ✅ logout → MessageResponse
- ✅ refresh → 新しい SessionResponse

各テストで作成したユーザーは finally で削除。

### 8. README 更新

認証API の使い方、環境変数 `SUPABASE_JWT_SECRET` の取得方法追記。

### 9. OpenAPI クライアント再生成

- `pnpm openapi:sync` で TS 型を再生成
- `apps/web/src/app/page.tsx` で不要になった型参照を壊さないこと（既存実装を維持）
- 生成物は commit しない（.gitignore 済）

---

## スコープ外（やらないこと）

- ❌ フロントエンドのログイン画面（WEB-007）
- ❌ パスワードリセット機能（WEB-006.1として将来分離）
- ❌ OAuth プロバイダ（Google/GitHub等）連携
- ❌ メール確認フロー（Supabase デフォルトに任せる）
- ❌ MFA / 2FA
- ❌ レート制限（Sprint 4 でミドルウェア追加）
- ❌ CORS 詳細設定（Sprint 2 で frontend と統合時に調整）
- ❌ 本番 Supabase への push

---

## 必須検証コマンド

```bash
cd /Users/kitakoujirou/Desktop/AI関連/joyfoundation_project/sns-calendar-app

# 1. 依存インストール
cd apps/api && poetry lock && poetry install

# 2. OpenAPI schema 再生成
cd ../.. && pnpm openapi:sync

# 3. テスト実行（ローカル Supabase の JWT secret が必要）
# ローカル Supabase JWT secret は supabase status で表示されるのでそれを使う
cd apps/api
SUPABASE_URL=http://127.0.0.1:54321 \
SUPABASE_ANON_KEY=sb_publishable_ACJWlzQHlZjBrEguHvfOxg_3BJgxAaH \
SUPABASE_SERVICE_ROLE_KEY=sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz \
SUPABASE_JWT_SECRET="super-secret-jwt-token-with-at-least-32-characters-long" \
poetry run pytest -v

# 4. 既存 WEB-001〜005 の維持確認
cd ../.. && pnpm typecheck && pnpm build && pnpm lint
```

---

## 絶対守るべきこと

- **既存の WEB-001〜005 成果物を壊さない**
- **本番リモートへの認証リクエストを実行しない**
- **パスワードを絶対にログ出力しない**（SecretStrを使う）
- **service_role は最小限の使用**（`/me` の profile 取得のみ）
- スコープ外禁止（パスワードリセット・OAuth・フロント等）
- axios は使わない（継続）
- JWT検証は **必ず PyJWT で HS256 ローカル検証**（Supabase Auth への毎回問い合わせはレイテンシとコスト増）
- **EmailStr を使う** → `pydantic[email]` extra が必要
- ポリシーに reliant するため、service_role で `/me` の profile 取得時も明示的にユーザーIDで絞り込む（service_role でも漏れ防止）

---

## 成果物チェックリスト

- [ ] `apps/api/app/core/security.py` 作成（`get_current_user` dependency）
- [ ] `apps/api/app/schemas/auth.py` 作成（5つ以上のPydantic models）
- [ ] `apps/api/app/api/auth.py` 作成（5エンドポイント）
- [ ] `apps/api/app/main.py` で router 登録
- [ ] `apps/api/pyproject.toml` に `pyjwt` と `pydantic[email]` 追加
- [ ] `apps/api/poetry.lock` 更新
- [ ] `.env.example` に `SUPABASE_JWT_SECRET` 追加
- [ ] `apps/api/tests/test_auth.py` 追加（10+ テストケース）
- [ ] ローカル Supabase で pytest 全パス
- [ ] OpenAPI schema 再生成 → `apps/web/src/generated/` に新しい型
- [ ] `pnpm typecheck / build / lint` 維持
- [ ] README に認証API使い方追記
- [ ] スコープ外の実装混入なし
- [ ] パスワード等の機微情報がログ・エラーレスポンスに漏れていない
- [ ] `.env` 実ファイルをコミットしていない

---

## コミット指示

- `git add` は明示指定のみ
- `.env` は絶対コミットしない
- `apps/web/src/generated/` もコミットしない（.gitignore 済）
- コミットメッセージ: `feat: WEB-006 認証API実装（signup/login/logout/refresh/me）`
- Co-Authored-By 不要

---

## 補足: Codex環境情報

- ローカル Supabase 稼働中（`supabase status` で JWT secret 含む全情報取得可）
- JWT secret の取得方法: `supabase status` の出力 `JWT secret` フィールド
- Docker 起動中
- poetry 2.3.4 @ `~/.local/bin/poetry`
- pnpm 9.15.9
- Python 3.11.14
- `sns-calendar-app/.env` 本番設定済み（人間側）

**テスト時の注意**: `SUPABASE_JWT_SECRET` は `.env` には入れず、pytest実行時の環境変数で上書き（本番のJWT secretを .env に入れるのは人間側の次タスク）
