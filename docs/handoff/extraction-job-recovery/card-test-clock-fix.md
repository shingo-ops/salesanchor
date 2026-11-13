---
mode: handoff
---
# 実装カード：試験の時刻ずれ直し（便1・ADR-1015 B-3）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る・ready で起票） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（試験3ファイルの直しと見張り1ファイルの追加だけ） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/test-clock-fix`） | ○ |
| 6 | 書式は実例で示す（変更前後は design.md にそのまま） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順5〜8） |
| 8 | 件数と名前を対で出す | ○（手順5・7） |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は前後の文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write/Edit で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/extraction-job-recovery/design.md` の「追記（2026-11-13）」節。変更前後はその「変更前後（実装役はこのとおりに書く）」に全部ある。設計に無い変更はしない。
- 設計審査: `review-opus.md`。区分 B-3 で PO 承認は不要（B）。PO はマージ・本番反映まで任せると指示済み（2026-11-13 チャット）。審査2 APPROVE のあと Opus がこのカードを渡す。
- 土台: c296af3bb。2026-11-13 に、c296af3bb と origin/main e930f1b24 の間で backend/tests の変更は `test_single_set_rejudge_tool.py` の1ファイルだけ（対象の3ファイルは変更 0）であることを Opus が確かめた。e930f1b24 の backend/tests に設計の見張りを当てても4か所ちょうど。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 試験の時刻ずれ直し（便1）の実行結果である」と書く。
2. `git fetch origin` のあと `git switch -C release/test-clock-fix origin/release/test-clock-fix`。`git log -1 --format=%H` を記録する（設計の HEAD 以降であること。違えば記録して続ける）。
3. `git diff --stat c296af3bb origin/main -- backend/tests/test_tcg_extraction_recovery_pg.py backend/tests/test_viewer_api.py backend/tests/test_line_import_devices.py` を記録する。1行でも出たら **停止**（土台がずれたため。Opus が設計を直す）。
4. design.md の「変更前後」のとおりに、Edit/Write ツールで4ファイルを書く（3ファイルの直しと `backend/tests/test_no_import_time_clock.py` の新規）。行番号は目安で、必ず前後の文の一致で場所を決める。新規ファイルの中身は design.md のコードの塊を一字一句そのまま写す。
5. `grep -n "_NOW" backend/tests/test_tcg_extraction_recovery_pg.py` の出力（0件が期待）と、`grep -n "now()" backend/tests/test_line_import_devices.py` の出力（新しい試験の1行だけが期待）を記録する。
6. 先に依存を入れる: `cd backend && python3 -m pip install -q -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`（CI と同じ一覧。`.github/workflows/test.yml` は backend で `uv pip install --system -r requirements.txt -r requirements-dev.txt`）。出力の最後の20行と `exit=` を記録する。失敗しても停止しない。続けて `python3 -m pytest backend/tests/test_no_import_time_clock.py backend/tests/test_line_import_devices.py backend/tests/test_viewer_api.py -p no:cacheprovider -o addopts="" -q` の出力を全文記録する。依存が無くて動かないときは、その出力を記録し、`python3 -I` で `test_no_import_time_clock.py` の2つの関数だけを呼ぶ形でも確かめて記録する。赤でも停止しない（記録して続ける）。
7. T5: `test_tcg_extraction_recovery_pg.py` の import 群の直後に一時的に `_NOW = datetime.now(timezone.utc)` を1行足し、`python3 -m pytest backend/tests/test_no_import_time_clock.py -p no:cacheprovider -o addopts="" -q` が赤になり、ファイル名と行番号が出ることを記録する。そのあと Edit でその1行を消し、`git diff --stat` を記録する（4ファイルだけが期待）。
8. `git diff origin/release/test-clock-fix --stat` と `git diff origin/release/test-clock-fix` の全文を記録する。消された行が design.md の対象行だけであることを自分で照らし、照らした結果を書く。
9. commit（文の最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `test: read DB clock per test and guard import-time clock reads`。
10. `git push origin release/test-clock-fix`（force は禁止）。push の出力を記録する。
11. PR は作らない。マージしない。

## 停止
- 止めるのは手順3の食い違い、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 完了報告の本文に、手順2〜10の生出力を全文含める（要約しない）。
- 最後の1行は `DONE` か `BLOCKED: <理由>`（終端合図）。
