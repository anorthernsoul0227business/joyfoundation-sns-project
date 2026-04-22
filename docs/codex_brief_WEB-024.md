# Codexブリーフィング: WEB-024 画像自動変換（R2アップロード + リサイズ）

**作成日**: 2026-04-21
**担当Issue**: WEB-024（Sprint 3 / 工数: 1.5日）
**依存**: WEB-016（投稿作成画面 / 画像アップロード UI）、WEB-021（IG Publisher）
**参考**: プロジェクト直下 `ig_auto_poster.py` の `upload_to_r2` / `resize_for_ig`
**後続**: Phase 2 の動画対応

---

## タスク概要

画像アップロード → R2 アップロード → IG向けリサイズ（4:5 白余白パディング）→ 公開URL保存 の自動化を実装する。フロントから画像アップロードリクエストを受け、API側でR2に保存し公開URL を返す。`post_media.storage_path` はこの公開URL。

既存 `ig_auto_poster.py` のR2ロジックをサービス層に移植。Phase 1 はR2のみ（Supabase Storage 併用は Phase 2）。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| ストレージ | **Cloudflare R2**（S3互換） | 既存 `ig_auto_poster.py` と整合 |
| SDK | **boto3** + `aws_access_key_id`/`aws_secret_access_key` を R2 資格情報で使用 | 既存実装と同じ |
| リサイズ | **Pillow** で 4:5 aspect に白余白パディング | IG フィード準拠 |
| パス構造 | `post-media/{org_id}/{YYYY/MM/DD}/{uuid}.{ext}` | 既存 `ig-temp/` と区別、将来の削除・管理用 |
| 公開URL | `R2_PUBLIC_URL/post-media/...` | R2 Public Bucket 前提 |
| エンドポイント | `POST /api/media/upload` (multipart/form-data) | WEB-016 のフロントと整合 |
| 認証 | JWT 必須 | |
| 画像サイズ制限 | 最大 10MB / 10枚まで | IG カルーセル上限に合わせる |
| リサイズ発火条件 | `auto_resize_ig=true` クエリ時のみ | 将来 X は別ルール |

---

## スコープ

### 1. 新規サービス: `apps/api/app/services/media_processor.py`

```python
class MediaProcessor:
    def __init__(self, settings): ...
    def upload_original(self, *, org_id: str, file_bytes: bytes, mime: str) -> tuple[str, str]:
        """R2 にアップロードし (public_url, storage_path) を返す"""
    def process_for_ig(self, file_bytes: bytes) -> bytes:
        """4:5 に白余白パディングして JPEG bytes を返す"""
    def delete(self, storage_path: str) -> None:
        """R2 から削除（失敗時はログ warning）"""
```

環境変数:
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL`

### 2. 新規エンドポイント: `POST /api/media/upload`

`apps/api/app/api/media.py` 新規:

| メソッド | パス | 認証 | 動作 |
|---|---|---|---|
| POST | `/api/media/upload` | JWT | multipart/form-data で画像ファイル受信、R2 保存、公開URLとストレージパスを返却 |

リクエスト:
```
POST /api/media/upload?auto_resize_ig=true
Content-Type: multipart/form-data
files[]: <image1>, <image2>, ...
```

レスポンス:
```json
{
  "media": [
    {"public_url": "https://...", "storage_path": "post-media/...", "width": 1080, "height": 1350, "mime_type": "image/jpeg"}
  ]
}
```

- 10MB/枚 超過は 413
- 10枚超過は 400
- mime が image/* 以外は 400
- 成功時、`post_media` テーブルには**まだ書かない**（post 作成時にフロントが storage_path を送るフロー、WEB-011 と整合）

### 3. `main.py` ルーター登録

```python
from app.api import media
app.include_router(media.router, prefix="/api/media", tags=["media"])
```

### 4. フロント統合（最小変更）

`apps/web/src/app/create/page.tsx` の画像アップロードハンドラを更新:
- 旧: ローカル Blob URL を直接 `post_media.storage_path` に入れていた（仮）
- 新: `POST /api/media/upload` を呼び、返された `public_url` を `storage_path` に入れる

既存フロー破壊を防ぐため、`apps/web/src/lib/api-client.ts` に `uploadMedia(files: File[]): Promise<MediaUploadResponse>` を追加。

### 5. 依存追加

`pyproject.toml`:
```toml
boto3 = "^1.34"
pillow = "^10.4"
python-multipart = "^0.0.9"  # FastAPI multipart対応
```

### 6. テスト（`apps/api/tests/services/test_media_processor.py` / `tests/api/test_media.py` 新規）

#### `test_media_processor.py`
- `process_for_ig`: 横長画像 → 4:5 パディング後の寸法が正しい
- 縦長画像 → 同様
- 既に 4:5 → そのまま返す
- JPEG/PNG 両対応
- PNG の透過背景 → 白背景で塗りつぶし

#### `test_media.py` (`responses` or moto で R2 モック)
- 正常アップロード: `public_url` と `storage_path` 返却
- mime 非対応 → 400
- 10MB 超 → 413
- 11枚 → 400
- 未認証 → 401

既存 pytest 全通過維持。

### 7. README 更新

`apps/api/README.md` に R2 環境変数と`/api/media/upload` 仕様追記。

---

## スコープ外

- ❌ 動画アップロード（Phase 2）
- ❌ X 用リサイズ（X はアスペクト制約緩いため Phase 1 非対応）
- ❌ 自動削除 / TTL（post 削除時の cascade は WEB-030 で検討）
- ❌ 画像 AI 生成（Phase 2）
- ❌ 署名付きURL（Public Bucket 前提）
- ❌ Supabase Storage 併用
- ❌ Video thumbnail 生成
- ❌ EXIF 除去（Phase 2 privacy 対応）

---

## 必須検証コマンド

```bash
cd sns-calendar-app/apps/api
poetry install
poetry run pytest
poetry run ruff check .
cd ../.. && pnpm typecheck && pnpm build
```

---

## 絶対守るべきこと

- **R2 キーをログ出力しない**
- **既存 `ig_auto_poster.py` の R2 実装は触らない**
- **`orig 2.*` 等 Finder 複製禁止**
- **偽装禁止**（boto3, Pillow はPyPI正規版のみ）
- **upload 時のユーザー入力 mime を信用しすぎない**（サーバ側で再判定）
- **post_media テーブルへの直接 INSERT はしない**（エンドポイントはR2だけ、DB反映はWEB-011 経路）

---

## 成果物チェックリスト

- [ ] `apps/api/app/services/media_processor.py` 新規
- [ ] `apps/api/app/api/media.py` 新規
- [ ] `apps/api/app/main.py` ルーター登録
- [ ] `apps/api/app/config.py` R2 設定追加
- [ ] `apps/api/.env.example` 更新
- [ ] `apps/api/pyproject.toml` に boto3 / pillow / python-multipart 追加
- [ ] `apps/api/tests/services/test_media_processor.py` 新規
- [ ] `apps/api/tests/api/test_media.py` 新規
- [ ] `apps/web/src/lib/api-client.ts` に `uploadMedia` 追加
- [ ] `apps/web/src/app/create/page.tsx` 画像アップロード経路を `/api/media/upload` に変更
- [ ] `apps/web/src/generated/*` 再生成
- [ ] `packages/shared-types` 再ビルド
- [ ] `pytest` / `ruff` / `pnpm typecheck` / `pnpm build` 全通過
- [ ] 偽装なし / Finder複製なし

## コミット指示

- コミットメッセージ: `feat: WEB-024 画像自動変換（R2アップロード + 4:5リサイズ）`
- Co-Authored-By 不要
