# design — SA-02 Stage2 移行スクリプト プレフライト修正

**仕事名**: sa-02-stage2-preflight-fix  
**日付**: 2026-06-14  
**対象ADR**: ADR-096  
**recon**: docs/handoff/sa-02-stage2-preflight-fix/recon.md

---

## 問題定義

### 修正前の状態

`scripts/migrate_sa02_stage2_meta_to_conv_logs.py` の `main()` 関数内:

```python
# 修正前（バグあり）
q = "SELECT id, tenant_code FROM public.tenants WHERE is_active = true ORDER BY id"
if target_tenant_id:
    q += f" AND id = {target_tenant_id}"  # ① ORDER BY の後に AND 追加（SQL エラー）
                                           # ② f-string 埋め込みで SQL インジェクション危険
```

**問題 1**: `ORDER BY id AND id = N` という不正な SQL が生成される。  
**問題 2**: ユーザー入力 `target_tenant_id` を直接埋め込んでいる（SQL インジェクション）。  
**問題 3**: `verify_sa02_stage2_count_check.py` に `--tenant-id` オプションがなく、特定テナントの確認ができない。

---

## 修正内容

### How（実装方法）

**migrate スクリプト**: SQL を段階的に組み立て、ORDER BY を最後に追加。値はバインドパラメータで渡す。

```python
# 修正後
q = "SELECT id, tenant_code FROM public.tenants WHERE is_active = true"
params: dict = {}
if target_tenant_id:
    q += " AND id = :target_tenant_id"
    params["target_tenant_id"] = target_tenant_id
q += " ORDER BY id"
r = await conn.execute(text(q), params)
```

**verify スクリプト**: 同じパターンで `--tenant-id` オプションと WHERE 条件を追加。  
`main()` シグネチャ: `async def main(strict: bool, target_tenant_id: int | None)`

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `AND id = :target_tenant_id` が ORDER BY の前に定義されている | `test_migrate_tenant_id_sql_order_by_after_where`: ソース位置比較 |
| f-string による直接埋め込みがない | `test_migrate_tenant_id_sql_order`: ソース内 f-string 検索 |
| dry_run=True では INSERT を実行しない | `test_migrate_tenant_dry_run_no_insert`: execute 呼び出し回数 = 3 |
| dry_run=True でも stats["total"] が取得できる | `test_migrate_tenant_dry_run_returns_total` |
| tenant 未指定時 params = {} で実行される | `test_migrate_main_no_tenant_id_uses_empty_params` |
| INSERT の analysis に `sa02_stage2_migration` マーカーが含まれる | `test_migrate_script_has_rollback_marker` |
| migrate と verify のマーカー文字列が一致 | `test_rollback_marker_matches_verify_script` |
| verify スクリプトに `--tenant-id` オプションあり | `test_verify_script_has_tenant_id_option` |
| verify スクリプトでも ORDER BY が WHERE の後 | `test_verify_script_order_by_after_tenant_condition` |
| rollback.md の削除条件がマーカーと一致 | `test_rollback_doc_marker_matches_script` |

全基準: `pytest backend/tests/test_sa02_stage2_preflight.py -v` → 10/10 PASSED 確認済み

---

## 外部・過去事例

- **SQLAlchemy textual SQL + params pattern**: `text()` + パラメータ辞書によるバインドは SQLAlchemy 推奨パターン（ORM不使用でも安全なパラメータバインド）
- **同リポジトリの既存実装**: `backend/app/services/conv_log_writer.py` / `backend/app/routers/conv_logs.py` で同パターン使用済み（ADR-096 PR #2174）
- **OWASP SQL Injection**: f-string やフォーマット文字列での SQL 組み立ては OWASP Top 10 A03 に該当する既知の危険パターン

---

## 影響範囲

- `scripts/` 変更のみ（本番移行は Shingo GO 後に別作業として実施）
- `migrations/` 変更なし
- `deploy.yml` 変更なし
- アプリケーション本体（`backend/app/`）変更なし
- 既存テスト（`backend/tests/test_sa02_recon_monitor.py`）には影響なし

---

## 弊害・リスク

- 修正により `--tenant-id` なし実行時の SQL は `ORDER BY id` のみになる（元の意図と同じ）
- `--tenant-id 1` 指定時の SQL: `WHERE is_active = true AND id = :target_tenant_id ORDER BY id` — 正しい SQL
- dry_run=True は元の動作を維持（INSERT なし、total のみ表示）
- rollback.md の削除条件 `analysis->>'_source' = 'sa02_stage2_migration'` は変更なし（冪等性維持）
