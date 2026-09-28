# CARD-PR-LIFECYCLE-02 — 確定した呼出契約の反映と検証

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。担当Sol、設計/審査Astra。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、05-pr.md、06-merge.md、11-lint.md。
§5.5照合: 記号○、ready指定○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates
ブランチ: release/pr-lifecycle-gates、起点origin/main 4bad43a4dca6368ffa7370792a3c912e90bba521。
目的: 審査分離の実装を確定契約に合わせ、否定/正常試験で検証する。
設計: pr-lifecycle-design.mdの全文と末尾「呼出契約の確定追補」。追補が前節と食い違う場合は追補が優先。
許可対象はCARD-PR-LIFECYCLE-01の8コード/テストと3台帳に、scripts/aeon-release.shの呼出1箇所を追加する。
他者と共用中。前便の変更とAstra文書を保持する。commit/push/PR/merge/deploy/GO創作/個人hook/trust/CI変更は禁止。
Astraが前便CLIをSIGINTで中断した。部分変更を壊さずstatus/diff確認から続行する。

手順1 正式カード確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/card-lint.sh docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-02.md
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git status --short --untracked-files=all

手順2 実装を確定契約へ合わせる

特にAstra中間レビューのREVISE事項:
1. create wrapperにGITHUB_ACTIONS素通りが残っている。設計どおり除去する。
2. aeon-release.shの既存--merge --delete-branch呼出は--mergeだけにする。wrapperが勝手に引数を無視する設計にしない。
3. helperはPR番号/branchの2引数。exit0=送信成功かつMERGED確認、exit1=送信前拒否、exit2=送信後異常。非0でcleanup禁止。
4. 送信非0でも結果GETを1回実施。MERGED観測ならその事実を示すがexit2。再送もcleanupもしない。
5. required checksは非空かつpass/skippingだけ許可、skipping件数は成功実行と区別。reviewDecisionはAPPROVED/空だけ許可。
6. checker --validation-onlyは未知/重複引数を拒否し、全検査維持・Issue write0を検証する。
7. create本文の4構文、read不可/非regular/非UTF8/NUL/空/二重/stdin拒否を確定設計に合わせる。
8. merge前の最後の状態取得時にもlocal HEAD/cleanを確認し、検査中の作業机変更は停止する。
9. existing wrapperテストは鍵とhelper非0→cleanup0、新lifecycleテストは実helperのGO/checks/BEHIND/送信0を担当する。

前便のDelete/Add同一pathでpatch形式が拒否された事実を記録する。同じパスの更新はUpdate Fileを使う。
新たなガード拒否はその時点で停止し、別の編集手段や設定変更で回避しない。
設計不明/失敗は根拠付きでAstraへ報告。外部書込は偽ghの試験内だけ。

手順3 テストと報告
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && node scripts/tests/test-process-artifacts.js
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/tests/test-merge-safe-guard.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && python3 scripts/tests/test-pr-lifecycle.py
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash -n scripts/gh-pr-create-safe.sh scripts/dev/validate-pr-body.sh scripts/gh-pr-merge-safe.sh scripts/aeon-release.sh >> /tmp/pr-lifecycle-shell-syntax.log 2>&1
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git diff --check

preflight成功は前便から継続。sandbox起因の通信/一時git制限は同一コマンドをrequire_escalatedの正規個別審査へ出してよい。
否定fixtureで外部merge/create/issueが0回、正常時だけmergeが検査済SHAで1回となることをassert。
既存full checker正常/否定判定を弱めない。試験で実GitHub/本番へ送信しない。
台帳とtasks/evidenceを実測で更新、DONEにしない。Astra宛に変更と件数/終了値/未確認を報告して停止する。

END OF CARD
