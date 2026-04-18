# Supabase Migrations Notes

- WEB-005 では `organizations` / `org_members` / `public.users` にだけ RLS を追加した。既存の `20260418100000_initial_schema.sql` は変更していない。
- `public.users` の RLS は `RLS_DESIGN.md` に未記載だったため、本タスクで新規設計した。`SELECT` は自分自身と同一 org メンバー、`UPDATE` は自分自身のみを許可する。
- RLS パフォーマンス用の `org_members(user_id)` / `org_members(org_id)` など、WEB-005 対象テーブルに必要な基本インデックスは WEB-004 の初期スキーマ側で作成済み。
- APP 設計決定 #14 の `sns_accounts_safe` ビューは有効な方針だが、今回のスコープ外のため未実装。`sns_accounts` など他テーブルの RLS とあわせて Sprint 2-3 で追加する。
