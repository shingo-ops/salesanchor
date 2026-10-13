# Design: 在庫集計テスト用データの仕入元名を仮名に置き換える

recon: `docs/handoff/fixture-supplier-anonymize/recon.md`
対象 ADR: ADR-099（在庫モデル。この fixture が検証する在庫集計の親 ADR。本変更はテストデータの表記のみで、ADR の判断は変えない）。仮名化そのものは PO 判断（2026-10-01・2026-10-13）に基づく

## 変更前後

| 項目 | 変更前 | 変更後 |
|------|--------|--------|
| `ver41_output.csv` 提供者列（141行） | 仕入元の実名（11種類） | 提供者A〜K（最初に現れた順） |
| `ver41_aggregation.csv` 提供者列（94行） | 同上 | 同じ対応の仮名 |
| notetrack 2本 | TEST_A 等 | 変更なし |
| `README.md` | 「実 export をそのまま配置」 | 「仕入元名を仮名に置き換えて配置（社外秘のため、2026-10-13）」 |

書式（列の並び・引用符・CRLF・BOM なし・末尾改行なし）は Python の csv モジュールで保持。触らない範囲：CSV 以外の文書・コード・notetrack の2本・過去の git 履歴（実名が残っている。今回は扱わない）。

## 受入条件

|基準|検証方法|
|---|---|
|テスト結果が変更前と同じ|変更前後で `cd backend && python3 -m pytest tests/test_inventory_aggregation.py -v --no-cov` を実行し、いずれも 3 passed, 1 skipped|
|実名が 0 件|`git diff origin/main...HEAD` と追加ファイルに対し、対応表の実名で `grep -F -f` して 0 件|
|行数・列数が同じ|変更前後で CSV の行数（142/95/6/4）と列数（18/18/19/19）が同じ|

## 外部・過去事例の参照と我々への応用

該当なし。理由：自社の社外秘情報を自社 repo のテストデータから外す作業で、外部の導入事例が設計を左右しない。

## 維持の仕組み

守り手: 今回のテスト（`backend/tests/test_inventory_aggregation.py` のゴールデンテスト）。仮名に置き換えても入力と期待値の対応がずれれば即座に落ちる。新しい実 export を fixture に足すときは、仮名化してから置く（`backend/tests/fixtures/inventory_aggregation/README.md` に明記）。

## 戻し方

PR を revert する（CSV と README が元に戻る）。ただし revert すると実名が再び公開されるため、通常は戻さない。
