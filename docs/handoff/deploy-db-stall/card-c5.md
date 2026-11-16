---
mode: handoff
---
# 実装カード：毎週の数えを定時の遅れ・抜けに強くする（deploy-db-stall 段7 (c) の直し 第3.6版・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（定時の実行の週の決め方と拾い直し、その試験だけ） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/deploy-lock-count-late-run`） | ○ |
| 6 | 書式は実例で示す（動きは design.md §19-19-3 にそのまま） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順5〜7） |
| 8 | 件数と名前を対で出す | ○（手順5） |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は前後の文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write/Edit で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/deploy-db-stall/design.md` §19-19（第3.6版。このブランチにある）。§19-19 を全部と、§19-4・§19-8 を読んでから作る。設計とこのカードが食い違ったら設計を正とし、記録して続ける。設計に無い変更はしない。
- 今の試験（D1〜D8）は全部合格している。今回はそれを壊さずに足す。
- PO 承認: 2026-11-17「1」（遅れはそのままにして、数えが狂わないようにする）。実装の承認は、このカードを渡す前に PO から別にもらう。
- 触るのは次の3ファイルだけ: 新規 scripts/ops/weekly-deploy-lock-plan.sh、`.github/workflows/weekly-deploy-lock-count.yml`、`backend/tests/ops/test_deploy_lock_count.py`。数えの台本 `scripts/ops/count-deploy-lock-failures.sh` と `.github/workflows/test.yml` は触らない（test.yml の filters は `scripts/**` を含むので足さなくてよい）。

## 作りの決め（Opus が決めた。この形で作る）
- plan の台本（新規 scripts/ops/weekly-deploy-lock-plan.sh、`#!/usr/bin/env bash`、実行権を付ける）:
  - 引数: `--now <UNIX秒>`（省略時は今）、`--runs-file <PATH>`（省略時は API を呼ぶ）、`--run-id <ID>`（省略時は環境変数 `GITHUB_RUN_ID`）。知らない引数は終わり1。
  - 週: `TZ=Asia/Tokyo` で `--now` の日付と曜日（`date +%u`、月曜=1）を出し、`until` = その日付から（曜日−1）日前、`since` = `until` の7日前。日付の計算は数えの台本と同じく GNU date（`date -u -d "<日付> -N days" +%F`）。
  - 数え済み: `--runs-file` が無ければ `gh api "repos/${GITHUB_REPOSITORY:-shingo-ops/salesanchor}/actions/workflows/weekly-deploy-lock-count.yml/runs?event=schedule&status=success&per_page=100&created=>=<until の 00:00 JST を UTC にした ISO 時刻、例 2026-11-15T15:00:00Z>"` を1回呼ぶ（`api_calls=1`。`>=` は `%3E%3D` と書く）。`--runs-file` があれば読むだけ（`api_calls=0`）。JSON の `.workflow_runs[]` を、台本の側でも jq で `select(.created_at >= "<上と同じ UTC の時刻>")` に絞り（GitHub 側の絞り込みが効かなくても前の週の run で飛ばさないため）、その `id` から `--run-id` と同じものを除き、1件でもあれば `decision=skip`、無ければ `decision=count`。呼び出しの失敗・ファイルが無い・jq で読めないときは `decision=count` と、`reason=` に短い理由（例 `runs lookup failed`）。
  - `late`: 曜日が1なら `late=0`、それ以外は `late=1`。
  - 出力: 標準出力に `since=`・`until=`・`decision=`・`late=`・`reason=`・`api_calls=` の6行をこの順で出す（reason は空でもよい）。終わりは0（引数の誤りだけ1）。
- workflow（`.github/workflows/weekly-deploy-lock-count.yml`）:
  - `on.schedule` を `- cron: '0 1 * * 1'` と `- cron: '17 3 * * 2'` の2本にする（2本目の注釈: 火曜 12:17 JST。月曜の回が来なかったときの拾い直し）。
  - 一番上の段に `concurrency:` を足す（`group: weekly-deploy-lock-count`、`cancel-in-progress: false`）。
  - run の段の env に `EVENT_NAME: ${{ github.event_name }}` を足す。
  - run の段の初めで、`EVENT_NAME` が `schedule` のときは `bash scripts/ops/weekly-deploy-lock-plan.sh > "${RUNNER_TEMP}/plan.txt"` を流し、中身を `cat` で記録に出し、`since`・`until`・`decision`・`late` を読み取る。`decision=skip` なら `echo "この週（<since>〜<until>）は数え済みのため数えません"` を出して `exit 0`（数えの台本も Discord も流さない）。`decision=count` なら `RANGE_ARGS=(--since "<since>" --until "<until>")`。
  - `schedule` でないとき（手動）は今の分け方のまま（入力が両方あれば since・until、両方空なら `--days 7`、片方だけなら `exit 1`）。
  - 知らせ: `late=1` のとき、先頭の行を `月曜のうちに定時の実行が来なかったため、<TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M'> JST に数えました（<since>〜<until>）` にする。通知ファイルがあればその前に付けて送る。通知ファイルが無い（対象0）ときも、その1行に `本番反映の止まり 0 件` を続けて送る。`late=0` のときは今のまま（ファイルがあるときだけ送る）。送信の失敗は今と同じく `exit 1`。
  - 数えの台本の終わりが0でなければ job を失敗にする作りは今のまま残す。権限（`actions: read`・`contents: read`）は変えない。
- 試験（`backend/tests/ops/test_deploy_lock_count.py`）:
  - D4 の `test_d4_workflow_shape` を直す: cron が2本（`0 1 * * 1` と `17 3 * * 2`）、`concurrency` の group と `cancel-in-progress` が false、run に `weekly-deploy-lock-plan.sh` があり `count-deploy-lock-failures.sh` より前、`decision=skip` の分かれと `exit 0`、`late` の分かれと「月曜のうちに定時の実行が来なかった」の文、今の assert（`--days 7`・`set +e`・`COUNT_RC`・片方だけの失敗・`exit 1` が3つ以上）を残す。
  - D9 を足す（plan の台本を subprocess で流す。`--now` と `--runs-file` を使い、GitHub を呼ばない）:
    - `test_d9_week_is_previous_monday`: 月曜 2026-11-16 00:00 JST・月曜 23:59 JST・火曜 2026-11-17 12:17 JST・日曜 2026-11-22 23:59 JST の4つで `since=2026-11-09`・`until=2026-11-16`。日曜 2026-11-15 23:59 JST で `since=2026-11-02`・`until=2026-11-09`。
    - `test_d9_skip_when_other_success_run_exists`: (i) 自分以外の id が1件 → `skip`、(ii) 自分の id だけ → `count`、(iii) 0件 → `count`、(v) 自分以外の success の run が until より前（例 `2026-11-09T07:30:01Z`）に作られたものだけ → `count`。
    - `test_d9_lookup_failure_counts`: 無い PATH → `count` で `reason=` が空でない。
    - `test_d9_late_flag`: 月曜 `late=0`、火曜・日曜 `late=1`。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 毎週の数えを定時の遅れ・抜けに強くする（段7 (c) 第3.6版）の実行結果である」と書く。
2. 作業場所: `git fetch origin` のあと、`git checkout -B release/deploy-lock-count-late-run origin/release/deploy-lock-count-late-run` を流し、`git log -1 --format=%H` を記録する（ぶつかりや失敗が出たら **停止**）。
3. 手元にあれば `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（クラウドで落ちる項目は記録して続ける）。
4. design.md §19-19 を Read し、上の「作りの決め」のとおり3ファイルを Write／Edit で作る・直す。
5. Python 3.12 があればそれで、無ければ使える python3 で（版を記録する）`python -m pytest backend/tests/ops/test_deploy_lock_count.py -p no:cacheprovider -o addopts="" -q` の全文を記録する。試験の名前と結果を1行ずつ並べる（今の件数に D9 の4件を足した数が期待。今の件数も記録する）。赤があれば直す。直しても赤なら記録して続ける。
6. `bash -n scripts/ops/weekly-deploy-lock-plan.sh` と、使えれば `shellcheck scripts/ops/weekly-deploy-lock-plan.sh` の出力を記録する。
7. 赤の実演（K19-14）: 削除の命令を使わず、新しいフォルダ `/tmp/red/8`・`/tmp/red/9`・`/tmp/red/10` に plan の台本と試験を写す。8 は写しの台本で「（曜日−1）日前に戻す」計算を消し（`until` を今日のままにする）、`test_d9_week_is_previous_monday` が赤になることを記録する。9 は写しの台本で自分の run を除く処理を消し、`test_d9_skip_when_other_success_run_exists` が赤になることを記録する。10 は `/tmp/red/10` に写した台本で `created_at` の絞り込みを消し、同じ試験の (v) が赤になることを記録する（壊した行の差分・赤になった試験の名前・期待どおりか ○×）。作業場所の台本は壊さない。最後に `git status --short` を記録する。
8. `git add` を上の3ファイルだけに流し、`git diff --cached --stat` を記録する。
9. commit（文は Write で `/tmp/impl/commit-msg.txt` に書いて `git commit -F /tmp/impl/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `fix(ops): anchor the weekly lock count to Monday and re-run on Tuesday when Monday's schedule is missed`。
10. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/deploy-lock-count-late-run`（force は禁止）。push の出力の全文を記録する。
11. PR は作らない。マージしない。workflow を手で流さない。

## 停止
- 止めるのは手順2の失敗、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- Bash に psql の語を書かない。git は1命令ずつ流す。sleep しない。削除の命令（rm）を使わない。
- 台帳の登録ファイルは commit しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 手順2〜10の生出力の全文を `/tmp/impl/手順番号.txt` に保存する（commit しない）。
- 手順ごとの結果は別々の Bash 呼び出しで echo 1つだけ・300字まで・先頭に「手順N:」を付けて出す。
- 最後の1行は `DONE` か `BLOCKED: 理由の1行`（終端合図）。

END OF CARD
