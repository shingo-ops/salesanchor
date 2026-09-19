# design: 商品マスタ migration guard（チェック 7）

## 目的

マイグレーションから商品マスタ関連テーブルへの値操作（INSERT/UPDATE/DELETE）を CI で自動ブロックし、データの情報源を CSV 取り込みとアプリ画面に一本化する。

## 対象と対象外

### 対象（CI でブロックする）

新規マイグレーション SQL 内の以下の操作:
- `INSERT INTO` 保護テーブル
- `UPDATE` 保護テーブル
- `DELETE FROM` 保護テーブル

保護テーブル: `products`, `tcg_products`, `product_search_keywords`, `product_exclude_keywords`

スキーマ修飾（`public.`, `tenant_004.` 等）の有無を問わず検出する。

### 対象外（許可する）

- `ALTER TABLE`（列追加・型変更）
- `CREATE INDEX`
- `ADD CONSTRAINT` / `DROP CONSTRAINT`
- `DROP COLUMN`（チェック 6 で ADR 必須として別途ガード済み）

## 変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `.github/workflows/migration-guard.yml` | チェック 7 を末尾に追加（行 393〜） |
| `docs/adr/ADR-155-product-master-ssot-csv-app.md` | 新規 ADR |
| `docs/adr/README.md` | ADR 索引再生成 |

## 実装方式

チェック 6（DROP COLUMN guard）と同じパターン:

1. `steps.detect_sql.outputs.new_sql == 'true'` の場合のみ実行
2. PR 差分の追加行のみを対象（`grep '^+'`）
3. SQL コメント行（`--`）を除外
4. 保護テーブル名の正規表現でマッチ
5. マッチした場合 `exit 1` で CI を赤にする

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| INSERT ブロック | `INSERT INTO public.products` を含むテスト SQL で CI 赤 |
| UPDATE ブロック | `UPDATE products SET mark = 'X'` を含むテスト SQL で CI 赤 |
| DELETE ブロック | `DELETE FROM product_search_keywords` を含むテスト SQL で CI 赤 |
| ALTER 許可 | `ALTER TABLE products ADD COLUMN x TEXT` を含む SQL で CI 緑 |
| コメント除外 | `-- INSERT INTO products` で CI 緑（コメントは無視） |

## リスクと対処

| リスク | 対処 |
|-------|------|
| 正規表現が広すぎて関係ない SQL をブロック | テーブル名を完全一致（`products` 等 4 つのみ）で検出。`product_categories` 等は対象外 |
| 初期データ投入ができなくなる | 新規テナント立ち上げ時は CSV 取り込みを使う |

## 外部・過去事例の参照と我々への応用

自プロジェクト内の前例のみ。外部事例は不要。

- migration-guard.yml チェック 1〜6 が同一方式で稼働中。チェック 6（DROP COLUMN guard）は ADR-1002 Phase C で追加し、PR #3526 で main マージ済み。同じ grep + exit 1 パターンを踏襲する。
- ADR-025（手動 DB INSERT 原則禁止）が方針の先行決定。本 ADR-155 はその延長で、CI 自動ブロックによる技術的強制を追加する。

## 維持の仕組み

守り手: `.github/workflows/migration-guard.yml`（CI 自動実行 — PRごとに毎回チェック）

## 参照

- recon: `docs/handoff/product-master-migration-guard/recon.md`
- ADR: `docs/adr/ADR-155-product-master-ssot-csv-app.md`
- 既存ガード: `.github/workflows/migration-guard.yml` チェック 1〜6
