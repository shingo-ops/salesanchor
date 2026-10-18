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

## r3 CI 指摘の修正の審査（2026-10-18、Opus）

- 判定: APPROVE
- 対象: 42a9c4e37。変更したのは backend/tests/test_inventory_aggregated.py だけ（7行追加・19行削除）。
- 内容: test-schema-dup gate が、本番の表定義のコピーが 3 から 4 に増えたことを止めた。r2 で R2 として挙げた type_master のコピーを消し、既存の bootstrap_public_products（migration を適用して seed を入れる）から type_master を得るように変えた。
- 結果: R2 も解消した。gate は手元で BASE=3 HEAD=3 になり pass（実装者の生出力 impl1/schema_dup_after.txt）。

## r4 CI 指摘の修正の審査（2026-10-18、Opus）

- CI 実行 39083662764 で backend pytest が3件失敗した。
- 1) tests/test_inventory_bootstrap_lock.py の2件（NameError）: この試験は seed 関数の中の import を消してから実行する。そのため r3 で足した関数内 import が効かなかった。79d5f13b4 で試験側に代役を差し込んだ。共有 lock を取ってから DDL を流す順は実物と同じ。判定 APPROVE。
- 2) tests/test_products_tcg_type_fk.py の1件: 便1 で API から tcg_type の入力を外したので、API 経由の検査は成り立たない。design.md §3-6 に追記したとおり、API 部分だけを消し、外部キーを直接確かめる部分は便2 まで残す。不足分の扱いは選択肢 A/B/C を比べて A に決めた。B（ファイルごと削除）を選ばなかった理由: 列が残っている間に外部キーが効いていることを、確かめ続けるため。
