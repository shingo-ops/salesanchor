# recon: AI が Mac で重い試験を回す命令を止める（mac-test-guard）

この文書は何か(専門用語なしの1行): 「試験は Mac で回さず GitHub とクラウドで」を機械で守らせる前に、今どこで Mac の試験が動いているかを調べた記録。

調べた人・日時: Opus（設計役）、2026-11-02 JST、手元の読むだけの命令。生の記録は /tmp/CC報告ファイル/mac-test-guard/（recon_notes.md ほか）と /tmp/CC報告ファイル/ci-flake-fix/。

## 0. PO の決定（2026-11-02 チャット）
- 「Macで試験をする意図は？スペックが低いからクラウドとgithubで完結させたい、」→ 選択肢「1 試験はすべて GitHub とクラウドで回し、Mac では何も回さない」に「1」。
- 続けて「1 Mac で試験を回そうとしたら機械で止める見張りを作る」に「1」。
- 続けて「1 送る直前の軽い確かめは Mac に残し、AI が打つ重い試験だけを止める」に「1」。

## 1. 既存 ADR・設計の検索
- `git grep -ilE "mac ?(の|で|上)|macos|colima|手元で試験|local test" docs/adr/` → 16 件。Mac の役割に触れるのは ADR-029（Mac を GitHub の作業を受ける機械にする）・ADR-111（その機械を Shingo-Mac-Temp に固定）・ADR-055（評価する係の画面確認の道具）・ADR-1052（Mac が重くなるので相談係を Mac で動かさない。:34・:54）。AI が手元で打つ試験の置き場を決めた ADR は無い。docs/adr/FEATURE-INDEX.md にも「試験の実行場所」の項目は無い（Mac を含む行は :22 の社外秘の見張りだけ）。
- 近い既存設計: /Users/tanizawashingo/worktrees/salesanchor/release-mac-test-guard-design/docs/handoff/mac-vm-hook/design.md（Mac で試験用の仮想マシンを作る命令を止める見張り。§3 止める形・§5 許可券・§6 fail-open）。本件は同じ形にそろえる。
- 近い既存設計: docs/handoff/rule-enforcement/design.md「## R4b」（送る直前の確かめ。PO 2026-10-30「1,2」）。本件では変えない。

## 2. 事実（観測）
### R1 この Mac で全部の試験を回すと毎回落ちる
- 機械: `sysctl -n hw.ncpu hw.memsize` → 8・8589934592（8 コア・8GB）。
- agent-console の `npm test`（vitest run）を4回: 4回とも落ちた。
  - /tmp/CC報告ファイル/ci-flake-fix/s9_before_npmtest.txt:122-125 → 2 failed、452.58s
  - /tmp/CC報告ファイル/ci-flake-fix/s9_after_npmtest.txt:172-175 → 5 failed、593.09s
  - /tmp/CC報告ファイル/ci-flake-fix/eval_d8d9/02_test.txt:349-350 → 16 件前後 failed（FAIL 行 :122〜:314）、618.83s、開始時の負荷 17.32（eval_d8d9/02_load.txt）
  - /tmp/CC報告ファイル/ci-flake-fix/eval_d8d9_rerun/npm_test.txt:120-123 → 2 failed、442.09s、開始時の負荷 6.12（eval_d8d9_rerun/npm_test.uptime）
- 落ち方の多くは `Error: Test timed out in 5000ms.`（vitest の既定の時間切れ）。agent-console の vitest.config.ts（origin/main 02857e2）に testTimeout の指定は無い。
- 同じ試験を GitHub の確かめ（macOS と ubuntu）で10回: 20/20 ジョブ合格（agent-console docs/handoff/ci-flake-fix/design.md:274）。

### R2 Mac で試験が動く道
- (a) AI（Opus 本体・手元の審査役・評価する係）が Bash で打つ命令。例: `npm test`、`npm run test:e2e`、`npx playwright test`、`pytest`。
  - ~/.claude/agents/evaluator.md:126 と :131 に `npx playwright test --config tests/qa-smoke/playwright.config.ts` を手元で打つ手順が残る。ただし GitHub 側の qa-smoke.yml は 2026-10-30 に PO 決定で自動起動を止めている（.github/workflows/qa-smoke.yml:11）。
- (b) git push の直前に自動で動く確かめ: frontend/.husky/pre-push → scripts/dev/check-before-submit.sh。CI と同じ軽い検査だけを流し、重い組は CI に回す（check-before-submit.sh:5-6、:294）。
  - 記録 /Users/tanizawashingo/salesanchor/.git/check-before-submit.log（写し /tmp/CC報告ファイル/mac-test-guard/cbs.log）: 2026-10-30T13:02Z〜2026-11-02T13:04Z に 375 回、秒の中央値 23.5、最大 250.9、60 秒超 71 回。
  - PO 決定により本件では止めない（§0 の3つ目）。
- (c) agent-console は PO の Mac で動くアプリで、入れ替えに `npm run build` を使う。試験ではないので止めない。
- (e) この Mac は GitHub の作業を受ける機械（self-hosted runner）でもある: `launchctl list` に actions.runner.shingo-ops-salesanchor.Shingo-Mac-Temp（ADR-029・ADR-111）。Mac で動くよう指定された作業は2つだけ（.github/workflows/hook-permission-check.yml:30 毎週月曜、.github/workflows/reaper-schedule.yml:28 毎日 03:00 JST。全一覧 /tmp/CC報告ファイル/mac-test-guard/selfhosted_runs_on.txt）。どちらも npm・pytest・vitest・playwright を含まない（grep で 0 行）＝ GitHub 経由で試験がこの Mac に来る道は無い。
- (d) クラウドの担当は ~/.claude/settings.json を読まない（クラウドの見張りは scripts/agent-hooks/cloud/ の別系統）。本件の見張りはクラウドに効かない＝クラウドの試験は今までどおり。

### R3 見張りの置き方の手本
- ~/.claude/settings.json の PreToolUse Bash に 54 件中 Bash 対象が 20 件以上登録済み（/tmp/CC報告ファイル/mac-test-guard/hooks_registered.txt）。mac-vm-guard は :511 付近。
- リポジトリに正本を置き PO の `!` で入れる型: scripts/agent-hooks/confidential-quote-guard/install.sh（93 行。:22 で写し、:58-61 で settings.json を写しを取ってから書き換え）と rollback.sh（63 行）。
- 手元の担当（Sonnet）は起動できない（~/.claude/scripts/local-agent-guard/guard.py）。よって ~/.claude へ直接書くのは PO の `!` で流す install.sh だけ。

## 3. 未確認
- AI が過去7日に Mac で重い試験を何回打ったか: Bash の命令の記録が残っていないため数えられない（agent-events.jsonl は見張りが止めた分だけ）。導入後は見張りの記録で数える。
- （解消 2026-11-02）Claude Code の PreToolUse で exit 2 が命令を止めて標準エラーを AI に返す仕様: Context7 `/websites/code_claude` で https://code.claude.com/docs/en/hooks「Exit code 2」を確認（design.md §8）。
