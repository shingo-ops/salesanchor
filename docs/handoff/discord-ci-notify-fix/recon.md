# recon: PR の自動の点検の知らせが一度も動いていない件

- 依頼: PO 2026-11-22「1」（動かない理由を調べて、直し方を設計する。直すときは改めて相談）
- 基準: origin/main 2560f963f（2026-11-22 時点）
- 生出力: `/tmp/CC報告ファイル/discord-channels/ci-notify/`（手元の Mac のみ）

## 1. 既存 ADR の検索

- `git grep -il "workflow_run\|check_suite" origin/main -- docs/adr` → `docs/adr/ADR-1051-prod-ui-black-box-check.md` の 1 件。`workflow_run` を使う前例（配備の後の画面点検）。
- `discord` を含む ADR は 30 件以上。PR の点検の知らせの起動の仕方を決めた ADR は無い。
- 届け先は `docs/handoff/discord-dev-notices/design.md`（PR #5676）で「🛠開発の知らせ」と決まっている。

## 2. 観測した事実

| # | 事実 | 根拠 |
|---|------|------|
| F1 | 知らせの仕組みは `check_suite` の `completed` だけで起動する | `.github/workflows/discord-ci-notify.yml:16-18` |
| F2 | この仕組みの実行の記録は今までに 0 回 | `gh api repos/shingo-ops/salesanchor/actions/workflows/discord-ci-notify.yml/runs` の total_count 0（PR #5676 の作業中に観測。`docs/handoff/discord-dev-notices/design.md` §8-2） |
| F3 | GitHub の公式文書: 「再帰を防ぐため、点検のまとまりが GitHub Actions で作られたときは、このイベントで仕組みは起動しない」 | docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows の check_suite の注記（Context7 `/websites/github_en_actions` で 2026-11-22 に確認） |
| F4 | PR #5676 の最後の版（76484d65c）の点検のまとまりは 30 個。28 個が github-actions、1 個が claude、1 個が google-cloud-build（後ろの 2 個は queued のまま） | `gh api repos/shingo-ops/salesanchor/commits/76484d65cc4bcab42cbea3e98cec04b2f5042786/check-suites`（`suites-76484.txt`） |
| F5 | 仕組みは 2026-05-28 に作られ、そのあと変更は送り口の分け直しの 1 回だけ | `git log origin/main -- .github/workflows/discord-ci-notify.yml`（440626bad、5e3ade28e） |
| F6 | リポジトリは公開 | `gh repo view --json visibility` → PUBLIC |
| F7 | PR の点検の実行の数（1 日）: 11/15 2314、11/16 2225、11/17 2500 以上、11/18 1314、11/19 1040、11/20 2500 以上、11/21 2500 以上 | `actions/runs?event=pull_request&created=<日>` の total_count（`pr-runs-days.txt`）。2500 はこの道の数えの上限で、実際はもっと多い可能性がある |
| F8 | 1 回の送り込みで動く点検の数は 28〜36 個が多い（11/21 の 34 回分） | `pr-runs-7d.txt` を head_sha ごとに数えた |
| F9 | PR の点検の失敗の数（1 日）: 11/15 17 回（15 版）、11/16 35（16）、11/17 51（34）、11/18 16（10）、11/19 16（10）、11/20 40（34）、11/21 18（15） | `actions/runs?event=pull_request&status=failure`（`pr-fail-days.txt`） |
| F10 | 11/21 に失敗した点検の内訳: Process Artifacts Gate 11、Backend Tests 5、Doc Index Reachability 1、API Contract Check 1 | `fail-names-1121.txt` |
| F11 | 公式文書: `workflow_run` は別の仕組みが終わったときに起動する。`workflows` の指定には `*` などの形を使える。起動されたほうは secret を使える | 同じ公式文書の workflow_run 節と workflow-syntax の節（Context7 で 2026-11-22 に確認） |
| F12 | 公式文書: `jobs.<id>.if` で外れたジョブは「skipped」になり、成功と同じ扱いになる | docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-jobs-with-conditions（Context7） |
| F13 | このリポジトリには `workflow_run` と、ジョブの `if` で結果を見る前例がある | `.github/workflows/prod-ui-check.yml:11-14`・`:33` |
| F14 | 知らせの文面は、PR の題名を環境変数と `jq --arg` で渡している（題名が命令として動く心配がない形） | `.github/workflows/discord-ci-notify.yml:102`・`:125-133` |
| F15 | 合流後の今の形（`.github/workflows/discord-ci-notify.yml:64`、`jq ... \| head -n 10`）は、失敗した点検が 300 件のとき終了コード 141（途中で切られた）で止まり、知らせが出ない。200 件までは止まらない。点検の一覧は 100 件までしか読まない（`:63` の `per_page=100`）。100 件の文字の量は 12580 バイト。jq の中で 10 件に切る形は 0〜5000 件すべて終了コード 0・10 行 | 手元（macOS）での試し 2026-11-22。`/tmp/CC報告ファイル/discord-channels/ci-notify/` には残さず、試しの台本は本文 §11 に書いた |
| F16 | 合流（2026-11-22 07:53:56）から 08:05:52 までに、知らせの仕組みは 135 回起動。133 回は外れて（skipped）終わり、2 回が動いた。外れた 10 件の見本では、ジョブの記録の 2 つの時刻の差は 0 秒が 6 件・1 秒が 3 件・8 秒が 1 件 | 手元の Mac の /tmp/CC報告ファイル/discord-channels/ci-notify/ の runs-since-merge.tsv（2026-11-22 に一覧を読み直して数えた）と k4-sample.txt |
| F17 | 動いた 2 回は PR #5683 の別々の版。版 b2d70be: 点検の失敗 07:57:23 → Discord の投稿 07:57:35（12 秒）。版 cc011c8: 失敗 08:01:07 → 投稿 08:02:57（1 分 50 秒）。cc011c8 は 08:12:51 にもう一度失敗したが 2 通目は無く、版の印は 1 件だけ | 手元の Mac の /tmp/CC報告ファイル/discord-channels/ci-notify/ の k1-discord.jsonl（Bot で読んだ投稿の時刻）・cc011c8-failed.json（08:12:51 の失敗）・run-44959366699.log・run-44959669845.log |

## 3. 原因（事実の組み合わせ）

F1・F3・F4 から、PR の点検のまとまりは GitHub Actions で作られています。そのため、`check_suite` では知らせの仕組みが起動しません。F2 の「0 回」とも合います。作ったとき（F5）から、この形では一度も動けなかった、という説明になります。

## 4. 未確認

- U1: ジョブの `if` で外れたとき、実行の場所（runner）を取らないか。公式文書に「skipped」になることは書いてある（F12）。runner を使わないことは、直す便の試しで、実行の記録の秒数を読んで確かめる。
- U2: `workflows: ["*"]` が、このリポジトリのすべての仕組みに当たるか。公式文書には形が使えるとだけ書いてある（F11）。直す便の試しで確かめる。
- U3: 1 日の点検の実行の数の本当の数（2500 を超えた日）。設計の判断には「1 日 1000 回より多い」で足りるので、これ以上は数えない。
