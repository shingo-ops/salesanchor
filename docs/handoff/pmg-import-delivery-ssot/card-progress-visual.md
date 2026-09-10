---
mode: handoff
---
CARD-PMG-PROGRESS-VISUAL-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、03-file.md、11-lint.md。cd接頭辞・許可範囲・正式lintを照合。
設計: design.md「2026-09-11 認知負荷を減らす進捗表示」のHow8項目/C1-C7。表示範囲の自己審査APPROVE。
担当Codex Terra、設計root。POは認知科学に基づく改善と離席中の完走を依頼済み。
カード発行前照合: 1記号○、2ready PR○、3宛先○、4一目的○、5作業場所○、6書式○、7実物確認○。
受領確認: カード名と受領を返す。専用作業場所release/pmg-progress-visual-hierarchy、起点57eb951e。
他の担当がいる。他者変更を戻さない。追加agent起動禁止。rootの文書は編集しない。
許可: frontend/src/features/tcg-import-workflow/ImportWorkflowPanel.tsx、import-workflow.css、ImportWorkflowPanel.test.tsx。
許可: frontend/src/pages/super-admin/TcgLineImportPage.tsx、frontend/src/locales/ja.json・en.json。
許可: frontend/tests-e2e/tcg-import-workflow.spec.ts。既存機能のテストは削除せず必要なDOM期待値だけ更新。
禁止: API型/hooks/共通部品/token/routing/Backend/DB/CI/本番/認証変更、commit/push/PR/マージ。rootが担当する。
報告と画像の一時出力先は/tmp/reports/pmg-progress-visual/。既存ファイル名は一字一句そのまま使う。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy && bash scripts/validate-worktree-start.sh
期待する出力: exit0。

手順1（実装）
設計How/C1-C7に忠実に許可範囲を編集する。コード編集ツールの利用を明示許可。
既存Badge/意味色を使い、選択済み時は進捗先頭・uploadをdetails化。入力値と確認操作を保持。
native progressは抽出終了割合のみ、総数0/不明時は省略。解析成功や配信可能を推測しない。
未知/エラー/要確認/前回値表示の区別を最優先。不明はrootへ報告し、独断で仕様を変えない。

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy/frontend && npm ci
期待する出力: exit0。依存/lock変更なし。共有hook設定が変わったら報告する。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy/frontend && npm run build
期待する出力: exit0。

手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy/frontend && npm run check:all
期待する出力: exit0。許可範囲の違反だけ修正して再確認。

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy/frontend && npm run test:unit
期待する出力: exit0。C1-C4の状態分岐とボタンを試験する。

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy/frontend && npx playwright test tests-e2e/tcg-import-workflow.spec.ts
期待する出力: exit0。既存5件を維持し、初期upload・選択時collapse・入力保持・要確認遷移を検証。
既存の隔離API fixtureを使いPC日本語ライト/390px英語ダークの画像を一時出力先へ保存。
本番API・実配信先へのPOSTは禁止。画面取得用の一時ローカルサーバは許可する。

手順7
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-progress-visual-hierarchy && git diff --check
期待する出力: exit0。

完了報告の冒頭: 本報告はカード CARD-PMG-PROGRESS-VISUAL-01 の実行結果である。
実行した検証と未実行を区別し、画像パスと変更ファイルをrootへ返す。
停止時は手順番号・最後のコマンド・理由・エラー全文をrootへ報告する。検査の迂回禁止。
END OF CARD
