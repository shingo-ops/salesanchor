# recon 便3a: 旧列 product_formats.type_master_id を読む・書くコードを外す

> 親の書類: [recon.md](recon.md)（全体の現在地）。この書類は便3a の現在地だけ。
> 基準: origin/main 544e124ee（PR #4631 取り込み後）。生出力の保存場所は PR の報告に記載。

## 現在地（変更前）
旧列 product_formats.type_master_id を指す行（A）は、次の 3 つのファイルと api-contract・locales・試験だけにある。
- backend/app/routers/super_admin_product_formats.py:30（_COLS）、:31（_UPDATABLE）、:93-94（INSERT）
- backend/app/schemas/product_format.py:19（ProductFormatBase）、:33（ProductFormatUpdate）。ProductFormatResponse は Base を継ぐので :19 を通して返していた。作成・更新のスキーマに model_config は無い（extra の設定なし）。
- frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx:44,57,68,134,159,222,328-341（型・状態・送信・一覧の列・単独欄）と、同 .test.tsx:39
- frontend/api-contract/openapi.json:24675,24777,24878
- frontend/src/locales/ja.json:5204 と en.json:5204（キー typeMasterId）。他の画面は使っていない（git grep -n "typeMasterId" frontend/src は上の 3 ファイルだけ）。

links 由来の行（B）。触らない。
- backend/app/routers/super_admin_product_formats.py:40（array_agg）、:185（DELETE）、:192-193（INSERT）
- backend/app/services/tcg_product_master_svc.py:109,134-135、migrations 各ファイル、backend/tests の links の INSERT・SELECT

(A) が上の一覧の外にあった件数: 0 件。

## 解析・監視の読み手
- v102 の解析（gemini_raw_copy*、line_analysis*、tcg_analyzer_svc、tcg_work_reference、extraction_judgement_svc）、backend/app/tasks、scripts/accuracy、gas/ に type_master_id・typeMasterId を含む行は 0 件（git grep の出力 0 行）。
- product_formats を読む解析側の 6 行（tcg_product_import_svc.py:267 は code と id、tcg_product_roundtrip_svc.py:240 は to_jsonb で全列を取るが使うのは ["code"] と ["id"] だけ :241,:294）。旧列の値は使わない。
- ai_ro の閲覧用ビュー（migrations/20261017_130100_create_ai_ro_views.sql）は product_formats を名指ししていない（grep 0 行）。

## API contract の手順
- .github/workflows/api-contract-check.yml:35 が `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流し、:50 で差分があれば失敗する。手で書き換えず、この手順で再生成する。

## ADR を探した結果
- ADR-1038（docs/adr/ADR-1038-product-format-child-of-work.md）: この便の根拠。
- ADR-1026（docs/adr/ADR-1026-drop-products-type-master-id.md）: 旧列は便3b で落とす。この便は列を残す。
