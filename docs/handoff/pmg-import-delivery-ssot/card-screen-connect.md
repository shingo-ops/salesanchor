---
mode: handoff
---
CARD-PMG-SCREEN-CONNECT-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、03-file.md、11-lint.md。cd接頭辞・編集範囲・正式lintを照合済み。
設計: design.md「方針承認と総合ページ接続便」。当該ページ接続のみ自己審査APPROVE。親の切替設計REVISE。
カード発行前照合: 1記号○、2ready PR○、3宛先○、4一目的○、5既存作業場所○、6書式○、7実出力/対象確認○。
担当Codex Terra、設計root。PO「承認する」「確立したならページ作成まですすめる」。
受領確認: カード名と受領を返す。作業場所release/pmg-screen-completion、起点4f1c2b81。
他の担当がいるため他者変更を戻さない。追加agent起動禁止。rootの文書は編集しない。
許可: TcgLineImportPage.tsx、TcgDistributionPage.tsx、features/tcg-import-workflow/の新規部品/型/API/試験/CSS。
許可: features/tcg-distribution/の共有内容部品と必要な既存部品修正/試験、locales/ja.json・en.json。
許可: frontend/tests-e2e/tcg-import-workflow.spec.ts。全製品パスはfrontend/src/基準（E2Eを除く）。
禁止: Backend/DB/CI/本番/認証/共通api.tsやroutingの独断変更、commit/push/PR/マージ。rootが担当する。
報告用一時ファイルは/tmp/reports/pmg-screen-completion/だけ。上記ファイル名は一字一句そのまま使う。

手順0
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion && bash scripts/validate-worktree-start.sh
期待する出力: exit0。

手順1（実装）
設計のHow/12受入条件に忠実に許可範囲を編集する。コード生成/編集ツールを明示許可する。
既存APIだけを接続し、未記録を成功にしない。実装不明はrootへ報告し推測で仕様変更しない。

手順2
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion/frontend && npm ci
期待する出力: exit0。依存追加/lock変更なし。既存prepareによる共有hook設定変化はrootへ報告する。

手順3
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion/frontend && npm run build
期待する出力: exit0。

手順4
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion/frontend && npm run check:all
期待する出力: exit0。失敗時は許可範囲だけ修正し再検査する。

手順5
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion/frontend && npm run test:unit
期待する出力: exit0。

手順6
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion/frontend && npx playwright test tests-e2e/tcg-import-workflow.spec.ts
期待する出力: exit0。APIは既存のfixture方式で隔離。本番APIや配信先へ送らない。

手順7
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-screen-completion && git diff --check
期待する出力: exit0。

完了報告の冒頭: 本報告はカード CARD-PMG-SCREEN-CONNECT-01 の実行結果である。
実行した検証結果と未実行を分け、実出力をrootに返す。途中で完了扱いにしない。
停止時は手順番号・最後のコマンド・理由・エラー全文をrootへ返す。ガードの迂回禁止。
END OF CARD
