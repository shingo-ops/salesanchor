# design: Gemini resolved_product_code を pid 照合の第一候補に採用

recon: docs/handoff/use-gemini-product-code/recon.md

対象ADR: ADR-1001（public.products 統一後の analyzer 実装改善）

## KGI

v5 プロンプトジョブで Gemini が返した商品コードが、unit kubun チェックを通じて正しく採用されること。

## KPI（観測可能な事象）

| 基準 | 検証方法 |
|------|---------|
| v5 ジョブで有効コードが `pid_basis = 'GEMINI'` で保存される | 解析後 `SELECT pid_basis FROM public.analysis_results WHERE pid_basis='GEMINI' LIMIT 5` |
| 無効コード（マスタ外）はフォールバックで `FALLBACK|...` になる | `SELECT pid_basis FROM public.analysis_results WHERE pid_basis LIKE 'FALLBACK|%' LIMIT 1` |
| v4 ジョブの `GEMINI|WORK:...` は変わらない | 既存 v4 CI テストが引き続き PASS |

## 変更方針

`tcg_analyzer_svc.py` の Gemini direct hit パス（1331行目）を以下に変更:
- チェック: `gemini_product_id in product_code_to_uuid` → `gemini_product_id in filtered_codes`
- pid_basis: `f"GEMINI_DIRECT|WORK:{work_id}|ID:{matched_code}"[:100]` → `"GEMINI"`

根拠: `filtered_codes` は unit kubun フィルタ済みで、誤った種別のコードを拒否できる。`product_code_to_uuid` は全商品を対象とするため過剰。

## 影響範囲

- `backend/app/services/tcg_analyzer_svc.py`（Gemini v5+ パスのみ）
- v4 パス（`work_decisions` あり・`product_decisions` なし）は一切変更なし
- MANUAL パス（`has_product_correction`）は一切変更なし
- `analysis_results.pid_basis` の値形式が変更（`GEMINI_DIRECT|...` → `GEMINI`）

## 戻し方

`filtered_codes` を `product_code_to_uuid` に戻し、`pid_basis` を元の f-string に戻す。データ変更はなし（再解析しない限り既存レコードは変わらない）。

## 外部・過去事例の参照と我々への応用

- ADR-1001 で `public.products` 統一後の analyzer 実装を正式採用。本変更はその延長として Gemini v5 パスの精度改善。
- コミット 749006586 で実装された Gemini direct hit パスの改善（`product_code_to_uuid` → `filtered_codes`）
- unit kubun フィルタは既にキーワード照合パスで使用されており、同じフィルタを Gemini パスにも適用することで整合性を保つ

## 維持の仕組み

守り手: `backend/tests/test_tcg_work_matching_integration.py`（CI テスト2件）
- `test_gemini_resolved_product_code_v5_pid_basis` — v5 有効コードで `pid_basis == 'GEMINI'` を保証
- `test_gemini_resolved_product_code_v5_fallback_when_not_in_filtered_codes` — 無効コードでフォールバックを保証
