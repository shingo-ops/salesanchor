本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-DDL-ORDER

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親がCI job103688678583のcontrol初期行挿入後のCREATE INDEX失敗8件を確認。design.md「第2便の初期行・DDL順序と再適用の区切り」を自己審査APPROVE。実SQL/試験再合格は未確認。
受領確認: 同じ担当・新SQLと新試験2件だけの順序/試験区切り修正、commitまでと返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: 下記2ファイルだけの具体的修正・静的検査・commit。登録行は変更しない。
禁止: その他の製品/文書編集、他者変更の削除、push/PR/merge、本番/ローカルDB実行、制約緩和、例外握り潰し、試験省略、guard変更。失敗は報告停止。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ、未保存0。
手順3: SQL順序
    migrations/20260913_230000_tcg_stock_projection.sqlのcontrol初期行INSERT1文を、そのtenantの全DDLループ完了後、saved_path復元の直前へ移す。EXECUTEの括りを正しく付ける。INSERT本文、制約、索引、検査関数は一字も変えない。SQLへのCOMMIT/制約即時化/無効化は追加しない。
    期待する出力: 初期行の実行順序だけ変更。
手順4: 再適用試験
    backend/tests/test_tcg_stock_schema_pg.pyのtest_repeat_and_existing_data、test_existing_future_and_absent_tenantsで連続applyごとにpg.commit()を入れる。後者のbootstrap(pg, "tenant_953")直後にもcommitを入れる。他の6群、既定値None、全assert/負例を保持。
    期待する出力: ファイル単位の2回適用を再現。同一transactionの第4群は不変。
手順5: 静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && /private/tmp/line-stock-check-py312/bin/ruff check --no-cache backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: All checks passed。
手順6: 差分形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --check
    期待する出力: 終了0。
手順7: 差分確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --stat
    期待する出力: 指定SQLと試験2件だけ。
手順8: stage確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --name-only
    期待する出力: 空。
手順9: 指定2件stage
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git add migrations/20260913_230000_tcg_stock_projection.sql backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 終了0。
手順10: commit
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git commit -m "fix: initialize stock control after schema DDL"
    期待する出力: 成功。失敗は停止。
手順11: 実在確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format='%H %s' --stat
    期待する出力: 指定2件のcommit。完了報告に生出力を全文含めて停止。pushは別便。
END OF CARD
