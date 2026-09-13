本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-TEST-COMMIT

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: RESUME完了を親が実HEADとdiffで確認。SQLは変更なし。試験の変更は承認済みの原文削除拒否1件と冒頭説明だけ。実PGの成功とは扱わない。
受領確認: 同じ担当・指定ファイル1件だけのcommitであることを返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 既存の試験変更1件を静的検査してcommit。編集は禁止。親の文書が未保存でも触らず残す。
禁止: 文書/製品の追加編集、他ファイルstage、push/PR/merge、本番/DB実行、許可発行、ガード変更。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 対象照合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && shasum -a 256 backend/tests/test_tcg_stock_schema_pg.py migrations/20260913_230000_tcg_stock_projection.sql
    期待する出力: 試験a5227daa0e39f61e2f259ae7a99a8bea5ad1619094487767c81d5b354889174f、SQL0c68042e6de9b2c205916cf7f8c2f9d138dbe845e74a6d38c2b0a7204f783efa。一致しなければ停止。
手順3: 静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && /private/tmp/line-stock-check-py312/bin/ruff check --no-cache backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: All checks passed。
手順4: stage確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --name-only
    期待する出力: 空。他者のstageがあれば停止。
手順5: 指定試験のみstage
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git add backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 終了0。
手順6: stage確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --stat
    期待する出力: 指定試験1件だけ。
手順7: commit
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git commit -m "test: cover stock source removal refusal"
    期待する出力: 成功。失敗は迂回せず停止。
手順8: 確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format='%H %s' --stat
    期待する出力: commit実在と指定1ファイル。報告して停止。
END OF CARD
