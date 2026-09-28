# CARD-LINE-GUIDE-06 — 継続作業机の検算と保存済みガイドの統合

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を冒頭に示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、11-lint.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
目的: CARD-LINE-GUIDE-05成功後、保存済みガイドを最新mainに統合する。
他者と共用中。他者の変更を巻き戻さない。元branch/remote/UUID/台帳は保持する。
本便は統合作業のみ。commit・push・PR・本番変更は禁止。
保存済み設計docs/handoff/pipeline-procedure-map/design.mdの2026-09-28追記が対象。
本カードはAstra自己審査APPROVE。別Solの最新main意味監査で説明修正は0件。

手順1: 作成便の終了値0を確認してから、予定pathの実在とgit登録、pwd、branch、HEAD、UUIDを確認する。
本店の非台帳18件を作成前snapshotと比較する。差分があれば停止しAstraへ報告する。
新branchがrelease/line-workflow-guide-resume、HEADがfdf3b45a4c0423413e704694fb99700d94e1d5a7であること。
元branchのlocal/remoteが87c4ad83a96e25dfab792a3b57dda75ba51a65ebのままであること。
新作業机の初期変更は公式scriptが作ったメタデータに限る。未知の編集は停止。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && ./scripts/dev/executor-preflight.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-06.md

手順2: 上記一致時だけ保存済みbranchを通常mergeし、commit前で止める。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && git merge --no-ff --no-commit release/line-workflow-guide
競合したら解消せず、実際の競合pathと該当hunkをAstraへ報告して停止する。
成功時はgit status、git diff --cached --stat、差分pathを報告する。
mainに追加されたja/enのextractionJobSupplier/Resolved/Unresolved/NeedsReviewを保持したか読み取りで確認する。
実装・運用script・CI・DB・secretsを独断で修正しない。
正規sandbox escalationは可。実ガード拒否・前提不一致は停止して生出力をAstraへ報告する。

END OF CARD
