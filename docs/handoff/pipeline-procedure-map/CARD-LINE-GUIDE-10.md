# CARD-LINE-GUIDE-10 — 正しい作業rootでSol検証修正を再開

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol（gpt-5.6-sol）、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、11-lint.md、frontend/AGENTS.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
このCLI sessionはPOのAstra/Sol委任に基づきAstraが明示起動する。追加agent/session起動・モデル変更は禁止。
他者と共用中で、Astraが同じworktreeの文書を更新している。他者変更を巻き戻さない。
所有範囲はfrontend/tests-e2e/analysis-rules-line-guide.spec.tsのmode default指定と理由コメントだけ。
製品/他試験/lockfile/設定/文書の編集、commit/push/PR/merge/本番操作は禁止。
本店mainのセッションからのapply_patch拒否を受け、adapterが求める登録済みworktreeを起動rootに指定した。
hook/trust/rulesを維持し、無効化フラグを使わない。--approve-for-meはGO権限やマージ承認ではない。

手順1: pwd/branch/UUID/claimを確認し、作業rootとgpt-5.6-solが一致すること。
期待branch release/line-workflow-guide-resume、HEAD fdf3b45a4c0423413e704694fb99700d94e1d5a7。
MERGE_HEAD 87c4ad83a96e25dfab792a3b57dda75ba51a65eb、UUID bce43041-c2fe-4179-a45b-16ddfd59ec66。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && ./scripts/dev/executor-preflight.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-10.md

手順2: /private/tmp/CARD-LINE-GUIDE-09.mdを読み、その確定修正と検証だけを実行する。
CARD08は全6件成功済み。55秒、各10.4/6.2/6.8/6.6/10.2/3.7秒。製品/timeout/assert変更0。
理由コメントは原因断定せず、4件同時実行時のcold goto24〜25秒という観測と同時cold読込を避ける目的に限る。
編集は正しい起動rootのapply_patch。実ガードが再び拒否したら変更0のまま停止報告し、別書込手段を使わない。
CARD09のeslintと各run直前lsof確認、workers指定なしの全6件E2Eを実施する。
本番・CI・PO読解確認を済みとしない。既存失敗記録を保持する。

手順3: 実差分、試験コマンドと終了値、ケース時間、画像path、その他変更0をAstraへ報告し停止。
失敗・前提相違・実ガード拒否は停止して生出力をAstraへ返す。正規sandbox権限申請は可。

END OF CARD
