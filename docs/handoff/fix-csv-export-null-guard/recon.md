# recon: fix-csv-export-null-guard

## 目的
本番エラー（AttributeError: 'NoneType' object has no attribute 'startswith'）の修正。
商品マスタCSVエクスポートが `product_code` NULL の商品で500エラーになる。

## 実測エラー（2026-09-23 08:58 JST 本番ログ）
```
File "tcg_product_roundtrip_svc.py", line 50, in escape_cell
    return "'" + value if needs_escape(value) else value
File "tcg_product_roundtrip_svc.py", line 44, in needs_escape
    return value.startswith(("'", "\t", "\r", "\n")) or value.lstrip().startswith(
AttributeError: 'NoneType' object has no attribute 'startswith'
```

## 影響ファイル
- `backend/app/services/tcg_product_roundtrip_svc.py:44-50` — `escape_cell()` / `needs_escape()`
- `backend/tests/test_tcg_product_roundtrip.py` — テスト追加

## 根本原因
`values()` が `product["product_code"]` を直接返す。`product_code` がNULLの商品（31件）で `escape_cell(None)` が呼ばれ、`None.startswith()` でクラッシュ。

## 既存ADR検索結果
- ADR-025: データ手動DB INSERT原則禁止（今回は非該当）
- 直接関連ADRなし（escape_cell はユーティリティ関数。ガード追加は自己完結）
