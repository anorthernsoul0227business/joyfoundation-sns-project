# Codexブリーフィング: ARCH-005 Resend 導入（認証メール / 投稿結果通知）

**作成日**: 2026-04-22
**担当Issue**: ARCH-005（Sprint ARCH / 工数: 0.3日）
**依存**: ARCH-004（Cloud Run デプロイ）
**参考**: `APP_DESIGN_SPEC.md` Section 15、既存 `apps/api/app/services/notifier.py`
**後続**: 本番デプロイ完了

---

## タスク概要

Supabase Auth の SMTP 制限（1日3通）を回避するため、**Resend** を外部 SMTP Transactional プロバイダとして統合する。認証メール（パスワードリセット・招待）と投稿結果通知（任意）をカバーする。

---

## 設計方針

| 項目 | 決定 | 根拠 |
|---|---|---|
| プロバイダ | **Resend** | 3000通/月無料、API 明快 |
| 用途 | (a) Supabase Auth カスタム SMTP (b) アプリ内 Transactional | 二段構え |
| 送信元 | `noreply@<custom-domain>` | SPF/DKIM 必須 |
| テンプレート | React Email + Resend SDK | 管理しやすい |
| 認証メール | Supabase Auth Dashboard で SMTP 設定 | パスワードリセット/招待は Supabase が送信 |
| 投稿結果通知 | オプトイン（ユーザー設定）: `users.email_on_post_result` | デフォルト OFF |

---

## スコープ

### 1. Resend アカウント準備

1. https://resend.com/ でサインアップ
2. ドメイン追加（独自ドメイン推奨、なければ `onboarding@resend.dev` から送信可）
3. SPF/DKIM レコードを DNS に登録
4. API Key を発行（Production / Restricted scope）
5. GH Secrets `RESEND_API_KEY` に登録

### 2. Supabase Auth カスタム SMTP 設定

Supabase Dashboard → Auth → SMTP Settings:

```
Enable Custom SMTP: ON
Sender email: noreply@<custom-domain>
Sender name: SNS Calendar App
Host: smtp.resend.com
Port: 465
Username: resend
Password: <RESEND_API_KEY>
```

### 3. API 側の投稿結果通知実装（オプトイン）

`apps/api/app/services/notifier.py` に追加:

```python
import resend

class EmailNotifier:
    def __init__(self, api_key: str, from_address: str):
        resend.api_key = api_key
        self.from_address = from_address

    async def send_post_result(
        self,
        to: str,
        subject: str,
        body_html: str,
    ):
        return resend.Emails.send({
            "from": self.from_address,
            "to": [to],
            "subject": subject,
            "html": body_html,
        })
```

### 4. `users` テーブルマイグレーション

```sql
ALTER TABLE public.users
ADD COLUMN email_on_post_result BOOLEAN DEFAULT FALSE;
```

### 5. Web 設定画面に「メール通知」トグル

`apps/web/src/app/settings/notifications/page.tsx` 新規:

```tsx
const [emailOptIn, setEmailOptIn] = useState(user.email_on_post_result);

<Switch
  checked={emailOptIn}
  onCheckedChange={(checked) => {
    setEmailOptIn(checked);
    api.updateUserPreferences({ email_on_post_result: checked });
  }}
/>
```

### 6. 通知ポイントに組み込み

`apps/api/app/services/publisher.py`（ARCH-002 で作成）で投稿成功/失敗時:

```python
if user.email_on_post_result:
    await email_notifier.send_post_result(
        to=user.email,
        subject=f"✅ 投稿成功: {post.title[:30]}",
        body_html=render_post_result_email(post, status="success"),
    )
```

### 7. React Email テンプレート（optional）

`apps/api/app/emails/post_result.html` または React Email で記述:

```html
<html>
  <body>
    <h2>{{status_icon}} 投稿{{status_text}}</h2>
    <p>{{post_title}}</p>
    <p><a href="{{frontend_url}}/notifications">詳細を確認</a></p>
  </body>
</html>
```

---

## テスト計画

- [ ] Resend API Key でテスト送信成功
- [ ] Supabase Auth でパスワードリセット → Resend 経由で届く
- [ ] `email_on_post_result=true` の user で投稿成功 → メール到着
- [ ] `email_on_post_result=false` ではメール送信されない
- [ ] SPF/DKIM チェックサイト（mxtoolbox 等）で pass

---

## リスク

1. **DNS 伝播待ち**: SPF/DKIM 設定後 24〜48 時間
2. **Resend 送信数超過**: 3000通/月超過で送信停止 → Pro ($20/月) 課金
3. **ドメイン調達**: 独自ドメイン取得（年 $10〜）→ 無料のままなら `onboarding@resend.dev` 暫定使用

---

## 完了条件

- [ ] Resend アカウント作成・API Key 発行
- [ ] Supabase Auth SMTP カスタム化
- [ ] `users.email_on_post_result` カラム追加
- [ ] Web 設定画面でトグル可能
- [ ] 投稿成功/失敗時にメール送信動作確認
