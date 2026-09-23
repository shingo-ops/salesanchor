本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-RESUME

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親は台帳競合を双方保持で解決・stage済み、未解決0を再確認。POは追従続行と拒否負例保存に限定して「進める」、通常ターミナルの承認登録について「完了」と返答した。PO承認の範囲内で同じ担当を再開する。チケットの有効性は操作時のガード結果で確認する。
受領確認: 同じ担当・作業台・追従続行と負例1件だけの編集を返す。
担当: stock_contract_01。他者と共同作業中。他者変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
許可: 親が解決済みの追従続行、保全SQL/試験hash照合、承認済み負例1件の試験ファイルへの追加と静的検査。
禁止: 競合自己解決、skip/abort、permit自己発行、DB実行、他ファイルの製品変更、push/PR/merge/本番操作、文字列分割や別ツールによる拒否回避。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 未解決
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --name-only --diff-filter=U
    期待する出力: 0件。
手順3: 続行
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && GIT_EDITOR=true git rebase --continue
    期待する出力: 成功。新たな競合/拒否/失敗は停止して報告。
手順4: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: release/line-stock-storage、clean。
手順5: 保全照合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && shasum -a 256 migrations/20260913_230000_tcg_stock_projection.sql backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: SQL0c68042e6de9b2c205916cf7f8c2f9d138dbe845e74a6d38c2b0a7204f783efa、試験ec921a76d83e7011eb0a95dac6ee8ff97a5b153587c7a982890b87c54359cfab。
手順6: 登録照合
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff 7dcb9ce982af39b3b6ef9c1089fe1255952ae37a -- scripts/run_all_migrations.sh
    期待する出力: 新SQL登録の末尾1行だけ。
手順7: 承認された負例の保存
    前回最終報告で提示した追加予定コードだけをtest_event_integrityの保留コメント位置へ保存する。対象source1件の削除要求がpsycopg2.errors.ForeignKeyViolationになること、rollback後にsource1件/event1件が残ることをassertする。冒頭docstringと保留コメントの未保存説明を実態に合わせて更新してよい。その他の試験・SQL・登録は編集しない。DB実行はしない。
    期待する出力: backend/tests/test_tcg_stock_schema_pg.pyだけ変更。ガードが拒否した場合は停止し、別表記・別ツールへ変えない。
手順8: 静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && /private/tmp/line-stock-check-py312/bin/ruff check --no-cache backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 成功。
手順9: 形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --check
    期待する出力: 指摘0。
手順10: 差分報告
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff -- backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 指定負例と未保存説明の更新だけ。HEAD/hash/静的検査を報告し停止。実PG未実施を明示。
END OF CARD
