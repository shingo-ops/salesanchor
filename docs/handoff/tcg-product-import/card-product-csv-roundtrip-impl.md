CARD-PRODUCT-CSV-ROUNDTRIP-IMPL-01
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、04-worktree.md、05-pr.md、10-executor.md、11-lint.md。
受領確認: 「CARD-PRODUCT-CSV-ROUNDTRIP-IMPL-01を受領。設計§21の出力と更新往復を実装・検証します。」
担当/所有: 既存/root/csv_card_executorが下記13製品ファイルを所有。親は設計/文書/読取レビュー。他者と同じコードベースなので他者の変更を戻さない。

承認と設計
PO原文「合意、この内容を目標として進める、離席するのでエクスポート機能を実装してPRマージ本番反映まで完了させてくれ」。合意対象の3条件はdesign§21-1/21-2。
設計 docs/handoff/tcg-product-import/design.md §21、mode:handoff。同一AI自己審査APPROVE、旧10列新規経路維持。固定文書commit d56649c5の7文書を取込む。
設計SHA 7fbc9e44e9aff1166f5335a41951c56f90282b5f65651807889330f8cf3b85ab。契約/不変条件/R1–R11/対象13ファイルを忠実実装し、変更が必要なら親へ戻す。
作業承認は記録するが、番号付きGO原文は未受領。GO #番号を創作/代筆しない。今回カードではマージ/本番反映を実行しない。

対象13ファイル
backend/app/services/tcg_product_roundtrip_svc.py（新規）
backend/app/routers/tcg_product_import.py
backend/tests/test_tcg_product_roundtrip.py（新規）
backend/tests/test_tcg_product_roundtrip_pg.py（新規）
frontend/src/pages/super-admin/TcgProductMasterPage.tsx
frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx
frontend/src/features/tcg-product-import/TcgProductImportPreview.tsx
frontend/src/features/tcg-product-import/importMessages.ts
frontend/src/locales/ja.json
frontend/src/locales/en.json
frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx
frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx
frontend/tests-e2e/tcg-product-import.spec.ts

許可/禁止
上記ファイルの実装/必要試験/同範囲修正、依存定義を変えないnpm ciとvenv/既定requirements導入、合成APIでのローカルUI起動/Playwright/スクリーンショットを許可。
backend/AGENTS.md・frontend/AGENTS.md・既存規則を遵守。DB新DDLコピーではなく既存provision/HISTORY fixtureを再利用。
旧tcg_product_master_svc/旧tcg_product_import_svc/DB migration/CI/運用scripts/secrets/依存lock/共通API client/共通UI部品の変更禁止。
新規agent起動禁止。localhost以外のDB手動接続、実商品登録/既存8商品変更、再解析/3シート配信は禁止。
Docker不在ならローカルpytestを実行せず未実施とする。GITHUB_ACTIONS偽装/新PGskip追加/ガード緩和/検査削除/CI時間変更は禁止。
API/SQL仕様は既存+確認済み公式資料（Context7不在）で設計済み。新ライブラリ/新APIが必要なら親へ戻す。

報告/停止
/tmp/reports/CARD-PRODUCT-CSV-ROUNDTRIP-IMPL-01.txtを排他的新規作成し、全操作/終了コード/差分/検証を直接追記。秘密は[REDACTED]。
未知main/先約/製品競合/仕様不足/検証で設計変更が必要/権限拒否は該当操作を停止し生出力を親へ返す。範囲内実装/テスト誤りは原因を読み修正再検査可。
生出力は報告ファイルへ保存し、親への連絡は短い現在地でよい。1分程度ごとに現在地を連絡する。

再開注意: 旧手順1の短いブランチ名は設計場所との前方一致で実在しない場所を既存と誤判定した。親がgit worktree listとscript96行を直接確認済み。新しいrelease/product-csv-roundtrip-implを正式scriptで作成し、既存報告へ追記して手順1から再開。報告の排他新規作成は繰り返さない。
手順1 正式作業場所
  cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/product-csv-roundtrip-impl
旧終了worktreeの再使用はしない。自動cleanup対象外の他者作業を触らない。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl && ./scripts/dev/executor-preflight.sh
HEADはorigin/main1021268623f2dba566d953fea056ff548ae28f3a、status空、台帳先約なしを確認。異なるmainなら親へ確認。
手順2 設計取込
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl && git merge --no-edit d56649c5
7文書以外の追加がないこと、固定designSHAを確認。
手順3 実装
設計§21通り13ファイルのみ変更。GET export12列、既存preview/commitヘッダ分岐、更新はrevision/全行lock再照合/商品語履歴commit1回。
有効無効/未公開列の維持、無変更語のUUID/位置維持、同一digest再送409、既存10列回帰維持。実装裁量は命名/fixture具体値など非契約だけ。
DB定義/SQL条件は既存migrationの列を直接確認してから書く。独自テストCREATE TABLE禁止。
手順4 静的検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl/backend && make lint-ci
既定dev依存だけで不足する場合はローカルvenvへ既定requirementsを導入可、lock定義の変更はしない。
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl/frontend && npm ci
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl/frontend && npm run check:all
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl/frontend && npm run build
手順5 テスト
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl/frontend && npm run test:unit
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl/frontend && npx playwright test tests-e2e/tcg-product-import.spec.ts --project=chromium
既定playwright.config.tsのPORTで他者と衝突しない空きportを使ってよい。合成APIのみ、検査を無効化しない。新日英390/1440の画像を/tmp/reportsへ保存し親へパス報告。
Backend実PGは既存Docker可否を確認。不可なら未実施とし、親レビュー後の正式CIで実行。R1–R11の対応表を報告へ作る。
手順6 差分検査/親レビュー待ち
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-csv-roundtrip-impl && git diff --check
13製品だけの変更、7文書固定、依存lock変更0、全製品差分とSHA一覧、新規試験sourceを報告へ保存する。
親が実差分/スクリーンショット/試験をレビューできる状態で停止。まだ製品commit/push/PR作成はせず、親の公開カードを待つ。
実装詳細の明確化（固定設計の契約は変更しない）
2MiB生バイト制限を先に検査する。csv.field_size_limitは同期読取のtry/finally内だけMAX_BYTESへ拡大し、awaitを挟まず元値へ必ず戻す。128KiB超セル、2MiB境界、読取例外後の復元を試験する。
外側更新CSVはQUOTE_ALL。式先頭の可逆保護にはASCIIに加え全角＝＋－＠を含め、apostrophe/引用符/改行とともに往復試験する。Excelで保存・再読込後まで万能な式実行防止を保証しない。
確認根拠: Python3.12 csv公式資料とOWASP CSV Injection（2026-09-13読取）。新しい依存や既存10列契約の変更はない。
END OF CARD
