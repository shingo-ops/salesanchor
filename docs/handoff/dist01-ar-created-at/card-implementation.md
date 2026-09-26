CARD-DIST01-PREVIEW-3258-04
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、09-gh.md、11-lint.md。
照合: 1○記号、2○既存ready PR、3○全文報告、4○PR更新1目的、5○既存起点、6○本文確定、7○実出力確認。
受領確認: 「CARD-DIST01-PREVIEW-3258-04を受領」と返す。

PO原文「進めるPRマージして本番反映させてくれ」を受領。今回のカードは必要な準備として既存PR更新・CI確認までを実施する。
まだ現行チェック用の番号付きGO原文がないため、マージはこのカードに含めない。過去GO再利用・PO発話への番号補完は禁止。
実装担当は同じ作業台を継続し、root作成の本カード・design/recon追補を含めてローカル保存・push・PR本文更新する。
起点はrelease/fix-dist01-ar-created-at、HEAD510548c30df5bccd8f851c82bca7d86e2c2aaf72。実装済み製品/試験を保持。
root確認時最新main66b417665c013fdb354d5bda63226d07a1b2182cは文書4件の追加のみ。fetch後に別の変更があれば内容を照合する。
許可ファイルは既存PRの5件だけ。製品の追加変更、CI/DB/本番変更、代理GO、新規エージェント、強制pushは禁止。
本文確定ファイル: /tmp/CC報告ファイル/dist01-3258/pr-body-3258.md。誤記を避け、このファイルをそのまま使用する。

停止時: 手順番号・最後のコマンド・理由・生出力全文を報告する。未知の競合や範囲外差分を独断解消しない。
CIの番号付きGO不足以外の失敗はrootへ報告し、今回の5ファイル内の形式不備だけ修正可。製品の再設計やゲート変更は禁止。
報告冒頭: 本報告はカード CARD-DIST01-PREVIEW-3258-04 の実行結果である。
全生出力は /tmp/CC報告ファイル/dist01-3258/ に保存し全文とともに返す。HEAD/PR URL/各checkを含める。

手順0: preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && ./scripts/dev/executor-preflight.sh

手順1: 既存状態確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git status --short --branch

手順2: 文書3件のみstage
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git add docs/handoff/dist01-ar-created-at/card-implementation.md docs/handoff/dist01-ar-created-at/design.md docs/handoff/dist01-ar-created-at/recon.md

手順3: 文書保存
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git commit -m 'docs(dist01): record verified fix and prepare PR update'

手順4: 保存確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git log -1 --format=fuller

手順5: 参照更新
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git fetch origin

手順6: 最新main統合。競合時は報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git merge --no-edit origin/main

手順7: 差分5件と日時1行を確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git diff origin/main --stat

手順8: 空白検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git diff origin/main --check

手順9: PR所有権をブランチから確認。3258 OPENを照合
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && gh pr view --json number,state,headRefName,headRefOid,url

手順10: 通常push。forceなし
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git push -u origin HEAD

手順11: push後HEADの実在確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git log -1 --format=fuller

手順12: PRタイトル/本文更新
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && gh pr edit --title 'fix(dist01): computed_at基準の配信プレビューと実PG回帰試験' --body-file /tmp/CC報告ファイル/dist01-3258/pr-body-3258.md

手順13: PR登録確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && bash scripts/register-pr.sh

手順14: 最新PR状態確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && gh pr view --json number,headRefOid,state,mergeStateStatus,url

手順15: CI状態取得。pendingは60秒以内の間隔で再確認、GO不足以外の失敗をrootへ報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && gh pr checks --json name,state,link

手順16: 最終作業台確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-fix-dist01-ar-created-at && git status --short --branch

END OF CARD
