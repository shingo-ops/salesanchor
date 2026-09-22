# design: 細分類マスタ type_master_id 紐付け

## 目的

ADR-156 の3層商品分類ツリー（product_kinds → type_master → product_lines）において、
`product_formats`（細分類）を中分類（`type_master`）に直接リンクさせることで、
カードゲームごとの細分類フィルタリングを実現する。

現状は `type_master_id` カラムが本番 DB に存在するが全件 NULL であり、
バックエンド CRUD・フロントエンド UI のいずれも `type_master_id` を扱っていない。

## 参照

- recon: `docs/handoff/product-formats-type-link/recon.md`
- ADR-156: `docs/adr/ADR-156-product-classification-tree-and-master-separation.md`
- ADR-083: `docs/adr/ADR-083-tcg-type-master.md`
- ADR-027 (i18n): `docs/adr/ADR-027-ui-internationalization.md`
- ADR-144 (UI Governance): `docs/CC_UI_GOVERNANCE.md`

## 変更概要

| レイヤー | 変更内容 |
|---------|---------|
| DB migration | `type_master_id` 追加（CI test DB 用 idempotent）＋実績9件への値設定 |
| Backend schema | `ProductFormatBase` / `ProductFormatUpdate` に `type_master_id: Optional[int]` 追加 |
| Backend router | `_COLS` / `_UPDATABLE` に `type_master_id` 追加。GET/POST/PATCH 全対応 |
| Frontend panel | カードゲームドロップダウン（`SelectControl`）追加・テーブル列追加 |
| i18n | `productFormatsMaster.typeMasterId` を ja/en 両方に追加 |
| Migration runner | `run_all_migrations.sh` に `20260923_010000` を追加 |

## 変更詳細

### migration: `migrations/20260923_010000_product_formats_add_type_master_id.sql`

- Step 1: `type_master_id` カラム追加（idempotent DO $$ ブロック）
- Step 2: `kind_id` カラム追加（idempotent DO $$ ブロック）
- Step 3: 商品実績クロス集計に基づく9件への `type_master_id` 設定
  - ポケモンカード (id=1): format id 17-22（6件）
  - 遊戯王 (id=5): format id 23（1件）
  - One Piece (id=2): format id 24-25（2件）
  - format id 1-16（商品実績0件）: NULL 据置

### backend: `backend/app/schemas/product_format.py:12,22`

`ProductFormatBase` と `ProductFormatUpdate` に `type_master_id: Optional[int] = None` を追加。

### backend: `backend/app/routers/super_admin_product_formats.py:19,20`

`_COLS` に `type_master_id` を追加。
`_UPDATABLE` に `"type_master_id"` を追加。

### frontend: `frontend/src/pages/super-admin/components/ProductFormatsMasterPanel.tsx`

- `ProductFormat` インターフェース: `type_master_id: number | null` 追加
- `FormatFormState` / `emptyForm`: `type_master_id: null` 追加
- `loadTcgTypes()`: `/super-admin/tcg/types` から `TcgType[]` を取得
- テーブル列: `typeMasterId`（`getGameName()` で名称表示）追加
- 編集/新規モーダル: `SelectControl` でカードゲーム選択ドロップダウン追加

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 管理 UI の細分類マスタ画面でカードゲーム列が表示される | ブラウザで `/super-admin` → 細分類マスタパネル を開き、テーブルに「カードゲーム」列があること |
| format id 17-25 の9件にカードゲームが設定されている | テーブルの各行に対応するゲーム名が表示されること |
| format id 1-16 は「-」と表示される | 上記 id の行が空表示（`-`）であること |
| 編集モーダルでカードゲームを変更できる | 任意の行を編集してカードゲームを変更・保存後に反映されること |
| 新規作成時にカードゲームを選択できる | 新規作成モーダルでカードゲームドロップダウンが表示されること |
| i18n キー ja/en 一致 | `productFormatsMaster` セクション 13キー完全一致（確認済み） |

## 影響範囲

- `public.product_formats` テーブル（9件の `type_master_id` が NULL → 値設定に変わる）
- `/api/v1/super-admin/product-formats` API（レスポンスに `type_master_id` が含まれるようになる）
- ProductFormatsMasterPanel（管理画面のみ・エンドユーザー影響なし）

## 戻し方

```sql
-- type_master_id を NULL に戻す
UPDATE public.product_formats SET type_master_id = NULL WHERE id IN (17,18,19,20,21,22,23,24,25);
-- カラム追加は非破壊・ロールバック不要
```

フロントエンドは前コミットにrevertで対応。

## 外部事例

ADR-156 §Phase 1 の DB 設計（3層ツリー）に従った直接結線。同一パターンは `product_lines.type_id` FK 追加（同 ADR Phase 1）で実績あり。

## 維持の仕組み

### 守り手（CI）

| workflow | 対象 |
|---------|-----|
| `.github/workflows/migration-guard.yml` | migration DDL の構文・危険操作チェック |
| `.github/workflows/migration-test.yml` | migration を test DB で実行・冪等性確認 |
| `.github/workflows/frontend-check.yml` | TypeScript 型チェック・ESLint |
| `.github/workflows/test.yml` | backend pytest |
| `.github/workflows/ui-governance-gate.yml` | ADR-144 UI ガバナンス（生 select/input 禁止） |
| `.github/workflows/schema-check.yml` | DB スキーマ整合性 |

### 不変条件

- `type_master_id` は `ON DELETE SET NULL` のため、`type_master` レコード削除時も商品フォーマットが残る
- format id 1-16 の NULL 据置は意図的。PO 判断なしに値を設定しない
