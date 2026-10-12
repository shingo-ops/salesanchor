-- Discord チケットのウェルカム文の既定値を英語へ（PO 決定 2026-09-30「お客様向けは全部英語」）
-- 背景: 20260602_120000 が既定値を日本語で定義しており、コード側の英語既定
--       （docs/handoff/ticket-welcome-en/design.md）より DB の既定が優先されていた。
-- 詳細: docs/handoff/discord-bot-english-texts/design.md
-- 冪等: 既定値の再設定は何度でも同じ結果 / UPDATE は旧既定文のままの行のみ（独自文言は変更しない）
-- 注意: DROP・DELETE は含まない
-- 文言の正本: backend/app/discord_gateway/bot_texts.py の DEFAULT_WELCOME_TEMPLATE と同一

ALTER TABLE public.tenant_discord_ticket_config
    ALTER COLUMN welcome_template SET DEFAULT 'Thanks for reaching out! I''ve created a private channel just for you. I''ll connect you with our sales team — please reply with your name to get started.';

UPDATE public.tenant_discord_ticket_config
   SET welcome_template = 'Thanks for reaching out! I''ve created a private channel just for you. I''ll connect you with our sales team — please reply with your name to get started.',
       updated_at = NOW()
 WHERE welcome_template = 'ご連絡ありがとうございます。こちらのチャンネルでサポートいたします。';
