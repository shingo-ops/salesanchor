# products-rls-stage2 design

## 目標（KGI）

`public.products` を FORCE-RLS で「共通行＝運営のみ編集／テナント固有行＝自テナントのみ」に保護し、他社漏洩を防ぐ。

## ADR 参照

ADR-145 `docs/adr/ADR-145-public-products-force-rls.md`（段階2＝本 migration が実装フェーズ）。ADR-090 §3「public は RLS 無し」を明示的に上書き。

## 設計概要

### 外部事例

| 参照 | 内容 |
|------|------|
| 社内前例: `public.translation_glossary` | 同一 grant 構成（SELECT/INSERT/UPDATE/DELETE）で FORCE-RLS 稼働中（`relrowsecurity=t / relforcerowsecurity=t`）。4 ポリシーパターンを移植 |
| PostgreSQL 公式: FORCE ROW LEVEL SECURITY | `bypassrls=t` ロールも強制適用（superuser のみ免除）。`salesanchor_app` は `rolsuper=f / rolbypassrls=f` のため確実に有効 |

### migration ファイル

`migrations/20260626_130000_force_rls_public_products.sql`

- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`（冪等）
- 4 ポリシー（DROP IF EXISTS → CREATE）:
  - `products_select`: `tenant_id IS NULL OR tenant_id = app.tenant_id::INTEGER`
  - `products_insert`: `tenant_id IS NULL → is_operator='true'` / `tenant_id IS NOT NULL → 自テナント`
  - `products_update`: 同上（USING + WITH CHECK 両方）
  - `products_delete`: 同上（USING のみ）

### write 経路一覧

| 経路 | ファイル:行 | 操作 | 対応 |
|------|------------|------|------|
| W-1 | `backend/app/routers/super_admin_inbound.py:252,320` | INSERT shared（段階1で operator context 付与済み） | ○ |
| W-2 | `backend/app/routers/purchase_orders.py:255` | UPDATE tenant固有（search_path → tenant_NNN.products） | FORCE-RLS 対象外 |
| W-3 | `backend/app/routers/parse_review.py:159,280` | UPDATE shared（段階1で operator context 付与済み） | ○ |

### 触らないファイル

| ファイル | 理由 |
|---------|------|
| `backend/app/auth/dependencies.py` | set/reset_operator_context は段階1で完了 |
| `backend/app/services/inventory_movements.py` | W-3 の同一 db セッションを通じて context 継承 |
| `backend/app/routers/purchase_orders.py` | W-2 は public.products に非到達（search_path 経由で tenant_NNN.products） |

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| migration 適用後 `relforcerowsecurity=t` | 本番適用後 `SELECT relforcerowsecurity FROM pg_class WHERE relname='products' AND relnamespace='public'::regnamespace` が `t` を返す |
| W-1 INSERT shared（運営）が通る | `/api/v1/super-admin/inbound/apply` を super_admin 権限で呼び HTTP 200（or 204） |
| W-3 UPDATE shared（運営）が通る | `approve_review` エンドポイントを super_admin 権限で呼び HTTP 200 |
| 非運営テナントが shared 行を INSERT/UPDATE/DELETE できない | `is_operator=''` セッションで INSERT → `42501` エラーまたは空更新 |
| 他テナント固有行が SELECT から見えない | `app.tenant_id=6` セッションで `tenant_id=7` 行が返らない |
| W-2 は既存動作のまま | purchase_orders テストが CI でグリーン |
| migration 冪等 | 二重実行でエラーなし（DROP IF EXISTS / ENABLE は冪等） |
| CI テスト全通過 | migration-test / backend-test / backend-rls-test がグリーン |

## stage1 → stage2 対応関係

| フェーズ | 内容 | PR | 状態 |
|---------|------|----|------|
| 段階1 | W-1/W-3 write 経路に operator context 付与 | #2602 | develop マージ済み（26f0ede9） |
| 段階2 | FORCE-RLS 有効化 + 4 ポリシー migration | 本 PR | develop マージ待ち |

develop マージ ≠ 本番反映。本番で FORCE-RLS が効くのは後日の develop→main リリース時（別途 PO 最終 GO 必要）。

## 参照

- recon: `docs/handoff/products-rls-stage2/recon.md`
- stage1 recon/design: `docs/handoff/products-rls-stage1/`
- ADR-145: `docs/adr/ADR-145-public-products-force-rls.md`
