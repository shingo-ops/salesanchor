本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

# CARD-ANALYSIS-RULE-P6-UI

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
照合結果: P1（マイグレーション）、P5（API/worker）、P4（配信接続）完了が前提。

担当: POがこのカードを渡した実装役。設計担当自身は実行しない。
目的: 完売ルール・日付ルールの管理画面をhub-shellサイドメニュー方式で実装する（C90）。金型コンポーネントとデザイントークンを使用し、ハードコードしない。
設計審査: 同一AIによる自己審査APPROVE（design §86.3）。本カードの実装許可はP6（管理画面UI）のみ。マージ/本番GOではない。
前提カード: CARD-ANALYSIS-RULE-P1-MIGRATION、CARD-ANALYSIS-RULE-P5-API-WORKER、CARD-ANALYSIS-RULE-P4-DISTRIBUTION が完了していること。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design
ブランチ: release/line-stock-message-design

許可: 以下ファイルの新規作成と既存ファイルの限定変更、読み取り調査。
新規ファイル:
    - frontend/src/pages/super-admin/AnalysisRulesPage.tsx（メインページ）
    - frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx（サイドメニュー）
    - frontend/src/pages/super-admin/components/SoldOutRulesPanel.tsx（完売ルール4サブタブ）
    - frontend/src/pages/super-admin/components/DateRulesPanel.tsx（日付ルール4サブタブ）
既存変更:
    - frontend/src/locales/ja.json（i18nキー追加）
    - frontend/src/locales/en.json（i18nキー追加）
    - frontend/src/App.tsx または該当ルーティングファイル（ルート追加1行）
禁止: 上記以外の既存製品コード編集、backend変更、migration追加、CI・scripts・secretsの編集、外部AI/Sheets/本番アクセス、文書/台帳/GO記録の編集、コミット/push/PR/マージ、サブエージェント起動。他者の変更を戻さない。

手順1: 必須preflight
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && ./scripts/dev/executor-preflight.sh
    期待する出力: PREFLIGHT OK。

手順2: ブランチ・未保存確認

手順3: P5のAPI存在確認
    backend/app/routers/tcg_analysis_rule.py が存在することを確認する。未存在なら停止。

手順4: 設計とUI前提の確認
    4a. design.md §5（UIレイアウト: hub-shell、サイドメニュー4項目、各ルール4サブタブ）を読む。
    4b. frontend/src/hub-shell.css を読み、既存のhub-shell金型クラスを確認する。
    4c. frontend/src/pages/orders/OrdersPage.tsx（行62-124）を読み、hub-shellの実装パターンを確認する。
    4d. docs/CC_UI_GOVERNANCE.md を読み、UIガバナンスルール（ADR-144）を確認する。
    4e. frontend/src/components/ の既存金型コンポーネントを確認する。

手順5: ページ実装
    design §5 と C90 に従い、以下の構造で実装する:

    AnalysisRulesPage.tsx:
    - hub-shell レイアウト（hub-shell.css のクラスを使用）
    - 左: AnalysisRulesSidebar（200px固定、hub-subnav クラス）
    - 右: 選択に応じた Panel（hub-content クラス）
    - レスポンシブ: 850px以下で横並び、540px以下でアプリサイドバー非表示

    AnalysisRulesSidebar.tsx:
    - グループヘッダー「解析状況」「ルール管理」
    - 4項目: 解析精度管理、要確認、完売ルール、日付ルール
    - アクティブ状態のスタイルは hub-shell.css のクラスを使用（ハードコード禁止）

    SoldOutRulesPanel.tsx:
    - 4サブタブ: ルール一覧、テスト、テスト結果、有効化
    - 各タブの内容は P5 の API を呼び出して表示
    - タブコンポーネントは既存金型を使用（生select/生input禁止、ADR-144）
    - 完売判断結果の無効化表示（invalidated_at IS NOT NULL のものはグレーアウト等）
    - 有効化ボタン: テスト未合格時は非活性（C91）
    - 配信エラー表示: tcg_distribution_targets.last_result のエラーを表示（C96）

    DateRulesPanel.tsx:
    - SoldOutRulesPanelと同じ4サブタブ構造
    - policy_type='date-format'でAPIを呼び出す
    - フォーマットテンプレート（MM月DD日入荷予定）の編集UI（C88）

手順6: i18n
    全UI文字列を t("key") 経由にする（ADR-027）。
    ja.json と en.json に同一キーで追加する。ハードコード日本語は絶対禁止。
    キー命名例: analysisRules.sidebar.soldOut, analysisRules.tabs.ruleList 等。

手順7: frontend静的検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/frontend && npm run lint
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/frontend && npx tsc --noEmit
    期待する出力: lint成功、型検査成功。

手順8: i18nセルフチェック
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design/frontend && grep -rn 'ルール\|完売\|日付\|解析\|テスト結果\|有効化' src/pages/super-admin/ --include='*.tsx' | grep -v 't(' | grep -v '//' | grep -v 'import'
    期待する出力: 0件（ハードコード日本語なし）。ヒットがあれば t() 経由に修正する。

手順9: 範囲検査
    cd /Users/tanizawashingo/worktrees/salesanchor/release-line-stock-message-design && git status --short --untracked-files=all
    期待する出力: 新規4ファイル + 既存3ファイルの変更のみ。その他の差分0。
    全ファイル全文/diff全文を設計担当へ返して停止する。

失敗・不明・契約矛盾・権限拒否があれば該当操作で停止し、コマンドと生出力全文を返す。
報告: CARD ID、ブランチとHEAD、全ファイル全文/diff、各検証のコマンド/生出力。
backend変更・本番適用・マージはこのカードでは未実施と明記する。
END OF CARD
