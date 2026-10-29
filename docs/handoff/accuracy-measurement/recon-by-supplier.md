---
mode: handoff
---
# recon: 正答率を仕入元ごと・中分類ごとに分ける（段1）

親: [design-by-supplier.md](./design-by-supplier.md)・[card-by-group-bin1.md](./card-by-group-bin1.md)。2026-10-29 Opus（origin/main 起点の枝で確認）。

## 既存 ADR の検索
- 窓口: `docs/adr/ADR-1042-cloud-read-window.md`（読むだけの窓口。`ai_ro.public__<表名>` だけを見せる）
- 正解表: `docs/adr/ADR-1043-accuracy-gold-in-db.md`
- 中分類のたどり方: `docs/adr/ADR-1026-drop-products-type-master-id.md`（products から type_master_id を削除）、`docs/adr/ADR-1038-product-format-child-of-work.md`（type_master を中分類の親とする）

## 今の姿（事実）
- 採点の結果は全体の数だけ: `scripts/accuracy/score_v102.py:285-300`（`result_rows()`）。仕入元ごと・中分類ごとの表は無い。
- 窓口への送り方は `scripts/accuracy/fetch_gold.py` の `post()` にある。新しい道具はこれを読み込んで使う。
- 窓口の作り方: `migrations/20261017_130100_create_ai_ro_views.sql:25-60`。拒否の正規表現は同:23。
- 投稿→仕入元: `migrations/20260921_110000_pipeline_tables_public.sql:11-17,20-22`（source_messages.supplier_channel_id → supplier_channels.supplier_id）。
- 中分類: `migrations/20260922_030000_product_format_game_links.sql:9`（type_master）、`migrations/20261017_210000_drop_products_type_master_id.sql:1`（products.work_id でたどる）。
- 本番の窓口の列（2026-10-29 クラウドで information_schema.columns を引いた。表名と列名だけ）: source_messages(id uuid, supplier_channel_id)、supplier_channels(id uuid, supplier_id integer)、products(id integer, product_code, work_id integer)、type_master(id integer, name_ja)。すべて出ていた。
- 試験は CI で集められない: `.github/workflows/test.yml:207-208`, `:241` は backend の試験だけを流し、`backend/pyproject.toml:54` の testpaths は `tests`。workflows に scripts/accuracy の記述は 0 件。

## 未確認
- 正解表の A1 の値が products のどの列と同じか。段2 で 10/25 の照合表を使うときは、システムが付けた商品（products.id）で分けるので、段2 の分け方には影響しない。
