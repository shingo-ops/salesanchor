---
mode: handoff
---
# 実装カード：本番反映の止まりを毎週数える（deploy-db-stall 段7 (c)・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（毎週の数えの台本・workflow・試験と、test.yml の2行だけ） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/deploy-lock-count`） | ○ |
| 6 | 書式は実例で示す（動きは design.md §19-4 にそのまま） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順8〜11） |
| 8 | 件数と名前を対で出す | ○（手順8・10） |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は前後の文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write/Edit で書く・PR を作らない・止められたら言い換えない | ○ |

## 読んだ節（guards/ の照合）
| guards の文書 | 引いた止まる形 | このカードでの扱い | 結果 |
|---|---|---|---|
| guards/00-common.md | 共通の止まる形 | sleep させない・git は1命令ずつ・言い換えない | ○ |
| guards/03-file.md | 散文で本文を頼むと止まる・山かっこの空欄で止まる | 中身は設計 §19-4 に全部ある。山かっこの空欄は置かない | ○ |
| guards/04-worktree.md | worktree の外の commit は止まる | 手順2で new-worktree.sh で作り、そこで作業する | ○ |
| guards/09-gh.md | `gh run view` 等は既定拒否 | 実行役に gh を流させない（台本の中の `gh api` は試験では流れない） | ○ |
| guards/10-executor.md | 受領確認・終端合図 | 手順1と報告の最後の1行 | ○ |
| guards/12-guard-authoring.md | 見張り・カード点検・点検器の作り方 | 今回の4ファイルは見張りでないので対象外（PR の guard-authoring/evaluation で確かめる） | ○ |

## 前提
- 設計: `docs/handoff/deploy-db-stall/design.md` §19 第3.2版（main に合流済み）。作る中身は §19-4 の「変更するファイル」「台本の動き 1.〜10.」「試験 D1〜D5・赤の実演」に全部ある。§19-1・§19-4・§19-7・§19-8・§19-12 を全部読んでから作る。設計とこのカードが食い違ったら設計を正とし、記録して続ける（手順の中で止めない）。設計に無い変更はしない。
- 設計審査: クラウドの Architect（opus）第3版 APPROVE、マージ前審査（opus）第3.2版 APPROVE（§19-14）。
- PO 承認: 2026-11-13「1」（3つの直しをまとめて設計し、作って試すのは1つずつ）と、同日の「PRマージ、デプロイまで完走させてくれ」。
- 本番のサーバー・DB・`.github/workflows/deploy.yml` には触らない。触るのは下の4ファイルだけ:
  - 新規 `scripts/ops/count-deploy-lock-failures.sh`
  - 新規 `.github/workflows/weekly-deploy-lock-count.yml`
  - 新規 `backend/tests/ops/test_deploy_lock_count.py`
  - 変更 `.github/workflows/test.yml`（push の paths と detect-changes の filters に1行ずつ）

## 設計で書き切っていない作りの決め（Opus が決めた。この形で作る）
- 台本は bash。JSON は `jq` で読む。API は `gh api` で呼ぶ（鍵は環境変数 `GH_TOKEN`。前例 `.github/workflows/weekly-stale-pr.yml` と同じ）。相手のリポジトリは環境変数 `GITHUB_REPOSITORY`、無ければ `shingo-ops/salesanchor`。
- 一覧はページを送って引く: `gh api "repos/${REPO}/actions/workflows/deploy.yml/runs?created=${D}..${D}&per_page=100&page=${P}"`。`workflow_runs` が100件未満になったら止める。1回の `gh api` ごとに呼び出しの数を1つ足す。
- 回: `gh api repos/${REPO}/actions/runs/${ID}/attempts/${N}`、job: `gh api "repos/${REPO}/actions/runs/${ID}/attempts/${N}/jobs?per_page=100"`、記録: `gh api repos/${REPO}/actions/jobs/${JOB}/logs`。
- `--from-dir` の形は §19-4 の 1. のとおり（API の返事をそのままファイルに置く。ファイルが無ければ「引けなかった」）。
- 知らせの本文は台本が作る。引数 `--notify-file PATH` を足す。知らせの対象（上限失敗・その他の失敗・STOP停止・その他の停止・読めなかった の合計）が0でないときだけ、その本文を PATH に書く。0なら PATH を作らない。本文は日本語で、合計・分けごとの数・run id（最大10件、それより多ければ「ほか N 件」）・数えた期間を入れ、1,900字以内にする。一覧の日が引けなかった（API の失敗・1,000件に達した）ときは、その日付も本文に入れる。
- workflow の手順は1つの step で次の順にする: 台本を `--notify-file` 付きで流して終わりの数を取る（`set +e` で受ける）→ PATH があれば `bash scripts/notify/discord-owner-ping.sh "$(cat PATH)"` を流し、失敗なら job を失敗にする → 台本の終わりが0でなければ job を失敗にする。`$GITHUB_STEP_SUMMARY` への書き込みは台本がする（環境変数があるときだけ）。
- workflow の入力 since・until が空なら `--days 7`。片方だけなら job を失敗にする（黙って片方を無視しない）。
- workflow の `on.schedule` は `cron: '0 1 * * 1'`（毎週月曜 01:00 UTC＝10:00 JST）。`permissions` は `actions: read` と `contents: read` だけ。
- 試験は `subprocess` で `bash scripts/ops/count-deploy-lock-failures.sh --from-dir <tmp_path>` を流す（`backend/tests/ops/test_deploy_precheck_wiring.py` と同じ書き方）。作り物の JSON とログは試験の中で `tmp_path` に作る。`jq` が無い環境では試験を skip にせず失敗にする（CI の ubuntu-latest には jq がある）。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 本番反映の止まりを毎週数える（段7 (c)）の実行結果である」と書く。
2. 作業フォルダを正式な手順で作る（`frontend/.husky/pre-commit` は `$HOME/worktrees/` の外の commit を止める）。
   (a) `git fetch origin`。`git branch --list release/deploy-lock-count` が空であることを記録する（空でなければ **停止**）。
   (b) `bash scripts/new-worktree.sh release/deploy-lock-count`（`--claude` は付けない）の出力を記録する。
   (c) 以後の Bash はすべて `cd $HOME/worktrees/salesanchor/release-deploy-lock-count && ` で始め、Edit/Write はこのフォルダの下の絶対パスで書く。
   (d) そのフォルダで `git merge --no-edit origin/release/deploy-lock-count`（このカードと設計の直しを取り込む。force でも reset でもない）。ぶつかりが出たら **停止**。
   (e) `git log -1 --format=%H`、`git diff --stat origin/main HEAD` を記録する（`docs/handoff/deploy-db-stall/card-c.md` と `docs/handoff/deploy-db-stall/design.md` の2つだけが期待。台帳の登録ファイルはこのブランチに commit していない）。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する。落ちたら記録して続ける。
4. design.md §19 を Read で全部読む。§19-4 が引く行（`scripts/run_all_migrations.sh` :57〜:68・:95〜:134、`scripts/deploy-db-precheck.sh` :177〜:207、`scripts/notify/discord-owner-ping.sh` :45・:61〜:63、`.github/workflows/test.yml` :20〜:29・:45〜:54、`.github/workflows/weekly-stale-pr.yml` :19）を Read し、書かれた中身と合うかを ○× で記録する。合わなくても続ける（場所は前後の文の一致で決める）。
5. `command -v bash jq gh python3` と `jq --version`・`grep --version | head -1` を記録する。
6. Write/Edit で4ファイルを作る（上の「作りの決め」と §19-4 のとおり）。
   - 台本の頭の説明に、§19-4 の 2. の限界（作ってから7日より後のやり直しは数えない）と、`grep -a` で行を取り出してから数える理由（§19-4 の 4.）を書く。
   - 数えに `grep -c`・`grep -q` を使わない。決まった文字は `grep -aF`、`grep -aE` は `lock conflict; retry [0-9]` の1つだけ。
   - 行の頭の時刻（最初の空白までの1語とその後の空白1つ）を外してから読む。
   - 出力に `fetched dates: ` の行・1行1回の表・合計・API の呼び出し回数を出す（§19-4 の 1.・6.）。
7. Python 3.12 の専用の環境を作る（クラウドの見張り py312-guard は 3.12 以外の環境作りと、環境の外の `pip install` を止める）。
   (a) `command -v uv python3.12` を記録する。
   (b) uv があれば `uv venv --python 3.12 /tmp/v312` のあと `cd backend && uv pip install --python /tmp/v312/bin/python -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`。uv が無く python3.12 があれば `python3.12 -m venv /tmp/v312` のあと `cd backend && /tmp/v312/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt; echo "exit=$?"; cd ..`。出力の最後の20行と `exit=` を記録する。
   (c) どちらも無い・依存が入らないときは、その出力を記録して続ける。環境を作り直す別の書き方は試さない。
8. 試験を流す: `/tmp/v312/bin/python -m pytest backend/tests/ops/test_deploy_lock_count.py -p no:cacheprovider -o addopts="" -q` の出力を全文記録する。D1・D1b・D1c・D2・D3・D4・D5 の試験の名前と結果を1行ずつ並べる（件数と名前を対で）。赤があれば直す。直しても赤なら記録して続ける。
9. `bash -n scripts/ops/count-deploy-lock-failures.sh` と、使えれば `shellcheck scripts/ops/count-deploy-lock-failures.sh` の出力を記録する。
10. 赤の実演（K19-3・§19-4 の6つ）: push しない一時の写し（`/tmp/red/` に台本と試験を写す）で、1つずつ台本を壊して試験を流し、赤になった試験の名前を記録する。壊し方は §19-4 のとおり:
    (1) `-a` を外す → D1 が赤
    (2) 読めなかった回を0にする → D3 が赤
    (3) 握り手を失敗の回だけから取る → D2 が赤
    (4) 頭の時刻を外す処理を消す → D2 が赤
    (5) `[precheck] STOP:` を `-F` なしで探す → D1 が赤
    (6) 回を run を作った時刻で週に入れる → D1b が赤
    6つそれぞれに「壊した行の差分・赤になった試験の名前・期待どおりか ○×」を書く。期待と違っても記録して続ける。作業フォルダの台本は壊さない。最後に `git -C $HOME/worktrees/salesanchor/release-deploy-lock-count status --short` で、作業フォルダに壊した跡が無いことを記録する。
11. `git add scripts/ops/count-deploy-lock-failures.sh .github/workflows/weekly-deploy-lock-count.yml backend/tests/ops/test_deploy_lock_count.py .github/workflows/test.yml` のあと、`git diff --cached --stat` と `git diff --cached -- .github/workflows/test.yml` の全文を記録する。test.yml の変更が「足した2行だけ」であることを ○× で書く。台帳の登録ファイルは add しない。
12. commit（文は Write でファイルに書いて `git commit -F /tmp/impl/commit-msg.txt`（文は先に Write でそのパスに書く）。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `feat(ops): count deploy lock-wait failures weekly and notify Discord`。
13. `git log -1 --format=%H%n%s` を記録し、手順12の commit が出来ていることを確かめる。そのあと `git push -u origin release/deploy-lock-count`（force は禁止。手順2(d) の合わせで早送りになるのが期待）。push の出力の全文（pre-push の検査の行を含む）を記録する。
14. PR は作らない。マージしない。workflow を手で流さない（基準の数えは Opus がマージの後にする）。

## 停止
- 止めるのは手順2(a)(d)、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- Bash に psql の語を書かない。git は1命令ずつ流す。sleep しない。
- クラウド既定の停止時の見張りが「未保存の変更を commit して push せよ」と促すことがある（`new-worktree.sh` が作る台帳の登録ファイルが理由）。その登録ファイルは commit しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 手順2〜13の生出力の全文を `/tmp/impl/手順番号.txt` に保存する（commit しない）。
- 記録は1回の道具の出力が約400字で切れるため、手順ごとの結果は別々の Bash 呼び出しで echo 1つだけ・300字まで・先頭に「手順N:」を付けて出す。
- 最後の1行は `DONE` か `BLOCKED: 理由の1行`（終端合図）。

END OF CARD
