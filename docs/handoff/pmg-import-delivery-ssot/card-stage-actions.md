CARD-PMG-STAGE-CTA-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: guards/00-common.md、03-file.md、04-worktree.md、05-pr.md、09-gh.md、11-lint.md。
照合: 1○記号、2○専用PR、3○全文報告、4○3段階確認導線、5○main起点、6○仕様確定、7○実出力確認。
受領確認: 「CARD-PMG-STAGE-CTA-01を受領」と返す。
PO原文「この表示に変更してくれ」を製品実装承認として受領。対象は直前の3枚カード下部CTA表示。
設計正本: docs/handoff/pmg-import-delivery-ssot/design.md の「2026-09-13 3段階カードCTAの製品実装設計」。
実物調査: 同ディレクトリrecon.mdの同日節。レビュー後の契約を再解釈せず実装する。
担当: POが追加委任を承認したpmg_cta_completion、製品/試験はあなたが単独所有。rootは設計/審査/引継ぎ担当。
他者も作業中。既存未保存・他branchの変更を上書き/巻き戻ししない。新規エージェント起動禁止。
作業台: /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions。
起点: origin/main dd1df11c。正式机作成・台帳登録済み。
許可製品: backend/app/services/tcg_import_progress.py、backend/app/routers/tcg_line_import.py。
許可試験: backend/tests/test_tcg_import_progress_pg.py、frontend/tests-e2e/tcg-import-workflow.spec.ts。
許可UI: frontend/src/features/tcg-import-workflow/配下（専用hook/component/unit/storyを必要時追加可）。
許可辞書: frontend/src/locales/ja.json、frontend/src/locales/en.jsonのpmgWorkflowキーのみ。
許可文書: 同テーマdesign.md/recon.md/card-stage-actions.mdの今回便、tasks/todo.md/evidence-registryの今回行。
許可出力: reports/pmg-stage-card-actions/と/tmp/CC報告ファイル/pmg-stage-card-actions/。
禁止: DB migration、認証/権限変更、CI/運用scripts/secrets変更、解析や配信条件の変更、本番書込。
禁止: 試作の架空値・原因分類・デモ再抽出ボタンを製品に混入、外部送信、GO創作、force/admin、PRマージ。
許可操作: 契約どおり実装、依存インストール、専用ローカルDB試験、build/check/unit/E2E、文書検査。
ローカルDBはlocalhostの明示的テストDBだけ。既存の停止中dist01-3258 Colima profileと専用PGは再利用可。
使用前に所有/状態/接続先を確認。既存sa-private-ci/profile/default Docker contextを変更しない。不要後停止。
Python3.12の/tmp/dist01-3258-py312は再利用可。ローカルfixture用schema作成削除はテストDB限定。
ローカル成功後、rootに差分と検証結果を渡す。root審査の指摘はこの範囲内で修正可。
審査後に通常commit/push・main起点PR起票・register-pr・CI確認まで実施可。マージ/本番反映は別GO。
新規PRは現物確認のうえ安全スクリプトで作成しmainをbaseにする。PR本文はファイルで渡す。
設計/実物の矛盾・範囲外修正が必要なら該当処理を止めrootへ報告。安全検査/guardの迂回は禁止。
テスト失敗は許可範囲の実装修正で解消し、ログ途中を完了と報告しない。CI全体再設計や基準緩和は禁止。
最終報告は実行終了code、試験成功/skip、HEAD、PR URL、未確認を分離。全ログを上記出力へ保存。
報告冒頭: 本報告はカード CARD-PMG-STAGE-CTA-01 の実行結果である。

手順0: preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && ./scripts/dev/executor-preflight.sh

手順1: 開始状態確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && git status --short --branch

手順2: 正式カードを再検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && bash scripts/card-lint.sh docs/handoff/pmg-import-delivery-ssot/card-stage-actions.md

手順3: 上記契約に従って実装と対象unit/実PG/E2Eを行い、frontend build/check:allとbackend lint-ciを完了する。
期待する出力: 件数の実測・正常終了・JSエラー0・不要POST0を報告。画像をPC/狭幅・明暗で保存する。

手順4: root差分審査前の空白確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-pmg-stage-card-actions && git diff --check

担当交代の根拠: 新規実装担当1名への引継ぎ確認にPO原文「進める」を受領。元担当は停止、範囲と設計は同じ。

END OF CARD
