# design — tcg-diagnostics-readonly（TCG診断API・固定クエリ方式）

**対象ADR**: ADR-154  
**recon**: docs/handoff/tcg-diagnostics-readonly/recon.md  
**日付**: 2026-09-04  
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- 固定クエリ方式（Fixed SQL / Stored SQL Map）は OWASP SQL Injection 防止ガイドラインの標準推奨事項。外部入力からSQL文字列を組み立てない原則を実装する最も単純な手段として広く採用される。
- ADR-154（GAS→Python 段階移植方針）の延長として、TCG スキーマの状態を Python バックエンドから参照する方式を確立する。既存の require_super_admin ガードパターン（tcg_supplier_quality.py:64 等）を踏襲。
- 任意SQL方式（クエリ文字列を外部から受け取る方式）は、過去多数の本番インシデントの原因となっている。本実装では採用しない（理由は下記「固定クエリ方式を採用した理由」参照）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 認証なしで 401/403 が返る | `pytest backend/tests/test_tcg_diagnostics.py::test_diagnostics_requires_auth` |
| 未知キーで 400 が返り許可キー一覧がエラーに含まれる | `pytest backend/tests/test_tcg_diagnostics.py::test_unknown_key_returns_400` |
| suppliers キーで 200 + 正しいフィールド形状が返る | `pytest backend/tests/test_tcg_diagnostics.py::test_suppliers_returns_200` |
| supplier-name-dupes キーで 200 + name_lower/cnt フィールドが返る | `pytest backend/tests/test_tcg_diagnostics.py::test_supplier_name_dupes_returns_200` |
| supplier-channels キーで 200 + supplier_code/channel_count フィールドが返る | `pytest backend/tests/test_tcg_diagnostics.py::test_supplier_channels_returns_200` |
| orphan-messages キーで 200 + null_channel_count フィールドが返る | `pytest backend/tests/test_tcg_diagnostics.py::test_orphan_messages_returns_200` |
| 6 tests 全 PASS | CI `pytest-run-internal` green |

---

## 固定クエリ方式を採用した理由・任意SQL方式を採らなかった理由

**採用: 固定クエリ方式（_QUERIES dict + _ALLOWED_KEYS frozenset）**
- SQL はコード内に埋め込み済み。外部入力（key パラメータ）は許可リストへの完全一致チェック後に dict ルックアップのキーとしてのみ使用する
- key が SQL 文字列に展開されることはない。SQL インジェクションの余地がない
- SELECT のみ。INSERT / UPDATE / DELETE / DDL はコードに含まれない
- テストが容易。mock で run_diagnostic を差し替えるだけでエンドポイント挙動を検証できる

**不採用: 任意SQL受け取り方式（外部から SQL 文字列を POST する等）**
- key の代わりに SQL 文字列を直接受け取る方式は、認可済みユーザーであっても任意の UPDATE / DROP / DELETE を実行できるリスクがある
- SELECT専用ロールの postgres ロールが未定義（recon §3）であるため、DB 側での防御も不完全
- 監査ログが残らない運用では、事後追跡が困難になる

---

## 技術 How・KPI

- KPI: 6 tests 全 PASS / CI green / process-artifacts gate green
- `_ALLOWED_KEYS`: frozenset で4キーを定義。frozenset は変更不可能なため、実行時に許可リストが書き換えられない
- `TCG_SCHEMA = "tenant_004"`: スキーマ名をコード定数に固定。外部から注入不可
- `run_diagnostic`: `_QUERIES[key]` で取得した固定 SQL のみを `db.execute(text(sql))` で実行
- router 層で key の許可チェックを先行させる（service 層への到達前にガード）

---

## 弊害・トレードオフ

- 診断クエリを追加・変更するにはコードの変更が必要。運用上の柔軟性は低い
- 一方、コードレビューを通じてすべての SQL 変更が審査される。これは意図した制約

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | DB-A1: SSH / ポート / ロール / 既存API の実測 | architect |
| 2 | backend/app/services/tcg_diagnostics_svc.py 作成（_ALLOWED_KEYS / _QUERIES / run_diagnostic） | Generator |
| 3 | backend/app/routers/tcg_diagnostics.py 作成（GET エンドポイント / require_super_admin） | Generator |
| 4 | backend/tests/test_tcg_diagnostics.py 作成（6テスト） | Generator |
| 5 | backend/app/main.py に include_router 追加 | Generator |
| 6 | pytest 6 passed 確認 | Generator |

---

## 継続

- 完了後の監視: テスト6件が _ALLOWED_KEYS / _QUERIES の整合性を継続的に保証する
- 診断キーを追加する場合: _ALLOWED_KEYS / _QUERIES / テスト を同時に追加し PR レビューを経ること

---

## 維持の仕組み

守り手: `backend/tests/test_tcg_diagnostics.py` — 6件のテストが許可キー・レスポンス形状・認証ガードを網羅。固定SQLの書き換えやキー追加は必ずこのテストの修正を伴う。
