# Design: fix-analyzer-kubun-filter

## recon参照

- docs/handoff/fix-analyzer-kubun-filter/recon.md

## 問題

`filter_product_codes_by_unit_kubun()` が `product_code_to_kubun_type` に存在しない商品コード（＝`product_category_id=NULL`）を「箱系でない」として除外していた。
全1,336件の94%が未設定のため、箱系フィルタが実質ほぼ全候補を除外する状態になっていた。

## 設計方針

| 基準 | 検証方法 |
|------|----------|
| `kubun_type="箱系"` の商品は候補に含める | 既存動作と同じ |
| `kubun_type` が存在しない（NULL）商品は候補に含める | `or c not in product_code_to_kubun_type` 追加 |
| `kubun_type="シングル系"` 等の明示非箱系は除外 | 変更なし（既存の条件で除外される） |
| pid_resolved率の改善 | デプロイ後に197件再解析で数値確認 |

## 外部事例

GAS対照: `filterProductMasterByUnitCategoryV2_` (SystemResolverV2.gs) — category未設定商品は除外しないロジックと同等

## 影響範囲

- `backend/app/services/tcg_analyzer_svc.py` 1箇所のみ
- 箱系以外の単位（シングル系等）の解析: `if "箱系" not in kubun: return product_codes` で早期リターンのため影響なし

## 戻し方

`or c not in product_code_to_kubun_type` の1行を削除してrevert commit

## 測り方

デプロイ後に197件の仕入元データを再解析し、pid_resolved率が29.9%以上に改善したことを確認
