# CARD-PR-LIFECYCLE-05 — GO前の最新main取り込み

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。担当Sol、設計/審査Astra。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、05-pr.md、06-merge.md、11-lint.md。
§5.5照合: 記号○、ready指定○（既存PR）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates
ブランチ: release/pr-lifecycle-gates。現在HEAD01ca3df87ae52355facec232b4c2f175a7dd5bdd。
目的: PR #3824がBEHINDになったため、番号付きGOを求める前に最新mainを取り込んで検証する。
PO番号付きGOは未受領。承認済みHEADの自動追従ではなく、Astraが差分確認した正式な準備作業。
取得済origin/mainは6a1564012（PR #3822）。差分は以下3ファイルだけとAstra確認済み。
backend/app/services/tcg_analysis_dashboard_svc.py
 docs/handoff/extraction-hide-excluded/design.md
 docs/handoff/extraction-hide-excluded/recon.md
今回の修正対象との同一ファイル重複0。上記実装を再設計・編集しない。
他者と共用中。scope外の変更や競合があれば停止しAstraへ返す。
許可: 現HEADとorigin/mainを再確認、git merge --no-ff origin/main、再検証、本カード保存用の文書コミット。
push/PR編集/リモートmerge/deploy/GO作成は本便禁止。force/reset/trust/hook/CI変更禁止。

手順1
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/card-lint.sh docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-05.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git status --short
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git rev-parse HEAD origin/main
本カードの未追跡1件だけを許容。他の未保存変更があれば停止。

手順2
origin/mainが6a1564012以外へ更新されていれば停止。git merge --no-ff origin/main を通常hook付きで実行する。
競合は独断解決しない。マージ後に本カードだけをstageし、docs: record pre-approval main synchronization でコミット。

手順3
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && node scripts/tests/test-process-artifacts.js
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/tests/test-merge-safe-guard.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && python3 scripts/tests/test-pr-lifecycle.py
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git diff --check
実装9ファイルの内容が実装commit90c6dbeccと一致すること、PR差分へ別件3ファイルが混入していないことを確認する。
各操作は単独コマンド、明示cdとworkdirを固定。sandbox固有制限は同じ操作を正規escalation可。ガード拒否は停止。
最終SHA、clean、試験件数、比較結果をAstraへ報告して停止する。

END OF CARD
