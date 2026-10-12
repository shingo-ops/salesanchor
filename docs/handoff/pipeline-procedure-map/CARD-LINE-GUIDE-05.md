# CARD-LINE-GUIDE-05 — 正規入口による継続作業机の作成

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。担当Sol、設計/審査Astra。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、11-lint.md。
§5.5照合: 記号○、ready指定○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
目的: 保存済みLINEガイドの続きを、正規入口で作った専用branchへ引き継ぐ準備。
作成branch: release/line-workflow-guide-resume
予定path: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
作成前cwd: /Users/tanizawashingo/salesanchor
確認済みremote main: fdf3b45a4c0423413e704694fb99700d94e1d5a7。
元branch release/line-workflow-guide、HEAD87c4ad83a96e25dfab792a3b57dda75ba51a65eb、UUID退避は保持。
元branch/remote/claim/台帳の削除・DONE化は禁止。他者と共用中で、他者変更を巻き戻さない。
本便は新規作業机作成まで。作成後cd・編集・merge・commit・push・PR・deployは別カードまで禁止。

設計判断と根拠:
前便の直接復元はL12で拒否され未実行。本便はnew-worktree.shという指定された正規新規作成入口を使う。
POは手順・検査の整合を進める提案に対し、事実確認の上で必要操作を進め、Astra/Solで完遂するよう再指示した。
Astraはその承認範囲で、本店を変更せずorigin/main起点を検証する進め方を採用し自己審査APPROVE。
正典CLAUDE.md:46-47、branch-operations/README.md:40-42はorigin/main起点と公式スクリプトを指定。
new-worktree.sh:90-106はfetch後origin/mainを起点にし、本店の古いtreeは使わない。
Astra直接比較で、本店HEADからorigin/mainまでnew-worktree.sh差分0。preflight exit0。
本店local HEAD==origin/mainという04-worktree.md:20の確認を、本店保護・remote SHA記録・作成後HEAD一致検算へ改める設計とする。
本店の18件の未保存変更やmain HEADを動かして条件を見かけ上満たすことは禁止。
ガード設定・trust・CI・カード検査は変更/無効化しない。直接復元L12は維持する。
この判断と04-worktree.mdの文面整合は、作成成功後に専用branchで正式保存・PR審査する。
PO発話として個別PRのGOや例外承認文を創作しない。番号付きGOの既存条件は維持。

手順1
    cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh
    cd /Users/tanizawashingo/salesanchor && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-05.md
本店branchがmain、remote mainが上記SHA、作成先branch/path/claim未存在、空き2Gi以上、作業机上限内を再確認する。
本店の非台帳変更を記録し、作成後の別カードで変化0を確認する。本店の変更は保護し、修正しない。

手順2
    cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/line-workflow-guide-resume
終了値と生出力をAstraへ報告し停止。作成後の存在・HEAD検算と移動は次カード。
失敗・実ガード拒否・前提変化は停止報告。sandbox固有制限は同じ操作を正規escalation可。

END OF CARD
