# ADR-1026: 商品の使われていない作品欄 products.type_master_id を取り除く

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（方針は PO 2026-10-17 チャット「type_master_id→削除」。適用は PO 本人の「GO #PR番号」後。docs/STANDARD-WORKFLOW.md の例外「DROP TABLE/COLUMN を含む migration は PO 本人の GO」。What 3 は ADR-1038 で改められた: Amended by ADR-1038） |
| 起案日 | 2026-10-17 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-156（分類の木。Phase 7 で列を追加）、docs/specs/master-ssot-migration/design.md（作品の正本は products.work_id）、ADR-1020（中分類＝work_id を必須）、ADR-1024（ai_ro ビュー）、ADR-1007（migration で値を入れない） |
| 設計 | docs/handoff/drop-products-type-master-id/design.md（現在地: 同 recon.md） |

---

## What（何を決めるか）

1. 共用・テナントを問わず `public.products` の列 `type_master_id` と、その外部キー `products_type_master_id_fkey`・索引 `idx_products_type_master_id` を取り除く。
2. 列を足していた `migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql` の「2. products に type_master_id FK 追加」の2文を消す。同じファイルの product_formats.kind_id の部分は残す。
3. 商品の作品（中分類）は `products.work_id` だけに置く。`product_formats.type_master_id` と `product_format_game_links.type_master_id`（細分類とゲームの対応）は別の情報なので変えない。
4. 消す直前に、共用・テナントの全行の `id, type_master_id, work_id` を CSV に退避して保存する。

## Why（なぜ）

- 作品の正本は `products.work_id`（docs/specs/master-ssot-migration/design.md:13,22）。画面・API・解析・在庫一覧 GAS はすべて work_id か tcg_type を使い、`products.type_master_id` を読み書きするコードは origin/main に 0 件（recon §2）。
- それなのに値は入っていて、共用 1420 行のうち 9 行で work_id と違う作品を指し、73 行は空（recon §1）。値を入れた記録はリポジトリにも作業記録にも無い。
- 正しい値で埋め直すと、同じ情報が2か所に残る。PO の決まり「配線と DB の SSOT を守り、データを分散させない」（2026-10-17）に反する。
- 残すと、将来この欄を正しい作品だと思って使った処理が、間違った作品で動く。

## 選ばなかった案

- **値を work_id に揃えて残す**: 同じ情報が2か所になる。片方を直し忘れると、また食い違う。
- **残して「使っていない」と文書に書くだけ**: 間違った値が残り続ける。PO が削除を選んだ。

## 守ること・危ないこと

- **列の数の上限**: 本番の products は列番号（attnum）が既に上限 1600 に達している（生きている列 57・消した列 1543。recon §1）。列を消しても番号は戻らない。2 の ADD 文を残すと、次のデプロイから毎回「列を足す」が走り、上限で失敗してデプロイが止まる。だから 1 と 2 は同じ PR で入れる。
- **戻し方**: 同じ列は二度と足せない（上限のため）。戻すときは退避した CSV から値を読む。アプリは列を使っていないので、戻さなくても動作は変わらない。
- **ai_ro ビュー**: `migrations/20261017_125900_drop_ai_ro_views.sql` が全 migration の前にビューを外し、最後に `20261017_130100_create_ai_ro_views.sql` が列を数え直して作る（scripts/run_all_migrations.sh:80,86-106）。だから DROP COLUMN はビューに止められず、作り直した後のビューからこの列が消える。

## 確かめ方

design.md §5 の受入条件の表による。
