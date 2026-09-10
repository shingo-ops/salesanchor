本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-CONDITION-NOTE-01

この文書は、配信前の状態とNOTE_JAをマスタ・再解析で訂正する実装指示です。
読んだ節: docs/ai-agents/design-partner.md §5.5、guards/00-common.md、guards/11-lint.md、backend/AGENTS.md。
自己照合: 実在作業台、設計§13、所有5ファイル、実DB受入、ready PR、停止報告を確認。mode: handoff。ADR-113 / ADR-154。
設計: docs/handoff/tcg-product-master-growth/design-keyword.md §13。親: docs/specs/product-master/README.md。

受領確認
最初に「CARD-LINE-CONDITION-NOTE-01 受領」と返す。

PO承認
原文「配信まで完了させてくれ」「通常カートンだがNOTE_JAに記載」を受領。既存の修正・反映・配信の依頼を継続する。
番号付きGOを創作しない。rootが正規GO確認・本番反映後の再解析・配信を担う。

所有範囲
作業台 /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record、release/line-recovery-delivery-record。
origin/main起点、最新origin/mainはrootが通常取り込み済み。
所有する製品ファイルは以下5件だけ。
backend/app/services/tcg_analyzer_svc.py
backend/tests/test_tcg_keyword_matching.py
backend/tests/test_tcg_work_matching_integration.py
migrations/20260910_200000_tcg_condition_note_delivery_t004.sql
scripts/run_all_migrations.sh
他者と同じ作業場所を使っている。rootの文書/台帳を戻さず整合させる。文書/tasks/台帳/根拠登録はroot所有で編集しない。
新規作業台・追加エージェント・独断の設計拡張・本番操作・再解析・配信・マージ・CI/secrets・ガード解除は禁止。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record && ./scripts/dev/executor-preflight.sh
手順1
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record && git status --short
手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record && git log -3 --oneline

実装
設計§13の契約に忠実に5ファイルを実装し、指定した否定/実DB/2回再解析/配信出力の検証を既存試験へ追加する。
生原文・顧客データは試験へ含めず匿名fixtureを使う。既存ENGINE_VERSION固定期待値は新バージョンへ整合させる。
不明・仕様矛盾はrootへ報告して停止する。ローカルDockerなしなら実DB試験はCIの使い捨てPostgreSQLで実施する。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record/backend && make lint-ci
手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record && git diff --check
手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-recovery-delivery-record && bash scripts/check-task-state.sh

提出
所有ファイルだけをコミットしてpushし、scripts/gh-pr-create-safe.shでmain向けready PRを作る。
本文は /private/tmp/line-condition-note-pr-body.md に保存して--body-fileで渡す。パスは一字一句そのまま使う。
本文の「### 標準ワークフロー確認」に設計: docs/handoff/tcg-product-master-growth/design-keyword.mdを記す。
触る/削除するファイル欄はrootの文書も含むPR差分全体を列挙する。旧番号GOは転用しない。
技術CIを全確認し、所有範囲の失敗を修正・再検証する。技術CI完了後はrootへ引き継ぎ、以後のgit変更を停止する。

完了・停止報告
冒頭「本報告はカード CARD-LINE-CONDITION-NOTE-01 の実行結果である」。rootへPR URL・HEAD・検証結果を返す。
実行ログは /private/tmp/line-condition-note-execution-report.md に保存し、直接実行と他者報告を区別する。
停止時は手順番号・最後のコマンド・理由をrootへ報告。承認チェックの拒否を迂回しない。
END OF CARD
