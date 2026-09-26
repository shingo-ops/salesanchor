---
mode: handoff
---
CARD-PMG-ERROR-VISIBILITY-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、guards/03-file.md、guards/11-lint.md（design-partner-card-ops配下）。
照合: cd付き手順、実在作業台、正式lint、出力/停止経路を確認。
受領確認: カード名をrootへ返す。
設計: docs/handoff/pmg-import-delivery-ssot/design.md末尾のGemini原因表示・既存試行記録への接続。
判定: 同一AIによる限定設計自己審査APPROVE、独立設計レビューではない。
担当: error_visibility_recon。rootは設計/文書/台帳、別担当がコードレビューを所有。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility
所有ファイル: frontend/src/features/tcg-import-workflow/配下のAPI型・新履歴component/hookとそのunit、既存Panelとunit、import-workflow.css。
追加所有: frontend/src/locales/ja.json、frontend/src/locales/en.json、frontend/tests-e2e/配下の本便E2Eのみ。
他者も作業中。他者の編集を戻さず、自分の差分だけを作る。
製品backend/DB/CI/scripts/secrets/本番/他branch/台帳/GO/commit/push/PRは禁止。
依存PR3494は読み取りだけ。独自データ保存、現在状態の推定、詳細API、変更APIを追加しない。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && ./scripts/dev/executor-preflight.sh
期待する出力: PREFLIGHT OK。

手順1
指定所有範囲で編集ツールを使い設計を忠実に実装することを許可する。
既存API一覧を明示操作後のみ取得し、履歴として表示する。
設計に列挙した未知値/別job/秘密/遅延/ページング/Clipboardのunitを実装する。
依存不足はローカルnpm ciを許可する。guardを迂回しない。
設計と実物が矛盾したらrootへ戻し、勝手にAPIやDBを追加しない。

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility/frontend && npm run test:unit -- src/features/tcg-import-workflow
期待する出力: 対象unit失敗0。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility/frontend && npm run build
期待する出力: exit0。

手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility/frontend && npm run check:all
期待する出力: exit0。

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-gemini-error-visibility && git diff --check
期待する出力: exit0。
結果・変更一覧・未検証点をrootへ報告し編集停止する。
失敗/制約/範囲差異は操作と出力をrootへ報告。自分の不具合修正と必要再検証は許可する。
END OF CARD
