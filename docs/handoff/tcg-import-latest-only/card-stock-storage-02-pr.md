本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-PR

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親が試験commit ad0d9fc7と承認範囲3製品ファイルを直接確認。実PGは未実施。design-partner.md §5.5-2とcard-lint L14に従い通常PRで作成する。PR状態は検収合格やマージ承認を意味しない。既承認の公開GitHub shingo-ops/salesanchorへの提出だけ進める。
受領確認: 同じ担当・自分のブランチだけの通常レビュー用PR提出であることを返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 親がpush成功を確認した後、自ブランチの通常レビュー用PRを公式wrapperで1件作成。wrapperの.pr-numberと自台帳PR番号登録を許可。pushは禁止。
禁止: 製品/設計の編集、commit、他ブランチ操作、強制送信、merge、本番/ローカルDB実行、許可発行、ガード変更。失敗は停止。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ、未保存0。
手順3: 既存PR確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && gh pr list --head release/line-stock-storage --state open --json number,url,headRefOid
    期待する出力: 空。存在したら新規作成せず報告停止。
手順4: 本文確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && cat /private/tmp/line-stock-storage-pr-body.md
    期待する出力: 親の正式本文。実PG未実施・GO未記録。
手順5: 通常レビュー用PR作成
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && bash scripts/gh-pr-create-safe.sh --base main --head release/line-stock-storage --title "feat: add isolated storage for product stock updates" --body-file /private/tmp/line-stock-storage-pr-body.md
    期待する出力: PR URLと登録成功。
手順6: 番号確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && cat .pr-number
    期待する出力: 作成番号。
手順7: GitHub照合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && gh pr list --head release/line-stock-storage --state open --json number,url,headRefOid,isDraft
    期待する出力: 1件、番号一致、isDraft false。報告して停止。CI判定は親の後続作業。
END OF CARD
