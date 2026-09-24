# design: extraction_example_text 追加

## KGI
- 仕入元ごとに代表的なメッセージ例文を登録・保存でき、Gemini 抽出プロンプトに自動注入されること

## KPI / 検証方法

| 基準 | 検証方法 |
|------|---------|
| DB カラム追加 | `SELECT extraction_example_text FROM public.suppliers LIMIT 1` が動作する |
| API GET: フィールドが返る | `/super-admin/suppliers/{id}/extraction-rules` レスポンスに `extraction_example_text` が含まれる |
| API PATCH: 保存・クリアできる | PATCH で値を送信→再 GET で値が返る / PATCH で null→再 GET で null |
| Gemini プロンプト注入 | `_build_supplier_context_note()` に `extraction_example_text` がある場合、返り値に「典型的なメッセージ例」文言が含まれる |
| フロントエンド UI | 仕入元選択→Textarea に入力→保存→再選択で値が表示される |
| i18n | ja/en 両方でラベルが表示される |

## 設計方針

既存の `extraction_notes` / `extraction_price_format` 等と同一パターンで拡張。
新たなアーキテクチャ変更なし。

## 外部・過去事例の参照と我々への応用

該当なし。既存の `extraction_notes` / `extraction_price_format` 等と同一パターンの拡張であり、新たなアーキテクチャ判断を要しない内部拡張。

## 影響範囲（守り手）
- `_EXTRACTION_RULE_COLS` を参照する全箇所: GET / PATCH エンドポイント（同ファイル内）
- `supplier_context` を受け取る `_build_supplier_context_note()` / `call_gemini_extraction()`
- mock タプル: `test_tcg_work_id.py` の 2 箇所

## 弊害
- なし（既存フィールドと同一パターン、Optional・IF NOT EXISTS で後方互換）

## 戻し方
```sql
ALTER TABLE public.suppliers DROP COLUMN IF EXISTS extraction_example_text;
```
フロントエンドはフィールドを削除するだけで元に戻る。

## 維持の仕組み

- 守り手: 人手で守る（`_EXTRACTION_RULE_COLS` と `_EXTRACTION_RULE_UPDATABLE` を変更する際に同時更新するパターン）
- 対象: `extraction_example_text` が SELECT / UPDATE / レスポンス構築 / テストの mock タプルで欠落すること
- 関所なし: フィールド追加パターンは機械検査困難。コードレビューで確認する。
