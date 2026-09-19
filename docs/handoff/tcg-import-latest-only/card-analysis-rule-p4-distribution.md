本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-ANALYSIS-RULE-P4-DISTRIBUTION

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: P1（マイグレーション）とP5（API/worker）完了が前提。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。
目的: Google Sheets配信に完売判断結果を反映する。安全装置#8c追加とリトライ機構を実装する（C96）。
設計審査: 同一AIによる自己審査APPROVE（design §86.3）。本カードの実装許可はP4（配信接続）のみ。マージ/本番GOではない。
前提カード: CARD-ANALYSIS-RULE-P1-MIGRATION、CARD-ANALYSIS-RULE-P5-API-WORKER が完了していること。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design
ブランチ: release/line-stock-message-design

許可: 以下ファイルの限定変更と試験ファイルの新規作成、読み取り調査。
既存変更:
    - backend/app/services/tcg_distribution_svc.py（安全装置#8c追加・リトライ追加・配信クエリ変更）
新規ファイル:
    - backend/tests/analysis_rule/test_distribution_integration.py（配信統合試験）
禁止: 上記以外の既存製品コード編集、migration追加、CI・scripts・secretsの編集、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、コミット/push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。

手順2: ブランチ・未保存確認

手順3: P1/P5の成果物存在確認
    マイグレーションファイルとtcg_analysis_rule_svc.pyが存在することを確認する。未存在なら停止。

手順4: 設計の確認
    design.md §14.1.4（C96: リトライ・安全装置）、§14.1.1（C93: invalidated_at除外）を読む。

手順5: 安全装置#8c追加
    tcg_distribution_svc.py の配信ランナー（行629-702付近）に安全装置#8cを追加する。
    既存の#8（行650-656）と#8b（行679-687）の直後に配置:
    ```python
    # Safety guard #8c: analysis rule runs in progress
    pending_rule_runs = (
        await db.execute(
            text(
                f"SELECT id, started_at FROM {TCG_SCHEMA}.analysis_rule_runs"
                " WHERE state IN ('pending', 'running')"
                " ORDER BY started_at LIMIT 10"
            )
        )
    ).mappings().all()
    if pending_rule_runs:
        # 配信中止: ルール判断が実行中
        ...（既存の#8/#8bと同じエラー報告形式で）
    ```

手順6: 配信クエリへのinvalidated_at除外追加
    tcg_distribution_svc.py の出力データ取得SQL（行183-245付近）に、
    analysis_rule_run_resultsのinvalidated_at IS NULLフィルターを追加する。
    ※ analysis_rule_run_resultsが配信対象データに結合される場合のみ。
    結合がまだ不要な場合（P5で完売判断が配信フローにまだ接続されていない場合）はスキップして明記する。

手順7: Sheets書き込みリトライ追加
    tcg_distribution_svc.py の個別配信先へのシート書き込み処理にリトライを追加する:
    - 最大4回再試行（指数バックオフ: 1秒→2秒→4秒→8秒）
    - 4回失敗でエラー記録 + Discord通知（既存仕組み維持）
    - 個別配信先の失敗は他の配信先に影響しない（既存動作維持）

手順8: アプリ画面エラー表示の準備
    配信失敗をアプリ画面に表示するために、tcg_distribution_targets テーブルの last_result カラムに
    エラー詳細を記録する。UIでの表示はP6カードで実装する。

手順9: 統合試験
    test_distribution_integration.py に以下のテストを実装:
    - 安全装置#8c: analysis_rule_runs pending/running中に配信が中止されること
    - リトライ: 1回目失敗→2回目成功のケースで配信が完了すること
    - リトライ上限: 4回連続失敗でエラー記録されること
    - invalidated_at除外: 無効化された結果が配信データに含まれないこと（結合が存在する場合）

手順10: backend静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/backend && make lint-ci

手順11: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --untracked-files=all
    期待する出力: 既存1ファイルの変更 + 新規1ファイルのみ。その他の差分0。
    既存ファイルのdiff全文と新規ファイル全文を設計担当へ返して停止する。

失敗・不明・契約矛盾・権限拒否があれば該当操作で停止し、コマンドと生出力全文を返す。
報告: CARD ID、ブランチとHEAD、既存ファイルdiff全文、新規ファイル全文、各検証のコマンド/生出力。
画面UI・本番適用・マージはこのカードでは未実施と明記する。
END OF CARD
