---
mode: handoff
---
CARD-PMG-ERROR-VISIBILITY-02
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、guards/03-file.md、guards/05-pr.md、guards/11-lint.md。
照合: 実在作業台、正式PR窓口、番号直書きなし、GO原文未受領の扱い。
受領確認: カード名をrootへ返す。
担当: error_visibility_recon。rootによる交付メッセージを受けてから実行する。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility
許可: 本便のfrontend実装とroot保存文書の検算・commit・push・通常PR起票・CI結果確認。
前提: rootが最終テスト結果と独立レビュー合格を確認済みであること。
製品編集は01カードの範囲で指摘修正時だけ。CI/DB/本番/他branch/GO原文作成は禁止。
他者の変更を戻さない。PR3494は依存であり変更しない。依存の修正/GO未完を明記する。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && git status --short
期待する出力: 本便14前後の対象ファイルのみ。意図しないファイルはrootへ報告。

手順1
編集ツールでPR本文を/private/tmp/pmg-error-visibility-pr.mdへ作成することを許可する。
内容は問題/挙動、SSOT、実行検証と未検証、依存PR3494の2件REVISE、未本番、正式様式。
触る/削除するファイルは実差分から全列挙。削除とは行の置換も含む。
GO記録欄を創作しない。正式番号付きGO前なのでprocess gate停止を正しく記す。
root文書4対象と本カード/01カード、frontend本便差分だけを明示的git addする。
文書4対象: tasks/todo.md、docs/ai-agents/evidence-registry.md、PMG既存design.md/recon.md。
チェック済みの本便差分のみ通常commit。commit失敗は理由を報告し、hookを無効化しない。

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && git log -1 --oneline
期待する出力: 本便commitの実在。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && git push -u origin release/gemini-error-visibility
期待する出力: 正常push。forceなし。

手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && bash scripts/gh-pr-create-safe.sh --base main --title 'feat: 抽出試行の履歴と失敗理由を表示' --body-file /private/tmp/pmg-error-visibility-pr.md
期待する出力: PR URLと.pr-number登録。

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && cat .pr-number
期待する出力: 作成PR番号。

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && gh pr checks
期待する出力: 現在のCI結果。pendingと失敗を成功にしない。
書式不備は本便PR本文だけ修正可能。未受領GO、依存不備を偽装しない。
PR番号/URL/HEADと各結果をrootへ返して停止。マージ/配備/本番再抽出/配信は行わない。
END OF CARD
