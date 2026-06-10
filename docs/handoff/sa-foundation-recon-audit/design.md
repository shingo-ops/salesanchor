# Phase 3 設計 — sa-foundation-recon-audit

**対象ADR**: ADR-131  
**recon**: docs/handoff/sa-foundation-recon-audit/recon.md  
**日付**: 2026-06-10  
**担当**: architect

---

## 外部・過去事例の参照と我々への応用

- ADR-072（per-router reset_tenant_context）: 2025年に多発したテナント越境バグの根本対策として導入。ADR-131 はその補完として get_db 層でコネクションプール返却前に構造的にクリア。
- PostgreSQL session-level GUC 汚染パターン: `SET` vs `SET LOCAL` の差異が connection pool 再利用時に問題になるパターンは PostgreSQL コミュニティ既知。`SET LOCAL` への変更は txn commit で消えるため finally での明示クリアが堅牢。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| get_db の finally ブロックで clear_tenant_context が呼ばれること | `pytest tests/test_adr072_phase_2_reset_rollout.py::test_get_db_has_clear_tenant_context_in_finally` |
| 正常終了後に clear_tenant_context が呼ばれること | `pytest tests/test_adr072_phase_2_reset_rollout.py::test_get_db_clears_context_on_success` |
| 例外発生後も clear_tenant_context が呼ばれること | `pytest tests/test_adr072_phase_2_reset_rollout.py::test_get_db_clears_context_on_exception` |
| SQLite 環境で clear_tenant_context が no-op になること | `pytest tests/test_adr072_phase_2_reset_rollout.py::test_get_db_no_op_without_tenant_context` |
| process_messenger_event の finally で clear_tenant_context が呼ばれること | `pytest tests/test_adr072_phase_2_reset_rollout.py::test_process_messenger_event_has_clear_tenant_context_in_finally` |
| migration 056 コメントが PO決定（2026-06-10）を反映していること | `migrations/056_add_suppliers_type_and_promote_public.sql:14` を目視確認 |
| docs/recon/recon-sa-foundation-full-audit-20260610.md に PO判断 #4/#5 の決定が記録されていること | `docs/recon/recon-sa-foundation-full-audit-20260610.md:184-199` |

---

## 技術 How・KPI

- `clear_tenant_context`: `SET search_path = public`, `SET app.tenant_id = ''`, `SET app.is_operator = ''` を実行。SQLite は `_dialect_supports_search_path` で no-op。
- `get_db` finally: circular import 回避のため `finally` ブロック内で local import（`# noqa: PLC0415`）。
- ADR-131/132 番号: ADR-129 が別PR（監査ログ中重要度）で先行マージのため 131/132 に振り直し。

---

## 弊害・トレードオフ

- `get_db` に finally 追加: 正常パスで3つの SQL が追加される。本番影響軽微（ADR-072 の per-router reset と同程度）。
- 書類のみPR: migration 056 はコメント変更のみ（スキーマ変更なし）。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | clear_tenant_context() を dependencies.py に追加 | Generator |
| 2 | get_db finally ブロック追加 | Generator |
| 3 | process_messenger_event try/finally 追加 | Generator |
| 4 | テスト追加（AC-1〜8） | Generator |
| 5 | migration 056 コメント是正・recon文書クローズ | Generator |

---

## 継続

- 完了後の監視: CI pytest で ADR-131/132 回帰保護テストが green であり続けることを確認
- 次フェーズへの引き継ぎ: ADR-132 将来分（BackgroundTasks 共通ラッパー）は別スプリントで起案
