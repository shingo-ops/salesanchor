本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-INTERRUPTED-RECOVERY-01

この文書は、配信を止める中断2件を限定して復旧可能にする実装指示です。
親: docs/specs/product-master/README.md。設計: docs/handoff/tcg-product-master-growth/design-keyword.md §12。mode: handoff。ADR-154 / ADR-113。
読んだ節: docs/ai-agents/design-partner.md §5.5、guards/00-common.md、guards/11-lint.md。
自己照合: 既存作業台と起点明示、所有3製品ファイル、1目的、ready PR、本文例、実DB受入、rootへの停止報告を明記。

受領確認
最初に「CARD-LINE-INTERRUPTED-RECOVERY-01 受領」と返す。

PO承認
無効原文1件を再実行せず有効1件だけ復旧する提案に原文「進める」を受領。
追加原文「› › 次に進む、また離席するのでPRマージとデプロイまで進めてくれ」を受領。2026-09-10 JST、時分未取得。
番号付きGOを創作しない。rootが承認済みのマージ・本番確認・既存サービスによる1件再実行・配信を担う。

所有範囲
既存worktree /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification、release/line-loop-verification、origin/main d21599c7起点。
製品変更は設計§12.2記載のmigration1本、scripts/run_all_migrations.sh末尾の1登録、backend/tests/test_tcg_work_matching_integration.py追加試験のみ。
他者と同じ作業場所を使っている。rootの文書変更を戻さず、整合させる。docs/tasks/台帳/根拠はroot所有で変更しない。
新規作業台・追加エージェント・本番直接更新・サービス再実行・配信・マージ・本番操作・ガード解除・CI/secrets/プロンプト変更は禁止。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification && ./scripts/dev/executor-preflight.sh
手順1
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification && git status --short
手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification && git rev-list --left-right --count HEAD...origin/main

実装
設計§12の契約通り実装する。不明・設計矛盾はrootへ戻す。独断の対象追加・状態変更をしない。
§12.4の実DB試験を既存fixtureへ追加。モデル通信はmockで、実サービスの1件限定retryと無効job保持を検証する。
生原文・顧客データを試験へ含めない。匿名原文を使う。ローカルDockerなしではCIの使い捨てPostgreSQLで検証する。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification/backend && make lint-ci
手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification && git diff --check
手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-loop-verification && bash scripts/check-task-state.sh

提出
所有3ファイルをコミットしてpushする。公式scripts/gh-pr-create-safe.shでmain向けready PRを作る。
本文は /private/tmp/line-recovery-pr-body.md に実際の文章を保存して--body-fileで渡す。パスは一字一句そのまま使う。
本文例: 「### 標準ワークフロー確認」の中に「設計: docs/handoff/tcg-product-master-growth/design-keyword.md」を記す。
触る/削除するファイル欄は文書も含む実差分全体を宣言。GO原文は上記受領内容のまま、旧番号流用なし。バックアップは未実施と実績を区別する。
技術CIを全確認して、所有範囲内の失敗は修正・再検証。最終技術CI完了後はrootへ引き継ぎ、以後git変更を止める。

完了・停止報告
冒頭「本報告はカード CARD-LINE-INTERRUPTED-RECOVERY-01 の実行結果である」。rootへPR URL・HEAD・検証・ログ保存先と生出力全文を返す。
停止時は手順番号・最後のコマンド・理由をrootへ報告。原文不足や拒否を迂回しない。
END OF CARD
