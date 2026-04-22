# Codexブリーフィング: WEB-030 内部運用開始

**作成日**: 2026-04-21
**担当Issue**: WEB-030（Sprint 4 / 工数: 継続）
**依存**: WEB-029（本番デプロイ完了）
**後続**: Phase 2 機能開発

---

## タスク概要

自社アカウントで **実運用テスト** を開始するための運用ドキュメントと運用開始前チェックリストを整備する。1〜2週間の試験運用で問題なければ Phase 1 完了とみなす。

---

## スコープ

### 1. 運用ランブック作成

`docs/OPS_RUNBOOK.md` 新規:

- **日次チェック**: Celery beat/worker 稼働、通知メール、投稿成功率
- **ログ確認**: Railway logs の grep パターン（success/failed）
- **トラブルシュート**:
  - X API rate limit ヒット時の対応
  - IG Container ERROR 時の対応
  - トークン失効時の手順
  - DB 接続切れ時の再起動順
- **バックアップ**: Supabase 自動 backup、手動 export 手順
- **インシデント対応**: 一次切り分けフロー、連絡先テンプレート

### 2. 運用開始チェックリスト

`docs/GO_LIVE_CHECKLIST.md` 新規:

- [ ] 本番 URL 疎通確認（`/health` 200）
- [ ] 自社 X / IG アカウント接続（WEB-019）
- [ ] テスト投稿（即時、予約、カルーセル）
- [ ] メール通知受信確認
- [ ] WebSocket 通知受信確認
- [ ] 画像 R2 アップロード確認
- [ ] OAuth 再接続テスト
- [ ] バックアップ取得確認
- [ ] ロールバック手順リハーサル

### 3. 運用 KPI 定義

`docs/KPI.md` 新規:
- 投稿成功率（目標 >= 99%）
- 通知到達率
- API レスポンス時間（p95 < 500ms）
- 障害発生数（月 <= 1）

### 4. リリースノート

`CHANGELOG.md` 新規 / 更新:
- Phase 1 MVP リリース内容

### 5. 既存 `x_auto_poster.py` / `ig_auto_poster.py` との並走方針

- Phase 1 は **両方稼働**（launchd 版を safety net として残す）
- 重複投稿を避けるため、Web アプリ版で投稿したものは Google Sheets シートのステータスを「Webアプリ化済」にマーク
- 2 週間問題なければ launchd を停止し、Web アプリ版単独運用に移行

---

## スコープ外

- ❌ 外部ユーザー向けリリース（Phase 2）
- ❌ 料金プラン / 課金（Phase 2）
- ❌ マーケティング資料

## 成果物チェックリスト

- [ ] `docs/OPS_RUNBOOK.md`
- [ ] `docs/GO_LIVE_CHECKLIST.md`
- [ ] `docs/KPI.md`
- [ ] `CHANGELOG.md`
- [ ] 運用開始テスト実施（Claude 側で手動）

## コミット指示

- コミットメッセージ: `docs: WEB-030 内部運用開始 ランブック + チェックリスト`
- Co-Authored-By 不要

**注意**: 本 Issue は主にドキュメント整備 + 運用テスト。Codex はドキュメント作成、Claude は本番環境での実テスト実施。
