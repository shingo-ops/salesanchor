# Design: unit-ignore-phrases

## 参照
- recon: docs/handoff/unit-ignore-phrases/recon.md
- ADR-155: マスタ値は画面から登録（migration は構造のみ）
- ADR-027 / ADR-144 / ADR-072

## KGI
super_admin が単位ルール画面で「単位にしない言い回し」を追加・編集・無効化・削除でき、表 public.line_unit_ignore_phrases に保存される。

## 設計
- 表: id bigint identity PK / phrase text NOT NULL UNIQUE / note text / is_active bool default true / created_at / updated_at。全列 COMMENT。INSERT/UPDATE/DELETE を含まない。
- API: GET/POST/PATCH/DELETE /api/v1/super-admin/unit-ignore-phrases（require_super_admin）。一覧は ORDER BY is_active DESC, id。
- 画面: AnalysisRulesPage の unit-master で UnitMasterPanel の下に UnitIgnorePhrasesPanel を並べる。

## 基準と検証方法
|基準|検証方法|
|---|---|
|migration が構造だけ|migration-guard CI|
|権限なしで 403|backend/tests/test_super_admin_unit_ignore_phrases.py（ローカルで実行済み）|
|追加・重複 409・無効化・一覧順|同上の PostgreSQL テスト（CI で実行）|
|画面の追加・編集・無効化・削除|Vitest UnitIgnorePhrasesPanel.test.tsx|
|ガバナンス|UI governance gate・Lint・i18n チェック|

## 外部・過去事例の参照と我々への応用
- 過去事例: 社内の単位マスタ CRUD（super_admin_units.py / UnitMasterPanel.tsx）。同じ形で作るため、運用・権限・画面操作が既存と揃う。
- 応用: 追加先の表だけ新設し、判定側への結線は後続便で行う（本便は構造と登録画面のみ）。

## 維持の仕組み
- 値はコードに直書きせず画面から登録する（ADR-155）。
- 表の追加は scripts/run_all_migrations.sh への登録と migration-guard で担保。
- API の権限（403）は backend/tests/test_super_admin_unit_ignore_phrases.py、画面は Vitest で CI が常時検査する。

## 触るファイル
触るファイル: backend/app/main.py, backend/app/routers/super_admin_unit_ignore_phrases.py, backend/app/schemas/central_masters.py, backend/tests/test_super_admin_unit_ignore_phrases.py, docs/handoff/unit-ignore-phrases/design.md, docs/handoff/unit-ignore-phrases/recon.md, frontend/api-contract/openapi.json, frontend/src/locales/en.json, frontend/src/locales/ja.json, frontend/src/pages/super-admin/AnalysisRulesPage.tsx, frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.test.tsx, frontend/src/pages/super-admin/components/UnitIgnorePhrasesPanel.tsx, migrations/20261008_100000_create_line_unit_ignore_phrases.sql, scripts/run_all_migrations.sh
