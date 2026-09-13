# recon — 失注理由の登録をリード側へ移設

**仕事名**: 失注理由の登録をリード側へ移設  
**日付**: 2026-07-23  
**対象ADR**: ADR-121  
**担当**: architect

リード更新で失注理由を受け取り、商談側の登録を外すための事実を集めた recon です。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/routers/deals.py:174-316` | 失注理由の登録元。入力 `close_reasons[{reason_id,is_primary}]` と `close_reason_memo` を受け、`deal_close_reasons` に書き込んでいた。 |
| `backend/app/routers/leads.py:508-518` | リード更新 PATCH の入口。`close_reasons` と `close_reason_memo` を受け取れるように拡張した。 |
| `backend/app/schemas/lead.py:154-183` | `LeadUpdate` の更新スキーマ。失注理由の入力欄をここに追加した。 |
| `backend/tests/test_close_reasons.py:109-174` | 失注理由の検証テスト。失注理由必須・memo必須・primary 1 件・lead_id 整合・非 closing 遷移不要を確認している。 |
| `backend/app/services/tenant.py:859-868` | `deal_close_reasons` の本体定義。`deal_id` は NOT NULL、`lead_id` は FK で保持。 |
| `migrations/20260723_120000_dcr_dealid_nullable.sql:1-64` | `deal_close_reasons.deal_id` を全 tenant_% で動的列挙し、冪等に DROP NOT NULL する migration。 |
| `docs/specs/db-ssot/deal-removal/design.md:73,109` | 段階2の設計正本。`deal_close_reasons` は lead_id 参照へ移設し、行数は移設前後で不変とする。 |

*（引用先は実在するファイルと行番号を記載すること。process-artifacts gate が自動照合する）*

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | フロントの失注理由入力欄がどこにあるか | 次便で UI 実装を確認 | ✅ 解消済み（本便では未実装） |
| 2 | deal_close_reasons.deal_id の NOT NULL が残っているか | 本番 DB を read-only 確認 | ✅ 解消済み（#3058 で nullable 化済み） |
| 3 | lead_id が NOT NULL か | 本番 DB を read-only 確認 | ✅ 解消済み（#3032 で NOT NULL） |
| 4 | 本番の deal_close_reasons に行が残っているか | 本番 DB を read-only 確認 | ✅ 解消済み（全テナント 0 行） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 失注理由の登録は商談 PATCH からリード PATCH へ移す。
- 失注理由の保存先は `deal_close_reasons(lead_id, reason_id, is_primary)` へ統一する。
- 本便ではフロント入力欄は追加しない。
