# ADR-1030: 商品の作品の写し products.tcg_type をやめ、中分類 products.work_id だけで絞る

| 項目 | 内容 |
|------|------|
| ステータス | Accepted（2026-10-19。便1 #4508・便2 #4512 とも本番反映済み、受入結果は design.md §6-1。方針は PO 2026-10-18 チャット「在庫表のタブは中分類で絞る（y）」「SSOTしたいので不要なら列を消してくれ」。列を消す便2は危険 PR。GO は PO の委任に基づく Claude Opus 発行（PO 2026-10-18「GO記録…必要な権限は全て…使用して良い」「PRマージ、デプロイまで完走」）） |
| 起案日 | 2026-10-18 |
| 方針の決定者 | Shingo（PO） |
| 関連 | ADR-1026（作品は products.work_id だけに置く）、ADR-156（type_master＝中分類）、ADR-090（PR5a で tcg_type 追加）、ADR-1020（中分類は必須）、ADR-1024（ai_ro ビュー）、ADR-1007（migration で値を入れない） |
| 設計 | docs/handoff/inventory-tab-by-work-id/design.md（現在地: 同 recon.md） |

---

## What（何を決めるか）

1. 在庫表のタブ・商品一覧の絞り込み・在庫の集計と検索は、作品を `products.work_id` から `type_master` をたどって判定する。`products.tcg_type` は読まない（便1）。
2. API は作品の符号を `work_code`（`type_master.code` を work_id からたどった値）として返し、絞り込みの引数も `work_code` にする。`tcg_type` という名前の入出力は products 系・在庫系の API から無くす（便1）。
3. 商品編集画面（/admin/products/:id/edit）の「カテゴリ」欄（tcg_type を書く唯一の画面入力）を取り除く。作品は TCG 商品マスタの商品詳細の「作品」（work_id）で編集する（便1）。
4. 便1 の本番反映と確認の後、`public.products.tcg_type` 列・外部キー `fk_products_tcg_type`・索引 `idx_public_products_tcg_type` を取り除き、列を足す migration の ADD 文を消す。消す前に全行の `id, tcg_type, work_id` を CSV に退避する（便2）。
5. `public.tcg_series_master.tcg_type`（別の表の同名列）は対象外。

## Why（なぜ）

- 作品の正本は `products.work_id`（ADR-1026:17、docs/specs/master-ssot-migration/design.md:13,22）。`tcg_type` は work_id の指す `type_master.code` の写しで、値が入っている 1347 行は全部 work_id と一致し、食い違いは 0（recon §c）。
- 共用商品の登録（backend/app/services/tcg_product_master_svc.py:566-573）は work_id だけを入れ、tcg_type を入れない。このため 79 行が空で（recon §d）、在庫表のタブ（inventory_offers.py:196 `d.tcg_type = :tcg_type`）に出ない。実例: ハドウシーカー（466045）は「ポケモンBOX」タブに出なかった（2026-10-18 PO 報告）。
- 写しを埋め直すと、同じ情報が2か所に残り、登録のたびに写し忘れが再発する。PO の決まり「配線と DB の SSOT を守り、データを分散させない」（2026-10-17, 2026-10-18）に反する。

## 選ばなかった案

- **空の 79 行に tcg_type を埋める**: 今後の登録でまた空になる。二重持ちが残る。
- **登録処理で tcg_type も書くようにする**: 二重持ちが残り、片方だけ直す経路（商品編集画面）で再び食い違う。
- **API の引数名 `tcg_type` を残して中身だけ work_id にする**: 名前と正本が食い違い、消したはずの列を探す点検（grep）で毎回ひっかかる。

## 守ること・危ないこと

- **列の数の上限**: 本番 products は列番号が上限 1600 に達している（recon §h）。便2 で列を消した後に `migrations/20260602_020000_add_products_tcg_type.sql` の ADD が流れると毎デプロイ失敗する。ADD 文の削除と列の削除は同じ PR に入れる。
- **順番**: 便1（読む側をすべて work_id へ）を本番に出して確かめてから便2（列を消す）。逆にすると在庫表と商品一覧が 500 になる。
- **戻し方**: 便1 は PR の revert で戻る。便2 の後は同じ列を足せない（上限）ため、値が要るときは退避 CSV とデプロイ前の自動 pg_dump（deploy.yml:195-216）から読む。アプリは便1 の時点で列を使わないので、戻さなくても動作は変わらない。

## 確かめ方

design.md §6 の受入条件の表による。受入結果（K1〜K10）は docs/handoff/inventory-tab-by-work-id/design.md §6-1 に記録した。
