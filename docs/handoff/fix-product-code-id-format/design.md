# design: fix-product-code-id-format

## ADR 参照

- ADR-1002 (Phase C): TCG マスタ SSOT 統合 — products.id を商品識別子として統一

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| `resolved_product_code IS NOT NULL AND pid_resolved=false` の件数が 0 になる | 再解析後に同クエリを実行して確認 |
| 既存の pid_resolved=true の行が変化しない | 再解析後に pid_resolved=true の件数が減少していないこと |

## 変更設計

### 問題

`analyze_extraction_job()` で v5 ジョブの `resolved_product_code` を `validate_product_id()` で再検証する際、旧形式（product_code 文字列: "M1L"）が新形式スナップショット（id フィールド: "33"）に存在しないため `None` を返し `pid_resolved=false` になる。

### 修正方針

`backend/app/services/tcg_analyzer_svc.py:1167-1173` に `product_code_to_id` マッピングを追加:

```python
legacy_code_rows = session.execute(
    text("SELECT product_code, id FROM public.products WHERE is_active = TRUE AND product_code IS NOT NULL")
).fetchall()
product_code_to_id: dict[str, str] = {str(r[0]): str(r[1]) for r in legacy_code_rows}
```

`backend/app/services/tcg_analyzer_svc.py:1222-1238` に `_resolve_pid()` クロージャを追加:

```python
def _resolve_pid(pid: str | None) -> str | None:
    if pid is None or pid == "":
        return None
    # 直接 products.id 照合（新形式: "33" 等）
    validated = validate_product_id(pid, reference)
    if validated is not None:
        return validated
    # product_code → id マッピングでフォールバック（旧形式: "M1L" 等）
    mapped_id = product_code_to_id.get(pid)
    if mapped_id is not None:
        return validate_product_id(mapped_id, reference)
    return None
```

### 影響範囲

- 呼び出し元: `analyze_extraction_job()` 内のみ（L1235-1238）
- 外部インターフェース変更: なし
- スナップショット形式変更: なし（既存データをそのまま読む）

### 戻し方

git revert で元の `validate_product_id` 直接呼び出しに戻す（1コミット）。

### 測り方

再解析後に以下のクエリで確認:

```sql
SELECT COUNT(*) FROM public.analysis_results ar
JOIN public.extraction_items ei ON ei.id = ar.extraction_item_id
JOIN public.extraction_jobs ej ON ej.id = ei.extraction_job_id
JOIN public.source_messages sm ON sm.id = ej.source_message_id
WHERE ei.resolved_product_code IS NOT NULL
AND ar.pid_resolved = false
AND sm.is_active = true;
```

## 外部事例

ADR-1002 Phase C のデータ移行パターンとして、段階的識別子移行でアプリ層フォールバック変換を採用する手法は一般的（Django の migration, Rails の double-write パターン等）。

## 維持の仕組み

- 将来的に `extraction_items.resolved_product_code` が全て products.id 形式になれば `_resolve_pid()` はフォールバックなしの直接照合のみになる
- `product_code_to_id` マッピングは `public.products` の `product_code` が不要になれば削除可能

## 守り手

- CI: `test_gemini_resolved_product_code_v5_pid_basis` — 新形式の正常動作
- CI: `test_gemini_resolved_product_code_legacy_format_fallback` — 旧形式フォールバック動作（今回追加）
