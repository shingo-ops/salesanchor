# Phase 2 調査 — 完売ルール

日付: 2026-09-14。対象ADR: ADR-113 / ADR-154。
設計: docs/handoff/tcg-import-latest-only/sold-out-page/design.md
詳細実測保存先: docs/handoff/tcg-import-latest-only/recon.md

## 観測事実

- backend/app/routers/tcg_analysis_review.py:94 — 既存status_tabは6種類、Sold out専用条件がない。
- backend/app/services/tcg_analysis_review_svc.py:32 — 原文JOINにis_active=TRUE、過去原文は取得対象外。
- backend/app/services/tcg_analysis_review_svc.py:15 — TCG_SCHEMAを既存正本として参照。
- docs/specs/db-ssot/README.md:3 — 同じ事実の二重管理を禁止。
- 2026-09-14、本番read-only集計: Sold out550、原文までJOIN550、distinct解析ID550。active24/history526、投稿日未記録526。新投影4表は存在照会に出ない。先頭50行の原文合計416563bytes、最大13157bytes。いずれもその時点の集計、固定受入数値ではない。
- 2026-09-14、担当の最新main5afb5af1照合: 旧59f644cdから対象router/App/DesktopShell/routeTitlesの差分なし。rootもorigin/mainの既存APIとJOINを直接読み取り確認。

## 未解決事項

設計の前提として未確認の在庫投影を使用しない。製品実装と下記ローカル検査は完了。実DBfixture試験・実HTTPの本番検収は未実施。過去の人工分類試験を本便の検証結果へ転用しない。

## 審査

同一AIの自己審査APPROVEは既存解析正本の閲覧便に限定。メニュー名はPO最新確定「完売ルール」。ページ名称によりルール更新権限を推定しない。商品/原文/解析データを変更しないことを実装後差分で検収する。


## 実装検証（2026-09-14・stock_contract_01が実行）

作業基点main 5afb5af1。専用branch release/line-soldout-readonly-page。既存DBだけの単一SELECTと管理者限定ページを実装。商品/原文/解析/現在庫の更新、モデル呼出し、ブラウザー永続保存なし。メニュー名・ページ名は完売ルール / Sold-out rules。検索は確定ボタンまたはEnterで1回取得し、先頭ページへ戻る。

- frontend `npm ci --ignore-scripts --no-audit --no-fund`: 783 packages導入、依存ファイル変更なし。
- frontend `npm run check:all`: 終了0。専用UI試験は最終8件成功（メニューの管理者限定/LINE取込直後、直接URL拒否、検索/再ページング、日時、空欄、原文、失敗、旧応答破棄）。追加メニュー試験のeslintと最終tscも終了0。
- frontend `npm run build`: 終了0。既存の500kB超chunk/dynamic import警告あり。初回は自己実装試験の型エラーを検出し、既存target対応とTestingLibrary引数を修正して成功。
- backend Python3.12隔離環境で正規requirements導入。`make lint-ci`: 終了0、ruff成功、Bandit High0、既存mypy警告あり。対象service/routerのmypyは2ファイル警告0。
- backend `python -m pytest tests/test_tcg_sold_out_results.py -k 'not test_pg' -o addopts='' -q`: 12成功、実PG2件は選択外。全体coverage/実PG合格を意味しない。認可は実require_super_admin依存、DB部分はAsyncMock。安定503・入力422・単一SQL/検索bind・不整合検出を検証。
- 既存公式schema-copy検査関数で新試験のテーブル定義コピー0。実PG試験は既存migrationを使用し、隔離CI DBにfixtureを作ってからREAD ONLY transactionでサービスを呼ぶ。Sold out/In Stock/Pre-order混在、active/history、原文名/数量NULL、未知マスタ、検索記号、別ID、ページ範囲外を含む。Docker不在のローカルでCIフラグを偽装したりskipを合格扱いにはしていない。
- 実Chromiumで実ページに人工fixtureを渡すローカル確認成功。日本語タイトル、原文開閉/強調、直接アクセス拒否を確認。画像soldout-browser-ja.pngは一時成果物（PRには含めない）。本番API/DBには接続しない。初回fixtureのモジュール解決待ちtimeoutを修正後成功。
- 差分形式チェック成功。マージ/本番配備/再解析/配信は未実施。

## 親設計担当による実測（担当からの報告・実装担当の実行ではない）

2026-09-14、rootが作成serviceのASTから実際の単一SQLを抽出し、本番PostgreSQLへreadonly=on、statement_timeout=10000、all/空q/offset0/limit50のSELECTのみ実行。終了0、missing_sources=0、total=571、page_count=50、5キー応答のDB jsonb直列化サイズ353345bytes。原文/個人情報の出力なし。SQL実機照合と転送量の参考であり、FastAPI実HTTPや上記PGfixtureの合格を代替しない。以前の550件は過去時点の値で、固定受入値ではない。

## 次の検収

通常レビュー用PRで既存CIの実PG2試験を実行して確認する。専用ページの実HTTP認可・本番同時点total照合・原文ID一致の検収は未実施。PO GOを創作せず、GO要求のガードはそのまま報告する。

## PR3505 UIゲート指摘の修正（2026-09-14）

既存CIのUI governanceが新規の生search入力を検出したため、検索欄を既存標準TextFieldへ置換。例外コメントやガードは変更していない。担当再実行: UI8件成功、check:all終了0（eslint既存警告218、error0）、build終了0（既存chunk警告）。実PGの成否はこのUI検査では判定しない。
