本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-LINE-STOCK-STORAGE-02-CONNECTION-FIX

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md。
照合結果: 親取得CI job103690386821は3267成功/95skip/第4群のみ1失敗。2本目のpg.dsn接続で認証失敗。Psycopg公式はconnection.dsnのパスワードを隠す仕様、connectのキーワード引数がDSNを上書き可能と説明。https://www.psycopg.org/docs/connection.html / https://www.psycopg.org/docs/module.html 。Context7利用不可、許可済み公式代替で2026-09-13確認。同じ試験用接続先/DBを保持し、既にfixtureが検証したCI用環境変数のpasswordだけを追加引数に渡す設計補正を自己審査APPROVE。秘密値の表示・保存・変更はしない。
受領確認: 同じ担当・試験第4群の2本目接続1箇所の修正とcommitのみと返す。
担当: stock_contract_01。他者と共同作業中。他者の変更を戻さない。新規担当禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage
ブランチ: release/line-stock-storage
許可: backend/tests/test_tcg_stock_schema_pg.pyの下記1箇所だけ修正し静的検査/commit。試験用の既存CI環境変数を実行時に読む式だけで、実際の秘密値をこの端末で読む/表示する操作はしない。
禁止: SQL/登録/他製品/文書編集、secrets/CI設定変更、接続先変更、試験省略、push/PR/merge、本番/ローカルDB実行、ガード変更。失敗時は報告停止。

手順1: preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。
手順2: 状態
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git status --short --branch
    期待する出力: 自ブランチ・未保存0。
手順3: 指定1箇所修正
    second = psycopg2.connect(pg.dsn) が1箇所だけあることをassertし、second = psycopg2.connect(pg.dsn, password=make_url(os.environ["RLS_ADMIN_DATABASE_URL"]).password) に置換して保存する。構文上の行折返しだけは許可。
    期待する出力: 第4群の同じDBへの接続補正だけ。全assert・タイムアウト・トランザクション処理・他7群は不変。
手順4: 静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && /private/tmp/line-stock-check-py312/bin/ruff check --no-cache backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: All checks passed。
手順5: 差分形式
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --check
    期待する出力: 終了0。
手順6: 差分
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --stat
    期待する出力: 指定試験1件だけ。
手順7: stage確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git diff --cached --name-only
    期待する出力: 空。
手順8: stage
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git add backend/tests/test_tcg_stock_schema_pg.py
    期待する出力: 終了0。
手順9: commit
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git commit -m "test: authenticate isolated stock concurrency connection"
    期待する出力: 指定1件commit成功。失敗時停止。
手順10: 実在確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-storage && git log -1 --format='%H %s' --stat
    期待する出力: 指定1件のcommit。完了報告に生出力を全文含めて停止。pushは別便。
END OF CARD
