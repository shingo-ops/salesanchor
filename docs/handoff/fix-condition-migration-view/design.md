# design: fix-condition-migration-view

## 参照
- recon: docs/handoff/fix-condition-migration-view/recon.md
- 対象ADR: ADR-1002-unify-product-id-and-fix-migration-compat.md

## あるべき姿

`migrations/20260925_010000_conditions_add_match_type.sql` は：

1. `public.line_conditions`（実テーブル）に `match_type` / `effect` カラムを追加する
2. `public.conditions`（VIEW）を `CREATE OR REPLACE VIEW` で再作成し新カラムを含める
3. テナントスキーマの `line_conditions` にも同様に追加する
4. `conditions` が実テーブルの環境（旧環境・ローカル等）にも対応する

## 変更方針

ADR-1002 Phase A パターン: 既存 migration に `table_type = 'BASE TABLE'` チェックを追加し、
VIEW と実テーブルを区別して処理を分岐させる。

## KGI/KPI

| 基準 | 検証方法 |
|------|---------|
| デプロイ時に migration が成功（エラーなし） | deploy ログで ERROR 行が 0 件 |
| `public.line_conditions.match_type` カラムが存在する | `\d public.line_conditions` で確認 |
| `public.conditions` VIEW に match_type が含まれる | `SELECT match_type FROM public.conditions LIMIT 1` が成功 |

## 影響範囲

- 変更ファイル: `migrations/20260925_010000_conditions_add_match_type.sql`（1ファイルのみ）
- 触らない範囲: backend Python コード、フロントエンド、その他 migration ファイル

## 外部事例

ADR-1002 で確立済みのパターン（migration ガード修正）を踏襲。
追加の外部事例調査は不要。

## 戻し方

`ALTER TABLE ADD COLUMN` は additive-only のため、カラム削除なし。
問題が発生した場合は `ALTER TABLE public.line_conditions DROP COLUMN match_type, DROP COLUMN effect;` で戻せる（PO 確認必須）。
