# recon — SA-02 R1/R2（contact_id/company_id 補完）

**仕事名**: sa-02-r1-r2  
**日付**: 2026-06-14  
**対象ADR**: ADR-096  
**担当**: Terminal CC（architect recon）  
**詳細**: `docs/plans/sa-progress/SA-02-plan.md` §6 に KGI G1a/G1b 未達理由と残課題 R1/R2 の分析あり

---

## file:line 引用表

| 引用先 path:line | 確認内容 |
|-------------------|---------|
| `backend/app/services/conv_log_writer.py:29` | write_conversation_log — R1修正対象: contact_id 引数を追加 |
| `backend/app/services/conv_log_writer.py:34` | contact_id: int \| None = None — 新規引数（既存呼び出し元は後方互換） |
| `backend/app/services/conv_log_writer.py:64` | contact_id が None かつ lead_id あり → _get_contact_id_for_lead() で補完 |
| `backend/app/services/conv_log_writer.py:112` | _get_company_id_for_lead — deals から company_id を補完（既存ヘルパー） |
| `backend/app/services/conv_log_writer.py:129` | _get_contact_id_for_lead — 新規: deals から contact_id を補完（R1追加） |
| `backend/app/routers/conv_logs.py:35` | _get_company_id_for_lead インポート（R2追加） |
| `backend/app/routers/conv_logs.py:223` | create_conv_log — R2修正対象: 手動記録 INSERT に company_id を追加 |
| `backend/app/routers/conv_logs.py:279` | company_id = await _get_company_id_for_lead(db, lead_id) — 補完ロジック（R2追加） |
| `backend/tests/test_conv_log_writer.py:129` | test_write_conversation_log_contact_id_derived_from_deal — R1追加テスト |
| `backend/tests/test_conv_logs_router.py:133` | test_create_conv_log_company_id_in_insert — R2追加テスト |
| `backend/tests/test_discord_inbox.py:537` | assert mock_session.execute.call_count == 8 — R1による deals 追加クエリを反映 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | contact_id の取得元 | deals テーブルに contact_id カラムあり（deals.py:40 確認済み）。_get_company_id_for_lead と同パターンで deals から補完可能 | ✅ 解消済み |
| 2 | migration の要否 | conversation_logs テーブルには contact_id カラムが既存（Stage 1 migration 確認済み）。migration 不要 | ✅ 解消済み |
| 3 | 既存テスト test_discord_inbox への影響 | write_conversation_log の DB 呼び出しが1回増加（contact_id 補完）→ execute.call_count を 7→8 に更新 | ✅ 解消済み |
| 4 | v_company_stats への反映 | v_company_stats が conversation_logs.company_id で集計するため、R2 で company_id が保存されれば自動で反映される | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- R3（meta_messages → conversation_logs 既存データ移行）は本 PR の対象外。Shingo GO 後に別作業として実施。
- webhook 経由の contact_id は deals からの補完（deals に案件なければ NULL）。NULL 許容で 500 にしない設計を踏襲。
- _get_company_id_for_lead / _get_contact_id_for_lead は両方とも `ORDER BY created_at DESC LIMIT 1` で最新案件を参照する。
