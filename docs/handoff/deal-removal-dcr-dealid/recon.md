# deal_close_reasons.deal_id 廃止 recon

設計書: [design.md](design.md)

## 実測結果

- `backend/app/routers/leads.py:596,599,614-615`: 失注理由は `lead_id` のみで削除・登録しており、`deal_id` は読み書きしていない。
- `backend/app/routers/close_reasons.py`: `deal_close_reasons` と `deal_id` の使用なし。
- `backend/app/routers/analytics.py:1995-1997,2023-2025`: `deal_close_reasons` は `lead_id` 経由で参照。`dcr.deal_id` は参照していない。
- `backend/app/routers/analytics.py:2019,2037`: `lead_id` をAPI互換上の `deal_id` として返す別名。今回は対象外。
- `backend/app/schemas/lead.py:100-103,181-183`: 失注理由入力は `reason_id`・`is_primary` とlead保存設定のみで、`deal_id` はない。
- `backend/app/services/tenant.py:861,865,867`: 新規テナントDDLに `deal_id`、`UNIQUE (deal_id, reason_id)`、deal_id専用indexがある。`lead_id` とそのindexは残す。
- `backend/tests/conftest.py:1189,1193`: テスト用DDLに `deal_id` と `UNIQUE (deal_id, reason_id)` がある。
- `backend/tests/test_close_reasons.py:161,169`: `deal_id` をSELECTしNULLを検証するテストがある。これはdeal_id機能そのものの検査。
- `backend/tests/test_analytics.py:823-824,862-868`: `deal_close_reasons` へ `lead_id` のみで登録しており、deal_id列は使わない。
- `backend/tests/test_analytics.py:838-843`: API互換フィールド `deal_id` がlead_id由来であることを検証。DB列の検査ではない。
- `frontend/src/api/funnel.ts:85`, `frontend/src/pages/dashboard/FunnelReasonsPage.tsx:92`, `frontend/src/mocks/funnelFixtures.ts:142,148,164`: analyticsメモのAPI互換フィールドを型・React key・fixtureで扱う。物理 `deal_close_reasons.deal_id` 参照ではない。

## テスト分類

| 箇所 | 分類 | 内容 |
|---|---|---|
| `backend/tests/test_close_reasons.py:161,169` | X | deal_idをSELECTしNULLを明示検証。廃止で不要。 |
| `backend/tests/conftest.py:1189,1193` | Z | テストDDLのスキーマ定義。deal_id削除とlead_id UNIQUEへの置換が必要。 |
| `backend/tests/test_analytics.py:823-824,862-868` | Y | lead_id経由の補助検査。変更不要。 |
| `backend/tests/test_analytics.py:838-843` | Z | API互換名の検査。物理列削除とは別契約のため今回は維持。 |

## 本番DB実測（read-only）

全5テナントで行数0、deal_id非NULL0件、lead_id非NULL0件、deal_id列は存在した。

全5テナントに以下が存在した。

- `deal_close_reasons_deal_id_fkey`
- `UNIQUE (deal_id, reason_id)` とそのインデックス
- `idx_deal_close_reasons_deal`（deal_id専用index）
- `idx_deal_close_reasons_lead_id`

## UNIQUE制約の判断

`#3061`後の登録処理は `lead_id` 単位で既存理由を削除してから登録している。従来の「対象IDとreason_idの組を重複させない」という意図は、現在の対象IDであるlead_idへ移すのが自然であり、`UNIQUE (lead_id, reason_id)`を採用した。

## 変更対象確定

- `backend/app/services/tenant.py`
- `backend/tests/conftest.py`
- `backend/tests/test_close_reasons.py`
- `docs/handoff/deal-removal-dcr-dealid/recon.md`
- `docs/handoff/deal-removal-dcr-dealid/design.md`
- `.claude-pipeline/active-work.md`
- 本店側個票

本番DBの列・FK・既存インデックス削除は次便の対象である。
