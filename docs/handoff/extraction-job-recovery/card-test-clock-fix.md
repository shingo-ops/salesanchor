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
2. 作業フォルダを正式な手順で作る（`frontend/.husky/pre-commit` は `$HOME/worktrees/` の外の commit を止める。2026-11-13 の1回目の実行はここで止まった）。(a) `git fetch origin`。`git branch --list release/test-clock-fix` が空であることを記録する（空でなければ **停止**）。(b) `bash scripts/new-worktree.sh release/test-clock-fix`（`--claude` は付けない）の出力を記録する。(c) 以後の Bash はすべて `cd $HOME/worktrees/salesanchor/release-test-clock-fix && ` で始め、Edit/Write はこのフォルダの下の絶対パスで書く（Bash の今いる場所は呼び出しごとに元へ戻るため）。(d) そのフォルダで `git merge --no-edit origin/release/test-clock-fix`（設計の文書を本線の上に合わせる。force でも reset でもない）。ぶつかりが出たら **停止**。(e) `git log -1 --format=%H`、`git rev-parse HEAD^2`（`origin/release/test-clock-fix` の先頭と同じが期待）、`git diff --stat origin/main HEAD`（docs/handoff/extraction-job-recovery の4ファイルだけが期待）を記録する。
3. `git diff --stat c296af3bb origin/main -- backend/tests/test_tcg_extraction_recovery_pg.py backend/tests/test_viewer_api.py backend/tests/test_line_import_devices.py` を記録する。1行でも出たら **停止**（土台がずれたため。Opus が設計を直す）。
4. design.md の「変更前後」のとおりに、Edit/Write ツールで4ファイルを書く（3ファイルの直しと `backend/tests/test_no_import_time_clock.py` の新規）。行番号は目安で、必ず前後の文の一致で場所を決める。新規ファイルの中身は design.md のコードの塊を一字一句そのまま写す。
5. `grep -n "_NOW" backend/tests/test_tcg_extraction_recovery_pg.py` の出力（0件が期待）と、`grep -n "now()" backend/tests/test_line_import_devices.py` の出力（2行が期待: 関数 `row` の本体の既存の1行と、新しい試験の1行）を記録する。
6. 先に Python 3.12 の専用の環境を作って依存を入れる（クラウドの見張り py312-guard は 3.12 以外の環境作りと、環境の外の `pip install` を止める。`scripts/agent-hooks/cloud/python_version_guard.py`）。(a) `command -v uv python3.12` を記録する。(b) uv があれば `uv venv --python 3.12 /tmp/v312` のあと `cd backend && uv pip install --python /tmp/v312/bin/python -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`（CI と同じ一覧。`.github/workflows/test.yml` は backend で `uv pip install --system -r requirements.txt -r requirements-dev.txt`）。uv が無く python3.12 があれば `python3.12 -m venv /tmp/v312` のあと `cd backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`。出力の最後の20行と `exit=` を記録する。(c) `/tmp/v312/bin/python -m pytest backend/tests/test_no_import_time_clock.py backend/tests/test_line_import_devices.py backend/tests/test_viewer_api.py -p no:cacheprovider -o addopts="" -q` の出力を全文記録する。(d) どちらも無い・依存が入らない・pytest が動かないときは、その出力を記録し、`python3 -I` で `test_no_import_time_clock.py` の2つの関数だけを呼ぶ形でも確かめて記録する。どの場合も停止しない（記録して続ける）。環境を作り直す別の書き方は試さない。
7. T5: `test_tcg_extraction_recovery_pg.py` の import 群の直後に一時的に `_NOW = datetime.now(timezone.utc)` を1行足し、手順6で pytest が動いた環境なら `/tmp/v312/bin/python -m pytest backend/tests/test_no_import_time_clock.py -p no:cacheprovider -o addopts="" -q`、動かなかったなら手順6(d) と同じ `python3 -I` の形で、赤になりファイル名と行番号が出ることを記録する。そのあと Edit でその1行を消し、`git diff --stat` を記録する（4ファイルだけが期待）。
8. `git add backend/tests` のあと `git diff --cached --stat` と `git diff --cached` の全文を記録する（手順2(d) の合わせの後なので、比べる相手は HEAD）。消された行が design.md の対象行だけであることを自分で照らし、照らした結果を書く。
9. commit（文の最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `test: read DB clock per test and guard import-time clock reads`。
10. `git push -u origin release/test-clock-fix`（force は禁止。手順2(d) の合わせで今の先頭の子孫になっているので、早送りで通るのが期待）。push の出力の全文（pre-push の「オーナーシップチェック」の行を含む）を記録する。
11. PR は作らない。マージしない。

## 停止
- 止めるのは手順2(a)(d)、手順3の食い違い、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- クラウド既定の停止時の見張りが「未保存の変更を commit して push せよ」と促すことがある（`new-worktree.sh` が作る台帳の登録ファイルが理由。`docs/handoff/cloud-parity/recon.md` 試行2）。その登録ファイルは commit しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 完了報告の本文に、手順2〜10の生出力を全文含める（要約しない）。
- 最後の1行は `DONE` か `BLOCKED: <理由>`（終端合図）。
