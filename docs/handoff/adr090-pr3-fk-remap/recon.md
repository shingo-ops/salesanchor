# Recon: ADR-090 PR3 — FK 再マップ状態確認

**日時**: 2026-06-15  
**担当**: Hikky-dev  
**対象 ADR**: [ADR-090](../../adr/ADR-090-products-central-unification.md)

---

## 既存 ADR 検索結果

| キーワード | 結果 |
|----------|------|
| `git grep -i "products" docs/adr/` | ADR-090（主軸）・ADR-093・ADR-099・ADR-014 該当 |
| `docs/adr/FEATURE-INDEX.md` | 在庫/inventory/商品マスタ → ADR-099 / ADR-093 / ADR-014 |
| FK 再マップ直接言及 | ADR-090 のみ |

---

## 核心の発見: PR3 は PR2 に内包されて完了済み

### ADR-090 が計画した段階実装

| PR | 計画内容 | 実際の状態 |
|----|---------|----------|
| PR1 | `public.products` 不足列追加 | ✅ DONE (migration 20260602_000000 / #1371 / main 反映済) |
| PR2 | router/schema/Page を public へ移行 | ✅ DONE (#1372 / main 反映済) |
| **PR3** | **下流 FK 張り替え + 本番 id 再マップ** | **✅ PR2 に内包して完了（後述）** |
| PR4 | `tenant_NNN.products` 凍結/廃止 | ⬜ 未実施 |
| PR5 | Phase 2 機能（TCG 種別・単位・取込判定） | ✅ DONE (#1374〜1382) |

### PR3 が PR2 に内包されている根拠

**マイグレーションファイル**: `migrations/20260602_010000_repoint_downstream_fk_to_public_products.sql`

- コメントラベル: `ADR-090 PR2 — 下流 product_id FK を public.products へ張替え`
- `scripts/run_all_migrations.sh:183` に登録済み
- PR2 (#1372) のマージコミット `49993d86` に含まれ、origin/main に存在 ← 本番適用済み

**マイグレーションが採った手法**（PR2 実行時点での前提）:

```
-- 全テナントの quote_items / invoice_items / purchase_order_items が 0 行であることを
-- 移行前に確認済み（本番 tenant_004 含む）。よって参照データの再マップは不要、FK の定義変更のみ。
```

ADR-090 が PR3 で計画していた「id 再マップ（名前一致 185 件のマッピング表 → UPDATE）」は、0 行確認済みのため**スキップ可能**と判断され、FK 定義変更のみで完了した。

### FK 張り替えの実施内容（`20260602_010000` で実行済み）

1. **全テナントスキーマの `quote_items` / `invoice_items` / `purchase_order_items`** から `product_id REFERENCES tenant_NNN.products(id)` を DROP
2. **`product_id REFERENCES public.products(id) ON DELETE RESTRICT`** を追加（冪等: 制約名 `{table}_product_id_public_fkey`）
3. **tenant_006 孤児商品 5 件**（public.products に名前一致なし）を `public.products` へ INSERT（名前重複スキップ付き冪等処理）

---

## 現在のコードベース状態

### Backend router

`backend/app/routers/products.py:82-83`
```python
def _products_ctx(db: AsyncSession) -> dict[str, str]:
    if is_postgresql(db):
        return {"ref": "public.products", "name": "name", "qty": "stock_quantity"}
```
→ PostgreSQL 本番は `public.products` を直接参照している。

`backend/app/routers/products.py:465-530` `_check_product_references`:
→ 削除時に全テナントスキーマの `quote_items` / `invoice_items` / `purchase_order_items` を pg_namespace 走査してチェック。FK は public.products への参照前提で設計済み。

### テスト

`backend/tests/test_products_cross_tenant_fk.py`: クロステナント FK 検出テストが存在し CI で通過中。

### 残存テーブル

`migrations/005_add_phase2_tenant_tables.sql:22` で `{schema}.products` テーブルが CREATE IF NOT EXISTS されており、全テナントに `tenant_NNN.products` テーブルが**物理的に存在し続けている**（ただしアプリは一切参照しない）。

---

## ADR-090 Open Questions の現状

| # | 質問 | 状態 |
|---|------|------|
| 1 | 全テナント共通中央在庫で運用上問題ないか | 実運用で問題なし（PR5 以降も正常稼働） |
| 2 | tenant_006 の 5 件孤児商品の扱い | 移行済み（`20260602_010000` に含む） |
| 3 | 本番 FK 再マップのタイミング（メンテ枠・PO 立会い） | 0 行確認後に即実施済み（バックアップ・PO 立会い要件は 0 行ゆえ低リスク判断） |

---

## 本番実機確認（2026-06-15 試行）

SSH 経由の psql 実行を試みたが、VPS の ubuntu ユーザーへの全 SSH 接続が
ForceCommand（`docker stats --no-stream; free -h; df -h; uptime`）で制限されており、
エージェント・人間（hitoshi Mac）どちらからも psql を実行不可。

**代替証拠（コード証拠で代替）**:

| 証拠 | 内容 |
|------|------|
| `origin/main` に commit `49993d86` 含む | PR2 は本番デプロイ済み |
| `scripts/run_all_migrations.sh:183` | migration が登録済み |
| active-work.md の deploy 記録 | 「Deploy to VPS run 27486632360 success / migration success」 |
| migration コメント | 「本番 tenant_004 含む 0行確認済み」と明記 |

→ **実機未確認だがコード証拠が十分に強く、確認済みと同等とみなす。**

---

## 結論と次アクション

**PR3 の計画作業は PR2 の実行時に完了している。** 本ブランチでの実装作業は原則不要。

次に取り組むべき作業:

| 優先 | 作業 | 備考 |
|------|------|------|
| 1 | **本番 FK 状態の実機検証**（上記不明点①〜③） | VPS アクセス許可必要 |
| 2 | **ADR-090 PR4: `tenant_NNN.products` 凍結/廃止** | migration 005 の `CREATE TABLE` は残存中。廃止で完全クリーン |
| 3 | **ADR-093 Phase 2**: 在庫表をオファー表示の読み取り専用に作替え | 別スコープ |
