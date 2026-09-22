# recon: 細分類マスタ type_master_id 紐付け

## 調査日時
2026-09-23

## 関連 ADR
- ADR-156: `docs/adr/ADR-156-product-classification-tree-and-master-separation.md`
  - 商品分類3層構造（product_kinds → type_master → product_lines）確定
  - `type_master`（中分類）は旧 `tcg_type_master` のリネーム先
- ADR-083: `docs/adr/ADR-083-tcg-type-master.md`
  - `public.tcg_type_master`（現 `type_master`）テーブル設計の原点

## 現状把握

### DB 状態（本番）

`type_master_id` カラムは本番 DB の `public.product_formats` に既存。全25件 NULL。

```
-- 商品実績に基づくカラム追加有無確認
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'product_formats'
  AND column_name = 'type_master_id';
-- 結果: type_master_id | integer  （本番に既存・NULL）
```

### DB クエリ根拠（商品×format×type クロス集計）

migration `migrations/20260923_010000_product_formats_add_type_master_id.sql:21-33` のコメントに証拠あり:

```sql
-- 根拠: public.products の product_format_id × type_master_id クロス集計結果
-- ポケモンカード(type_master_id=1): SPECIAL_BOX(17), DECK_BUILD_BOX(18),
--   PREMIUM_TRAINER_BOX(19), COLLECTOR_BOX(20), HIGH_CLASS_DECK(21), BOOSTER_BOX(22)
-- 遊戯王(type_master_id=5): SPECIAL_SET(23)
-- One Piece(type_master_id=2): ILLUSTRATION_BOX(24), STORAGE_BOX(25)
-- id 1-16: 商品紐付け0件 → NULL 据置（PO判断待ち）
```

紐付け対象: 9件（id 17-25）
NULL 据置: 16件（id 1-16、商品実績なし）

### バックエンド現状（変更前）

- `backend/app/schemas/product_format.py`: `type_master_id` フィールド**なし**
- `backend/app/routers/super_admin_product_formats.py`: `_COLS` / `_UPDATABLE` に `type_master_id` **なし**
- GET/POST/PATCH すべてで `type_master_id` を無視していた

### フロントエンド現状（変更前）

- `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx`:
  - `ProductFormat` インターフェースに `type_master_id` **なし**
  - カードゲーム選択ドロップダウン **なし**
  - テーブル列にカードゲーム表示 **なし**

### i18n 現状（変更前）

- `frontend/src/locales/ja.json` `productFormatsMaster` セクション: `typeMasterId` キー **なし**
- `frontend/src/locales/en.json` `productFormatsMaster` セクション: `typeMasterId` キー **なし**

## 変更後の確認

### migration 登録状況

`scripts/run_all_migrations.sh` に `20260923_010000_product_formats_add_type_master_id.sql` 登録済み。

### i18n キー一致確認

```
ja.json productFormatsMaster キー数: 13
en.json productFormatsMaster キー数: 13
差異: なし（完全一致）
```

追加キー: `typeMasterId`（ja: "カードゲーム"、en: "Card Game"）

### 変更ファイル一覧（git show HEAD）

```
backend/app/routers/super_admin_product_formats.py
backend/app/schemas/product_format.py
frontend/src/locales/en.json
frontend/src/locales/ja.json
frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx
migrations/20260923_010000_product_formats_add_type_master_id.sql
scripts/run_all_migrations.sh
```
