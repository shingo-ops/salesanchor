# CARD-LINE-GUIDE-08 — 時間切れの切り分けと全6ケース再検証

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、11-lint.md、frontend/AGENTS.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
目的: 07の時間切れを失敗記録として保持し、並列競合を除いて同じ6件の機能検査を実行する。
他者と共用中、製品/試験/設定/lockfile/文書の編集禁止。Astra並行文書変更を保持する。
commit/push/PR/merge/本番変更なし。

観測根拠: Solが失敗4件のtraceを読取。初回goto24.29〜25.41秒、menu focus3.61〜3.97秒。
shotは各0.186〜0.965秒で完了。後続2件は9.6/12秒で成功。
並列負荷とcold module loadの影響は仮説であり、未確認の原因を確定と書かない。
AstraはContext7 /microsoft/playwrightでworkers=1の公式仕様を確認。
https://github.com/microsoft/playwright/blob/main/docs/src/test-parallel-js.md
workers=1は同時実行数のみを制限し、timeoutやassert条件は変えない。
設計自己審査APPROVE: 製品を変更せず同一受入条件を保持した診断再実行。

手順1: 07のtest-results/traceと今回失敗画像を/tmp/reports/card-line-guide-resume-failedへ退避する。
5173が他者使用中なら停止。試験中の自分のserver以外を再利用/停止しない。
実コマンドと既存設定を照合する。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-08.md

手順2: workersだけ1へ指定し、全6件を30秒条件のまま実行する。
試験直前に以下を実行し、exit1かつ出力空（listenerなし）の場合だけ続行。PID表示または別エラーは停止。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && lsof -nP -iTCP:5173 -sTCP:LISTEN
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx playwright test tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium --workers=1
成功時も既定並列runが失敗した事実を消さず、実行条件を分けて報告する。
失敗時は追加再実行・閾値変更・コード修正せず停止しAstraへ報告する。
成功時は6件の時間・総時間・画像path/日時・製品副作用差分0をAstraへ報告し停止。
本番での読解確認や並列性能試験の合格とは称さない。
正規sandbox escalation可、実ガード拒否は停止報告。

END OF CARD
