# design — fix-supplier-channels-created-at

**設計日**: 2026-09-06  
**担当**: Hikky-dev (FIX-05)  
**対象ADR**: ADR-154  
**recon**: docs/handoff/fix-supplier-channels-created-at/recon.md

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `action='create'` の resolve が 500 でなく 200 を返す | 本番 smoke: `POST /tcg/line-import/{job_id}/resolve` |
| `supplier_channels` INSERT に DDL 外の列がない | `pytest backend/tests/test_tcg_schema_qualification.py::test_supplier_channels_insert_columns_match_ddl` |
| 既存テスト全件 PASS | CI pytest-run-internal |

---

## 変更内容

### `backend/app/routers/tcg_line_import.py:512`

```python
# 修正前（UndefinedColumnError の原因）
INSERT INTO {TCG_SCHEMA}.supplier_channels
  (id, supplier_id, channel, is_active, created_at)
VALUES
  (:id, :supplier_id, 'line', TRUE, now())

# 修正後（DDL に存在する列のみ）
INSERT INTO {TCG_SCHEMA}.supplier_channels
  (id, supplier_id, channel, is_active)
VALUES
  (:id, :supplier_id, 'line', TRUE)
```

### `backend/tests/test_tcg_schema_qualification.py`

`test_supplier_channels_insert_columns_match_ddl` を追加。  
DDL から括弧深さカウントで列名を抽出し、INSERT 列リストと静的照合する。

---

## テスト RED → GREEN

| 状態 | テスト結果 |
|---|---|
| 修正前（`created_at` あり） | FAILED: `supplier_channels INSERT に DDL 外の列があります: {'created_at'}` |
| 修正後（`created_at` なし） | PASSED |

---

## 外部・過去事例の参照と我々への応用

該当なし：DDL と INSERT の列名不一致という単純な実装ミス。  
「テスト緑・本番で落ちる」は本日6件目であり、静的解析テストの有効性を改めて確認。

---

## 維持の仕組み

守り手: `backend/tests/test_tcg_schema_qualification.py::test_supplier_channels_insert_columns_match_ddl`（DDL と INSERT の静的照合・CI で常時検証）  
守り手: 人手で守る — `supplier_channels` DDL を変更する場合は同テストの DDL 参照パスも更新する
