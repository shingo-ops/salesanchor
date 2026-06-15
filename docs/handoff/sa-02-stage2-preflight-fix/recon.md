# recon — SA-02 Stage2 移行スクリプト プレフライト修正

**仕事名**: sa-02-stage2-preflight-fix  
**日付**: 2026-06-14  
**対象ADR**: ADR-096  
**担当**: Terminal CC（architect recon）  
**詳細**: Stage2移行スクリプト 2本の SQL 安全化（SQL インジェクション修正・ORDER BY 位置修正・verify スクリプトの --tenant-id 追加）

---

## 既存ADR検索結果

`git grep -i docs/adr/` + `docs/adr/FEATURE-INDEX.md` 確認済み:

- **ADR-096**: conversation_logs SSOT — Stage2移行スクリプトは ADR-096 §4 の実行フェーズに該当
- **ADR-025**: 本番DB手動操作禁止 — migrate スクリプトは Shingo GO 後のみ実行可能（本 PR はスクリプト修正のみ）
- 他に直接関連する ADR なし

---

## file:line 引用表

| 引用先 path:line | 確認内容 |
|------------------|---------|
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:225` | main() — SQL構築: `q = "SELECT id, tenant_code FROM public.tenants WHERE is_active = true"` |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:226` | `params: dict = {}` — 空パラメータ辞書 |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:227` | `if target_tenant_id:` — tenant 指定あり時のみ条件追加 |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:228` | `q += " AND id = :target_tenant_id"` — パラメータ化（修正後） |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:229` | `params["target_tenant_id"] = target_tenant_id` — バインド値セット |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:230` | `q += " ORDER BY id"` — WHERE 句の後に ORDER BY（修正後） |
| `scripts/migrate_sa02_stage2_meta_to_conv_logs.py:171` | INSERT の analysis カラム: `'{"_source": "sa02_stage2_migration"}'::jsonb` — ロールバックマーカー |
| `scripts/verify_sa02_stage2_count_check.py:119` | `async def main(strict: bool, target_tenant_id: int \| None)` — --tenant-id 追加（修正後） |
| `scripts/verify_sa02_stage2_count_check.py:133` | `q = "SELECT id, tenant_code FROM public.tenants WHERE is_active = true"` — 同パターン |
| `scripts/verify_sa02_stage2_count_check.py:135` | `q += " AND id = :target_tenant_id"` — パラメータ化 |
| `scripts/verify_sa02_stage2_count_check.py:139` | `q += " ORDER BY id"` — ORDER BY 末尾 |
| `scripts/verify_sa02_stage2_count_check.py:199` | `parser.add_argument("--tenant-id", ...)` — CLI 引数追加 |
| `docs/handoff/sa-02-stage2-migration/rollback.md:1` | rollback.md: `analysis->>'_source' = 'sa02_stage2_migration'` でロールバック判定 |
| `backend/tests/test_sa02_stage2_preflight.py:47` | test_migrate_tenant_id_sql_order — ソース検査: AND id = :target_tenant_id あり |
| `backend/tests/test_sa02_stage2_preflight.py:60` | test_migrate_tenant_id_sql_order_by_after_where — ORDER BY が AND 条件より後 |
| `backend/tests/test_sa02_stage2_preflight.py:78` | test_migrate_tenant_dry_run_no_insert — dry_run=True で INSERT なし |
| `backend/tests/test_sa02_stage2_preflight.py:113` | test_migrate_tenant_dry_run_returns_total — dry_run でも total 取得可 |
| `backend/tests/test_sa02_stage2_preflight.py:142` | test_migrate_main_no_tenant_id_uses_empty_params — tenant 未指定時 params={} |
| `backend/tests/test_sa02_stage2_preflight.py:182` | test_migrate_script_has_rollback_marker — rollback marker 存在確認 |
| `backend/tests/test_sa02_stage2_preflight.py:188` | test_rollback_marker_matches_verify_script — migrate/verify の marker 一致 |
| `backend/tests/test_sa02_stage2_preflight.py:202` | test_verify_script_has_tenant_id_option — verify に --tenant-id あり |
| `backend/tests/test_sa02_stage2_preflight.py:210` | test_verify_script_order_by_after_tenant_condition — ORDER BY 位置 |
| `backend/tests/test_sa02_stage2_preflight.py:223` | test_rollback_doc_marker_matches_script — rollback.md marker 一致 |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 修正前の SQL バグ（ORDER BY 後に AND id 追加）がどこで発生するか | `scripts/migrate_sa02_stage2_meta_to_conv_logs.py` の元実装を確認。ORDER BY id がハードコードされた文字列内にあり、その後 f-string で AND id = {target_tenant_id} が追加される構造だった | ✅ 解消済み |
| 2 | verify スクリプトに --tenant-id がなかった理由 | 初期実装でテスト用オプションが漏れた。migrate スクリプトのパターンを移植して追加 | ✅ 解消済み |
| 3 | rollback marker (`sa02_stage2_migration`) が verify スクリプトにあるか | verify スクリプトは `analysis->>'_source' = 'sa02_stage2_migration'` で移行行を特定する。テスト test_rollback_marker_matches_verify_script で確認済み | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
