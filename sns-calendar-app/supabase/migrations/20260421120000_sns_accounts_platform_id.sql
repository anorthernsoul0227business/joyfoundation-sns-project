ALTER TABLE public.sns_accounts
  ADD COLUMN platform_account_id TEXT;

COMMENT ON COLUMN public.sns_accounts.platform_account_id IS
  'プロバイダー側のアカウントID。IG Business Account ID、X user_id 等、投稿APIで使う識別子';
