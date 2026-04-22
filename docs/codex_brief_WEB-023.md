# Codexブリーフィング: WEB-023 投稿結果通知（メール）

**作成日**: 2026-04-21
**担当Issue**: WEB-023（Sprint 3 / 工数: 1日）
**依存**: WEB-022（`publish_post` タスク）
**参考**: プロジェクト直下 `notifier.py`（Gmail API 経由）
**後続**: WEB-027（WebSocket リアルタイム通知）

---

## タスク概要

`publish_post` 完了後に投稿成功/失敗を **メール通知** する。既存 `notifier.py` のロジックを FastAPI 側に移植する。Phase 1 は通知先を固定（ログインユーザーの登録メール）、チャネルはメールのみ。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| 送信方式 | **SMTP (環境変数経由)** を第一候補、フォールバックで Gmail API | 既存 `notifier.py` は Gmail API 依存、Phase 1 は SMTP でシンプル化 |
| 送信先 | 投稿オーナーの `auth.users.email` | シングルユーザー運用の Phase 1 |
| 送信元 | `SMTP_FROM_ADDRESS` 環境変数 | |
| 発火タイミング | `publish_post` 完了後に `notify_post_result(post_id, summary)` を呼ぶ | `scheduled_posts.py` から同期呼び出し |
| 失敗時挙動 | 送信失敗はログ warning のみ。本体処理は成功扱い | 通知の失敗で投稿を落とさない |
| 本文テンプレート | 成功: `{platform} に投稿しました: {url}`、失敗: `{platform} 投稿失敗: {error}` | Phase 1 は簡易版 |
| テスト | SMTP / requests モック | 実送信しない |

---

## スコープ

### 1. `apps/api/app/services/notifier.py` 新規

```python
class EmailChannel:
    def __init__(self, settings): ...
    def send(self, *, to: str, subject: str, body: str) -> bool: ...

def notify_post_result(
    *,
    post_id: str,
    owner_email: str,
    summary: dict,  # {"success": [...], "failed": [...]}
) -> None:
    """publish_post の結果 summary をメール本文に整形して送信。失敗は握り潰し"""
```

- `EmailChannel` は `smtplib.SMTP_SSL` を使用
- 環境変数: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_ADDRESS`
- 未設定時はログ warning で no-op（テスト時に送信されないよう保護）

### 2. `apps/api/app/config.py` に SMTP 設定追加

```python
smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
smtp_port: int | None = Field(default=465, validation_alias="SMTP_PORT")
smtp_user: str | None = Field(default=None, validation_alias="SMTP_USER")
smtp_password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
smtp_from_address: str | None = Field(default=None, validation_alias="SMTP_FROM_ADDRESS")
```

`.env.example` に同項目を空値で追加。

### 3. `publish_post` タスクへの結線

`apps/api/app/tasks/scheduled_posts.py` の `publish_post` 最後に:

```python
from app.services.notifier import notify_post_result
# posts.user_id から auth.users.email を引く
user = client.table("users").select("email").eq("id", post["user_id"]).limit(1).execute().data
if user:
    notify_post_result(post_id=post_id, owner_email=user[0]["email"], summary=summary_dict)
```

Celery eager モードでテストできるよう、`notify_post_result` は依存注入可能にする:

```python
def publish_post(self, post_id: str, *, notifier=None) -> dict:
    notifier = notifier or notify_post_result
    ...
```

### 4. テスト（`apps/api/tests/services/test_notifier.py` 新規）

- SMTP モック (`smtplib.SMTP_SSL.send_message` を monkeypatch): 正常送信
- 設定未設定時: no-op で `False` 返却、例外は出さない
- 接続エラー時: `False` 返却、ログ warning
- `notify_post_result` が summary を本文に展開できている
- 成功/失敗混在時の本文フォーマット

既存 `test_scheduled_posts.py` (WEB-022) は notifier を注入するフェイクに差し替え、呼ばれたことを検証するテストを追加。

### 5. README 更新

`apps/api/README.md` に:
- SMTP 環境変数一覧
- ローカル開発時の Mailpit / MailHog 設定例
- `notify_post_result` の直呼び出し方法

---

## スコープ外

- ❌ Slack / Discord / LINE 通知（Phase 2）
- ❌ 通知設定画面（フロント）
- ❌ 通知履歴 DB 保存（WEB-027 で検討）
- ❌ マーケティングメール / 定期レポート
- ❌ HTML メール（plain text のみ）
- ❌ 多言語対応
- ❌ Gmail API 経由（既存 `notifier.py` の機能は残す。新規はSMTPのみ）

---

## 必須検証コマンド

```bash
cd sns-calendar-app/apps/api
poetry run pytest
poetry run ruff check .
```

---

## 絶対守るべきこと

- **実メールを送信しない**（テストはモック、開発は Mailpit 等）
- **SMTP パスワードをログに書かない**
- **既存 `notifier.py` は触らない**（プロジェクト直下）
- **`publish_post` の戻り値互換を維持**
- 偽装・Finder複製禁止

---

## 成果物チェックリスト

- [ ] `apps/api/app/services/notifier.py` 新規
- [ ] `apps/api/app/config.py` SMTP 設定追加
- [ ] `apps/api/.env.example` 更新
- [ ] `apps/api/app/tasks/scheduled_posts.py` に `notify_post_result` 呼び出し追加
- [ ] `apps/api/tests/services/test_notifier.py` 新規（5+ケース）
- [ ] `apps/api/tests/tasks/test_scheduled_posts.py` に通知呼び出しテスト追加
- [ ] `apps/api/README.md` 更新
- [ ] `pytest` / `ruff` 全通過
- [ ] 偽装なし

## コミット指示

- コミットメッセージ: `feat: WEB-023 投稿結果メール通知`
- Co-Authored-By 不要

## 環境

- Python 3.12+ / smtplib（標準ライブラリ）
- 追加依存なし（`email.message` 標準ライブラリ使用）
