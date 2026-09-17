本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-ANALYSIS-RULE-P5-API-WORKER

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: P1（マイグレーション）完了が前提。テーブルが存在しない場合は停止する。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。受領確認としてカードID・作業台・変更ファイルの範囲を最初に返す。
目的: 完売ルール・日付ルールのAPI 9エンドポイントと完売判断workerを実装する。共通router/serviceでpolicy_typeにより種別を切り替える。
設計審査: 同一AIによる自己審査APPROVE（design §86.3）。本カードの実装許可はP5（API/worker）のみ。マージ/本番GOではない。
前提カード: CARD-ANALYSIS-RULE-P1-MIGRATION が完了していること。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design
ブランチ: release/line-stock-message-design

許可: 以下ファイルの新規作成と既存ファイルの限定変更、同ファイルの試験、読み取り調査。
新規ファイル:
    - backend/app/routers/tcg_analysis_rule.py（API 9エンドポイント）
    - backend/app/services/tcg_analysis_rule_svc.py（共通サービス）
    - backend/app/tasks/tcg_analysis_rule.py（完売判断worker）
    - backend/tests/analysis_rule/test_tcg_analysis_rule_svc.py（サービス単体試験）
既存変更:
    - backend/app/main.py（routerの登録追加のみ、1-2行）
    - backend/app/services/item_corrections_svc.py（C93: product_id変更時のinvalidated_at記録追加）
    - backend/app/tasks/tcg_extraction.py（C94: 空テキストチェック追加、1行）
禁止: 上記以外の既存製品コード編集、migration追加、CI・scripts・secretsの編集、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、コミット/push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。

手順2: ブランチ・未保存確認
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --branch
    期待する出力: 上記ブランチ、追跡ファイルの未保存変更0件。

手順3: P1テーブル存在確認
    P1マイグレーションファイルが migrations/ に存在することを確認する。
    期待する出力: analysis_rule関連のマイグレーションファイルが存在。未存在なら停止。

手順4: 設計の確認
    design.md §6.2（API 9EP一覧）、§14.1（配信確定仕様）、§16.4（候補ファイル）を読む。

手順5: サービス実装（tcg_analysis_rule_svc.py）
    design §6.2 の9エンドポイントに対応する関数を実装する:
    - get_current_state(policy_type) → active/draft/suiteのID、lock_version、activation_state
    - get_revision_rules(revision_id, query_params) → 語句一覧（word_kind フィルター対応）
    - create_draft_revision(policy_type, changes, lock_version, request_key) → 新版作成+draft更新
    - save_test_suite(policy_type, cases, request_key) → 正解例保存
    - start_test_run(policy_type, revision_id, suite_revision_id, request_key) → テスト実行開始（202）
    - get_test_run_result(run_id) → 結果取得
    - activate_revision(policy_type, revision_id, run_id, lock_version, request_key) → 本番適用
    - get_history(policy_type, cursor) → 変更履歴
    - get_revision_detail(revision_id) → 版の全内容

    design §14.1.3（C95）: 本番判断は最新成功jobのitemsのみ対象。latest_jobクエリを使用する。
    design §14.1.1（C93）: activate時にinvalidated_at IS NULLの結果のみ使用する。
    request_keyによる冪等性を保証する（UNIQUE制約で重複排除）。
    lock_versionによる楽観的ロック（UPDATE ... WHERE lock_version = :expected）。

手順6: ルーター実装（tcg_analysis_rule.py）
    ベースパス: /api/v1/super-admin/analysis-policies/{policy_type}
    policy_type は sold-out または date-format（URLはkebab-case、DB値はsnake_case）。
    認証: require_super_admin（既存の認証デコレータを使用）。
    9エンドポイントをdesign §6.2の表に従って実装する。

手順7: worker実装（tasks/tcg_analysis_rule.py）
    Celeryタスクとして完売判断workerを実装する:
    - run_analysis_rule_task(run_id) → analysis_rule_runsのstateをrunning→passed/failed/errorに更新
    - テスト実行（purpose='test'）: suite内の全caseに対してルールマッチングを実行
    - 本番実行（purpose='production'）: source_messageのextraction_items（C95: 最新jobのみ）に対して実行
    - 結果をanalysis_rule_run_resultsに記録

手順8: 既存ファイル変更
    8a. backend/app/main.py: tcg_analysis_ruleルーターを登録（include_router 1行追加）
    8b. backend/app/services/item_corrections_svc.py: save_corrections() 内のproduct_id変更処理（行56-70）の直後に、
        当該extraction_item_idを参照するanalysis_rule_run_resultsのinvalidated_atをNOW()で更新するSQLを追加（C93）
    8c. backend/app/tasks/tcg_extraction.py: 行155の直後に空テキストチェック追加（C94）:
        if len(raw_text.strip()) == 0: → status='empty'でGeminiスキップ

手順9: 単体試験
    test_tcg_analysis_rule_svc.py に以下のテストを実装:
    - request_keyの冪等性（同じkeyで2回呼んでもエラーにならない）
    - lock_versionの競合検出（古いversionで更新するとエラー）
    - policy_typeフィルター（sold_outクエリがdate_formatデータを返さない）
    - invalidated_atの除外（無効化された結果が配信クエリに含まれない）
    - 空テキストチェック（strip後0文字でstatus='empty'）
    - 最新jobフィルター（C95: 複数jobで最新のみ使用）

手順10: backend静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/backend && make lint-ci
    期待する出力: 必須検査成功。

手順11: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --untracked-files=all
    期待する出力: 新規4ファイル + 既存3ファイルの変更のみ。その他の差分0。
    新規ファイル全文と既存ファイルのdiffを設計担当へ返して停止する。

失敗・不明・契約矛盾・権限拒否があれば該当操作で停止し、コマンドと生出力全文を返す。
報告: CARD ID、ブランチとHEAD、新規4ファイル全文、既存3ファイルのdiff全文、各検証のコマンド/生出力。
画面・配信リトライ・本番適用・マージはこのカードでは未実施と明記する。
END OF CARD
