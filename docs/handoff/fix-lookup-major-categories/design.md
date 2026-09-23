# 実体の無いマスタ参照を引かないようにする

対象ADR: ADR-156（商品分類ツリーと共用マスタ分離）
recon: `docs/handoff/fix-lookup-major-categories/recon.md`（事象・根拠・影響・検出漏れの理由）

## 方針

`load_lookup_maps()` のループで、**直後に public の SSOT から上書きされる列を引かない**。

- 対象列: `division_code`（→ `public.product_kinds`）、`product_category_code`（→ `public.tcg_product_categories`）
- `_OVERRIDDEN_BY_PUBLIC_SSOT` を定義し、ループ先頭で `continue` する
- `LOOKUP_TABLES` の中身とループの形（`for column, table in LOOKUP_TABLES.items():`）は**変更しない**。
  `backend/tests/test_tcg_schema_qualification.py` の `_assert_dynamic_lookup_contract` が、
  宣言が1つ・再束縛なし・動的 `text()` 呼び出しが1つ・ループの iter が `LOOKUP_TABLES.items()` であることを
  AST で検証しているため、構造を変えるとCIが落ちる
- 事実と異なっていたコメント（「初回クエリは無駄になるが」）を、実態（例外になる）に書き換える

データ側の変更は行わない。参照先は既に public の SSOT に一本化されており、**新たな保存先を作らない**。

## 受け入れ基準

| 基準 | 検証方法 |
| --- | --- |
| `tcg_major_categories` を引くクエリが発行されない | 追加テスト `test_load_lookup_maps_never_queries_tcg_major_categories`（実行SQLを収集して検査） |
| `division_code` が `public.product_kinds` 由来の値になる | 同テスト（`TCG`→10、互換エイリアス `DIV01`→10 を検証） |
| `product_category_code` が `public.tcg_product_categories` 由来になる | 同テスト |
| 静的ガードの契約を壊していない | `pytest backend/tests/test_tcg_schema_qualification.py`（実測 9 passed） |
| 既存テストを壊していない | 同ファイルを main と同条件で比較（実測: main 18 failed/22 passed → 本便 15 failed/26 passed。失敗は `--noconftest` 実行による環境要因で、本便で増えていない） |

## 外部・過去事例の参照と我々への応用

- 同一リポジトリの先行事例: `backend/app/services/tcg_product_roundtrip_svc.py:29-34` は、同じ
  `LOOKUP_TABLES` を使いながら `division_code` を `product_kinds` に事前上書きしており、この不具合を
  踏んでいない。本便はその考え方（移行済みの列は旧テーブルを引かない）を取り込み側にも適用する。
- 2026-09-21 の本番障害（`docs/handoff/line-import-schema-rewire/recon.md`）: スキーマ移行の検証が
  「文字列の有無」を測っていたため取りこぼしを検出できなかった。今回も静的検査だけでは
  「テーブルが実在するか」は分からないため、実行SQLを検査するテストを足している。
- PostgreSQL 一般の慣行: 移行期に旧テーブルへのクエリを残すと、削除された瞬間に実行時例外になる。
  読み捨て前提の「無駄なクエリ」は、削除後は無駄では済まない。

## 弊害・トレードオフ

- `LOOKUP_TABLES` に、ループでは引かない列が残る（後方互換と静的ガードのため）。
  `_OVERRIDDEN_BY_PUBLIC_SSOT` と NOTE コメントで理由を明示し、読んだ人が誤解しないようにしている
- 本番DBでの再現確認はできていない（当該APIは super_admin 認証が必要）。
  デプロイ後の確認は画面からの操作が必要で、人手に依存する

## 維持の仕組み

- 守り手: `backend/tests/test_tcg_product_import.py` の追加テスト（実行SQLの検査）、
  `backend/tests/test_tcg_schema_qualification.py`（構造の契約）
- 人手で守る: 移行でテーブルを削除するときは、参照している箇所を「文字列」ではなく
  「実行されるクエリ」の観点で確認する
