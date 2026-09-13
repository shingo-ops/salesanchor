# design.md：便2 — 受注明細（order_items）の新設と仕入の接続（S3・S6）

> **この文書は何か（素人向け1行説明)**：「受注」の箱に、何をいくつ・いくらで売ったかを商品ごとに1行ずつ入れる引き出し（order_items）を作り、その1行1行に「どこからいくらで仕入れたか」の糸を繋ぐ変更手順書。

- 親: `docs/specs/transaction-flow/README.md`（K5・K7素材／SSOT割当 S3・S6）
- recon: recon_ben2.txt（2026-07-03・origin/main b4a1ced7・file:line実物）
- 危険度: **低**（本番 orders 0件＝backfillなし。migrationはCREATE/ALTERのみ）。ただし migrations/ を触るため GO必須。

## 1. reconで確定した現状（根拠）
- 明細の型は既に2つ実在：quote_items（tenant.py:844-858）・invoice_items（同:897-911）。列構成＝product_id→public.products / product_name / name_en / condition / unit / quantity / unit_price / weight / subtotal / sort_order（invoices側INSERTは hs_code も：invoices.py:304）
- 仕入は伝票＋明細が実在：purchase_orders（同:945-958。ordered_at/received_at あり・**paid_at なし・送料列なし**）＋purchase_order_items（同:960-968。product_id/quantity/unit_cost/subtotal。**どの受注明細のためかの参照なし**）
- 旧系統 order_purchase_details（migration 049）＝「1受注=1仕入」のOrderFlow互換。**便2では触らない**（併存・統合は別便。台帳登録）
- 商品参照は public.products に統一済み（ADR-090。テナント側productsはDEPRECATED）。condition は現状 varchar（商材マスタ実装時に condition_id FK へ昇格＝S11・便5系）

## 2. 変更内容
### 2-1. 新テーブル {schema}.order_items（tenant.py 追記＋migration）
invoice_items と同型＋SSOT割当ぶんの拡張（**S3：売った物の唯一の正**）:
```sql
CREATE TABLE IF NOT EXISTS {schema}.order_items (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL DEFAULT {tenant_id},
    order_id INTEGER NOT NULL REFERENCES {schema}.orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES public.products(id),
    product_name VARCHAR(255) NOT NULL,
    name_en VARCHAR(255),
    condition VARCHAR(50),          -- 商材マスタ実装後に condition_id FK へ昇格（S11）
    unit VARCHAR(20),
    sku VARCHAR(100),               -- 都度SKU（elogi用・マスタに持たない：PO確定済）
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(15, 2) NOT NULL,
    subtotal NUMERIC(15, 2) NOT NULL,
    weight NUMERIC(10, 3),
    hs_code VARCHAR(20),            -- 品目のHTS（elogi申告）
    usd_unit_value NUMERIC(15, 2),  -- USD内容品単価（elogi申告）
    exchange_rate_usd NUMERIC(12, 4), -- elogi申告用為替（S割当：明細側の為替）
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON {schema}.order_items (order_id);
```
＋RLS有効化・tenant_isolation ポリシー・updated_at トリガ（便1a と同書式）。

### 2-2. 仕入の接続（ALTER・migration）
- `purchase_order_items` に **order_item_id INTEGER REFERENCES {schema}.order_items(id)**（NULL可＝在庫向け仕入は受注に紐づかない。S14在庫接点と整合）＋INDEX
- `purchase_orders` に **paid_at TIMESTAMPTZ**（K7⑤仕入費支払い）と **shipping_fee NUMERIC(15,2) DEFAULT 0**（仕入送料）

### 2-3. 最小API（既存パターン複製）
- `POST /orders/{id}/items`（複数行一括・quotes.py:226 のINSERT流儀を複製）／`GET /orders/{id}/items`
- purchase_orders 作成/明細に order_item_id を受け付け（purchase_orders.py:191 のINSERTへ1列追加）
- 画面は便5（本便はAPIまで。既存画面は非破壊）

### 2-4. スプレッドシート取引列の割当（原本→箱・本便ぶん）
| 原本列 | 置き場所 |
|---|---|
| 商品名/状態/数量/単価/小計/SKU/品目・HTSコード/USD内容品単価/為替(USD) | **order_items**（2-1） |
| 仕入れ注文日/取引番号/仕入元/仕入単価/仕入数量/仕入送料/仕入総額/仕入備考/仕入担当 | **purchase_orders＋items**（既存列＋2-2。取引番号=po_number・担当=created_by） |
| 送料/関税/合計/決済方法/決済通貨/入金系 | order・invoices（既存。向きの正常化は便3=S13） |
| 発送系/トラブル系/売上情報（利益等） | 便3（発送・trouble・導出）／便4（派生値） |

## 3. 触らない範囲
order_purchase_details（併存・別便で統合）／invoices・quotes の既存フロー／orders の status・段階（便3）／フロント画面／在庫本体（接点列のみ）。

## 4. KPI（○×・数値）
| # | KPI | 合格条件 |
|---|---|---|
| P1 | order_items が全テナントに存在・RLS有効 | `\d` で列一式＋policy 存在（004/006） |
| P2 | 仕入接続列 | purchase_order_items.order_item_id / purchase_orders.paid_at / shipping_fee が存在（is_nullable含め生出力） |
| P3 | 1受注複数商品 | QAで1 orderに2行登録→GET で2行・order_id同一 |
| P4 | 分割仕入の検算 | 1つの order_item(100個) に PO明細 60+40 を紐づけ、検算SQL（明細qty合計=仕入qty合計）が一致 |
| P5 | 非破壊 | 既存テスト全緑（既知2件除く）＋quotes/invoices/PO のCRUDテスト緑 |
| P6 | 本番適用 | dry-run（構造のみ・ROLLBACK）→GO→適用→`\d`生出力で新列確認 |

## 5. 外部・過去事例
- ヘッダ+明細+明細間リンクは販売管理の定石（quote/invoice の既存2例に完全準拠＝発明なし）
- 便1a/1b の migration 作法（冪等DOループ・条件分岐NOTICE・dry-run→GO）を踏襲

## 6. 維持の仕組み
- 守り手: migration（DB構造）＋ `backend/tests/test_order_items_ben2.py`（P3/P4を常時CI: pytest系ワークフロー）
- 対象: 受注明細の粒度崩れ（1受注1行に逆戻り・仕入と明細の断線）
