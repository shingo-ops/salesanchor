# 設計 — conv-logs-direction-guard

**対象ADR**: ADR-110（翻訳サブシステム）
**recon**: docs/handoff/conv-logs-direction-guard/recon.md
**日付**: 2026-06-24
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 該当なし：単一関数のロジック修正（direction ガード追加）であり、設計パターンの外部参照は不要と判断。既存の `ensure_inbound_translations` の契約（inbound 専用）を守るだけの修正。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| outbound を渡すと `ensure_inbound_translations` が呼ばれない | `pytest tests/test_conv_logs_fire_translation.py::test_fire_translation_skips_outbound` |
| inbound は従来どおり翻訳が発火する | `pytest tests/test_conv_logs_fire_translation.py::test_fire_translation_fires_for_inbound` |
| 既存の tenant context 順序テストが維持される | `pytest tests/test_conv_logs_fire_translation.py::test_fire_translation_sets_tenant_context_before_ensure` |
| ルーター層の既存テスト全件維持 | `pytest tests/test_conv_logs_router.py` |
| migration/deploy.yml/DBスキーマ変更なし | diff 確認: 変更ファイルは `conv_logs.py` と `test_conv_logs_fire_translation.py` のみ |
