# design: 商品 440406 の除外語「バラパック」を外す

関連: [recon.md](./recon.md) / [README.md](./README.md) / ADR-155（docs/adr/ADR-155-product-master-ssot-csv-app.md）/ ADR-1020（docs/adr/FEATURE-INDEX.md:19）/ 前例 docs/handoff/master-keyword-fix/design.md・docs/handoff/deckbuild-master-fix/README.md

## KGI
同じ投稿文で、取り違え 0・悪化 0 のまま、除外語「バラパック」だけで外れていた 1 文面が商品 440406 に当たる（試算値。recon.md §3）。

## 方法（How）
除外語の表から 440406 の「バラパック」1 行を外し、後ろの 6 行の position を 1 つ詰める。1 本のトランザクションで「照合 → 変更 → 再照合 → audit_log → COMMIT」。照合が 1 つでも外れたら例外で全部戻る。dryrun.sql は同じ本体で最後だけ ROLLBACK。position は詰める（recon.md §2: アプリの保存は 1..n の連番、末尾追加は件数 + 1。詰めないと次の追加が既存の position と重なる）。

## 触るファイル / 触らない範囲
- 触る: docs/handoff/master-exclude-barapack/ の gen_sql.py・precheck.sql・dryrun.sql・apply.sql・postcheck.sql・rollback.sql・rollback_dryrun.sql・README.md・recon.md・design.md（新規・docs のみ）
- 触らない: backend/・frontend/・migrations/・.github/、440406 の検索語・ほかの除外語、ほかの商品、A5（ゴールデンボックス）

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 変更前の値が README の表どおり | precheck.sql が `OK (before) id=440406` を出す（除外語 52 語の並び・position 1..52・「バラパック」ちょうど 1 行・id 2000・position 46） |
| 消すのは 440406 の「バラパック」1 行だけ | 行を消す文は apply.sql と dryrun.sql に各 1 本（keyword と product_id で絞る）。消した件数が 1 でなければ例外で止まる。行を消す文の数は apply.sql=1、dryrun.sql=1、他の .sql は 0。表ごと消す文・条件なしの文は 0 本（台本が grep で数える） |
| position が 1..51 の連番に保たれる | dryrun 出力の `OK (after) id=440406` と、`DONE:` 行の「6 rows shifted」 |
| 失敗時は何も残らない | dryrun 後に postcheck.sql を流すと `MISMATCH (after)` で止まる（値が変わっていない） |
| 対象外の行が動かない | 動くのは 440406 の除外語 7 行（外す 1 + 詰める 6）と products 440406 の updated_at のみ。事後照合で 51 語の並びが期待と完全一致 |
| 監査が残る | apply 後に postcheck が audit_log の actor 行 = 1 を確認 |
| dryrun と apply の本体が同じ | `diff dryrun.sql apply.sql` の差が、先頭 2 行の説明と最終行（ROLLBACK; と COMMIT;）だけ |
| 戻せる | rollback.sql が「外した後」の状態でだけ動き、同じ id 2000・position 46・updated_at で入れ直す。末尾で 52 語・連番の照合を通す。rollback_dryrun.sql で試走できる |
| 悪化 0 | recon.md §3 の試算（実行前）＋再解析後の差分確認（台本側） |

## 試算の結果（件数のみ）
- 母集団 1498 文（直近 30 日の現行行 1424 + 未登録グループ 74）
- 「バラパック」を外して変わる文: 1（unmatched → matched 440406）
- 悪くなる文: 0（matched → 別の商品 0、matched → 未一致/迷い 0）
- 限界: 30 日より古い行は母集団外。SQL はローカルの DB では試していない（本番 dryrun が最初の実行確認）[未確認]。

## 戻し方
rollback.sql を PO が台本（run-rollback.sh）で流す。外した行を元の id 2000・keyword・position 46・updated_at（2026-10-17 06:50:02.770819+00）で入れ直し、47〜51 の行を 1 つ後ろへ戻して 52 語・1..52 に復元する。audit_log に 1 行。商品 440406 の updated_at は戻した時刻に進む（変更前の時刻には戻らない）。行を消す文は含まない。再解析で書き換わった行は rollback では戻らない（再解析は別手順）。

## 外部・過去事例
- 前例: docs/handoff/master-keyword-fix/（語の追加・dryrun と apply が同じ本体・precheck/postcheck の型）、docs/handoff/deckbuild-master-fix/。今回は「語を外す」点が違い、そのため position の詰めと戻し（rollback）を足した。
- 外部事例: 検索辞書の語の削除を、照合付き・同一トランザクション・事前試走で行う運用は一般的な変更管理の型。この変更の規模（1 行）では外部事例の数値調査は行わない。

## 弊害
- 「バラパック」を含む投稿のうち、30th 系でないものが 440406 に当たる可能性。試算 1498 文では悪化 0。母集団外は未検証。
- 「バラパック」は単位が Pack の行。商品は同じ 440406 だが、単位の扱いは ADR-1036（Proposed）の対象で運用は未決。
- 入れた人の意図は確認できていない（recon.md §3）。PO 決定は 2026-10-21 済み。

## 計画票
1. 本 PR をマージ（docs のみ。区分 B）
2. PO が dryrun 台本を実行 → 出力を確認
3. PO が commit 台本を実行（dryrun と同じ sha のときだけ進む）
4. 再解析（台本。有効な投稿 2 本）
5. 不具合が出たら rollback 台本

## 継続
変更は audit_log に残る。次回以降の語の削除も同じ型（gen_sql.py の表を書き換える）。
