# 商品マスタの二重登録10組の統合（merge 2）: 実行手順書

状態: SQL 生成済み・**未適用**。設計は design.md（設計担当が作成）。根拠は recon.md。
PO 決定（2026-10-05）: 「2.はい」（確認済みの二重登録10組を、DUAL EVOLUTION の統合と同じ方法でまとめる）。
残す行・退役する行・キーワードの引き継ぎは設計担当（Opus）が決定（下表）。

## 変更の内容
| 残す（survivor） | 退役（is_active=false） |
|---|---|
| 398 UA-PC02BT | 440573 PM0225 |
| 440434 PM0232 | 1386 LOR-the-first-chapter |
| 440435 PM0233 | 1385 LOR-rise-of-the-floodborn |
| 440578 PM0234 | 1384 LOR-into-the-inklands |
| 440579 PM0235 | 1383 LOR-ursulas-return |
| 440580 PM0236 | 1382 LOR-shimmering-skies |
| 440581 PM0237 | 1381 LOR-azurite-sea |
| 440582 PM0238 | 1380 LOR-archazias-island |
| 440583 PM0239 | 1379 LOR-reign-of-jafar |
| 440587 PM0243 | 1376 LOR-wilds-unknown |

やること（1組ごと、1つのトランザクション内）:
1. analysis_results.product_id、extraction_items.resolved_product_code（id の文字列）、buyback_shop_products.product_id、extraction_shadow_results.product_id を、退役側から残す側へ付け替える。
2. 残す側の is_current を、影響する区切りの中だけアプリの規則（tcg_analyzer_svc.py:1759-1791）で付け直す。同時刻の引き分けだけ `is_current DESC, id` で決める（recon.md §5）。
3. 退役側の検索・除外の語のうち、残す側にないもの（normalize_for_match で比較済み）を、残す側の次の position に追加する。
4. 退役側を is_active=false にする（物理削除なし。退役側のキーワード行は残す）。
5. audit_log に1組1行を書く（new_values に付け替えた行の id、is_current の旧値、追加したキーワード行の id を保存。merge_id = `dup-merge-2-20261005`）。

変えないもの: mark・名称・product_code・JAN・分類。履歴の表（snapshots・backups・extraction_attempts・work_reference_snapshot・旧 product_code 文字列）。

## 期待件数（specs.json、2026-10-05T03:16Z に読み取り。実行直前に precheck で再確認）
| 残す ← 退役 | analysis_results | is_current false | extraction_items | buyback | shadow | 追加キーワード |
|---|---|---|---|---|---|---|
| 398 ← 440573 | 10 | 0 | 0 | 0 | 0 | 検索1・除外3 |
| 440434 ← 1386 | 11 | 1 | 14 | 0 | 0 | 検索1 |
| 440435 ← 1385 | 7 | 1 | 4 | 0 | 0 | 検索1 |
| 440578 ← 1384 | 8 | 2 | 8 | 0 | 0 | 検索1 |
| 440579 ← 1383 | 4 | 1 | 4 | 0 | 0 | 検索1 |
| 440580 ← 1382 | 18 | 2 | 22 | 0 | 0 | 検索1 |
| 440581 ← 1381 | 12 | 1 | 16 | 0 | 0 | 検索1 |
| 440582 ← 1380 | 4 | 1 | 4 | 0 | 0 | 検索1 |
| 440583 ← 1379 | 1 | 0 | 1 | 0 | 0 | 検索1 |
| 440587 ← 1376 | 0 | 0 | 0 | 0 | 0 | 検索1 |
| 合計 | 75 | 9 | 73 | 0 | 0 | 13（検索10・除外3） |

これらの件数は SQL の中で完全一致のガードになっている（1つでも違えば、書き込む前にエラーで止まる）。残す側の analysis_results 件数・キーワード件数も同様にガードする。件数が動いたら gen_sql.py の specs.json を読み取りで取り直して生成し直す。

## ファイル
| ファイル | 内容 | 書き込み |
|---|---|---|
| specs.json | 期待件数と引き継ぐキーワードの一覧（読み取りから作成） | なし |
| gen_sql.py | specs.json から下の5つを生成（手で編集しない） | なし |
| precheck.sql | 件数・状態・予測した is_current の変化・引き継ぐ語を照合。違えばエラー | なし（READ ONLY） |
| dryrun.sql | apply と同じ処理。最後に ROLLBACK | なし |
| apply.sql | 本番へ適用。1つのトランザクション、最後に COMMIT | あり |
| postcheck.sql | 適用後の状態を照合（退役側が非活性・参照0・保存した id が残す側にある・語が入っている・audit 10行） | なし（READ ONLY） |
| rollback.sql | audit に保存した行だけを元に戻す。**新しい PO の判断なしに実行しない** | あり |
| recon.md | 事実（読み取りの結果） | |
| logs/ | 実行ログ（実行後に追加） | |

## 実行の順序（PO の GO と、都度の permit-danger のチケットが必要。dup-merge-20261005 と同じ）
1. precheck.sql（読み取り）→ 全 OK を確認
2. dryrun.sql（ROLLBACK で終わる）→ 件数が期待どおりか確認
3. apply.sql（1回だけ）
4. postcheck.sql（読み取り）
5. 戻すときだけ rollback.sql（新しい PO の判断が必要）

## 注意
- マイグレーション `migrations/20260604_010000_seed_product_marks.sql` は毎回のデプロイで再実行され、products.mark を名称の完全一致で UPDATE する。20 id の名称・コード・mark はそのシード（154行）に現れないので、この統合を元に戻さない（recon.md §8）。シードは is_active・キーワード・analysis_results に触らない。
- 作品の参照の digest はマスタの編集で変わるため、保存済みの v5 以降のジョブの再解析が「作業の参照が変わった」で止まることがある（マスタを編集するたびに起きる既存の動き）。試験の時間を避ける。
- 本番の SQL は平文のみ（符号化しない）。重複ではない SQL を混ぜない。

## テスト
手元の使い捨て Postgres 16 での apply → rollback の検証は実施しない（設計担当の決定 2026-10-05: 手元の DB の作成がツールのガードで止まったため、ガードを迂回しない）。テストの代わりに、本番での dryrun.sql（apply と同じ処理で、最後に ROLLBACK。全ての件数ガードと最終状態の照合が入っている）を使う。rollback.sql は一度も実行していないので、検証の範囲は本番の dryrun と、適用後の postcheck.sql までで、rollback の動作は未検証である。

## is_current の同時刻の引き分け（アプリの規則への追加）
440435 ← 1385 の1区切りに、received_at と computed_at が完全に同じ退役側2行がある。アプリの規則（tcg_analyzer_svc.py:1759-1791）はこの順序を決めていない。この SQL は `ORDER BY received_at DESC, computed_at DESC, is_current DESC, id` として、今 is_current の行を残す（この区切りは変更なし）。この追加は引き分けの区切りにだけ効き、ほかの区切りは規則どおり。設計担当が承認済み（2026-10-05）。

## 実行記録
- 2026-10-05T03:22:03Z dryrun.sql（sha256 da6d2ec594a1b2032a886aa36fc54322b9feae8033bb220d6017051abb7da32b）を本番で実行。全ガード通過、ROLLBACK で終了。ログ: logs/dryrun.log。
- 2026-10-05T03:23:17Z apply.sql（sha256 312be7c60f5cb44f2bc92017402b996847afbecc2e3c0be938ef0ec73d047a05）を本番で実行。1つのトランザクションで COMMIT。ログ: logs/apply.log。permit-danger のチケットは1回の実行ごとに発行（dryrun 03:21:57Z、apply 03:23:13Z）。
- 結果（apply.log）: analysis_results 付け替え 75、is_current の false への変更 9（true への変更 0）、extraction_items 73、buyback 0、shadow 0、キーワード行の追加 13（検索10・除外3）、退役 10行、audit_log 10行（id 44〜53、changed_by `claude-opus (PO承認 2026-10-05 dup-merge-2)`、merge_id `dup-merge-2-20261005`）。dryrun.log と apply.log の差は、`DO` の出力位置と最後の `ROLLBACK`/`COMMIT` のみ（diff で確認）。
- 適用後の読み取り確認（全て読み取り、-c の単文）:
  - (a) 20商品: 退役10行は is_active=false で参照 0。残す10行は is_active=true で、analysis_results 14/25/14/17/8/33/23/8/1/3（398・440434・440435・440578・440579・440580・440581・440582・440583・440587 の順）、extraction_items 5/17/4/8/4/23/17/4/1/0、shadow 0/2/0/0/4/6/2/4/0/0、検索の語の行は 398 が3、ほかが2、除外の語の行は 398 が3、ほかが0。
  - (b) 残す10行の is_current が2行以上ある区切り（channel×condition）: 0 件。
  - (c) audit_log に dup-merge-2-20261005 を含む行: 10 行（id 44〜53、changed_at 2026-10-05 03:23:18Z）。
  - (d) 追加したキーワード行: 検索 id 14187〜14196（各残す側の position の次、398 は position 2）、除外 id 1310〜1312（398 の position 0〜2）。
- rollback.sql は実行していない（新しい PO の判断が必要）。
