# recon: チケット歓迎メッセージ初期値の英語CTA統一

調査日: 2026-06-28 / 担当: CC / 関連: ADR-146 / ADR-091

## F1 — 実送信に使われる初期値は _DEFAULT_WELCOME（コード定数）

`backend/app/discord_gateway/ticket_channel_creator.py:32`

```python
_DEFAULT_WELCOME = "ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"
```

`backend/app/discord_gateway/ticket_channel_creator.py:226`

```python
welcome_template = config.get("welcome_template") or _DEFAULT_WELCOME
```

`backend/app/discord_gateway/ticket_channel_creator.py:323`

```python
await new_channel.send(welcome_template)
```

`config` は `get_ticket_config()` が返す `dict(row)`（DBからのSELECT結果）。DB値が None または空文字の場合、`or` の右辺 `_DEFAULT_WELCOME` が採用され、そのまま Discord に送信される。

## F2 — APIスキーマのデフォルト値は「管理画面フォーム表示」用

`backend/app/routers/discord_ticket_config.py:53-57`

```python
class DiscordTicketConfigResponse(BaseModel):
    ...
    welcome_template: str = "ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。"
```

`backend/app/routers/discord_ticket_config.py:115-117`

```python
    row = result.mappings().first()
    if not row:
        return DiscordTicketConfigResponse()   # DB未設定時：フィールドデフォルトで返る
```

DB未設定テナントが GET `/admin/discord-ticket-config` を呼ぶと上記デフォルト文言がレスポンスに含まれ、管理画面フォームに表示される。実送信とは別経路。

## F3 — DiscordTicketConfigUpdate のデフォルトは PUT 省略時フォールバック

`backend/app/routers/discord_ticket_config.py:65-71`

```python
class DiscordTicketConfigUpdate(BaseModel):
    ...
    welcome_template: str = Field(
        default="ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。",
        max_length=500,
    )
```

管理画面は常に `welcome_template` を送信するため通常は不使用。ただし整合上変更対象。

## F4 — フロントのwelcomeTemplateDefault はローディング中の一瞬だけのプレースホルダ

`frontend/src/pages/admin/DiscordConfigPage.tsx:66-67`

```typescript
const [welcomeTemplate, setWelcomeTemplate] = useState(() =>
    t("discordTicketConfig.welcomeTemplateDefault")
);
```

`frontend/src/pages/admin/DiscordConfigPage.tsx:100`

```typescript
setWelcomeTemplate(ticketData.welcome_template);  // API応答で即上書き
```

`frontend/src/locales/ja.json:2776`: `"こんにちは！お問い合わせありがとうございます。担当者が確認次第ご連絡します。"`  
`frontend/src/locales/en.json:2776`: `"Hello! Thanks for reaching out. A staff member will get back to you shortly."`

API応答が返ると `setWelcomeTemplate(ticketData.welcome_template)` で上書きされるため、実質的にはローディング中（~100ms）のみ表示。DBにも実送信にも直接影響しない。

## F5 — auto-setup は welcome_template を上書きしない

`backend/app/routers/discord_auto_setup.py:327-344`

```sql
INSERT INTO public.tenant_discord_ticket_config
    (tenant_id, staff_role_id, ticket_category_id, ticket_button_channel_id,
     small_channel_id, large_channel_id, updated_at)
-- welcome_template カラムなし
ON CONFLICT (tenant_id) DO UPDATE SET
    staff_role_id = COALESCE(...),
    ticket_category_id = COALESCE(...),
    ticket_button_channel_id = COALESCE(...),
    small_channel_id = COALESCE(...),
    large_channel_id = COALESCE(...)
    -- welcome_template SET対象外
```

auto-setup 再実行で `welcome_template` は変更されない。初期値変更は「DB行なし or welcome_template=NULL のテナント」にのみ効く。

## 参照 ADR

- ADR-146（Discord Bot スコープ定義）: `docs/adr/ADR-146-discord-bot-scope.md`
- ADR-091（Discord Bot 機能実装）: `docs/adr/ADR-091-discord-bot-scope-definition.md`
