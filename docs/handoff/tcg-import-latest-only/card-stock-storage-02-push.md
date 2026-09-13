本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-PUSH

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親がfixture修正commit07da520aの既定値1行のみと、最新main統合を直接確認。初回実PGは新規8群setup error、修正後の再CI待ち。既承認の公開GitHub shingo-ops/salesanchorへの提出だけ進める。
受領確認: 同じ担当・自分のブランチだけの通常pushであることを返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 自ブランチの通常pushだけ。PR作成は禁止。
禁止: 製品/設計の編集、commit、他ブランチ操作、強制送信、merge、本番/ローカルDB実行、許可発行、ガード変更。失敗は停止。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ、未保存0。
手順3: head確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format='%H %s'
    期待する出力: 親の文書保存commit。
手順4: 通常push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git push -u origin HEAD
    期待する出力: originのrelease/line-stock-storageへの成功。失敗時迂回なし。
手順5: remote確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git ls-remote origin refs/heads/release/line-stock-storage
    期待する出力: 手順3のHEAD一致。結果を報告して停止。
END OF CARD
