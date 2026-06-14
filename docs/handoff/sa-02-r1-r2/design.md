# 設計 — SA-02 R1/R2（contact_id/company_id 補完）

**対象ADR**: ADR-096  
**recon**: docs/handoff/sa-02-r1-r2/recon.md  
**日付**: 2026-06-14  
**担当**: Terminal CC

---

## 外部・過去事例の参照と我々への応用

- 該当なし：本修正は既存 conversation_logs テーブルの NULL カラムを埋める補完ロジックの追加のみ。migration なし・新テーブルなし。外部アーキテクチャパターンの参照は不要と判断。
- 参考: 同一パターンの先行実装として `_get_company_id_for_lead()` が `conv_log_writer.py:112` に存在し、deals テーブルから company_id を補完する実績済みパターンを contact_id 補完に流用した。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| write_conversation_log() が contact_id 引数を受け取れる | `pytest backend/tests/test_conv_log_writer.py::test_signature_has_required_params` |
| deals に contact がある lead では contact_id が保存される | `pytest backend/tests/test_conv_log_writer.py::test_write_conversation_log_contact_id_derived_from_deal` |
| 明示的に contact_id を渡した場合は DB 検索をスキップ | `pytest backend/tests/test_conv_log_writer.py::test_write_conversation_log_contact_id_explicit_skips_lookup` |
| lead_id=None では contact_id/company_id 検索が走らない | `pytest backend/tests/test_conv_log_writer.py::test_write_conversation_log_no_lead_id` |
| 手動記録 INSERT に company_id が含まれる | `pytest backend/tests/test_conv_logs_router.py::test_create_conv_log_company_id_in_insert` |
| 案件なし lead でも手動記録が 500 にならない | `pytest backend/tests/test_conv_logs_router.py::test_create_conv_log_no_company_id_does_not_error` |
| 既存テスト（重複ガード・翻訳発火・論理削除）が壊れない | `pytest backend/tests/test_conv_logs_router.py` |
| Discord DM 受信テストが execute 回数を正しく検証する | `pytest backend/tests/test_discord_inbox.py::test_dm_writer_creates_new_lead` |

---

## 技術 How・KPI

- KPI: SA-02 G1a（webhook 経由 contact_id NULL 解消）・G1b（手動記録 company_id NULL 解消）
- 技術選択: deals テーブルから `ORDER BY created_at DESC LIMIT 1` で最新案件の contact_id/company_id を補完。_get_company_id_for_lead の既存パターンを踏襲。
- migration: 不要（conversation_logs.contact_id カラムは Stage 1 migration で既存）

---

## 弊害・トレードオフ

- deals への追加 SELECT が1回増える（contact_id 補完）。ただし既に company_id 補完で同パターンの SELECT が実行されており、許容範囲と判断。
- contact_id が NULL のまま保存されるケース（deals に案件なし）は引き続き存在する。R3（既存データ移行）後に再評価。

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | conv_log_writer.py: _get_contact_id_for_lead 追加 + write_conversation_log に contact_id 引数 | Generator |
| 2 | conv_logs.py: create_conv_log に _get_company_id_for_lead を追加し company_id を INSERT | Generator |
| 3 | テスト更新: test_conv_log_writer / test_conv_logs_router / test_discord_inbox | Generator |
| 4 | PR #2174 → CI 緑 → develop マージ | Shingo GO |

---

## 継続

- 完了後の確認: 本番で手動記録 POST → `conversation_logs.company_id` が NULL でないことを確認（R3前の暫定）
- 次フェーズ: R3（meta_messages → conversation_logs 既存データ移行）は Shingo GO 後に別 PR
