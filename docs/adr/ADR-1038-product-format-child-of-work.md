# ADR-1038: 細分類は中分類（作品）の子。親子は product_format_game_links の 1 か所だけに持ち、DB で守る

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（2026-10-22） |
| 備考 | PO 2026-10-21「細分類は中分類と紐づけて中分類を親に親子関係にできる？」への設計。PO 前提（2026-10-22）: 配線と DB の SSOT を守る、データを分散させない、金型にないハードコードをしない。 |
| 起案日 | 2026-10-22 |
| 方針の決定者 | Shingo（PO）。形の選択: 2026-10-22 チャット「1,」（同じ細分類を複数の中分類で一緒に使う。design §1-2 の A）。設計: Claude Opus |
| 改める | Amends ADR-1026（What 3） |
| 関連 | ADR-1020 What 5（links が選択肢の正）、ADR-1026 What 3（本 ADR で改める）、ADR-156（分類の木）、ADR-1007（migration で値を書かない）、ADR-1037（lock_timeout）、ADR-135/136、ADR-1003 |
| 設計 | `docs/handoff/format-work-parent/design.md`、現状 `docs/handoff/format-work-parent/recon.md` |

---

## What（何を決めたか）

1. 中分類（`public.type_master`）を親、細分類（`public.product_formats`）を子とする。親子の記録は `public.product_format_game_links` だけに持つ。1 つの親は子を複数持ち、1 つの子は複数の親の下に並べられる。
2. `public.products` に複合 FK `fk_products_format_in_work`（product_format_id, work_id）→ `product_format_game_links`（format_id, type_master_id）を置く。MATCH SIMPLE、NO ACTION。親に属さない細分類を持つ商品は、どの経路からも書けない。
3. `product_formats.type_master_id` は二重の置き場として落とす。ADR-1026 What 3 の「別の情報なので変えない」は、この ADR で改める。落とす前に値を CSV に退避する。ADD 側の migration から ADD 文を取り除き、戻さない。
4. 作品と細分類を書く処理は、1 つの文で両方を書く。
5. 細分類を物理削除するときは、先に使用中の商品から外す。通常の削除は論理削除（is_active=FALSE）とする。

## Why（なぜ）

- 親子の表は既にあり、全入口がこれで選択肢を絞り照合している。本番の細分類入り商品 1283 件で、親子に合わない商品は 0 件（recon §3-3）。新しい表も列も要らない。
- 細分類 28 個のうち 15 個は、複数の中分類で使われている（ブースターパックは 16）（recon §3-1）。1 子 1 親の木にすると同じ細分類を最大 16 行に複製することになり、データが分散する。
- 旧列 `product_formats.type_master_id` は、商品の作品と 706/1283 件で食い違う。links とも 1 件食い違い、どこの絞り込みにも使われていない（recon §2-3、§10.1）。親子の置き場が 2 つあると、どちらが正か分からなくなる。
- 今はアプリの照合だけで、DB には保証が無い（recon §2-1）。SQL の直接書き込みや台本では、ずれを作れてしまう。
  - PG16 の複合 FK（MATCH SIMPLE）は、細分類が空の商品を検査しない（公式 sql-createtable）。
  - NOT VALID → VALIDATE で、表を長く止めずに足せる（公式 sql-altertable）。
  - 使い捨て PG16.15 で、この動きを確かめた（recon §10.3）。
- products は列番号の上限に達していて、列は足せない（recon §10.1）。FK は列を足さない。

## 対象外

- 中分類 9043・9044 に子が 0 件であること（マスタの値。PO に候補を見せて決める）。
- links の alias 列。
- 中分類ごとの子の一覧画面。

## 維持の仕組み

- 守り手: `backend/tests/test_product_format_game_links_pg.py`（FK と細分類削除の動きを CI で毎回確かめる）
- 守り手: `scripts/check-migration-column-churn.js`（旧列の ADD を戻さない）

## 結果

（実装後に記入）
