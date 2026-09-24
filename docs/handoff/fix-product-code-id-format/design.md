# 設計 — fix-product-code-id-format

**対象ADR**: ADR-1002  
**recon**: docs/handoff/fix-product-code-id-format/recon.md  
**日付**: 2026-09-24  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- Django migration の `allow_unicode_usernames` フォールバック / Rails の double-write パターン: 段階的識別子移行でアプリ層フォールバック変換を採用し DB スキーマを変えずに過渡期データを吸収する手法。我々への応用: `product_code_to_id` フォールバックマッピングをアプリ層に閉じることで、`extraction_items.resolved_product_code` の一括 DML 更新（不可逆操作）を回避する。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `resolved_product_code IS NOT NULL AND pid_resolved=false` の件数が 0 になる | 再解析後に同クエリを実行して確認 |
| 既存の `pid_resolved=true` の行が変化しない | 再解析後に `pid_resolved=true` の件数が減少していないこと |

---

## 技術 How・KPI

- KPI: 再解析後の `pid_resolved=false AND resolved_product_code IS NOT NULL` 件数 = 0
- 技術選択: `product_code_to_id` フォールバックマッピングをアプリ層クロージャ `_resolve_pid()` に追加（理由: DB スキーマ変更なし・最小リスク）

### 変更設計

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

---

## 弊害・トレードオフ

- `load_lookup_maps()` に 1 クエリ追加: 軽微なオーバーヘッド → 対策: `products` テーブルは小規模（数千行）なので許容範囲

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `product_code_to_id` マッピング追加 + `_resolve_pid()` クロージャ実装 | Generator |
| 2 | `test_validate_product_id_accepts_id_string` ユニットテスト追加 | Generator |
| 3 | `test_gemini_resolved_product_code_legacy_format_fallback` 統合テスト追加 | Generator |
| 4 | デプロイ後に再解析実行・件数確認 | PO |

---

## 継続

- 完了後の監視: 再解析後のクエリで `pid_resolved=false AND resolved_product_code IS NOT NULL` = 0 件を確認
- 次フェーズへの引き継ぎ: `product_code_to_id` フォールバックは将来 `extraction_items` が全て id 形式になれば不要になる

## 維持の仕組み

- 守り手: `backend/tests/test_tcg_work_matching_integration.py` — `test_gemini_resolved_product_code_v5_pid_basis`（新形式）・`test_gemini_resolved_product_code_legacy_format_fallback`（旧形式フォールバック）
- 守り手: `backend/tests/test_tcg_work_id.py` — `test_validate_product_id_accepts_id_string`
