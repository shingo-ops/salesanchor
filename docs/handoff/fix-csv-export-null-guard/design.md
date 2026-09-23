# design: fix-csv-export-null-guard

## 関連ドキュメント
- recon: docs/handoff/fix-csv-export-null-guard/recon.md
- 対象ADR: ADR-155（商品マスタCSVエクスポート定義）

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

## 外部・過去事例の参照と我々への応用
Python CSV エスケープユーティリティにおける None ガードは標準的パターン。
`csv.writer` の `writerow()` も None を空文字として扱う挙動と一致。
pandas の `to_csv()` も NaN/None を空文字として出力する（デフォルト）。
→ 我々への応用: None は空文字（出力しない）として扱うのが CSV ユーティリティの慣例に合致。

## 維持の仕組み
- 守り手: `test_escape_cell_handles_none` テスト（CI必須）、mypy 型チェック（`str | None` アノテーション）
- `escape_cell()` は型アノテーションを `str | None` に変更し、mypy でNone渡しの誤用を静的検出可能
- `test_escape_cell_handles_none` テストが None ガードの存在を毎回 CI で担保

## 戻し方
`git revert <commit>` で即復旧可能（migration/DB変更なし）。
