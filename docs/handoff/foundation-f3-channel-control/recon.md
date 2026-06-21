# Foundation F3 — 流入元の統制 recon

測定日: 2026-06-21

## 事実
- 既存の `channel_masters` seed は `migrations/20260611_100000_create_channel_masters.sql:30-73` にあり、標準値は `messenger / instagram / discord / phone / in_person` だった。
- `GET /api/v1/channel-masters` は `backend/app/routers/conv_logs.py:186-201` にあり、`platform / display_name / connection_type / is_active` を返す。
- リードの流入元入力は `frontend/src/pages/leads/LeadEditPage.tsx:145` と `frontend/src/pages/leads/LeadsPage.tsx:304` で input だった。
- `lead.channel_type` は `backend/app/schemas/lead.py:105-145` の自由文字列で、保存時の master 検証はなかった。
- メッセージ送信のガードは `backend/app/routers/leads.py:1335-1340` で `messenger / instagram / discord` のみを見ており、ここは壊してはいけない。
- 新規テナント作成は `backend/app/services/tenant.py:1459-1561` で `create_tenant_schema()` が実行される。

## 実装前の狙い
- `channel_masters` に canonical `whatsapp` を追加し、既存 `phone / in_person` を保持する。
- リード入力は `GET /api/v1/channel-masters` を消費するプルダウンにする。
- `whatsapp_personal / whatsapp_business` は canonical `whatsapp` に寄せる。

