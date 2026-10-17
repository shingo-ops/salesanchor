# design: 20260919_030000 で、表がビューのとき外部キーが作られない件（件4）

> 出発点: docs/handoff/found-untouched-20261017/handoff.md:22-25（#4481 件4）。recon: [recon.md](./recon.md)
> 状態: 設計案作成済み・設計審査済み（Opus 自己審査、APPROVE）。PO 2026-10-18 チャットで件4着手に「ｙ」（マージ・デプロイまでの完走は 2026-10-17 に委任済み）。

## KGI（○×で判定）
| # | 基準 | 検証方法 |
|---|---|---|
| K1 | 空の DB から全件を流したあと、fk_products_work_id が products → type_master（relkind r）にある | CI と同じ手順の再現で pg_constraint を引く（recon 事実5、fresh/select_result.txt） |
| K2 | 本番の fk_products_work_id が products → type_master、convalidated=t | docs/handoff/migration-guard-precision/recon.md:12 |
| K3 | 引継ぎ書の件4の行に、この便のパスと結論（変更不要）が書かれている | handoff.md の件4の行を見る |
| K4 | main マージ後、push で動く workflow がすべて success | `gh run list --commit <merge sha>` |

## 判断
- migrations/ は変えない。引継ぎ書の前提（relkind の欠落）は #4446 で直っていて、空から作る環境でも本番でも外部キーはある（recon 事実1・4・5）。
- この便の変更は記録だけにする（引継ぎ書の件4の行と、この便の recon・design・台帳）。

## 代替案
- 追加 migration で「外部キーが無ければ type_master に張る」安全網を足す案（前例 20260623_060000:14-30 のビュー分岐と揃える）。
  - 不採用。足りない環境が確認できた範囲に存在せず、本番では何もしない migration が1本増えるだけになる（recon 結論）。
  - migrations/ は危険パスで、効果の無い変更に GO を使うことになる。
- 030000 本文を書き換えてビュー分岐を足す案。
  - 不採用。ADR-1007 の「1回だけ流す」方針に反して既存ファイルを書き換えることになり、しかも効果が無い。

## 変更
- docs/handoff/found-untouched-20261017/handoff.md：件4に便のパスと結論を1行足す。
- 本 design.md・recon.md を新設する。.claude-pipeline/active-work.d/release-migration-fk-view-relkind.md（台帳）を足す。

## 触らない範囲
- migrations/、scripts/run_all_migrations.sh、.github/workflows/、deploy.yml、backend/。本番 DB にも触らない。

## リスクと対処
- 030000 が失敗したまま後続が流れた環境が、将来できる → 全件試し実行は失敗が1本でもあれば必須チェックを止める（#4476）。そのため、030000 だけが失敗したまま main に入ることは無い。

## 危険パス・GO
- docs だけ（docs/、.claude-pipeline/）。危険パスは含まない。GO は不要。本番反映は docs のみのため、Deploy の結果だけを観測する。

## 外部・過去事例の参照と我々への応用
- 過去事例：#4446 P5（commit 0e3dd5b5d）。同じ欠陥を本番照合で見つけ、relkind 条件を足して直した。本便は、その修正が空から作る環境でも効いていることを実測で確かめた。
- 外部事例は使わない。同じリポジトリの実測（CI と同じ手順の再現）が直接の根拠になるため。

## 維持の仕組み
- 全件試し実行（migration-test.yml `migration-full-dryrun`、#4476 で必須）。030000 やその前提が壊れれば、ここで止まる。
- 互換ビュー tcg_type_master の削除（2026-12-21 以降の予定）は、外部キーに影響しない。外部キーは oid で type_master を指している（recon 事実3）。

## 結果（2026-10-18）
- K1 ○（fresh/select_result.txt：`fk_products_work_id | products | type_master | t`、328本×2周 失敗0）。
- K2 ○（migration-guard-precision/recon.md:12）。
- K3 ○（handoff.md 件4に便の行を追加）。
- K4 はマージ後に観測する。
