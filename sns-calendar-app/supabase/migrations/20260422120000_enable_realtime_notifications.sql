-- ARCH-003: notifications テーブルを Supabase Realtime publication に追加
-- Depends on: 20260422000000_notifications.sql
-- 目的: Web クライアントが supabase-js の postgres_changes 経由で INSERT を購読可能にする
--       これにより FastAPI WebSocket (notifications_ws.py) + Redis PubSub は不要になる

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime'
  ) THEN
    -- publication がすでに notifications を含む場合は重複追加でエラーになるので条件付与
    IF NOT EXISTS (
      SELECT 1
      FROM pg_publication_tables
      WHERE pubname = 'supabase_realtime'
        AND schemaname = 'public'
        AND tablename = 'notifications'
    ) THEN
      ALTER PUBLICATION supabase_realtime ADD TABLE public.notifications;
    END IF;
  END IF;
END
$$;

COMMENT ON TABLE public.notifications IS
  '通知履歴。RLS SELECT policy 経由で Realtime postgres_changes INSERT イベントをクライアントが購読する';
