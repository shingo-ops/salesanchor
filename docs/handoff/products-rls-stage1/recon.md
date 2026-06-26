# recon — public.products FORCE-RLS 段階1

**仕事名**: products-rls-stage1
**日付**: 2026-06-26
**対象ADR**: ADR-145（新規）
**担当**: CC (recon #07〜#11)

---

## 目的

`public.products` への FORCE ROW LEVEL SECURITY 付与（段階2）の前段として、
書き込みパス W-1/W-3 に operator context を付与できるか事実確認する。

---

## file:line 引用表

### RL-1: RLS 現状と bypassrls の脅威

`public.products` テーブルの RLS は現在無効（DB 直接確認: 2026-06-26）。  
DB オーナー `jarvis` は `rolsuper=t / rolbypassrls=t` であり、通常の RLS では素通りする。
`FORCE ROW LEVEL SECURITY` を使うと `bypassrls=t` であっても強制的にポリシーが適用される。

前例（FORCE-RLS 採用済みテーブル）: `public.translation_glossary`
→ migration `migrations/20260605_010000_rls_translation_glossary.sql` で ENABLE + FORCE を適用済み。

### RL-2: set/reset_operator_context の実装

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/auth/dependencies.py:419` | `async def set_operator_context(db: AsyncSession) -> None:` — `SET app.is_operator = 'true'` を実行 |
| `backend/app/auth/dependencies.py:436` | `async def reset_operator_context(db: AsyncSession) -> None:` — `SET app.is_operator = ''` を実行 |

### RL-3: get_current_tenant の fail-close 保証

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/auth/dependencies.py:228-237` | `SET search_path = tenant_NNN, public` + `SET app.tenant_id = N` + `SET app.is_operator = ''`（フェイルクローズ）。テナントリクエスト開始時に is_operator を必ず '' にリセットする。 |

### RL-4: W-1 書き込みパス（apply_product_candidates）

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/routers/super_admin_inbound.py:237` | `async def apply_product_candidates(...)` 定義。`require_super_admin` 依存。 |
| `backend/app/routers/super_admin_inbound.py:252` | `await set_operator_context(db)` — 段階1で追加（PR #2602） |
| `backend/app/routers/super_admin_inbound.py:293` | `"INSERT INTO public.products (name, category, unit, condition, language) ..."` — `public.products` への直接 INSERT |
| `backend/app/routers/super_admin_inbound.py:320` | `await reset_operator_context(db)` — finally ブロック内（段階1で追加） |

### RL-5: W-3 書き込みパス（approve_review → apply_inbound_items）

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/routers/parse_review.py:145` | `async def approve_review(...)` 定義。`require_super_admin` 依存。 |
| `backend/app/routers/parse_review.py:159` | `await set_operator_context(db)` — 段階1で追加（PR #2602） |
| `backend/app/routers/parse_review.py:280` | `await reset_operator_context(db)` — finally ブロック内（段階1で追加） |
| `backend/app/services/inventory_movements.py:181` | `async def apply_inbound_items(...)` 定義。同一 `db` セッションを受け取る。 |
| `backend/app/services/inventory_movements.py:353` | `"UPDATE public.products SET stock_quantity = :new_qty WHERE id = :pid"` — `public.products` への直接 UPDATE。`approve_review` から同一 `db` セッションで呼ばれるため W-3 の operator context が伝播。 |

### RL-6: W-2 スコープ外確認（recon #10）

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/routers/purchase_orders.py:255` | `text("UPDATE products SET quantity = quantity + :qty ...")` — スキーマ無修飾。 |
| `backend/app/auth/dependencies.py:228-237` | `get_current_tenant` が `SET search_path = tenant_NNN, public` を設定するため、上記 UPDATE は `tenant_NNN.products` に解決。 |

W-2 が `public.products` を触らないことを 2026-06-26 に VPS 本番 DB 上の `EXPLAIN (VERBOSE)` で確認:
```
SET search_path = tenant_006, public;
EXPLAIN (VERBOSE) UPDATE products SET quantity = quantity + 0 WHERE id = -1;
-- → Update on tenant_006.products  ← public.products ではない
```
`quantity` 列は各テナントスキーマのみに存在し、`public.products` には `stock_quantity` のみ。
W-2 は `public.products` FORCE-RLS の影響範囲外。修正不要。

### RL-7: 衝突チェック（recon #11）

設計起点コミット `348f618f` から調査時点（`fa2f7f40`）の間、対象 2 ファイルへの変更なし。  
関連するその他の作業（42501: app.tenant_id 系）は feature ブランチのみ・main 未マージ。干渉なし。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | W-2 が public.products を触るか | EXPLAIN で tenant_NNN.products と確認（RL-6） | ✅ 解消済み |
| 2 | bypassrls=t の jarvis が FORCE-RLS で制御できるか | translation_glossary 前例で確認済み（RL-1） | ✅ 解消済み |

**未解決ゼロ確認**: 全て解消済み
