# テストテナント サンプルデータ手順書

> **対象テナント**: `tenant-review`（schema: `tenant_006`、tenant_id=6）
> **用途**: UI使用感確認・Card化・デザイン作業時の"データが入った状態"の確認
> **最終更新**: 2026-06-10

---

## 現在の投入済みデータ（2026-06-10）

| エンティティ | 件数 | 備考 |
|------------|------|------|
| companies | 8 | Demo Trading / Demo Import 等 |
| contacts | 7 | 各取引先の担当者 |
| leads | 23 | デモリード |
| deals | 19 | デモ案件 |
| orders | 29 | ORD-2026-001〜、DEMO-2026-001 |
| order_financials | 29 | 売上・仕入コスト全件設定済み |
| order_commissions | 29 | スタッフ3名に均等割当（role='order'） |
| products | 190 | 全件に unit_price 設定済み |
| staff | 4 | EMP-00001〜EMP-00004 |
| suppliers | 47 | |
| quotes | 5 | |
| invoices | 7 | |

## 集計サマリ

| 指標 | 値 |
|------|-----|
| 総売上 | ¥13,630,000 |
| 仕入コスト | ¥8,451,000 |
| 粗利 | ¥5,179,000（38%） |
| スタッフ別報酬 | 田中 ¥499,000 / 鈴木 ¥486,000 / 山本 ¥378,000 |

---

## 再投入手順

### 前提
- VPS アクセス: `ssh -i ~/.ssh/id_ed25519 ubuntu@49.212.137.46`
- 権限: `ubuntu` ユーザー（sudo不要）

### 手順

```bash
# 1. seed SQLをVPSに送信
scp -i ~/.ssh/id_ed25519 docs/seed-data-tenant-review.sql ubuntu@49.212.137.46:/tmp/seed_tenant_006.sql

# 2. PostgreSQL コンテナで実行
ssh -i ~/.ssh/id_ed25519 ubuntu@49.212.137.46 "
  cat /tmp/seed_tenant_006.sql | \
  docker compose -f /home/ubuntu/salesanchor/docker-compose.yml exec -T postgres \
    psql -U jarvis -d jarvis_db
"
```

### リセット後の再投入（クリーンな状態から）

```sql
-- tenant_006 スキーマのデモデータ削除（注意: 全件削除）
TRUNCATE tenant_006.order_commissions CASCADE;
TRUNCATE tenant_006.order_financials CASCADE;
DELETE FROM tenant_006.staff WHERE staff_code IN ('EMP-00002','EMP-00003','EMP-00004');
DELETE FROM tenant_006.contacts WHERE contact_code IN ('CT-00004','CT-00005','CT-00006','CT-00007','CT-00008','CT-00009','CT-00010');
UPDATE tenant_006.products SET unit_price = 0 WHERE TRUE;
-- その後 seed SQL を再実行
```

---

## seed SQL（再投入用）

`.sql` ファイルは `.gitignore` 対象のため、以下に内容を記録する。

```sql
-- =============================================================
-- テストテナント (tenant_006) サンプルデータ seed
-- 目的: 集計・金額・報酬が実数で出る状態にする
-- 対象: tenant_id=6 (tenant-review) のみ
-- 実行: cat seed.sql | docker compose exec -T postgres psql -U jarvis -d jarvis_db
-- =============================================================

BEGIN;

-- 1. スタッフ追加（3名：営業2名 + リーダー1名）
INSERT INTO tenant_006.staff
  (tenant_id, user_id, staff_code, surname_jp, given_name_jp,
   surname_kana, given_name_kana, surname_en, given_name_en,
   primary_email, role_id, status, is_employee)
VALUES
  (6, NULL, 'EMP-00002', '田中', '誠一', 'タナカ', 'セイイチ', 'Tanaka', 'Seiichi',
   'tanaka.s@salesanchor.demo', 4, 'active', true),
  (6, NULL, 'EMP-00003', '鈴木', '花子', 'スズキ', 'ハナコ', 'Suzuki', 'Hanako',
   'suzuki.h@salesanchor.demo', 4, 'active', true),
  (6, NULL, 'EMP-00004', '山本', '大輔', 'ヤマモト', 'ダイスケ', 'Yamamoto', 'Daisuke',
   'yamamoto.d@salesanchor.demo', 3, 'active', true)
ON CONFLICT DO NOTHING;

-- 2. order_financials: 全受注に売上・仕入コストを設定
--    revenue_amount = total_amount / purchase_cost = 62% / exchange_fee = 1%
INSERT INTO tenant_006.order_financials
  (order_id, tenant_id, revenue_amount, purchase_cost, exchange_fee,
   commission_base_amount, created_at, updated_at)
SELECT
  o.id, 6,
  o.total_amount,
  ROUND(o.total_amount * 0.62, -3)::numeric(15,2),
  ROUND(o.total_amount * 0.01, -2)::numeric(15,2),
  o.total_amount, NOW(), NOW()
FROM tenant_006.orders o
WHERE NOT EXISTS (SELECT 1 FROM tenant_006.order_financials f WHERE f.order_id = o.id);

-- 3. order_commissions: 全受注にスタッフ割当（role='order'、10%）
WITH new_staff AS (
  SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn
  FROM tenant_006.staff
  WHERE staff_code IN ('EMP-00002', 'EMP-00003', 'EMP-00004')
)
INSERT INTO tenant_006.order_commissions
  (order_id, tenant_id, role, staff_id, calculated_amount, calculated_at, created_at, updated_at)
SELECT
  o.id, 6, 'order',
  (SELECT id FROM new_staff WHERE rn = (o.id % 3) + 1),
  ROUND(o.total_amount * 0.10, -2)::numeric(15,2),
  NOW(), NOW(), NOW()
FROM tenant_006.orders o
WHERE NOT EXISTS (
  SELECT 1 FROM tenant_006.order_commissions c WHERE c.order_id = o.id AND c.role = 'order');

-- 4. 商品価格: unit_price が 0/NULL の商品に価格設定（1,500〜15,000円）
UPDATE tenant_006.products
SET unit_price = CASE
    WHEN id % 7 = 0 THEN 1500  WHEN id % 7 = 1 THEN 2800
    WHEN id % 7 = 2 THEN 4500  WHEN id % 7 = 3 THEN 6800
    WHEN id % 7 = 4 THEN 9800  WHEN id % 7 = 5 THEN 12800
    ELSE 15000
  END
WHERE unit_price IS NULL OR unit_price = 0;

-- 5. 連絡先追加（各取引先の担当者）
INSERT INTO tenant_006.contacts
  (tenant_id, company_id, contact_code, surname, given_name, display_name,
   department, job_title, primary_email, primary_phone, is_primary_contact, status)
VALUES
  (6, 1, 'CT-00004', '青木', '雅彦', '青木 雅彦', '営業部', '部長', 'aoki.m@demo-trading.jp', '03-1234-5601', true, 'active'),
  (6, 1, 'CT-00005', '伊藤', 'さやか', '伊藤 さやか', '調達部', '課長', 'ito.s@demo-trading.jp', '03-1234-5602', false, 'active'),
  (6, 2, 'CT-00006', '上野', '浩二', '上野 浩二', '営業部', '主任', 'ueno.k@demo-import.jp', '06-2345-6701', true, 'active'),
  (6, 3, 'CT-00007', '小川', '健太', '小川 健太', 'ECチーム', 'リーダー', 'ogawa.k@demo-ec.jp', '045-3456-7801', true, 'active'),
  (6, 4, 'CT-00008', '加藤', '由美', '加藤 由美', 'バイヤー部', '担当', 'kato.y@demo-boutique.jp', '03-4567-8901', true, 'active'),
  (6, 5, 'CT-00009', '木村', '拓哉', '木村 拓哉', '仕入部', '課長', 'kimura.t@demo-wholesale.jp', '052-5678-9001', true, 'active'),
  (6, 11, 'CT-00010', '桜田', '裕子', '桜田 裕子', '営業本部', '次長', 'sakurada.h@demo-shoji.jp', '03-6789-0101', true, 'active')
ON CONFLICT DO NOTHING;

COMMIT;
```

---

## 設計メモ

### order_financials
- SalesPage（売上一覧）の集計はこのテーブルが空だと全部0になる
- `revenue_amount` = orders.total_amount（売上額）
- `purchase_cost` = total_amount × 62%（仕入コスト想定）
- `commission_base_amount` = revenue_amount（報酬計算の基礎）

### order_commissions
- CommissionsPage の「担当者別」「ロール別」集計はこのテーブルが空だと全部0
- UNIQUE制約: (order_id, role) → 受注1件 × ロール1種 = 1エントリ
- `role` 許容値: `sales`, `order`, `ship`, `purchase`, `trouble`
- `calculated_amount` = total_amount × 10%（tenant_commission_settings の 'order' レート）

### staff
- `user_id`, `firebase_uid` は NULL 可（デモスタッフはログイン不要）
- `role_id`: 3=リーダー、4=営業（tenant_006.roles より）

### products
- `unit_price` カラムに金額設定で商品詳細ページ・在庫ページに価格が表示される

---

## 実機確認ポイント

デプロイ後にしんごさんが確認する項目：

1. **SalesPage** (`/sales`) — 売上一覧が件数・金額付きで表示されること
2. **CommissionsPage** (`/commissions`) — by_staff（田中/鈴木/山本別）・by_role（order別）に金額が出ること
3. **OrdersPage** (`/orders`) — 29件の受注一覧が表示されること
4. **CompaniesPage** (`/companies`) — 8社の取引先一覧
5. **SuppliersPage** (`/suppliers`) — 47件 + 行クリックで編集モーダルが開くこと / ページ送りボタン
6. **ProductsPage** (`/products`) — 190件 + 価格表示
