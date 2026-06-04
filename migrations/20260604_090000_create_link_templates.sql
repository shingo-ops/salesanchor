-- SA-05: リンクテンプレート SSOT
-- public スキーマ（共有カタログ面・テナント分離なし）
--
-- 設計:
--   - channel を PRIMARY KEY とするシンプルなカタログテーブル
--   - is_verified=FALSE のチャンネルは UI 側で「未検証」バッジを表示
--   - ON CONFLICT DO NOTHING で冪等（再実行 no-op）
--
-- 冪等性:
--   - CREATE TABLE IF NOT EXISTS
--   - INSERT ... ON CONFLICT (channel) DO NOTHING

CREATE TABLE IF NOT EXISTS public.link_templates (
    channel VARCHAR(30) PRIMARY KEY,
    url_pattern TEXT NOT NULL,
    required_ids JSONB NOT NULL,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 初期データ投入（冪等: ON CONFLICT DO NOTHING）
INSERT INTO public.link_templates (channel, url_pattern, required_ids, is_verified, notes, updated_at) VALUES
  ('whatsapp',  'https://wa.me/{phone}',                               '{"phone":true}',                                       TRUE,  NULL,                                              NOW()),
  ('telegram',  'https://t.me/{username}',                             '{"username":true,"phone":true}',                       TRUE,  NULL,                                              NOW()),
  ('discord',   'https://discord.com/channels/{guild_id}/{channel_id}','{"guild_id":true,"channel_id":true}',                  TRUE,  NULL,                                              NOW()),
  ('messenger', 'https://business.facebook.com/latest/inbox/messenger','{"page_id":true,"bm_id":true,"psid":true}',            FALSE, 'Meta内部URL・Meta担当パートナー検証待ち',          NOW()),
  ('instagram', 'https://business.facebook.com/latest/inbox/instagram','{"igsid":true,"page_id":true}',                       FALSE, 'Meta内部URL・Meta担当パートナー検証待ち',          NOW())
ON CONFLICT (channel) DO NOTHING;
