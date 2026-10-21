# recon 便1: 詳細保存で作品と細分類を1文で書く

> 親の書類: [recon.md](recon.md)（全体の現在地）。この書類は便1 の現在地だけ。
> 基準: origin/main b43705ba2（PR #4625 取り込み後）

## 現在地（変更前）
- backend/app/services/tcg_product_detail_svc.py:258-284 付近: 作品などを書く UPDATE のあとに、細分類だけを別の UPDATE で書き、そのあとに細分類と作品の照合をしている。1 回目と 2 回目のあいだ、作品と細分類が一時的にずれる。
- backend/app/services/tcg_product_detail_svc.py:157-159: 行を `FOR UPDATE` で読んでから書く（同時更新を防ぐ）。
- backend/app/services/tcg_product_detail_svc.py:326: `db.commit()`。照合に失敗した場合は commit に届かず、書き込みは確定しない。
- backend/tests/test_product_format_game_links_pg.py: 既存の試験 8 件（`test_detail_update_keeps_unchanged_old_pair` を含む）。

## 型の確認
- `final_format_id` は int か None。API の検証モデル backend/app/routers/tcg_product_import.py:309 が `product_format_id: int | None`。
- 細分類が来なかったとき使う `product.get("product_format_id")` は、backend/app/services/tcg_product_detail_svc.py:64 の `row_to_json` 由来で、JSON の整数か NULL。
- 今まで 2 回目の UPDATE に渡していた値と同じ型。CAST は足さない。

## ADR を探した結果
- ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）: 細分類を作品の子にする設計。この便の根拠。
- ADR-1020（docs/adr/ADR-1020-shared-product-required-fields.md）: 細分類を来たときだけ書く規則（D5）と、照合を変わったときだけ行う規則（D2）。守る。
- ADR-1026（docs/adr/ADR-1026-drop-products-type-master-id.md）: 作品の持ち方（work_id）。変えない。
