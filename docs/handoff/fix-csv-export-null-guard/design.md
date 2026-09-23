# design: fix-csv-export-null-guard

## KGI
`/api/v1/tcg/products/export` が `product_code` NULL商品を含む場合でも200を返す。

## 変更方針
`escape_cell(value)` の先頭に `if value is None: return ""` ガードを追加（2行挿入）。
既存の動作を変えず、None のみ空文字として出力する。

## 変更前後
```python
# Before
def escape_cell(value: str) -> str:
    return "'" + value if needs_escape(value) else value

# After
def escape_cell(value: str | None) -> str:
    if value is None:
        return ""
    return "'" + value if needs_escape(value) else value
```

## 影響範囲
- `escape_cell()` の呼び出し元: `export_csv()` 内の `values()` 経由のみ（grep確認済み）
- `unescape_cell()` は非影響（CSVインポート時はパーサーが空文字を返す）

| 基準 | 検証方法 |
|------|---------|
| 本番エラーが解消する | デプロイ後 `/api/v1/tcg/products/export` が200を返すことをブラウザ確認 |
| 既存テストが壊れない | pytest PASSED（CI確認） |
| None 入力でも空文字を返す | `test_escape_cell_handles_none` テストで担保 |

## 外部事例
Python CSV エスケープユーティリティにおける None ガードは標準的パターン。
`csv.writer` の `writerow()` も None を空文字として扱う挙動と一致。

## 戻し方
`git revert <commit>` で即復旧可能（migration/DB変更なし）。
