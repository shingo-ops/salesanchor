# Design: fix-analyzer-kubun-filter

## recon参照

- docs/handoff/fix-analyzer-kubun-filter/recon.md

## 問題

`filter_product_codes_by_unit_kubun()` が箱系/シングル系フィルタを適用していたが、
システムは商品カテゴリ区分（箱系/シングル系）を見る必要がないことがPO判断で確定した。
全1,336件の94%が `product_category_id=NULL` のため、フィルタが機能していなかった。

## 設計方針

PO判断: 箱系/シングル系フィルタ工程自体を排除する。

| 基準 | 検証方法 |
|------|----------|
| 全商品が常に候補として返される | 関数が `product_codes` をそのまま返すことで確認 |
| pid_resolved率が改善する | デプロイ後に197件再解析で数値確認 |

## 外部・過去事例の参照と我々への応用

- GAS対照: `filterProductMasterByUnitCategoryV2_` (SystemResolverV2.gs) — 元々フィルタなし（全商品返却）のロジックが正式仕様であることを確認
- 応用: GASと同等の「フィルタなし」状態に戻すことで、category未設定商品の除外を防ぐ

## 影響範囲

- `backend/app/services/tcg_analyzer_svc.py` 1箇所のみ（関数内のフィルタロジック全削除）
- フロントエンド: 影響なし
- DB・マイグレーション: 影響なし

## 維持の仕組み

守り手: CI lint（tcg_analyzer_svc.py の型チェック）・既存テスト944件

- `filter_product_codes_by_unit_kubun` は引数シグネチャを維持（呼び出し元変更なし）
- 関数本体が `return product_codes` のみになるため、将来的に呼び出し元から削除可能

## 戻し方

フィルタロジックを復元してrevert commit（関数本体を元の実装に戻す）

## 測り方

デプロイ後に197件の仕入元データを再解析し、pid_resolved率が29.9%以上に改善したことを確認
