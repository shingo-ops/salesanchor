本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-EMPTY-BOX-REVIEW-01

状態: 発行済み。設計PR #3464 / HEAD54469a74に保存済み、同一AI自己審査APPROVE。POが空箱対応の別実装担当への委任（実装・テスト・PR提出まで）に「進める」と回答。マージ・本番反映は対象外。
このカードは、空箱を状態として記録し、人の確認前の配信を止めるための実装指示書です。
設計: docs/handoff/tcg-product-master-growth/design-keyword.md §19（§18の技術草案を置換）。
親: docs/specs/product-master/README.md。ADR-113 / ADR-154、mode: handoff。
読んだ節: docs/ai-agents/design-partner.md §5.5、docs/handoff/design-partner-card-ops/guards/00-common.md、guards/11-lint.md。
自己照合: 1○ 記号保護、2○ ready PR、3○ 全文報告、4○ 空箱確認の1目的、5○ 公式机作り、6○ PR例、7○ 設計モデルと実装試験の区別。
人手照合: 未確定の代入目印なし。作業台は手順1で作る。設計保存と今回の明示委任を確認。POの番号付きGO原文は受領しておらず生成しない。

受領確認
最初に「CARD-LINE-EMPTY-BOX-REVIEW-01 受領」と返す。開始条件未充足なら実行せず設計パートナーへ返す。

担当・所有範囲
実装担当1名。ほかの担当も同じリポジトリを使用する。他者の変更を戻さず、並行差分を保持する。
以下を所有する。記載外の変更が必要なら契約を変えず設計担当へ戻す。
- migrations/20260913_150000_tcg_empty_box_condition.sql（新規）
- scripts/run_all_migrations.sh（登録1行のみ）
- backend/app/services/tcg_empty_box_rules.py（新規）
- backend/app/services/tcg_condition_review_svc.py（新規）
- backend/app/services/tcg_analyzer_svc.py
- backend/app/services/item_corrections_svc.py
- backend/app/services/tcg_analysis_review_svc.py
- backend/app/services/tcg_distribution_svc.py
- backend/app/routers/item_corrections.py
- backend/app/routers/tcg_analysis_review.py
- backend/tests/test_item_corrections.py
- backend/tests/test_tcg_analysis_review.py
- backend/tests/test_tcg_distribution.py
- backend/tests/test_unit_recovery.py（既存E5非上書きの回帰試験）
- backend/tests/test_tcg_empty_box_rules.py（新規）
- backend/tests/test_tcg_condition_review.py（新規、実PostgreSQL試験）
- frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx
- frontend/src/features/tcg-analysis-review/ItemComparison.tsx（型の接続のみ）
- frontend/src/features/tcg-analysis-review/reviewIssues.ts
- frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx（新規）
- frontend/src/features/tcg-analysis-review/ConditionReviewPanel.test.tsx（新規）
- frontend/src/locales/ja.json
- frontend/src/locales/en.json

禁止範囲
本番接続/本番DB変更、マージ、再解析、シート配信、Gemini呼出、secrets、CI設定、認証変更、商品辞書変更、追加エージェント起動は禁止。
設計/recon/根拠台帳/GO記録は設計担当所有。過去のSSH読取許可は消費済みで再付与しない。

開始条件
設計§19はPR #3464のHEAD54469a74を固定参照する。main未マージのため専用設計作業台から読み取り参照する。製品作業台はorigin/main起点。設計自己審査は独立レビューではない。
起動名・代理GO・本カードの存在で許可を補わない。既存の未保存差分を取り込まない。

手順0
  cd /Users/tanizawashingo/salesanchor && ./scripts/dev/executor-preflight.sh

手順1
  cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/line-empty-box-condition-review

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && git status --short

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && git rev-list --left-right --count HEAD...origin/main

手順4（実装）
§19.1の有限判定を共有定義からPythonとSQLへ生成し、CN0011を一般状態ループから除く。
明示はEmpty box、曖昧は要確認、否定だけなら従来判定。純粋な空箱備考以外を消費しない。
tenant_004に条件1行を登録。code/canonical競合・定義相違・部分欠落は変更前に停止する。
既存状態や他テナントを変更せず、再実行差分0。全TCG表なしの扱いは既存移行規約に合わせ、部分欠落を正常扱いしない。
§19.2のbinding/review_versionをPostgreSQLで一元生成する。Pythonで同じ指紋を独自再現しない。
§19.3のAPI、行ロック、要求再送、履歴の検証、選択肢取得を実装。旧fields経由の予約名保存は禁止する。
§19.4の同一有効判定を一覧/件数/正常完了/配信/プレビューにLIMITより前で適用する。
商品確認による解析skipでも状態確認を検査し、手動商品IDを保持する。
§19.5の既存画面内パネルを接続する。状態だけ確認しても他理由は保持し、Sheetsへ直接送らない。

手順5（必須試験）
設計モデル26表現・15確認状態を匿名の固定試験として再現する。私的LINE原文はGit/CIへ入れない。
26表現は実PostgreSQL16のSQLとPythonへ通し全一致。モデル試験41成功を実装試験の代用にしない。
移行初回/再実行/競合/部分欠落/他テナント保持、古い版409、別source404、無効状態422、拒否時変更0を確認。
同時操作2件、同一要求再送、同じID別内容、不正JSON/旧版履歴、確認前後の実DB状態を確認。
同じ内容の再解析では確認保持、原文/商品/単位/数値/状態定義変更では失効することを確認。
商品確認後/単位補完後の再確認、E5によるEmpty boxと手動状態の非上書きを確認。
画面の確認/訂正/保存中抑止/409再読込/他理由保持、一覧件数とページング一致を確認。
確認前の空箱配信0、確認後はEmpty boxを保ち他の配信条件を満たす場合のみ候補となることを確認。
実シートへの書込みは禁止。既存解析/訂正/レビュー/配信/単位回帰試験も実行する。
Dockerがない環境ではpytestを実行しない。静的検査とready PRを先行し、既存CIのPostgreSQLで必須試験を確認する。
SQLite・モックだけでDB試験合格にしない。未実施・skipは成功に数えない。

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review/backend && make lint-ci

手順7
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review/frontend && npm run check:all

手順8
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review/frontend && npm run test:unit -- --run src/features/tcg-analysis-review/ConditionReviewPanel.test.tsx

手順9
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && git diff --check

手順10
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-empty-box-condition-review && bash scripts/check-task-state.sh

手順11（保存・提出）
所有ファイルだけの差分を確認してコミットする。git log -1 --format=%Hで保存を確認後にpushする。
公式scripts/gh-pr-create-safe.shを使用してmain向けready PRを作成する。実施済み/未実施/失敗を本文で区別する。
PR本文は一時ファイルを作成して実改行で保存し、--body-fileで渡す。必須CIはgh pr checksとGitHub APIで確認する。
良いPR記載例: 「標準ワークフロー確認: 設計 docs/handoff/tcg-product-master-growth/design-keyword.md §19」。
禁止形: 未実施試験を成功と記す、対象外の差分を同梱する、POのGO原文を生成する。
所有範囲の実装不具合は修正・再検証し、設計変更が必要なら停止して設計担当へ返す。

完了報告と停止
冒頭「本報告はカード CARD-LINE-EMPTY-BOX-REVIEW-01 の実行結果である」。
設計パートナーへPR URL、HEAD、変更ファイル、検証の実測/未実施を報告し、生出力を全文含める。
停止時は手順番号、最後のコマンド、停止理由とエラー生出力を全文返す。
実装/試験/PR提出の状態を区別して停止。本番反映や実配信が完了したと報告しない。
END OF CARD
