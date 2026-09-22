# Design: fix-units-view-index

## 参照
- recon: `docs/handoff/fix-units-view-index/recon.md`
- ADR-155: migration-guard 制約（DDLのみ・冪等性）

## KGI

デプロイが migration 252/280 でエラーなく完走する。

## KPI（観測可能な形で定義）

| 基準 | 検証方法 |
|---|---|
| `run_all_migrations.sh` が EXIT 0 で完了する | デプロイログで `[280/280]` まで到達することを確認 |
| `20260919_020000` 実行時に `ERROR:` 行が出ない | ログに `ERROR: cannot create index on relation` が含まれない |
| `NOTICE: ... skipping` のみ出て処理継続する | ログに `NOTICE: public.units は TABLE ではありません` が出てもエラー0 |

## 設計方針

### 変更対象

`migrations/20260919_020000_master_ssot_public_tables.sql` のみ。他ファイルは変更しない。

### 修正内容

4テーブル（units / unit_aliases / conditions / condition_aliases）の INDEX 作成を `DO $$` ブロックで包み、`pg_class.relkind = 'r'`（BASE TABLE）のときのみ実行する。

**VIEWの場合のスキップ判定:**
```sql
IF EXISTS (
    SELECT 1 FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relname = 'units' AND c.relkind = 'r'
) THEN
    -- INDEX 作成
ELSE
    RAISE NOTICE '...VIEW の可能性 — インデックス作成をスキップ';
END IF;
```

### unit_aliases / condition_aliases の CREATE TABLE FK 問題

`public.unit_aliases` の定義に `REFERENCES public.units(id)` がある。`public.units` がVIEWの場合、VIEWへのFK制約は作成不可のため `CREATE TABLE IF NOT EXISTS` 自体が失敗する。

対策: `unit_aliases` / `condition_aliases` の CREATE TABLE も同様に DO $$ ブロックで包み、
- `public.units` が TABLE のとき → FK あり で作成
- `public.units` が VIEW のとき → FK なし で作成（FK は後続migrationで追加予定）

### 冪等性の維持

INDEX の存在確認を `pg_indexes` で行い、既に存在する場合はスキップ（`CREATE INDEX IF NOT EXISTS` の同等動作を DO $$ 内で再現）。

### 影響範囲

- 変更ファイル: 1ファイル（`migrations/20260919_020000_master_ssot_public_tables.sql`）
- 呼び出し元: `scripts/run_all_migrations.sh`（変更なし・行番号はデプロイ側で管理）
- Step 5〜9（tcg_note_master等）: VIEW化対象外のため変更なし

### 戻し方

`git revert <commit>` で migration ファイルを元に戻す。ただし本番では既にVIEWが存在するため、戻した場合は同じエラーが再発する。

## 外部・過去事例の参照と我々への応用

**PostgreSQL 公式ドキュメント（pg_class）**: `relkind='r'` が ordinary table、`relkind='v'` が view。`CREATE INDEX` は ordinary table にのみ適用可能で VIEW はサポートされない。[公式: System Catalogs pg_class]

**過去事例（このリポジトリ）**: `migrations/20260920_040000_conditions_ssot_phase1.sql` 行45 で `to_regclass('public.conditions') IS NULL` による存在確認パターンを採用済み。本修正は同パターンを `relkind` 判定に拡張したもの。

**応用**: `pg_class.relkind='r'` チェックは一般的な PostgreSQL の冪等 migration パターン。今後 VIEW/TABLE 共存が発生する箇所にも同様のガードを適用できる。

## 維持の仕組み

- `DO $$` ガード内の `pg_indexes` チェックにより二重実行しても安全（冪等性維持）
- 将来 `public.units` が再度 BASE TABLE になった場合（LINE用VIEWが DROP された場合）、次回実行時に自動で INDEX が作成される
- CI Migration Guard（ADR-155 Check 7/8）は DDL のみのため引き続き通過

## 弊害・リスク

| リスク | 評価 |
|---|---|
| units が VIEW のときに unit_aliases の FK が省略される | 低。後続migration `20260920_010000` がFK再配線を担当しており、FK省略は一時的 |
| DO $$ ブロック内の INDEX 重複作成 | `pg_indexes` チェックで防止済み |
| `CREATE TABLE IF NOT EXISTS` がVIEW存在でスキップされる問題 | 既存の動作と同じ。TABLE作成はスキップされ既存VIEWが残る（これが今回のエラー原因ではない）|
