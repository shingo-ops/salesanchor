本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-RETRY-PUSH

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 前回の同一通常pushは自動承認審査が公開宛先/payloadの承認確認不足として拒否し停止した。親はその後、GitHubで宛先shingo-ops/salesanchorがPUBLICであること、未送信がa0d9ee4c/9711cc40の2commitだけ、公開済79890cfcとの差分8ファイル81追加/2削除を直接確認した。全差分を読取確認し、製品は既に公開済みの初期行INSERTの移動と試験commit3行だけ、残る6文書はCI失敗の件数/公開公式仕様/設計/カードの記録だけ。新たなLINE原文・個人情報・credentials・secretsは差分に含まれない。既存の第2便3ファイル実装/検証/commit/push/PR委任の範囲内で、同じ公開先・自ブランチ・同じコマンドの1回だけ再審査へ出す。ガード解除や別経路は使わず、再拒否なら停止してPOへ戻す。修正後実PG未実施、検収REVISE。
受領確認: 同じ担当・自ブランチの指定HEADを通常pushするだけと返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 公開GitHub shingo-ops/salesanchorの自ブランチへ指定HEADの通常pushだけ。
禁止: 編集/commit/PR変更/merge、本番/ローカルDB実行、他ブランチ操作、強制送信、guard変更。失敗時は停止。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ、未保存0。
手順3: HEAD
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git rev-parse HEAD
    期待する出力: 9711cc40badfd01b2d77de8fe92d32b359e7ee79。一致しなければ停止。
手順4: push
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git push -u origin HEAD
    期待する出力: 指定自ブランチへ成功。
手順5: remote
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git ls-remote origin refs/heads/release/line-stock-storage
    期待する出力: 指定HEAD一致。完了報告に生出力を全文含めて停止。
END OF CARD
