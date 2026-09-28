# CARD-LINE-GUIDE-14 — 検証済みbranchのremote保存

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
他者と共用中。他者変更の巻戻し禁止。目的はCARD13で検証・commit済みの成果をremoteへ保存すること。
前提: 13完了SHA/cleanとAstra最終レビューAPPROVEを明示受領後だけ実行。
製品/文書編集・commit・PR・main操作・merge・本番変更は禁止。

手順1: branch/HEAD/cleanが13完了報告と一致すること。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-14.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git log -1 --format=fuller

手順2: 専用branchだけを通常pushする。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git push -u origin HEAD
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git rev-parse HEAD origin/release/line-workflow-guide-resume
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git ls-remote origin refs/heads/release/line-workflow-guide-resume
local/origin tracking/remote実SHAの3一致と終了値をAstraへ報告して停止。PRは次カード。
正規sandbox escalation可。実ガード拒否・hook失敗・不一致は停止報告し、強制/skipなし。

END OF CARD
