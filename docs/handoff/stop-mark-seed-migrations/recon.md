<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — 商品マスタの mark を毎デプロイで上書きする migration の廃止

**仕事名**: stop-mark-seed-migrations  
**日付**: 2026-10-09  
**対象ADR**: ADR-155（関連: ADR-1005）  
**担当**: Dev（実装担当）  
**実測時の origin/main**: dfcd31c050e42cb1f5f4d40683b44146d9b12fc1

---

## 事実（原因）

- 2026-10-08 22:49:31Z の migration 付きデプロイで、products id 440559 の mark が M2a から M3 に、id 10 が MC から MBB に戻った（Opus 確認済み）。
- 書き戻した migration は migrations/20260604_010000_seed_product_marks.sql（削除済みのためパスのみ記載）。23-24 行 `UPDATE public.products p SET mark = v.mark, updated_at = NOW() FROM (VALUES ...)`、152-153 行 `WHERE p.tenant_id IS NULL AND p.name = v.name`。値が空かの条件が無く無条件上書き。36 行 `('MEGAドリームex', 'M3')`、34 行 `('MEGA スタートデッキ100 バトルコレクション', 'MBB')`。
- 登録は `scripts/run_all_migrations.sh:264`（変更前）。run_all_migrations.sh は実行済みの記録を持たず、登録された全件を毎デプロイ流し直す（`docs/adr/ADR-1005-migration-run-once-ledger.md:17`）。

## ADR と実際の食い違い

- `docs/adr/ADR-155-product-master-ssot-csv-app.md:26`：マイグレーションは構造変更のみ、値の操作（INSERT / UPDATE / DELETE）は禁止。
- `docs/adr/ADR-155-product-master-ssot-csv-app.md:43`：既存のデータ投入マイグレーション（20260604〜20260905）は「実行済みのため影響なし」。→ 実際は毎デプロイ再実行されており、この記述は事実と合わない。
- `docs/adr/ADR-155-product-master-ssot-csv-app.md:21`：PM0198 の型番誤登録（M3 → 正しくは M2a）が既に記録されている。

## 既存の検査（チェック7）

- `.github/workflows/migration-guard.yml:407-493`：新規追加ファイルの追加行に、保護表への INSERT / UPDATE / DELETE があると落とす（保護表は 416 行）。
- 検査対象は新規追加ファイルのみ（`.github/workflows/migration-guard.yml:75-84` の `--diff-filter=A`）。既存ファイルの再実行、既存ファイルの書き換えは対象外。抜けはここ。

## 影響調査（削除するファイル）

- seed_product_marks への名前参照：scripts/run_all_migrations.sh の登録行のみ。テスト・他 migration からの参照は無し（git grep -F seed_product_marks / 20260604_010000 で確認。docs 内の言及は docs/handoff/agent-complete-design/recon.md と docs/handoff/product-master-migration-guard/recon.md のみで履歴文書）。
- 登録を外すだけなら CI の登録実在点検は通る（`scripts/check-migration-registration-exists.sh:87-116` は登録行から実在を確認する方向）。ファイルを消して登録を残すと落ちるので、両方同時に消す。
- カラム churn 許可リスト `scripts/migration-column-churn-allowlist.json:11` に seed_product_marks は載っていない（列追加なし）。

## 判断保留（第1便では触らない）

- migrations/20260616_000000_fix_tcg_type_dedup.sql：テストが名前で読む（`backend/tests/rls_bootstrap.py:27`、`backend/tests/test_products_tcg_type_fk.py:45`）ため第1便では削除しない。
- mark_en_t004（COALESCE の補充型、同一実行内で0行）、phase2b・unify（本番に届かない）、classification_ids 等：触らない。一覧は手元の product_value_migrations.tsv。

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `scripts/run_all_migrations.sh:264` | 変更前の登録行（本PRで削除） |
| `docs/adr/ADR-155-product-master-ssot-csv-app.md:26` | 値の操作禁止 |
| `docs/adr/ADR-155-product-master-ssot-csv-app.md:43` | 「実行済みのため影響なし」の記述 |
| `docs/adr/ADR-1005-migration-run-once-ledger.md:17` | 全件を毎デプロイ流し直し、実行済みの記録なし |
| `.github/workflows/migration-guard.yml:407` | チェック7（新規ファイルのみ） |
| `.github/workflows/migration-guard.yml:75` | 新規ファイル検出（diff-filter=A） |
| `scripts/check-migration-registration-exists.sh:87` | 登録行から実在を点検するループ |
| `scripts/migration-column-churn-allowlist.json:11` | 許可リストに本件のファイルは無い |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | fix_tcg_type_dedup を今流すと変わる行が本番にあるか | Opus が件数を数える SELECT を本番で実行 | 第1便の範囲外（削除しないため） |

**未解決ゼロ確認**: 第1便の範囲では該当なし
