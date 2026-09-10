本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

CARD-LINE-PROMPT-RETENTION-01

読んだ節: guards/00-common.md、guards/11-lint.md、backend/AGENTS.md、ADR-113。
自己照合: 実在作業台・限定所有・逐語指示・停止報告・出力パス・正規PR経路を確認。

この文書は、実測した指示改善をGemini抽出へ反映する実装指示です。
mode: handoff。ADR-113/ADR-154。設計はdesign-keyword.md §15、比較証拠はprompt-retention-evaluation.json。
POは委任確認への回答として「合意、修正して抽出漏れ0兼を実現してくれ」と指示。既存実装担当へ本カードの限定範囲を引き渡す。番号付きGOは別途確認。

受領確認
最初に「CARD-LINE-PROMPT-RETENTION-01 受領」と返す。

目的・合格条件
発送日と状態の原文表記を取りこぼさない指示へ改善する。実測は現行12/14、改善14/14試験成功。本番全体の誤り0を宣言しない。
設計§15.2の追加文を逐語一致で適用し、PROMPT_VERSIONだけraw-extraction-v3-work-p2へ更新する。
PROMPT_TEXTのSHA256は4e6b2b55b989b1388362adc423896869dc6b88717cfdec6e31f7df9e8c0ca3beになる。

所有範囲
作業台 /Users/tanizawashingo/worktrees/salesanchor/release-line-extraction-prompt-retention。
ブランチ release/line-extraction-prompt-retention、origin/main起点。
所有する製品ファイルはbackend/app/services/gemini_extraction_svc.pyの1件だけ。
他者と同じコードベースで作業している。root所有の設計/台帳/評価記録を戻さない。独断の再設計、モデル変更、DB、解析マスタ、配信ガード変更は禁止。
設計§14全体の実装、サブエージェント追加、原文/応答の本番保存、再抽出、再解析、配信、マージ、デプロイは本カード対象外。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-extraction-prompt-retention && ./scripts/dev/executor-preflight.sh
手順1
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-extraction-prompt-retention && git status --short

実装
設計§15.2のPROMPT_TEXT追加とPROMPT_VERSION変更だけを行う。9列・作品の原文根拠・禁止事項を保持する。
文字列を組み立てた実値のhashを確認する。既存テストが失敗し修正範囲を超える場合は原因を報告する。

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-extraction-prompt-retention/backend && make lint-ci
手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-extraction-prompt-retention && git diff --check
手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-line-extraction-prompt-retention && bash scripts/check-task-state.sh

検証・提出
Dockerがなければ実DB試験をローカルで起動せず既存Backend CIで行う。現Gemini抽出・作品照合・状態/注記・配信の既存試験を維持する。
root文書コミットを保持し、所有1ファイルだけコミットする。scripts/gh-pr-create-safe.shでmain向けready PRを作成し技術CI完了まで確認する。
PR本文は/private/tmp/line-prompt-retention-pr-body.mdへ作成する。標準ワークフロー欄に設計: docs/handoff/tcg-product-master-growth/design-keyword.mdを明記し、差分全体の触る/削除欄を正確に記す。
過去の番号付きGOを流用しない。番号付きGOを作らない。技術CI完了後はGit変更を停止してrootへ返す。

停止条件・報告
設計との矛盾、所有範囲外変更の必要、ガード拒否、不明な外部仕様があれば手順番号・コマンド・理由を報告。制限解除で回避しない。
PR URL、HEAD、prompt hash、直接実行した試験と他者実測の区別を返す。文書保存・実装完了・本番反映を混同しない。
END OF CARD
