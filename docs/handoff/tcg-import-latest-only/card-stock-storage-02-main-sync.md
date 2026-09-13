本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-MAIN-SYNC

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: PR3479はeab1609bでMERGEABLEだが、run-guard-evaluation.js:28のbase祖先条件に未達。main8d5aa581の実在をGitHubで直接確認。既に公開済みの自ブランチへ通常の統合コミットで取り込む。履歴置換や強制送信は使わない。これはmainへのマージや本番反映ではない。
受領確認: 同じ担当・公開済み自ブランチへの指定main取り込みだけであることを返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 指定main8d5aa58146dc81bc84ef5db0e60f835d23d17d29を自ブランチへ通常統合。自分の製品差分は3ファイル不変。親の文書commitが先行する。
禁止: 製品の手書き修正、他ブランチ操作、push/PR操作、mainへマージ、本番/DB実行、ガード変更。競合は報告停止し自己解決しない。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ、未保存0。
手順3: 統合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git merge --no-edit 8d5aa58146dc81bc84ef5db0e60f835d23d17d29
    期待する出力: 成功。競合/拒否なら停止し完了報告に生出力を全文含める。
手順4: 製品照合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && shasum -a 256 migrations/20260913_230000_tcg_stock_projection.sql backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: SQL0c68042e6de9b2c205916cf7f8c2f9d138dbe845e74a6d38c2b0a7204f783efa、試験a5227daa0e39f61e2f259ae7a99a8bea5ad1619094487767c81d5b354889174f。
手順5: 登録差分
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff 8d5aa58146dc81bc84ef5db0e60f835d23d17d29 -- scripts/run_all_migrations.sh
    期待する出力: 新SQLの末尾1行だけ。
手順6: 実在確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format='%H %s'
    期待する出力: 統合commit。報告して停止。pushは次便。
END OF CARD
