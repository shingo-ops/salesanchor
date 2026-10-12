# Recon: fix-analyzer-kubun-filter

## 観測事実

- 本番DBで197仕入元の再抽出後にpid_resolved率が51.7%→29.9%に低下
- 全1,336アクティブ商品のうち1,252件（94%）が `product_category_id=NULL`
- `filter_product_codes_by_unit_kubun()` が箱系フィルタ適用時に NULL商品を除外していた

## 根拠ファイル

- `backend/app/services/tcg_analyzer_svc.py:345-371` — `filter_product_codes_by_unit_kubun` 関数

## 既存ADR検索結果

- `git grep -i "kubun" docs/adr/` → 該当なし
- `git grep -i "filter_product_codes" docs/adr/` → 該当なし
- ADR対象外（PO即断によるフィルタ廃止）

## 変更前コード（tcg_analyzer_svc.py:363-371）

```python
if "箱系" not in kubun:
    return product_codes

filtered = [
    c for c in product_codes
    if product_code_to_kubun_type.get(c) == "箱系"
    or c not in product_code_to_kubun_type  # category未設定は候補に残す
]
return filtered if filtered else product_codes
```

## 変更後コード

```python
return product_codes
```

## 触らない範囲

- `filter_product_codes_by_unit_kubun` 以外の関数すべて
- フロントエンド
- DB・マイグレーション
