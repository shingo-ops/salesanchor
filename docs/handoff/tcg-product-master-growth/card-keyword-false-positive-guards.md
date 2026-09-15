本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-KEYWORD-GUARDS-01

この文書は、別商品への確定を止める辞書3操作を実装する指示書です。
親: docs/specs/product-master/README.md
設計: docs/handoff/tcg-product-master-growth/design-keyword.md §11（特に§11.8）。mode: handoff。
対象ADR: ADR-154 / ADR-113。既存商品判定機構内の辞書修正で、プロンプト・API契約は変更しない。
読んだ節: docs/ai-agents/design-partner.md §5.5、docs/handoff/design-partner-card-ops/guards/00-common.md、guards/11-lint.md。
自己照合: 1○ 記号をコード表記、2○ ready PR、3○ rootへ全文報告、4○ 辞書3操作1目的、5○ 既存専用作業場所と起点明示、6○ 本文例指定、7○ 実測と期待値を設計へ固定。

受領確認
最初に「CARD-LINE-KEYWORD-GUARDS-01 受領」と返す。

承認
PO原文「承認する、修正から」「本番反映まで実施してくれ、」を受領済み。日時は2026-09-10 JST、時分未取得。
本担当は実装・試験・PR提出までを担い停止。rootがレビュー後のマージ・本番確認を担う。
実装の承認を再取得しない。今回の原文をPRのGO記録へそのまま転記し、GO番号を創作しない。

所有範囲
既存worktree /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit を使用する。
ブランチはrelease/line-postdeploy-audit、origin/main 864ace72起点、既存設計コミットcfb42e65と本カード保存コミットを保持。
他者と同じ作業場所を使っている。既存変更を戻さず、rootの文書作業と整合させる。
製品変更は migrations/20260910_170000_tcg_keyword_false_positive_guards.sql、scripts/run_all_migrations.sh の登録1行、backend/tests/test_tcg_work_matching_integration.py の試験追加だけ。
root所有のrecon・設計・根拠登録・tasks・本カードは変更しない。既存文書コミットを含めた同じPRで提出する。

禁止
本番DB直接更新、既存結果の再解析、配信、マージ、CI設定・deploy.yml・secrets変更、他テナント変更、追加サブエージェント、ガード迂回を禁止する。
PM0199の検索語追加は却下済みであり実装しない。検索語の数字境界・モデルのプロンプト・新規商品登録は対象外。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit && ./scripts/dev/executor-preflight.sh
手順1
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit && git status --short
手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit && git rev-list --left-right --count HEAD...origin/main

手順3（実装）
設計§11.2の3操作だけを§11.3/11.8どおり単一トランザクションのmigrationへ実装する。
対象TCG表0なら変更0。一部欠落・3商品同一性不一致・対象語重複なら変更前に停止。再実行差分0。
既存runnerの末尾にSQLを1回登録する。既存内容を保持する。

手順4（実DB検証）
既存試験の使い捨てCIデータベース内に、既存正本migration経由でtenant_004を用意して検証する。
本番ホスト・本番DBへ試験を接続しない。ローカルDockerがない場合は既存CIのPostgreSQLへ進む。
16合成例と誤判定10明細は /private/tmp/line-dictionary-safe-contrast.json の商品表記と期待のみを匿名fixture化する。生原文・顧客データをGitへ入れない。
期待: 初回検索1行減・除外2行増、再実行差分0、対象商品以外と他tenantの全辞書不変、商品名/作品/区分不一致と重複の全件原状保持、TCG表0変更0、一部欠落停止。
現状辞書から改定辞書へ同じfixtureを通し、誤商品10→NONE、正常例維持、状態/備考除外、Vol.10/11の誤確定0を確認。
745行・293名称は設計側の実測であり、CIに生データをコピーしない。既存TCG回帰試験も通す。fixture自身の結果だけを成功件数として報告する。

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit/backend && make lint-ci
手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit && git diff --check
手順7
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-postdeploy-audit && bash scripts/check-task-state.sh

手順8（提出）
ローカル検査後、所有3ファイルだけをコミットし git log -1 --format=%H で保存を確認してpushする。
公式scripts/gh-pr-create-safe.shでmain向けready PRを作る。最終本文は実ファイルに保存し--body-fileで渡す。
良い本文例: 「### 標準ワークフロー確認」の中に「設計: docs/handoff/tcg-product-master-growth/design-keyword.md」を記す。
触る/削除するファイル欄は既存の文書変更も含む実差分の全パスを記す。未検査を合格にしない。
GO記録は発行者しんごさん、日時日付のみ、上記原文2件、バックアップは既存deployの事実と今回反映前の工程を分けて書く。
技術CIは全確認する。gh pr checksとGitHub APIを使用する。失敗は根拠を調べ、所有範囲内で修正可能なら修正して再検証する。

完了報告と停止
報告冒頭「本報告はカード CARD-LINE-KEYWORD-GUARDS-01 の実行結果である」。rootへPR URL・HEAD・変更一覧・検証結果・実行ログの保存先と生出力を全文報告する。
停止時は停止した手順番号／最後のコマンド／理由と生出力をrootへ返す。設計にない判断は自力拡張しない。
END OF CARD
