# ADR-145: public.products への FORCE ROW LEVEL SECURITY 付与（共通/テナント固有の2層保護）

- **Status**: Accepted（段階1のみ。段階2は PO GO 後に別 PR）
- **Date**: 2026-06-26
- **Author**: Hikky-dev (Claude Code)
- **Supersedes**: ADR-090 §権限制御「public は RLS 無し」方針を本 ADR で更新する（下記参照）
- **Related**: ADR-090-products-central-unification.md, ADR-072

---

## 背景

ADR-090 では `public.products`（中央商品マスタ）を「RLS 無し・中央カタログ」と定義した（ADR-090 §3 line 35: "public は RLS 無し（中央）"）。
これはテナント固有商品（`tenant_id = N`）が存在しない前提での設計であった。

将来テナント固有商品を `public.products` に格納する場合、テナント A の固有商品がテナント B から見えてしまうリスクが生じる。
また `public.products` のオーナー `jarvis` は `rolsuper=t / rolbypassrls=t` であり、通常の RLS は素通りする。

`FORCE ROW LEVEL SECURITY` を使えば `bypassrls=t` であっても強制的にポリシーが適用される（`public.translation_glossary` で 2026-06-05 より運用中・前例）。

---

## ADR-090 との関係

ADR-090 §3「public は RLS 無し（中央）」の方針を本 ADR で意図的に更新する。
ADR-090 は「中央カタログ = 全テナント共有・READ-ONLY 的な運用」を想定していたが、
固有商品格納・運営専用書き込みの2要件が加わったため DB 層の保護が必要になった。
ADR-090 の他の決定（central unification, public スキーマ配置）は変更しない。

---

## 決定

### 段階1（本 ADR の承認済み範囲）: 書き込みパスへの operator context 付与

PR #2602（base=develop）で実施。

書き込みパス W-1/W-3 に `set_operator_context(db)` / `reset_operator_context(db)` を追加し、
段階2（FORCE-RLS）を有効化したときに既存経路が正しく動作できる前提を整える。

- **W-1**: `super_admin_inbound.apply_product_candidates` — `public.products` への INSERT
- **W-3**: `parse_review.approve_review` → `inventory_movements.apply_inbound_items` — `public.products` への UPDATE
- **W-2**: `purchase_orders` の `UPDATE products` は `tenant_NNN.products` に解決（EXPLAIN で確認）。対象外・変更なし。

段階1 は RLS を付与しないため本番挙動は変わらない。

### 段階2（別 PR・PO 明示 GO 必須）: FORCE-RLS + 4 ポリシー

以下の migration を別 PR で追加する（段階1 develop マージ後、別セッション・別 recon→設計→dry-run 実施）。

```sql
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.products FORCE ROW LEVEL SECURITY;

-- SELECT: 共通行 OR 自テナント行
CREATE POLICY products_select ON public.products FOR SELECT USING (
  tenant_id IS NULL
  OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
);

-- INSERT: 共通行は is_operator=true のみ / 固有行は自テナントのみ
CREATE POLICY products_insert ON public.products FOR INSERT WITH CHECK (
  CASE
    WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
    ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
  END
);

-- UPDATE: 同上
CREATE POLICY products_update ON public.products FOR UPDATE USING (
  CASE
    WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
    ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
  END
);

-- DELETE: 同上
CREATE POLICY products_delete ON public.products FOR DELETE USING (
  CASE
    WHEN tenant_id IS NULL THEN current_setting('app.is_operator', true) = 'true'
    ELSE tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
  END
);
```

---

## 影響経路

| 経路 | 認証 | public.products 経由 | 段階1 対応 | 段階2 影響 |
|---|---|---|---|---|
| W-1: `apply_product_candidates` | `require_super_admin` | ✅ INSERT | set/reset_operator_context 追加 | is_operator='true' でポリシー通過 |
| W-2: `purchase_orders` UPDATE | `require_permission` + `get_current_tenant` | ❌ tenant_NNN.products | 変更なし | 対象外 |
| W-3: `approve_review` → `apply_inbound_items` | `require_super_admin` | ✅ UPDATE | set/reset_operator_context 追加 | is_operator='true' でポリシー通過 |

---

## 上位 KGI

`public.products` を FORCE-RLS で「共通行＝運営のみ編集／テナント固有行＝自テナントのみ」に保護し、
将来テナント固有商品を格納しても他社への漏洩が DB 層で防がれる状態にする。

---

## 参考

- `public.translation_glossary` FORCE-RLS 実装: `migrations/20260605_010000_rls_translation_glossary.sql`
- `set_operator_context` / `reset_operator_context`: `backend/app/auth/dependencies.py:419/436`
- W-2 スコープ外確認: `docs/handoff/products-rls-stage1/recon.md` §RL-6
