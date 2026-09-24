# Recon: fix-analyzer-kubun-filter

## 観測事実

- 本番DBで197仕入元の再抽出後にpid_resolved率が51.7%→29.9%に低下
- 全1,336アクティブ商品のうち1,252件（94%）が `product_category_id=NULL`

## 根拠ファイル

- `backend/app/services/tcg_analyzer_svc.py:362-365` — `filter_product_codes_by_unit_kubun` 関数のfilter条件

## 既存ADR検索結果

- `git grep -i "kubun" docs/adr/` → 該当なし
- `git grep -i "filter_product_codes" docs/adr/` → 該当なし
- ADR対象外のバグ修正（既存ロジックの1行追加）

## 変更前コード（tcg_analyzer_svc.py:362-365）

```python
filtered = [
    c for c in product_codes
    if product_code_to_kubun_type.get(c) == "箱系"
]
```

## 変更後コード

```python
filtered = [
    c for c in product_codes
    if product_code_to_kubun_type.get(c) == "箱系"
    or c not in product_code_to_kubun_type  # category未設定は候補に残す
]
```

## 触らない範囲

- `filter_product_codes_by_unit_kubun` 以外の関数すべて
- フロントエンド
- DB・マイグレーション
