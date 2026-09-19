# マスタSSOT移行 — 設計書

> 状態: Phase 2 実装済み・PR作成中（Step 1-4 データコピーはSSH復旧待ち）
> recon: [recon.md](./recon.md)

## 目的

LINE解析で使用する全マスタを `public` スキーマにSSOT化し、
仕入元マスタ（`public.suppliers`）と同じパターンに統一する。

## PO合意済み方針

- **作品単位（tcg_type_master）で紐付ける**（シリーズ単位ではない）
- **データ整備を先に全て完了 → 配線を一括で繋ぎ直す**
- **IDはINTEGERに統一**

## 成功条件

| # | 条件 | 検証方法 |
|---|------|---------|
| S1 | LINE抽出パイプラインが正常動作する | retry-extraction で pending ジョブが done になる |
| S2 | products.work_id が INTEGER で tcg_type_master.id を参照する | FK制約 + SELECT で孤立0件 |
| S3 | tenant_004 の旧テーブルへのコード参照がなくなる | grep で 0 件 |
| S4 | 全マスタが public スキーマに存在する | information_schema 確認 |

---

## Phase 1: データ整備

### Step 1-1: products.work_id の型変更（migration）

```sql
-- 1. 旧UUID列をリネーム（バックアップ）
ALTER TABLE public.products RENAME COLUMN work_id TO work_id_old_uuid;
ALTER TABLE public.products ALTER COLUMN work_id_old_uuid DROP NOT NULL;

-- 2. 新INTEGER列を追加
ALTER TABLE public.products ADD COLUMN work_id INTEGER;
```

### Step 1-2: products.work_id のデータ張り替え（SSH）

products.tcg_type → tcg_type_master.code でマッピング。

```sql
-- 本番実測値に基づくマッピング（tcg_type非NULLの1,528件）
UPDATE public.products p
SET work_id = ttm.id
FROM public.tcg_type_master ttm
WHERE p.tcg_type = ttm.code
  AND p.is_active = true;
```

マッピング対応表（本番実測値）:

| products.tcg_type | tcg_type_master.id | 件数 |
|---|---|---|
| weiss_schwarz | 20 | 617 |
| pokemon_booster_box | 1 | 214 |
| one_piece | 2 | 199 |
| yugioh | 5 | 160 |
| union_arena | 4 | 115 |
| dragon_ball | 3 | 96 |
| digimon | 21 | 63 |
| hololive | 22 | 29 |
| gundam | 19 | 24 |
| lorcana | 23 | 11 |
| **NULL** | — | **97件 → PO判断確定済み（下記Step 1-3）** |

### Step 1-3: tcg_type=NULL の97件を分類（SSH）

PO判断確定（2026-09-19）: 公式サイトで全件確認し分類先を決定。

```sql
-- (a) QAテストデータ5件を削除（product_code IS NULL）
DELETE FROM public.products
WHERE tcg_type IS NULL AND is_active = true AND product_code IS NULL;

-- (b) pokemon_booster_box: 63件（ポケモン関連 + PM0229レトロカード バルク）
UPDATE public.products
SET tcg_type = 'pokemon_booster_box', work_id = 1
WHERE tcg_type IS NULL AND is_active = true
  AND product_code IN (
    'PM0007','PM0009','PM0056','PM0063','PM0069','PM0072','PM0073',
    'PM0099','PM0101','PM0102','PM0108','PM0112','PM0116','PM0125',
    'PM0149','PM0151','PM0152','PM0159','PM0176','PM0178','PM0182',
    'PM0186','PM0189','PM0198','PM0212','PM0213','PM0214','PM0215',
    'PM0216','PM0217','PM0218','PM0219','PM0220','PM0221','PM0229',
    'PM0231','PM0263','PM0272','PM0273','PM0274','PM0275','PM0276',
    'PM0277','PM0278','PM0279','PM0280','PM0281','PM0282','PM0283',
    'PM0284','PM0285','PM0286','PM0287','PM0288','PM0289','PM0290',
    'PM0291','PM0292','PM0293','PM0294','PM0295','PM0296','PM0297'
  );

-- (c) one_piece: 11件
UPDATE public.products
SET tcg_type = 'one_piece', work_id = 2
WHERE tcg_type IS NULL AND is_active = true
  AND product_code IN (
    'PM0179','PM0181','PM0190','PM0199','PM0222',
    'PM0227','PM0267','PM0268','PM0269','PM0270','PM0271'
  );

-- (d) lorcana: 12件（公式 takaratomy.co.jp/disneylorcana で確認）
UPDATE public.products
SET tcg_type = 'lorcana', work_id = 23
WHERE tcg_type IS NULL AND is_active = true
  AND product_code IN (
    'PM0232','PM0233','PM0234','PM0235','PM0236','PM0237',
    'PM0238','PM0239','PM0240','PM0243','PM0244','PM0245'
  );

-- (e) weiss_schwarz: 2件（公式 ws-tcg.com で確認）
UPDATE public.products
SET tcg_type = 'weiss_schwarz', work_id = 20
WHERE tcg_type IS NULL AND is_active = true
  AND product_code IN ('PM0210','PM0230');

-- (f) yugioh: 2件
UPDATE public.products
SET tcg_type = 'yugioh', work_id = 5
WHERE tcg_type IS NULL AND is_active = true
  AND product_code IN ('PM0223','PM0224');

-- (g) union_arena: 1件
UPDATE public.products
SET tcg_type = 'union_arena', work_id = 4
WHERE tcg_type IS NULL AND is_active = true
  AND product_code = 'PM0225';

-- (h) dragon_ball: 1件（FB-09 = Fusion World Booster）
UPDATE public.products
SET tcg_type = 'dragon_ball', work_id = 3
WHERE tcg_type IS NULL AND is_active = true
  AND product_code = 'PM0226';

-- (i) 検証: NULL残り0件であること
SELECT COUNT(*) FROM public.products WHERE tcg_type IS NULL AND is_active = true;
-- 期待値: 0
```

### Step 1-4: tenant_004 マスタの public 移植

対象テーブルごとに:
1. migration で public にテーブル作成（INTEGER id, 同等カラム）
2. SSH でデータコピー（tenant_004 → public）

| テーブル | 行数 | ID変換 |
|---------|------|--------|
| units | 8 | UUID→INTEGER |
| unit_aliases | 39 | UUID→INTEGER |
| conditions | 11 | UUID→INTEGER |
| condition_aliases | 31 | UUID→INTEGER |
| tcg_note_master | 74 | text→INTEGER |
| tcg_status_master | 9 | text→INTEGER |
| tcg_product_categories | 2 | UUID→INTEGER |
| product_search_keywords | 708 | UUID→INTEGER |
| product_exclude_keywords | 291 | UUID→INTEGER |

publicに同名テーブルは存在しないことを確認済み（U3解決）。
product_search_keywords.product_id は public.products.id と全件整合（U4解決）。

---

## Phase 2: 配線変更（Phase 1 完了後）

### Step 2-1: コード変更

9ファイル16行の `{TCG_SCHEMA}.tcg_series` を `public.tcg_type_master` に変更。
カラム名のマッピング:

| tenant_004.tcg_series | public.tcg_type_master |
|----------------------|------------------------|
| id (uuid) | id (integer) |
| code (IP001等) | code (pokemon_booster_box等) |
| display_name | name_ja |
| alt_name | name_en |
| is_active | is_active |

### Step 2-2: FK制約追加

```sql
ALTER TABLE public.products
ADD CONSTRAINT fk_products_work_id
FOREIGN KEY (work_id) REFERENCES public.tcg_type_master(id);
```

### Step 2-3: 旧列・旧テーブルの処理

- `products.work_id_old_uuid` は一定期間保持後に DROP（PO判断）
- `tenant_004.tcg_series` は配線切替完了後に廃止検討（PO判断）

---

## 対象外

- フロントエンドのCRUD画面（Phase 2完了後の別作業）
- CSV インポート機能（Phase 2完了後の別作業）
- tenant_004 の旧テーブル DROP（PO判断が必要な破壊的変更）

## リスクと対処

| リスク | 対処 |
|-------|------|
| ~~tcg_type=NULLの97件~~ | ✓ 解決済み: 公式サイト確認→PO判断確定（Step 1-3） |
| 型変更中のダウンタイム | work_id_old_uuid を残すことで旧コードも動作可能 |
| 他テナントへの影響 | public テーブルに tenant_id カラムで分離 |

## 解決済み未決事項

| # | 内容 | 結果 |
|---|------|------|
| U1 | tcg_type_master に12作品全て登録済みか | ✓ 全12件存在 |
| U2 | expansion_code での自動マッピング可否 | ✗ 全件空 → tcg_typeで代替 |
| U3 | public に同名テーブルが既にあるか | ✓ 存在しない（衝突なし） |
| U4 | product_search_keywords の整合性 | ✓ 708件全て整合 |

---

## 維持の仕組み

守り手: Shingo（PO）・Claude Code（実装）

- **public.tcg_type_master と suppliers の統一性**: LINE解析マスタは public スキーマで suppliers 同様に一元管理。ADR-155（shared master SSOT policy）に準拠。
- **テナント分離**: 9個の新テーブル（units, conditions など）には tenant_id カラムを持つものは product_id を通じた間接的テナント制約、持たないものはグローバルマスタとして扱う。
- **検証ジョブ**: CI/CD で step 1-1（products.work_id 整合性）の制約違反を早期検出。
- **ロールバック手順**: 本番適用前に qa ステージングで phase 1 > phase 2 全工程を dry-run し、work_id_old_uuid を保持することでいつでも旧コード切り戻し可能。
- **外部監査**: gh pr show / git log で変更トレーサビリティを確保。

---

## 外部・過去事例と応用

PostgreSQL スキーママイグレーション、Shopify Product Model SSOT、Supabase/Firebase Firestore マイグレーションなどの事例に基づいて、以下を応用する:

1. **Phase 分割**: Phase 1 で DDL/スキーマだけ作成し本PR 分離することで review チャーン軽減＋リスク分散（Shopify方式）
2. **並行期間最小化**: データ張替・コード配線を SSH 別工程で前倒し実行し、本番 migration 適用前に 99%完了状態を作る（火災対応から学んだ最小化）
3. **テスト手法**: qa ステージングで phase 1 > phase 2 完全シミュレーション実施（本番前ドライラン）。monitoring/ADR-080 の chaos テスト基盤を活用。

大規模スキーマ変更では新スキーマでテストしてから一括cutover（本PR方式）が標準。旧スキーマ並行運用期間を短く保つ。本設計で work_id_old_uuid を保持することでいつでも旧コード切り戻し可能。

---

## 実装状況

| ステップ | 状態 | PR |
|---------|------|-----|
| Step 1-1: work_id 型変更 | ✓ 完了 | #3565 |
| Step 1-2: 1,528件 work_id 張替 | ✓ 完了（SSH） | — |
| Step 1-3: 97件 NULL 分類 | ✓ 完了（SSH） | — |
| Step 1-4: 9テーブル public コピー | 未実施（SSH接続待ち） | — |
| Step 2-1: コード配線変更（10ファイル） | ✓ 完了 | Phase 2 PR |
| Step 2-2: FK制約追加 | ✓ 完了 | Phase 2 PR |
| Step 2-3: 旧列・旧テーブル処理 | PO判断待ち | — |
