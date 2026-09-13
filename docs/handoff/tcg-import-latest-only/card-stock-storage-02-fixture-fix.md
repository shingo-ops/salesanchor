本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-FIXTURE-FIX

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親がCI job103687400896の全8試験名とsetup error8を確認。queryが引数なしSQLへ空tupleを渡し、SQL内の%をパラメータとして処理してIndexError。Context7利用不可、許可済み代替でPsycopg公式cursor.execute(query, vars=None)とusageのパラメータ規則を照合。https://www.psycopg.org/docs/cursor.html / https://www.psycopg.org/docs/usage.html 。指定main統合HEAD3c0bc15eを親が確認。
受領確認: 同じ担当・試験共通関数の既定値1箇所だけを修正しcommitまで行うことを返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: backend/tests/test_tcg_stock_schema_pg.pyのquery関数のparams既定値を空tupleからNoneへ変更。パラメータ付き呼出しと既存SQL/試験条件は保持。検査・指定1件commitまで。
禁止: SQL/登録行/文書編集、他ファイルstage、push/PR操作、mainへのマージ、本番/ローカルDB実行、例外握り潰し、試験省略、guard変更。失敗は報告停止。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ、未保存0。
手順3: 指定1箇所修正
    Pythonで試験ファイルの def query(connection, statement, params=()): が1箇所だけあることをassertし、def query(connection, statement, params=None): に置換して保存する。
    期待する出力: 指定1行だけ変更。元SQL文字列は一切書き換えない。
手順4: 静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && /private/tmp/line-stock-check-py312/bin/ruff check --no-cache backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: All checks passed。
手順5: 差分
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff -- backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: queryの既定値1行だけ。
手順6: stage確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --name-only
    期待する出力: 空。
手順7: 指定1件stage
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git add backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 終了0。
手順8: commit
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git commit -m "test: execute stock fixture SQL without empty bindings"
    期待する出力: 成功。失敗時停止。
手順9: 実在確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format='%H %s' --stat
    期待する出力: 指定試験1件のcommit。完了報告に生出力を全文含めて停止。pushは別便。
END OF CARD
