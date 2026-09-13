CARD-PRODUCT-CSV-TEMPLATE-IMPL-02
本カードの許可・禁止は、過去便の禁止条項をすべて上書きする。

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、01-read.md、03-file.md、04-worktree.md、10-executor.md、11-lint.md。
照合: cdは実在の専用worktreeのみ。作成と移動は分便。L32は人手確認。設計文書は読取参照のみ。8製品ファイル以外を編集しない。

目的
承認済みdesign§15の空CSVダウンロードとUser型不整合の限定修正を実装し、手元で可能な検証を残す。
このカードは忠実実装用。手順内で指定する実装・テスト作成・範囲内の修正には編集ツールの使用を許可する。
機械的転記カードではない。設計契約の変更は禁止。実行役の自動起動は本カードでは行わない。

出力の置き場
/tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt
パスは一字一句そのまま使う。既存なら上書きせず停止する。
本カードは新規である。過去の報告の再送を禁止する。
報告にexecutor-preamble.mdの中身を含めない。表・要約・チェックマークだけの報告を禁止する。
各手順のコマンドの標準出力・標準エラーを全文保存する。
REDACT: 認証トークン・秘密鍵・password/token/APIキーの実値は保存せず [REDACTED] とする。
本カードでは認証情報・環境変数一覧・本番データを読み取るコマンドを実行しない。

禁止（名指し）
本店main/developの変更、他者worktreeの編集、依存manifest/lock変更、設計変更、共通部品変更、CI/運用スクリプト変更。
DB・本番への接続/書込み、44商品登録、再解析/配信、secrets変更、GO記録作成、代理GO、マージ、push、PR作成。
設計文書・tasks/todo.md・evidence-registry.mdへの書込み。台帳は設計担当が報告を確認して更新する。
サブエージェント・別セッション起動。本カードの担当は1実装役。

停止条件（2段）
即停止: 作業場所/基点不一致、既存変更、承認契約外の変更、権限拒否、秘密の露出、依存導入失敗。
失敗時: 範囲内の実装由来の検査失敗は8ファイル内で修正し該当検査を再実行できる。既存問題・契約変更が必要なら停止する。
Docker不在は確認済み。本便でpytestを実行せず「実DB検査はCI待ち」と記録する。Docker起動や環境改変へ拡張しない。
停止時は手順番号・最後のコマンド・秘密を伏せた生出力を設計担当へ返す。許可追加を推測して再開しない。

受領確認
「CARD-PRODUCT-CSV-TEMPLATE-IMPL-02を受領。設計§15の8ファイルのみ実装し、公開・本番変更は行いません。」と返す。

手順1 報告ファイルの新規作成
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && python3 -c 'from pathlib import Path; p=Path("/tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt"); p.parent.mkdir(parents=True,exist_ok=True); p.open("x").close()'
旧01の空報告は保持する。本カードの出力はコマンドの直接リダイレクトで保存する。
規則文書やログ全文をPython文字列・shellコマンド文字列へ埋め込んで再構成しない。
各手順の開始/完了・終了コードを追記し、10MBを超えたら停止する。既存ファイルへの追記はこの新規02報告だけ許可する。

手順2 作業場所と基点
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git branch --show-current >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: release/product-import-template-impl。

手順3 未保存変更
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git status --short --untracked-files=all >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: 空。既存変更があれば停止。

手順4 基点
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git rev-parse HEAD origin/main >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: 2行ともadc8bc4d67a94e8ede45a1e9c0ee9f28d28bb70b。異なる場合は設計担当へ戻す。

手順5 必須preflight
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && ./scripts/dev/executor-preflight.sh >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: PREFLIGHT OK。非ゼロ終了なら停止。

手順6 規則と承認済み設計を読む
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && cat AGENTS.md frontend/AGENTS.md backend/AGENTS.md >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
設計入力は /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-design/docs/handoff/tcg-product-import/design.md の§15と2026-09-12承認追記。
調査入力は /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-design/docs/handoff/tcg-product-import/recon.md の2026-09-11再開調査。
この2入力の読取を許可する。編集しない。ソース/テスト/部品を読む範囲は設計§15の根拠参照先まで許可する。

手順7 依存の準備
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/frontend && npm ci >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
lockファイルを変更しない。既存の依存導入に限る。追加依存・バージョン変更は禁止。

手順8 実装
編集場所は /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl。下記8ファイルの作成/編集とそれに必要な読取・範囲内修正を許可する。
- frontend/public/templates/tcg-product-import-template.csv（新規、親ディレクトリの作成可）
- frontend/src/features/tcg-product-import/TcgProductImportPanel.tsx
- frontend/src/features/tcg-product-import/TcgProductImportPanel.test.tsx
- frontend/src/locales/ja.json
- frontend/src/locales/en.json
- frontend/tests-e2e/tcg-product-import.spec.ts
- backend/app/routers/tcg_product_import.py
- backend/tests/test_tcg_product_import.py
実装内容はdesign§15-2〜15-4を逐語的契約とする。テストもAC1〜7を網羅する。
空CSVはUTF-8 BOM/10列固定順/CRLF/商品行0。本文操作台のButton secondaryで同一originの静的資産を保存する。
全UI文言は日英t()、既存File/preview/result/uncertainの動作を保つ。保存からpreview/commitを呼ばない。
User型/属性アクセスへ限定修正。既存認証条件・サービス・DB・API契約は不変。
実User/HTTPの成功・拒否・digest不一致・commit未呼出の回帰試験を追加する。
依存上書きはfinallyで元へ戻し、他試験を汚染しない。データ登録サービスのMock成功を実DB成功と呼ばない。

手順9 対象単体試験
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/frontend && npm run test:unit -- src/features/tcg-product-import/TcgProductImportPanel.test.tsx >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: 全ケース成功。AC1は実ファイルとbackendの列定義を比較し、抽出不能なら失敗する。

手順10 フロント静的検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/frontend && npm run check:all >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: 終了0。既存警告と今回の警告を区別する。

手順11 本番ビルド
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/frontend && npm run build >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: 終了0。dist/templates/tcg-product-import-template.csvが存在し、元ファイルとバイト一致を読取検査する。

手順12 E2Eポートの空き確認
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",5193)); s.close(); print("PORT 5193 available")' >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
既存サーバーの停止/再利用はしない。使用中なら停止して設計担当へ報告する。

手順13 E2E
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/frontend && PORT=5193 npx playwright test tests-e2e/tcg-product-import.spec.ts --project chromium --workers=1 --reporter=line >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
既存設定のwebServerを使用。対象Chromium未導入の場合だけ既存PlaywrightによるChromium導入を許可する。
日英390pxの画面・downloadされた実バイト・操作後同じURL・API呼出0を検査する。
画像の保存先は/tmp/reports配下の本カードIDで始まる未使用名。既存画像へ上書きしない。

手順14 バックエンド静的検査の準備
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/backend && /usr/local/bin/python3.12 -m venv .venv >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
未追跡の.venvが既に存在する場合は作り直さず停止する。製品・依存manifestは変更しない。

手順15 バックエンド既存依存の導入
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/backend && .venv/bin/python -m pip install -r requirements-dev.txt >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
導入失敗を無視しない。

手順16 バックエンド静的検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/backend && PATH="/Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl/backend/.venv/bin:$PATH" make lint-ci >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
期待する出力: 終了0。mypyは現行Makefileで警告扱いのため、診断を成功として隠さない。
pytestは本便で実行しない。CIの実PG試験と本番QAは別便待ちとして報告する。

手順17 差分検査
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git diff --check >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
新規CSVを含む変更一覧をgit status --shortで確認し、8ファイル以外に製品変更がないことを検算する。
自動生成ファイルに差分があれば独断で戻さず原因と一覧を報告して停止する。

手順18 完了報告
  cd /Users/tanizawashingo/worktrees/salesanchor/release-product-import-template-impl && git diff --stat >> /tmp/reports/CARD-PRODUCT-CSV-TEMPLATE-IMPL-02.txt 2>&1
全差分と試験の読取レビューを許可する。AC1〜7を実行済み/CI待ちに分け、未検証を合格にしない。
コミット・公開は本便では行わず、変更をこのworktreeに残す。設計担当が差分と生報告を読んで次便へ渡す。

報告様式
成功時は生報告ファイルのパスと実行済み/未実施の区別を返す。停止時は前述の停止報告を優先する。
END OF CARD
