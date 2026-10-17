# design: products.type_master_id の削除（ADR-1026）

- 現在地: [recon.md](./recon.md)／決定: [ADR-1026](../../adr/ADR-1026-drop-products-type-master-id.md)
- PO の言葉: 2026-10-17「type_master_id→削除」。同日の指示「配線と DB の SSOT は遵守してデータを分散させることは禁止」
- 区分: 危険 PR（migrations を含む・DROP COLUMN）。適用は PO 本人の「GO #PR番号」後（docs/STANDARD-WORKFLOW.md の例外）

## 1. 目的（PO に見える変化）
商品の作品は「中分類（work_id）」1か所だけに置かれる。食い違った値を持つ使われていない欄が DB から消える。画面・解析・在庫一覧の動きは変わらない。

## 2. 対象と対象外
| 対象 | 対象外（触らない） |
|---|---|
| public.products の列 type_master_id・FK products_type_master_id_fkey・索引 idx_products_type_master_id | product_formats.type_master_id、product_format_game_links.type_master_id（細分類とゲームの対応） |
| migrations/20260922_010000_…sql の「2. products に type_master_id FK 追加」2文 | 同ファイルの product_formats.kind_id の部分 |
| 新しい migration 1つと scripts/run_all_migrations.sh の登録1行 | products.work_id・tcg_type の値、tcg_type が空の 73 行（別件） |
| 消す前の値の退避 CSV（リポジトリ外） | アプリのコード（参照 0 件のため変えない） |

## 3. 変更前後
### 3-1. migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql
変更前（:17-22）:
```sql
------------------------------------------------------------
-- 2. products に type_master_id FK 追加（商品→中分類）
------------------------------------------------------------
ALTER TABLE public.products ADD COLUMN IF NOT EXISTS type_master_id INTEGER REFERENCES public.type_master(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_products_type_master_id ON public.products (type_master_id);
```
変更後:
```sql
------------------------------------------------------------
-- 2. （削除済み）products.type_master_id は ADR-1026 で取り除いた。
--    作品の正本は products.work_id。products は列番号が上限 1600 に達しているため、
--    ここで列を足し直すと毎デプロイ失敗する。この節に ADD を戻さないこと。
------------------------------------------------------------
```
1行目のコメント「+ 商品→中分類FK追加」は「（商品→中分類FK は ADR-1026 で削除）」に直す。

### 3-2. 新規 migrations/20261017_210000_drop_products_type_master_id.sql
```sql
-- ADR-1026: products.type_master_id を取り除く（作品の正本は products.work_id）
-- 参照 0 件・依存は FK/索引/ai_ro ビューのみ（docs/handoff/drop-products-type-master-id/recon.md §2-3）
-- ai_ro ビューは run_all_migrations.sh の先頭で外れ、最後に作り直される
-- 冪等: IF EXISTS。値は書かない（ADR-1007）。適用は PO 本人の GO 後
ALTER TABLE public.products DROP CONSTRAINT IF EXISTS products_type_master_id_fkey;
DROP INDEX IF EXISTS public.idx_products_type_master_id;
ALTER TABLE public.products DROP COLUMN IF EXISTS type_master_id;
```

### 3-3. scripts/run_all_migrations.sh
末尾（`migrations/20261017_140000_create_analysis_error_report_tables.sql` の行の後）に追加:
```bash
# ADR-1026: 使われていない作品欄 products.type_master_id を取り除く（FK・索引ごと。冪等）
run_sql migrations/20261017_210000_drop_products_type_master_id.sql
```
:793-794 の登録行（20260922_010000）はファイルに kind_id の部分が残るので消さない。コメント「商品→中分類FK追加」は「（商品→中分類FK は ADR-1026 で削除）」に直す。

### 3-4. 退避（マージ前・Opus が Sonnet に依頼。リポジトリに入れない）
- 本番の全行の `id, tenant_id, type_master_id, work_id` を CSV で ~/CC報告ファイル-keep/drop-products-type-master-id/products_type_master_id_backup.csv に保存する。
- 読み取りの道は ADR-1024（ai_ro.public__products）。ai_ro から見える行数と products の総行数が一致することを確かめる。一致しなければ止めて Opus に報告する。
- デプロイ前の pg_dump（deploy.yml:195-216）が自動で走ることも、デプロイ後にファイル名・サイズで確かめる。

## 4. 影響範囲・リスクと対処
| リスク | 対処 |
|---|---|
| ADD 文が残り、次のデプロイで上限 1600 を超えて失敗 | 3-1 と 3-2 を同じ PR に入れる。K3 で ADD 文 0 件を確かめる |
| どこかが列を読んでいて壊れる | 参照 0 件（recon §2）。K6 で画面とAPIを確かめる |
| ai_ro ビューの依存で DROP が失敗 | ビューは先頭で外れる（recon §5）。K4 で作り直し後の列を確かめる |
| 値を失う | 3-4 の CSV と自動 pg_dump。列は二度と足せないので、戻すときは CSV を読む |
| CI Check 10（ADD→後で DROP） | ADD 文を消すので組にならない。K1 で確認 |

戻し方: アプリは列を使わないため、戻さなくても動きは同じ。値が要るときは 3-4 の CSV から読む（同じ列は上限のため足せない）。

## 5. 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 CI がすべて緑（migration-guard の Check 2/6/10 を含む） | `gh pr checks <PR>` で fail 0・pending 0 |
| K2 退避 CSV の行数＝本番 products の総行数、type_master_id 非空の行数＝1347＋テナント分 | `wc -l` と本番の count(*) を並べて記録 |
| K3 リポジトリで products に type_master_id を足す文が 0 件 | `git grep -n -i "products ADD COLUMN IF NOT EXISTS type_master_id" origin/main` が 0 行 |
| K4 デプロイ後、列・FK・索引が 0、ai_ro.public__products に列が無く、ai_ro.public__product_formats には type_master_id が残る | 本番カタログ（pg_attribute not attisdropped / pg_constraint / pg_indexes / information_schema.columns の ai_ro）を読み取りの道で |
| K5 デプロイが成功し、migration の段に失敗が無い | `gh run view` の deploy 結果 success と migration 段のログ |
| K6 画面と API が動く | 本番 /health 200、未ログインの商品 API が 401（500 でない）、backend ログに type_master_id のエラーが 0 件（デプロイ後 10 分） |
| K7 次のデプロイも成功する（ADD が戻っていない） | この PR の後の最初の main デプロイの結果 success（観測は後日） |

## 6. 維持の仕組み
- 守り手: CI migration-guard Check 10（同じ列の ADD→DROP を止める）と、20260922_010000 の「ADD を戻さない」コメント
- 3-1 のコメントで「ADD を戻さない」を残す。CI Check 10 が同じ列の ADD→DROP を止める。
- products の列番号の上限は products-column-churn の記録と同じ扱い。

## 7. 外部・過去事例の参照と我々への応用
不要。判断は自分の DB の参照 0 件と列番号上限の実測で決まる（recon.md「外部事例」）。

## 8. 実装カード（Sonnet）
- ブランチ: release/drop-products-type-master-id（作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-drop-products-type-master-id）
- 最初に `./scripts/dev/executor-preflight.sh || exit 1`
- 触るファイル: migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql、migrations/20261017_210000_drop_products_type_master_id.sql（新規）、scripts/run_all_migrations.sh。これ以外は触らない。
- 内容は §3-1〜3-3 のとおり。文言を変えない。
- 点検: `node scripts/check-migration-column-churn.js`（または migration-guard.yml Check 10 と同じ呼び方）、`python3 scripts/check-migration-value-writes.py`（Check 7 と同じ呼び方）、K3 の grep を作業場所で。結果の生出力を /tmp/CC報告ファイル/drop-products-type-master-id/impl/ へ。
- 想定分岐: Check 10 が失敗したら直さず止めて報告。migration-guard が「既存 migration の変更」を禁じていたら止めて報告。run_all_migrations.sh の末尾が §3-3 の想定と違ったら止めて報告。
- commit は1つ（`feat: products.type_master_id を取り除く（ADR-1026）`）。push まで。PR は作らない（Opus が作る）。
- 報告: DONE/BLOCKED:/NEEDS_DECISION: で始め、HEAD、変更ファイル、点検の生出力のパス。
