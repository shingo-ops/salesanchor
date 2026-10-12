# CARD-PR-LIFECYCLE-03 — 送信対象と入力の固定

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。担当Sol、設計/審査Astra。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、05-pr.md、06-merge.md、11-lint.md。
§5.5照合: 記号○、ready指定○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates
ブランチ: release/pr-lifecycle-gates、起点origin/main 4bad43a4dca6368ffa7370792a3c912e90bba521。
目的: 追加レビューのREVISEを解消し、対象外への送信と入力の食い違いを防ぐ。
設計: pr-lifecycle-design.md全文、末尾「入力・送信対象の審査追補」を優先する。
許可対象: CARD-02と同じ9コード/テストと3台帳のみ。設計文書はAstra管理。
他者と共用中。他者と前便の変更を保持する。commit/push/PR/merge/deploy/GO創作/個人hook/trust/CI変更は禁止。

手順1 カード検査と実物確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/card-lint.sh docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-03.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git status --short --untracked-files=all

手順2 追補契約の実装
GH_REPO/GH_HOSTの対象固定をcreate/helper/checker/registerまで徹底する。
register本体を編集せずcaller環境を固定しGITHUB_ACTIONSを除去して登録skipを防ぐ。
createはtitle/body/body-file/base/headの長形式だけを許可する。検証値からargvを再構成しbody-fileは検証済文字列を送信する。
未知/重複/明示空/値欠落、対話系を拒否。既存callerの互換性を限定検索で確認し、不整合なら報告停止。
base/head/local/origin SHAは40桁hexを検証し、不正値ならNode/merge呼出0。
merge wrapperのGITHUB_ACTIONS成功skipを撤去する。
full checker後もrequired checksを再確認し、pass→pending/failならmerge0。
新たなガード拒否・設計不明は根拠付きで停止しAstraへ報告。別手段によるガード回避は禁止。

手順3 実測
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && node scripts/tests/test-process-artifacts.js
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/tests/test-merge-safe-guard.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && python3 scripts/tests/test-pr-lifecycle.py
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash -n scripts/gh-pr-create-safe.sh scripts/dev/validate-pr-body.sh scripts/gh-pr-merge-safe.sh scripts/aeon-release.sh >> /tmp/pr-lifecycle-shell-syntax.log 2>&1
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git diff --check

既存106/4/10成功を基準とし、新たな否定試験を追加する。実GitHub書込0、偽ghで対象host/repoと送信回数をassertする。
Python構文も確認。sandbox固有制限は同一操作を正規require_escalated審査へ出してよい。
台帳へ件数/終了値/未確認を記録し、Astraへ報告して停止する。DONEにしない。

追補: 手順1の複合read-onlyコマンドはPreToolUseにNested shell PR commands are not inspectableとして拒否された。
Solは指示どおり停止し、追加変更0。Astraが実ログのコマンドを確認した。
Astraによるscripts内のwrapper名の単独rgはexit0。固定引数を伴う実行callerは0、generatorの説明とlint/test参照だけ。
再開時は検索・読取を単独コマンドで実行し、PR操作を検索語に含む複合shellを作らない。
検査機能や設定の変更は禁止のまま。元のread-only目的を保つ検査可能な形式で進める。
新たな拒否は再び停止報告する。この追補は危険操作やPR書込を許可しない。

END OF CARD
