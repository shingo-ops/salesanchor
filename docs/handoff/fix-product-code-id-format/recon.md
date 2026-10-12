# recon: fix-product-code-id-format

## KGI

`resolved_product_code IS NOT NULL AND pid_resolved = false` の行が 0 件に減少する。

## 現在地把握

### 問題の発見

本番 DB クエリ（2026-09-24 実行）:

```sql
SELECT ei.resolved_product_code, COUNT(*), p.id as correct_product_id
FROM public.extraction_items ei
JOIN public.analysis_results ar ON ar.extraction_item_id = ei.id
...
WHERE ei.resolved_product_code IS NOT NULL
AND ar.pid_resolved = false
AND sm.is_active = true
AND ei.resolved_product_code !~ '^[0-9]+$'
GROUP BY ei.resolved_product_code, p.id
```

結果: `M1L|7|33`, `AR10D|6|201`, `ARD|5|199` 等、約 100 件以上が旧形式の product_code 文字列で保存されている。

### コード精読結果

#### `backend/app/services/tcg_work_reference.py`

- L45-47: `product_ids(reference)` — スナップショットの `p["id"]` を読む（新形式）
- L51-52: `product_codes()` — `product_ids()` のエイリアス（修正済み）
- L55-63: `validate_product_id()` — id 文字列で照合（修正済み）
- L67-68: `validate_product_code()` — `validate_product_id()` のエイリアス（修正済み）
- L75-94: `load_work_reference()` — `p.id::text` フィールドを使用（修正済み）

#### `backend/app/services/tcg_analyzer_svc.py`

- L83-85: `product_code_to_uuid` — `{str(id): id}` 形式（id 文字列キー）
- L1167-1173: `product_code_to_id` マッピング — **今回追加**
- L1212-1238: `product_decisions` 構築 — **今回 `_resolve_pid()` クロージャ追加**

#### `backend/app/services/gemini_extraction_svc.py`

- L539: `validate_product_id(item.get("resolved_product_code"), work_reference)` — 抽出時に検証済み

### 根本原因

2026-09-23 の ADR-1002 Phase C リファクタ（`refactor: unify product identification around products.id`）で:
- Gemini スナップショット: `products[].code` → `products[].id` フィールドに変更
- これ以降の新規ジョブ: `resolved_product_code` に `products.id` の文字列を保存

しかし **既存 extraction_items** の `resolved_product_code` は旧形式（product_code 文字列）のまま。再解析時に `validate_product_id()` が `None` を返し `pid_resolved=false` になる。

### ADR 検索結果

- `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md` — ADR-1002: TCG マスタ SSOT 統合（Phase A/B/C）
- 今回は ADR-1002 Phase C のデータ移行漏れの修正

## スコープ

- 変更: `backend/app/services/tcg_analyzer_svc.py` のみ
- 追加: `backend/tests/test_tcg_work_id.py`, `backend/tests/test_tcg_work_matching_integration.py`
- DB スキーマ変更: なし
- マイグレーション: なし（データ変換はアプリコードで吸収）
