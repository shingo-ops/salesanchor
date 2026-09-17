本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-ANALYSIS-RULE-P1-MIGRATION

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: 実在する専用作業台を指定。実装内容はdesign §4.9のDDLに固定。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。受領確認としてカードID・作業台・変更ファイルの範囲を最初に返す。
目的: 完売ルール・日付ルールの共通テーブル13表をDBに作成する。analysis_*共通名でpolicy_typeにより種別を識別する（C92）。
設計審査: 同一AIによる自己審査APPROVE（design §86.3）。本カードの実装許可はP1（DBマイグレーション）だけ。マージ/本番GOではない。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design
ブランチ: release/line-stock-message-design
このカードを引き渡す時点で設計担当は編集を終了する。受領者が正規にこの作業台を利用できる場合だけ続行する。所有制御の拒否を解除しない。

許可: 以下1ファイルの新規作成、読み取り調査。
変更ファイル: migrations/YYYYMMDD_HHMMSS_create_analysis_rule_tables.sql（タイムスタンプは実行時に最新既存+1で決定）。
禁止: 既存製品コード・設定・依存・既存migration・CI・scripts・secretsの編集、既存呼出元への接続、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、コミット/push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。成功した場合のみ次へ。

手順2: 作業ブランチと未保存変更を確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --branch
    期待する出力: 上記ブランチで、追跡ファイルの未保存変更0件。別ブランチや追跡ファイルの未保存変更があれば編集を停止して全文報告する。

手順3: 既存マイグレーション命名慣例を確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ls -1 migrations/*.sql | tail -5
    期待する出力: 最新ファイルのタイムスタンプを確認。新ファイルのタイムスタンプはこれより後にする。

手順4: 既存テーブルとの名前衝突確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && grep -r 'analysis_policies\|analysis_rule_runs\|analysis_rule_run_results' migrations/ --include='*.sql'
    期待する出力: 0件。衝突がある場合は停止して報告する。analysis_runsは既存テーブル（別物）なので衝突しない。

手順5: マイグレーションファイル作成
    design.md §4.9のDDL全文をマイグレーションファイルとして作成する。
    ファイル構成:
    - ファイル先頭にコメント: -- Analysis Rule Tables for Sold-Out and Date Format Rules (C92)
    - DO $$ ... BEGIN ... END $$; ブロック内にSET search_path、%Iを実スキーマ名に置換
    - 既存マイグレーション（20260906_120000_create_tcg_tables_t001.sql）と同じ実行形式を採用
    - 13テーブル + ALTER TABLE（自己参照FK）+ 初期データINSERT（sold_out/date_formatの2行をanalysis_policiesに投入）

    作成するテーブル（設計§4.9の順序で）:
    1.  analysis_policies
    2.  analysis_policy_revisions
    3.  analysis_instruction_versions
    4.  analysis_execution_profile_versions
    5.  analysis_rules
    6.  analysis_rule_versions
    7.  analysis_rule_words
    8.  analysis_revision_rules
    9.  analysis_test_case_versions
    10. analysis_test_suites
    11. analysis_suite_cases
    12. analysis_rule_runs
    13. analysis_rule_run_results

    FK参照（設計§4.9で確定済み）:
    - analysis_rule_runs.source_message_id → source_messages(id) ON DELETE CASCADE
    - analysis_rule_run_results.extraction_item_id → extraction_items(id) ON DELETE CASCADE
    - analysis_rule_run_results.case_version_id → analysis_test_case_versions(id)
    - analysis_rule_run_results に invalidated_at TIMESTAMPTZ カラム
    - analysis_rule_run_results に部分INDEX（WHERE invalidated_at IS NULL）

    初期データ:
    - analysis_policies に sold_out と date_format の2行をINSERT（activation_state='inactive'）

    設計§4.9のDDLをそのまま使い、独自の変更を加えない。

手順6: マイグレーションの構文検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && python3 -c "
    with open('migrations/作成したファイル名.sql') as f:
        sql = f.read()
    # 13テーブルのCREATE TABLE IF NOT EXISTSが存在することを確認
    import re
    tables = re.findall(r'CREATE TABLE IF NOT EXISTS\s+\S+\.(\w+)', sql)
    print(f'Tables found: {len(tables)}')
    for t in tables:
        print(f'  - {t}')
    assert len(tables) == 13, f'Expected 13 tables, found {len(tables)}'
    # invalidated_atカラムの存在確認
    assert 'invalidated_at' in sql, 'Missing invalidated_at column'
    # 初期データINSERTの存在確認
    assert 'sold_out' in sql and 'date_format' in sql, 'Missing initial data'
    print('Structure check: PASS')
    "
    期待する出力: Tables found: 13、各テーブル名、Structure check: PASS。

手順7: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --untracked-files=all
    期待する出力: 指定1ファイルだけが新規。その他の差分0。新規ファイル全文を設計担当へ返して停止する。

失敗・不明・契約矛盾・権限拒否があれば該当操作で停止し、コマンドと生出力全文を返す。許可の自己発行やチェック変更で回避しない。
報告: CARD ID、実際のブランチとHEAD、変更1ファイル全文、各検証のコマンド/生出力、未実施の検証を区別する。
API・画面・配信・テスト実行・本番適用はこのカードでは未実施と明記する。
END OF CARD
