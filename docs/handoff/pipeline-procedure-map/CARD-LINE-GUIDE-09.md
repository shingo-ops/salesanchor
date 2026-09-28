# CARD-LINE-GUIDE-09 — ガイドE2Eの同時cold読込を抑える

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: カード名を示す。担当Sol、設計/自己審査Astra。
読んだ節: guards/00-common.md、04-worktree.md、11-lint.md、frontend/AGENTS.md。
§5.5照合: 記号○、ready○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume
所有範囲: frontend/tests-e2e/analysis-rules-line-guide.spec.ts の実行mode指定と短い理由コメントのみ。
他者と共用中。Astraの文書変更を巻き戻さない。他ファイル編集・製品変更・timeout/expect緩和は禁止。
commit/push/PR/merge/本番変更禁止。CARD08が同一条件で6/6成功した場合だけ実行する。

設計契約:
同specは独立した6件を保持し、ファイル内をdefault順次実行にする。
import群の後、top-levelへ test.describe.configure({ mode: "default" }); を1箇所追加。
理由コメント: 07では4件同時実行時にcold gotoが24〜25秒となったため、同spec内の同時cold読込を避ける。
単回比較だけで負荷原因の全てを確定せず、観測と対処目的に限定して書く。
serialモードは使わない（失敗時の後続skip/まとめretryは今回の試験目的に不要）。
global fullyParallel/workers、test timeout30秒、action timeout、6ケースのassert、mock定義は変更しない。
根拠: CARD07 traceで初回goto24.29〜25.41秒、focus3.61〜3.97秒、後続warm2件は9.6/12秒。
Astra Context7 /microsoft/playwrightでmode defaultがfullyParallelを局所上書きする仕様を確認済み。
https://github.com/microsoft/playwright/blob/main/docs/src/test-parallel-js.md
設計自己審査APPROVE。08比較の合格が実装の前提。API404は別のfixture範囲問題として記録し、推測したpayloadを追加しない。

手順1: 08成功を確認し、カードlint後に所有1ファイルへ上記限定編集。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && bash scripts/card-lint.sh /private/tmp/CARD-LINE-GUIDE-09.md
同じファイルの別変更を発見したら止める。

手順2: 指定ファイルのlintと既定の実行コマンドで6件再検証。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx eslint tests-e2e/analysis-rules-line-guide.spec.ts
試験直前に以下を実行し、exit1かつ出力空（listenerなし）の場合だけ続行。PID表示または別エラーは停止。
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume && lsof -nP -iTCP:5173 -sTCP:LISTEN
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-workflow-guide-resume/frontend && npx playwright test tests-e2e/analysis-rules-line-guide.spec.ts --project=chromium
5173の他者serverを再利用/停止しない。自分が起動したserverの終了も確認する。
workers overrideを付けない最終実行で6/6成功を必要条件とする。

手順3: 差分、6件の時間、合否、画像path、既存失敗記録保持をAstraへ報告し停止。
失敗・実ガード拒否は停止。正規sandbox escalation可。独断の追加修正/再試験/制限緩和なし。

END OF CARD
