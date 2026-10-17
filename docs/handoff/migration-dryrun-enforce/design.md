# design: 全件試し実行を「失敗したらマージを止める」に切り替える

- 状態: 設計（Opus）。PO「y」（2026-10-17 チャット「この切り替えの設計から始めてよいですか」）。マージは PO の GO #番号 待ち（scripts/ を含むため）。
- 対象ADR: ADR-1007（決定5 :52-54「理由なく外している分を外さない」、段4 :99「全体の試し流しの対象の修正」）、ADR-1005（:27 段階0 安全網）
- recon: docs/handoff/migration-dryrun-enforce/recon.md
- 前便: docs/handoff/migration-dryrun-baseline/design.md（#4466。失敗21→0。:50 で強制化を別便と記載）

## 目的
新しく追加する migration が、空の DB から作り直すと壊れる書き方になっていたら、マージ前に止める。今は失敗しても「成功」のままマージできてしまう（recon: report.py:89 が常に 0 を返し、migration-test.yml:1818 が continue-on-error）。

## 変更前後（実装はこの3ファイル＋文言だけ）
| # | ファイル:行 | 変更前 | 変更後 |
|---|---|---|---|
| 1 | scripts/migration-dryrun-report.py:89 | `return 0  # 報告のみ` | `return 1 if any_failed else 0`。`any_failed` は run_report の先頭で False にし、各周で `failed` が空でなければ True にする（:79 の後） |
| 2 | 同 :2 docstring 1行目 | `…を決め、報告する。強制はしない。` | `…を決め、流す。1本でも落ちたら終了コード 1。` |
| 3 | 同 :8 | `…終了コードは常に 0（報告のみ）。` | `…1周でも失敗があれば終了コード 1（ADR-1007 決定5。強制）。` |
| 4 | 同 :68 print / :69 summary 見出し | `全件ドライラン（報告のみ）` / `### 全件ドライラン（報告のみ・強制しない）` | `全件ドライラン` / `### 全件ドライラン（失敗したら止める）` |
| 5 | .github/workflows/migration-test.yml:1813 step 名 | `全件ドライラン（報告のみ・強制しない）：登録された全ファイル − 除外一覧` | `全件ドライラン（失敗したら止める）：登録された全ファイル − 除外一覧` |
| 6 | 同 :1814-1817 コメント | 「落ちても job は失敗させない（強制への切り替えは…別の PR で行う）」 | 「1本でも落ちたら job を失敗させ、集約 migration-test 経由でマージを止める（#4466 で失敗0本を確認してから切替）。空の DB で通らないことが実測で分かったファイルだけ、dryrun-exclusions.tsv に実測の ERROR を理由に書いて外す。」 |
| 7 | 同 :1818 | `continue-on-error: true` | 行を削除 |
| 8 | scripts/migration-guard/dryrun-exclusions.tsv:2-3 コメント | 「…結果を報告する（強制はしない。強制への切り替えは、報告を見てから別の PR で行う）。」 | 「…流し、1本でも落ちたらマージを止める。ここに足すときは、見込みでなく実測の ERROR を reason に書く。」 |
| 9 | scripts/tests/test_migration_value_writes.py:240-250 | `test_run_reports_failures_but_exits_zero`（失敗ありで 0 を期待） | `test_run_exits_nonzero_when_a_file_fails` に改名し、`assertEqual(result.returncode, 1, …)` にする。表示の assert（:247-250）はそのまま |
| 10 | 同（追加） | なし | `test_run_exits_zero_when_all_pass`: fake psql が常に `exit 0` のとき returncode 0、「1周目: 成功 2 / 失敗 0」 |

触らない: 集約 job（:1829-1851）・paths-filter・Ruleset・既存の1周目/2周目 step（:1744-1811）・除外一覧のデータ行・migrations/・deploy.yml・本番。
直さない: main の時点で既に落ちている `test_protected_tables_include_the_four_added_masters`（28 != 27）。この便の範囲外として記録だけ残す。

## 代替案
- A（採用）: report.py の終了コードと、step の continue-on-error の両方を変える。集約と Ruleset はそのまま使う。
- B: continue-on-error だけ外す → report.py が 0 を返すので止まらない（recon の実測）。不採用。
- C: Ruleset に migration-full-dryrun を必須で足す → Ruleset の変更は不可逆操作リストに入っており、集約経由で既に効くので不要。不採用。

## 影響範囲
- migration 関係のファイルを触る PR だけ（paths-filter）。#4466 マージ後に main を取り込んで動いた2 run は、どちらも失敗0本（recon）。ただし #4466 より前に分岐し、まだ main を取り込んでいないブランチは、旧除外一覧のままでは失敗する。pull_request の run は main とのマージ結果で動くため、tsv と report.py は main 側の新しいものが使われる。
- 所要時間は変わらない（流す本数は同じ。60〜78秒）。

## リスクと対処
| リスク | 対処 |
|---|---|
| 空の DB でだけ落ちる正当な migration で、PR が止まる | 実測の ERROR を理由に dryrun-exclusions.tsv へ1行足す（tsv の規則コメントに明記）。これは止まって気付くための仕組み |
| 1周目は通り、2周目（冪等性）だけ落ちる | 2周目の失敗も any_failed に入れて止める。冪等でない migration は止めるべき対象 |
| 切り替えが原因で他の PR が一斉に止まる | マージ直前に、main 基準の直近 run が 0/0 であることを確かめる（受入条件 K1） |

## 受入条件
|基準|検証方法|
|---|---|
|K1 この PR の CI で、全件ドライランの集計が「1周目 失敗 0」「2周目 失敗 0」で、step・job・集約が success|最終 HEAD の Migration SQL Test の run ログと `gh pr checks`|
|K2 1本でも落ちたら終了コード 1|ローカルで `python3 scripts/migration-dryrun-report.py run --db x --rounds 1 --psql false` を実行し、exit=1 になること（変更前は 0。recon の local_false.txt）|
|K3 全部通れば終了コード 0|`--psql true` で exit=0|
|K4 試験: 改名した試験と追加した試験が通る。失敗するのは既知の1件（28 != 27）だけ|`python3 scripts/tests/test_migration_value_writes.py` で失敗が1件、その名前が test_protected_tables_include_the_four_added_masters であること|
|K5 continue-on-error が全件ドライランの step から消えた|`grep -n "continue-on-error" .github/workflows/migration-test.yml` に :1818 相当の行が無い|
|K6 本番に影響しない|`git diff origin/main...HEAD --name-only` に migrations/・deploy.yml・run_all_migrations.sh が無い|

## 戻し方
この PR を revert する。報告のみに戻り、本番には何も入らない。

## 残り（別便）
- scripts/tests/test_migration_value_writes.py を CI で動かす（今はどの workflow からも呼ばれていない）。既知の失敗（28 != 27）を先に直す必要がある。
- 除外一覧の残り27行を、同じ方法で実測して戻せるか確かめる。
- 20260919_030000 の DO は、表がビューになると ALTER を飛ばす件（前便の残り）。

## 維持の仕組み
守り手: migration を追加・変更する PR の審査役（Opus）。仕組み: 集約 job「マイグレーションSQL 実行テスト（実DB）」が Ruleset の必須チェックなので、全件ドライランが落ちるとマージできない。除外を足すときは、見込みでなく実測の ERROR を reason に書く（tsv:2-3 の規則）。

## 外部・過去事例の参照と我々への応用
- 前便 #4466（docs/handoff/migration-dryrun-baseline/design.md）: 見込みだけの除外が後続を連鎖して落としていた。実測で0本にしてから強制に切り替える順番は、この前便の結果に基づく。
- ADR-1005 :19: 全件ドライランが多くを対象外にしていたため、障害が本番で初めて見つかった。今回の強制化は、同じことを繰り返さないための関所になる。
- 外部事例は使わない（理由: 当リポジトリの集約 job と Ruleset の構成に固有の変更で、CI の実測が直接の根拠になるため）。

## 設計審査（Opus 自己審査・独立した第二者レビューではない）
- 判定: APPROVE
- 根拠: 止める経路（集約 job → Ruleset の必須チェック）を実物で確かめた（migration-test.yml:1831,:1845、Ruleset 15777895）。変える2か所は実測で特定した（--psql false でも exit 0）。受入条件 K1〜K6 は、すべてコマンドで○×を判定できる。
- 未解決: なし。既知の試験失敗1件は範囲外として記録した。
