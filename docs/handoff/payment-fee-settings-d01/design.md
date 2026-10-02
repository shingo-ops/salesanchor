# 設計 — payment_fee_settings §D01

**対象ADR**: ADR-072  
**recon**: docs/handoff/payment-fee-settings-d01/recon.md  
**日付**: 2026-10-02  
**担当**: Sonnet / Opus審査済み

---

## 外部・過去事例の参照と我々への応用

- 事例1: SaaS Multi-tenant fee configuration（Stripe Connect platform等）→ テナントごとに手数料率を上書き可能にするNULLパターンを採用。`tenant_id IS NULL` = 共用デフォルト、`tenant_id = X` = テナント独自設定
- 事例2: 既存実装 `backend/app/routers/units.py` → 同じNULLパターン・権限キー `suppliers.view` を踏襲。実績あるパターンの再利用

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `public.payment_fee_settings` テーブルが作成される | migration適用後 `\d public.payment_fee_settings` |
| super admin CRUD APIが200を返す | CI pytest + `test_super_admin_payment_fee_settings` |
| テナントCRUD APIがADR-072準拠（reset_tenant_context有り） | ADR-072 lint チェック（CI）|
| migration-guardが通過する | CI migration-guard チェック |

---

## 技術 How・KPI

- KPI: CI全チェック通過・migration-guard通過
- 技術選択: NULLパターン（units.pyと同一設計）。理由: プロジェクト内で確立済みの標準パターン
- テーブル定義のみのmigration（seed不要）: PO方針「値はアプリ画面から管理」に準拠

---

## 弊害・トレードオフ

- main.pyのimport順序（ruff I001）: 警告は出るがコミットはブロックされない。次の整理PRで対応可
- 本番適用にはPO GOが必要（migrations/含む）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | テーブル定義migration作成 | Sonnet |
| 2 | Pydanticスキーマ作成 | Sonnet |
| 3 | super admin CRUDルーター作成 | Sonnet |
| 4 | テナントCRUDルーター作成 | Sonnet |
| 5 | main.pyにルーター登録 | Sonnet |
| 6 | run_all_migrations.shに登録 | Sonnet |
| 7 | PR作成・CI確認 | Sonnet |
| 8 | 本番適用（PO GO後） | PO |

---

## 守り手

- ADR-072 lint（CI）: reset_tenant_contextチェック
- migration-guard（CI）: DROP等の危険操作チェック
- ADR-135/136: migrations/含むPRのPO GO必須
