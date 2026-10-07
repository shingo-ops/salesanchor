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

## 外部事例
該当なし（社内の単位マスタ CRUD と同形の追加。手本は recon.md に記載）。
