# CARD-PR-LIFECYCLE-01 — 作成前検査とマージ前GO検査の分離

本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
受領確認: 冒頭でカード名を示す。Astra設計/自己審査、Sol実装/試験。本セッションの明示委任による。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、04-worktree.md、05-pr.md、06-merge.md、11-lint.md。
§5.5照合: 記号○、ready指定○（本便PRなし）、報告先○、一目的○、起点○、書式○、検算○、L32未確定なし○。

目的: GO未発行のPRを提出でき、GO必須の変更が承認なしでマージされないこと。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates
ブランチ: release/pr-lifecycle-gates、起点: origin/main 4bad43a4dca6368ffa7370792a3c912e90bba521。
設計: docs/handoff/go-record-transcription/pr-lifecycle-design.md。reconは同ディレクトリpr-lifecycle-recon.md。
既存の代理GO制度全体はREVISEのまま。今回POが承認した審査順序の限定修正だけを実装する。
他者と共用中。Astraが保存した設計/recon/READMEを保持し、他者変更を戻さない。
本便はローカル実装と試験まで。commit/push/PR/merge/deploy、GO記録生成、hook/trust/個人設定/Ruleset/secrets/CI workflow変更は禁止。

## 編集許可ファイル

scripts/gh-pr-create-safe.sh
scripts/dev/validate-pr-body.sh
scripts/gh-pr-merge-safe.sh
scripts/dev/check-pr-merge-ready.py（新規・標準ライブラリのみ）
scripts/check-process-artifacts.js（validation-only追加だけ。GO/判定条件は維持）
scripts/tests/test-process-artifacts.js（検証専用モードの副作用0確認）
scripts/tests/test-merge-safe-guard.sh（既存鍵検査維持・自動追従期待を停止へ更新）
scripts/tests/test-pr-lifecycle.py（新規・一時gitと偽ghによる入口/否定試験）
.claude-pipeline/active-work.d/release-pr-lifecycle-gates.md
tasks/todo.md
docs/ai-agents/evidence-registry.md

手順0 作業机とカード確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && ./scripts/dev/executor-preflight.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git status --short --untracked-files=all
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/card-lint.sh docs/handoff/go-record-transcription/CARD-PR-LIFECYCLE-01.md

作業cwdとbranch一致、許可ファイルだけの文書準備差分を確認。ガード拒否は迂回せず根拠を報告して停止。

手順1 実装

設計追補の契約を忠実実装する。判断を要する設計変更はAstraへ戻す。
製品入口にテスト用MOCKやSKIPを追加しない。既存checkerへの入力はGitHubの実値で固定する。
validatorはGO要件だけ分離し構造/実diff/設計の検査を保つ。取得失敗を合格へ変換しない。
createはliteral bodyが必須、default main/current head、許可作者、push済みSHA、scope確認後に通常ready PRを作る。
create/editのGO未記入を準備段階として扱う。作成成功はマージ許可としない。
mergeは番号/所有権/実PR/HEAD/GO/必須checksを確認、--merge/--match-head-commitのみで1回送信。
自動追従・再送はしない。GOなし/値変化/取得失敗はmerge呼出0。正常merge確認後のみ既存cleanupへ返す。
full checkerのvalidation-onlyは緊急followup Issue起票だけを抑止する。判定自体は通常と同一。

手順2 検証
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && node scripts/tests/test-process-artifacts.js
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/tests/test-merge-safe-guard.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && python3 scripts/tests/test-pr-lifecycle.py
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash -n scripts/gh-pr-create-safe.sh scripts/dev/validate-pr-body.sh scripts/gh-pr-merge-safe.sh >> /tmp/pr-lifecycle-shell-syntax.log 2>&1
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && bash scripts/check-task-state.sh
    cd /Users/tanizawashingo/worktrees/salesanchor/release-pr-lifecycle-gates && git diff --check

新テストは偽ghの呼出を記録し、否定ケースでmerge/create/issueの呼出数をassertする。実GitHub writeは禁止。
既存full gate試験の一時fixtureは当該試験の通常手順で作成/削除を許可し、他者のファイルを消さない。
sandboxの通信/一時git作成制限なら、同一コマンドをrequire_escalatedの正規審査へ出すことは許可。拒否なら停止する。
試験失敗は原因を確認してAstraへ戻す。合格させるために否定条件・検証項目を外さない。

手順3 保存と報告

台帳/tasks/evidenceは実測結果と未commit/未PR/未mergeで記録する。自動登録ledgerを本店から作業机へ正規に取り込む。
担当する各テストの件数/終了値/不足、差分、未確認、fail時の生出力をAstraへ報告して待機する。
Astraレビュー前にコミット・外部変更しない。秘密は出力しない。

END OF CARD
