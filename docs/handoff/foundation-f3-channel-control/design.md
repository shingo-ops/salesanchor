# Foundation F3 — 流入元の統制 design

測定日: 2026-06-21

## 方針
1. `backend/app/services/tenant.py` に新規テナント用の `channel_masters` テーブルと seed を追加する。
2. `migrations/20260611_100000_create_channel_masters.sql` の標準 seed に canonical `whatsapp` を追加する。
3. `backend/app/routers/leads.py` で `channel_type` を master 検証し、`whatsapp_personal / whatsapp_business` を `whatsapp` に正規化する。
4. `frontend/src/components/ChannelTypeCombobox.tsx` を新設し、`frontend/src/pages/leads/LeadEditPage.tsx` と `frontend/src/pages/leads/LeadsPage.tsx` で input を差し替える。
5. `scripts/migrate_20260621_030000_backfill_lead_channel_type.py` で既存値を backfill する。

## 安全
- `messenger / instagram / discord` の値は保持する。
- 既知の別名だけ canonical 化し、珍しい値は backfill で null 化する。
- 既存レコードの更新を壊さないため、未変更の legacy 値は保存時に通す。

