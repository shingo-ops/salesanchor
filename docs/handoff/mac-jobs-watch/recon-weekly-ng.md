# recon 追補: 入口の文書の週次点検の NG を Discord で知らせる（2026-11-05・origin/main a7c5713c4 基準）

## 既存 ADR 検索
- `git grep -n -i -E 'mac-jobs-watch|doc-entry-weekly' -- docs/adr/`: docs/adr/ADR-1040-doc-agenda-nav-entry-index.md:58 だけ。週次点検は「外れたら PO へ知らせる」と書いてあるが、知らせる仕組みは定めていない。
- docs/adr/FEATURE-INDEX.md: mac / 週次 / 見張り の行は ADR-1045 の 1 行（社外秘の原文の見張り。本件と無関係）。
- 通知先 webhook は ADR-1009 の番人と共有（scripts/mac-jobs-watch.sh:6, :28）。

## 週次点検の今の形
- 台本: scripts/dev/doc-entry-weekly-check.sh。最後に `RESULT=OK` か `RESULT=NG <項目…>` を 1 行出す。
- 動かす人: agent-console の定期実行「入口の文書 週次点検」（有効・毎週月曜 16:00・Asia/Tokyo）。結果を `~/CC報告ファイル-keep/doc-entry-weekly/YYYYMMDD.txt` に書く（指示書に置き場の記載 4 か所）。指示書に Discord の語は 0 件で、NG のときは作業画面に残るだけ。
- 置き場の実物（2026-11-05 `ls -la` と `grep -n '^RESULT='`）:
  - `20261027.txt` 11 行目 `RESULT=OK`（10/27 04:35 作成）
  - `20261102.txt` 11 行目 `RESULT=NG K1>200 K9>6.5k`（11/02 16:01 作成）
  - 名前に `-after1`・`-trial-…` が付いた試しのファイル 4 つ（日付 8 桁＋`.txt` の形ではない）
  - 置き場の中の調べ物の書類 library-research-20261102（結果ファイルではない。リポジトリ外）

## 見張り役の作り（scripts/mac-jobs-watch.sh・593 行）
- :20-52 mjw_config（MJW_ 環境変数で上書き可）。:21 `home_dir="${HOME:-…}"`。
- :183-193 mjw_judged、:196-210 mjw_text（名前 → 固定文）。
- :237-259 mjw_read_state（状態キー prev_run・boot_sec・colima_seen・colima_d_run・dj_err_seen・disk_kick・phone_gone）。:261-274 mjw_write_state。
- :328-381 mjw_detect_states（状態型。DETECTED に積む → 24h 再通知・復旧は :439-455 mjw_classify と :562-582 が共通処理）。
- :400-436 mjw_detect_events（出来事型。EV_LIST に積む。:406-412 初回 FIRST は既読位置だけ合わせて知らせない）。:457 mjw_commit_events。
- :513-518 detect_states → detect_events → `C_*` に前回値 → 初回なら commit → classify。
- :520-525 dry-run はここで 1 行書いて終わる（送らない・状態を書かない）。
- :547-560 出来事は ① 異常 と一緒に送り、送れたときだけ既読位置を進める（失敗なら次の回に送り直す）。

## 試験
- scripts/tests/test-mac-jobs-watch.sh（818 行）。:115-140 setup は HOME を一時領域に向ける（`export HOME="${D}/home"` :123）。:107-112 mk_state は weekly_seen を書かない。
- BSD の `date -j` を使う（:94, :98-100）ので macOS でしか動かない。
- GitHub の CI でこの試験を流す workflow は無い（`grep -rn 'test-mac-jobs-watch' .github/workflows` 0 件）。GitHub が用意する macOS の機械（`runs-on: macos-latest` など）を使う workflow も無い。macOS の行は PO の Mac を使う 2 つだけ（.github/workflows/hook-permission-check.yml:30、.github/workflows/reaper-schedule.yml:28 の `[self-hosted, macOS]`）。PO の Mac で試験を回さない決まりがあるので、本件は self-hosted を使わない。kgi.md の P5・R6 は Mac で流した結果。
- .github/workflows/no-mac-vm-guard.yml は「Mac で一時的な仮想マシンを作る命令」だけを止める。.github/workflows/runner-label-lint.yml は claude-pipeline.yml だけを見る。GitHub が用意する macOS の機械（macos-latest）を使うことを止める決まりは無い。
