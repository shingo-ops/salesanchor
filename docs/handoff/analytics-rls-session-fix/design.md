# Design — Analytics RLS test session pinning

**対象ADR**: ADR-131  
**recon**: docs/handoff/analytics-rls-session-fix/recon.md  
**日付**: 2026-06-22  
**担当**: Codex

## 外部・過去事例の参照と我々への応用

- 該当なし。今回の変更はテスト harness の接続固定であり、既存の RLS テストの流儀をそのまま踏襲するため、外部事例の新規参照は不要。

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 失敗テストが request 経路で `app.tenant_id` を同一セッションに載せる | `override_get_current_tenant` が `db.execute(SET ...)` を実行することを確認 |
| 既存の RLS 参照テストと同じ流儀である | `test_lead_country_control.py` / `test_channel_type_control.py` の override パターンと比較 |
| 製品コードを変更しない | diff が `backend/tests/test_analytics_conversion_by_attribute_rls.py` と handoff docs のみに限定される |
| RLS の overall_rate が 0.5 に戻る | CI の `Backend Tests` で当該テストが pass する |
