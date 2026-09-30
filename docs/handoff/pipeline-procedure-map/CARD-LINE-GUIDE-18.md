# CARD-LINE-GUIDE-18 — main更新の限定統合

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、既存PR○、報告先○、一目的○、起点○、書式○、検算○、L32○。
所有範囲: 調査済みmainの通常統合だけ。他者と共用中、他者の変更を戻さない。
製品独自編集、DB実行、GO発行、PR編集、push、mainマージ送信、本番操作は禁止。
Sol実コード調査でskip_condition削除と残存message_excludeを区別し、ガイド修正不要と確認。Astra自己審査APPROVE。

手順1: 未保存はこのカードだけ、HEAD/mainが固定値と一致することを確認する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-18.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git status --short
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git rev-parse HEAD origin/main
期待値HEAD1b39bb461ab3dfb385fc128f460eaabafd8ff669、main aa74c0185f198041e3315519796a18845a06c0c8。

手順2: 通常統合をcommit前で止める。相違/競合/ガード拒否は停止してAstraへ報告する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git merge --no-ff --no-commit aa74c0185f198041e3315519796a18845a06c0c8
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git diff --cached 1b39bb461ab3dfb385fc128f460eaabafd8ff669 -- frontend
frontend差分0と未解消0を確認しAstraへ報告して終了。試験対象frontendはCARD17と同一なら前回実測を保持する。migrationを実行しない。

END OF CARD
