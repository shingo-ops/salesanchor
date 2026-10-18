# Opus 審査記録 — inventory-tab-by-work-id

同一 AI（Claude Opus）による審査。独立した第二者レビューではない。

## r1 設計審査（2026-10-18）

- 判定: APPROVE（便1 着手可）
- 対象: docs/handoff/inventory-tab-by-work-id/design.md、docs/handoff/inventory-tab-by-work-id/recon.md、docs/adr/ADR-1030-drop-products-tcg-type.md
- 根拠: 変更箇所が recon の file:line と一致している。作品の正本 work_id（ADR-1026）に寄せ、新しい写しを作らない。受入条件はコマンドの出力か PO の目視で○×が決まる。GAS が変更不要であることは実物で確かめた（design.md §5）。
- 実装中に止める点: B1／B2／B4（design.md §10）
- 実装中の変更 1件: products.py は曖昧列を避けるため相関サブクエリにした（design.md §3 の例外。同じ意味）。

## r2 実装差分の審査

- 判定: APPROVE（reviewer エージェント・Opus。対象 HEAD 45a4c28aa〜09297d6e8。間の差は docs だけ）
- SQL: inventory_offers・inventory_aggregated_service・inventory_search・products のそれぞれで、JOIN または相関サブクエリが正しいことを確かめた。曖昧列・テナント条件・SQLite と PG の分岐に問題は無い。
- 範囲: migrations/・scripts/・.github/ の変更は 0 件。§3-7 の grep で残るのは、許可した26行だけ。
- frontend: ProductEditPage に、もう使わない state・取得処理・import は残っていない。i18n は ja と en の両方が 4868 キーで、差は 0。
- K3 のテストは backend/tests/test_inventory_distribution_rows_pg.py:435 にあり、CI では skip されない経路にある。
- openapi.json: 書き出し直したものとスキーマ・道が一致した。違いは Decimal の pattern の版差だけで、main でも同じ差が出る。
- 軽い指摘:
  - R1: inventory_search の SQL は、CI でも手元でも実行されない（TEST_PG_URL が無い）。→ 便1 のデプロイ後に、本番で検索 API が 401 を返し 500 を返さないことを確かめる（K4 に足す）。
  - R2: テストの準備コードで作る type_master は列が少ない。既存の表と同じ型で、今回だけの問題ではない。
  - R3: openapi.json は差分を当てる方法で更新した。CI の api-contract-check で決着させる。
