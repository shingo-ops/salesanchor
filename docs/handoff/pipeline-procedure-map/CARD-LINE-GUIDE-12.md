# CARD-LINE-GUIDE-12 — 作業中に進んだmainを統合する

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、05-pr.md、11-lint.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
他者と共用中。未知差分を巻き戻さない。push/PR/本番変更/guard設定変更は禁止。
目的: CARD11で保存したガイドへ、意味影響を調査済みの最新mainを通常mergeする。
前提: CARD11のcommit実在/cleanを確認済み、branchはrelease/line-workflow-guide-resume。
対象main: 8862732e494ac5d92287d57aeea808cee05d3151。
Sol限定監査: ガイド8frontend/共通Card/Badge/Button/token/locale変更0。
参照先KnowledgeAliasesTabは既存Buttonへの移管のみ、ガイド説明修正0。
競合候補はevidence-registryの末尾追加、todoの別hunk。双方の記録を保持する設計。
自己審査APPROVE。実競合は報告を受けAstraが内容を照合する。

手順1: 11完了SHAとcleanを確認し、fetch後origin/mainが対象SHAに一致すること。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-12.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git fetch origin
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git rev-parse HEAD origin/main
相違なら停止し、新SHAを無断採用しない。

手順2: 調査済みmainをcommit前まで通常mergeする。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git merge --no-ff --no-commit origin/main
競合時は解消せず、該当hunk/pathをAstraへ報告し停止。
競合なしでもstatus/statと統合SHAを報告して停止。commit・試験は次のカードで実施する。
正規sandbox escalation可。実ガード拒否・未知差分・前提相違は停止。

END OF CARD
