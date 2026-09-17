# 仕入元マスタ（supplier-master）— あるべき姿

> この文書は「仕入元（仕入先）の情報を1か所で管理し、LINE取り込み・画面表示・CSV出力がすべて同じデータを見る状態」を定義する設計仕様書です。

## 1. 概要

仕入元マスタは `public.suppliers` テーブルを唯一の正本（SSOT）とする。

- **ビジネス名**（`name`）: 請求書・管理画面で使う呼び名
- **LINE表示名**（`line_name`）: LINEトーク履歴の送信者名。LINE取り込みの照合に使用
- **コード**（`supplier_code`）: `SP-NNNNN` 形式の一意識別子

## 2. 境界

| 含む | 含まない |
|------|---------|
| 仕入元の基本情報（名前・連絡先・住所） | 仕入元からのメッセージ本文（`source_messages` が管理） |
| LINE表示名による照合 | LINE解析・Gemini抽出のロジック |
| 画面CRUD + CSVインポート/エクスポート | テナント独自マスタ（`tcg_suppliers` はテナント用として別管理） |
| Discord連携ルーティング | 商品マスタ（`public.products` が管理） |

## 3. テーブル構造（あるべき姿）

### public.suppliers（全テナント共有・SSOT）

| カラム | 型 | 用途 |
|--------|-----|------|
| id | SERIAL PK | 内部ID（整数） |
| supplier_code | VARCHAR(20) UNIQUE | 識別コード（SP-NNNNN） |
| name | VARCHAR(255) NOT NULL | ビジネス名 |
| line_name | VARCHAR(255) | LINE表示名（LINE取り込みの照合キー） |
| supplier_type | VARCHAR(20) | individual / corporate |
| default_language | CHAR(2) | ja / en / ko / zh |
| contact_name | VARCHAR(255) | 担当者名 |
| email | VARCHAR(255) | メールアドレス |
| phone | VARCHAR(50) | 電話番号 |
| postal_code | VARCHAR(20) | 郵便番号 |
| prefecture | VARCHAR(50) | 都道府県 |
| city | VARCHAR(100) | 市区町村 |
| address1 | VARCHAR(255) | 住所1 |
| address2 | VARCHAR(255) | 住所2 |
| address | TEXT | 住所（旧形式・後方互換） |
| notes | TEXT | 備考 |
| is_active | BOOLEAN NOT NULL | 有効フラグ（FALSE=ソフトデリート） |
| created_by | INTEGER | 作成者 |
| created_at | TIMESTAMPTZ | 作成日時 |
| updated_at | TIMESTAMPTZ | 更新日時 |

### FK連鎖（あるべき姿）

```
supplier_channels.supplier_id (INTEGER) → public.suppliers.id
source_messages.supplier_channel_id (UUID) → supplier_channels.id
extraction_jobs.source_message_id (UUID) → source_messages.id
```

## 4. データ管理ルール

| ルール | 内容 |
|--------|------|
| migrationの役割 | テーブル構造（列の追加・削除・型変更）のみ管理。値のINSERT/UPDATE/DELETEは禁止 |
| 値の管理 | アプリ画面（CRUD）とCSV（一括インポート/エクスポート）で人間が管理 |
| 削除方式 | ソフトデリート（`is_active = FALSE`）。物理削除は禁止。過去データのFK参照を保護する |
| CIガード | `migration-guard.yml` で `public.suppliers` への INSERT/UPDATE/DELETE を含むmigrationをブロック |

## 5. LINE取り込みとの連携

- PC版・Android版ともに `public.suppliers.line_name` で仕入元を照合する
- PC版: `_split_sender` が `line_name` のリストで前方一致 → `resolve_suppliers` で完全一致
- Android版: TAB分割した送信者名を `resolve_suppliers` で `line_name` に完全一致
- 両方とも同じ `resolve_suppliers` 関数を使用（Android専用の `resolve_android` は廃止）

## 6. ステータス

| 項目 | 状態 | 日付 |
|------|------|------|
| あるべき姿 | PO合意済み | 2026-09-17 |
| フェーズ1（配線変更） | 設計済み・実装未着手 | — |
| フェーズ2（CRUD画面拡張） | 未設計 | — |
| フェーズ3（CSVインポート/エクスポート） | 未設計 | — |
| フェーズ4（migration INSERT文削除） | 未着手 | — |
| フェーズ5（CIガード追加） | 未着手 | — |

## 7. 関連文書

| 文書 | パス |
|------|------|
| recon（現状調査） | [../../handoff/supplier-ssot/recon.md](../../handoff/supplier-ssot/recon.md) |
| design（フェーズ1設計） | [../../handoff/supplier-ssot/design.md](../../handoff/supplier-ssot/design.md) |
| ADR-090（products中央化） | [../../../docs/adr/ADR-090-products-central-unification.md](../../adr/ADR-090-products-central-unification.md) |
| ADR-093（在庫・マスタ再設計） | [../../adr/ADR-093-inventory-table-product-master-redesign.md](../../adr/ADR-093-inventory-table-product-master-redesign.md) |
| ADR-085（仕入先別プロンプト） | [../../adr/ADR-085-supplier-prompts.md](../../adr/ADR-085-supplier-prompts.md) |
| 商品マスタ設計仕様書 | [../product-master/README.md](../product-master/README.md) |
