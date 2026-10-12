# recon: 「人が確認済み」列に POルール一括修正分を含める

作成: 2026-10-06（設計担当 Opus）／起点: origin/main `2361373d9`
前便: PR #3881（`docs/handoff/condition-fallback-count/design.md`）

## ADR 検索
- ADR-154（条件判定ロジック）、ADR-100（パイプライン全体）、ADR-027（i18n）、ADR-067・ADR-144（UI）— 前便 design.md「関連」と同じ。今回 UI 変更なし。

## 現状（コード）
- `backend/app/services/tcg_supplier_quality_svc.py:19` `CONDITION_MANUAL_BASIS = "MANUAL_CONDITION_REVIEW"`
- `backend/app/services/tcg_supplier_quality_svc.py:52` `COUNT(CASE WHEN ar.condition_basis = :manual_basis THEN 1 END) AS condition_manual_reviewed_count`
- `backend/app/services/tcg_supplier_quality_svc.py:66` params `"manual_basis": CONDITION_MANUAL_BASIS`
- `backend/tests/test_tcg_supplier_quality.py:246` 3バインド引数の検証で `manual_basis` を参照
- basis を `MANUAL_` で書き込むコードは `backend/app/services/tcg_condition_review_svc.py:286`（`MANUAL_CONDITION_REVIEW`）のみ。`MANUAL_RAW_REVIEW:PO_RULES` を書くコードは origin/main の全パス・全履歴に 0 件（`git grep` / `git log -S`、2026-10-02 調査）。

## 現状（本番DB・PO本人が実行した読み取りSQLの出力、2026-09-30 21:27 JST 以降）
- `analysis_results.condition_basis` 全41種。`MANUAL_CONDITION_REVIEW` = 0件、`MANUAL_RAW_REVIEW:PO_RULES` = 371件。
- 371件の `item_corrections`: `corrected_by = codex:PO-authorized:20260916-1203`、`field_name` = `manual_partial_update` 371件・`product_id` 371件。
- 371件の `condition_canonical`: Sealed box 264 / Damaged sealed box 74 / Case 25 / No shrink box 6 / Opened box 1 / Opened case 1。初回 updated_at 2026-09-16 03:40 UTC。
- 結論（事実）: PO 許可の一括修正で人（PO）のルールにより状態が確定した行。AI の推測・お手上げではない。

## PO 決定
- 2026-10-06 PO「y」: この371件を「人が確認済み」に数える。
