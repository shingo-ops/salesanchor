本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-RETRY-PUSH

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親が9711cc40の指定2ファイルの差分を直接確認。SQL初期行移動と試験commit3行だけ。修正後実PGは未実施、検収REVISEを維持。
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
