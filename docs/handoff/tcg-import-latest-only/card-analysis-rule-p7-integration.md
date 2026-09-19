本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-ANALYSIS-RULE-P7-INTEGRATION

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: P1/P4/P5/P6の全カード完了が前提。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。
目的: 全工程の一貫試験を実施し、§56.4の検収条件96件に対する検証状態を更新する。本番切替準備のための最終確認。
設計審査: 同一AIによる自己審査APPROVE（design §86.3）。本カードの実装許可はP7（一貫試験）のみ。マージ/本番GOではない。
前提カード: CARD-ANALYSIS-RULE-P1-MIGRATION、CARD-ANALYSIS-RULE-P5-API-WORKER、CARD-ANALYSIS-RULE-P4-DISTRIBUTION、CARD-ANALYSIS-RULE-P6-UI がすべて完了していること。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design
ブランチ: release/line-stock-message-design

許可: 試験ファイルの新規作成、読み取り調査、既存テストの実行。
新規ファイル:
    - backend/tests/analysis_rule/test_integration_e2e.py（一貫試験）
禁止: 既存製品コード・設定・依存・migration・CI・scripts・secretsの編集、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、コミット/push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ./scripts/dev/executor-preflight.sh

手順2: ブランチ・未保存確認

手順3: 全前提カードの成果物存在確認
    以下がすべて存在することを確認する。未存在なら停止。
    - migrations/ 内の analysis_rule マイグレーションファイル
    - backend/app/routers/tcg_analysis_rule.py
    - backend/app/services/tcg_analysis_rule_svc.py
    - backend/app/tasks/tcg_analysis_rule.py
    - frontend/src/pages/super-admin/AnalysisRulesPage.tsx

手順4: 一貫試験の実装
    test_integration_e2e.py に以下の一貫フローをテストする:

    フロー1: 完売ルール管理の基本フロー
    - API: GET current → POST draft-revisions → POST test-suites → POST test-runs → GET test-runs/{id} → POST activate → GET history
    - 検証: 各ステップで期待するレスポンスが返ること

    フロー2: 商品手動修正→無効化フロー（C93）
    - 完売判断実行 → 商品紐付け修正 → invalidated_at記録確認 → 配信クエリから除外確認

    フロー3: 空テキスト弾きフロー（C94）
    - 空テキストのsource_message → extraction status='empty' → analysis_rule_runs未作成

    フロー4: 再読み取り→最新結果のみ使用フロー（C95）
    - 1回目抽出（3件）→ 再抽出（5件）→ 完売判断 → 5件のみ対象

    フロー5: 配信安全装置フロー（C96）
    - analysis_rule_runs state='running' → 配信実行 → 中止確認

    フロー6: policy_type分離（C92）
    - sold_outルール追加 → date_formatクエリ → sold_outデータが含まれないこと

    フロー7: テスト不合格→有効化不可（C91）
    - テスト実行（不合格）→ POST activate → 拒否されること

手順5: 既存テスト実行
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/backend && python3 -m pytest tests/analysis_rule/ -v
    期待する出力: 全テスト成功。

手順6: frontend検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/frontend && npm run lint && npx tsc --noEmit
    期待する出力: lint成功、型検査成功。

手順7: §56.4検収条件との照合
    design.md §56.4の96件（C01-C96）を読み、本カードで検証できた項目とできていない項目を分類する。
    - 検証済み: テストで確認できた項目に「検証済み」マークを付ける
    - 未検証: 本番環境/実データでしか確認できない項目を明記する
    検収テーブルの更新はこのカードの範囲外（文書編集禁止）。照合結果を報告する。

手順8: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --untracked-files=all
    期待する出力: 新規1ファイルのみ。その他の差分0。

報告: CARD ID、ブランチとHEAD、テスト結果全文、§56.4との照合結果、検証済み/未検証の件数。
本番適用・マージ・データ移行はこのカードでは未実施と明記する。
設計合格をマージ/本番GOとみなさない。マージにはPOの明示的GOが必要。
END OF CARD
