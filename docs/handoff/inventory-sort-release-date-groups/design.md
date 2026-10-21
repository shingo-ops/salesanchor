# 設計: 在庫表の既定の並び順を「発売日の早い順・商品ごとのまとまり」にする

- recon: docs/handoff/inventory-sort-release-date-groups/recon.md
- 対象ADR: docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md（:37 を改訂）、ADR-1019（閲覧ページ）、ADR-027（i18n）、ADR-067・ADR-144（金型・トークン）

## PO の言葉
- 「デフォルトの並び順は発売日の新しい順にするようにしてくれ」（2026-10-17）
- 「デフォルトの表示は発売日の早い順に並べてくれ、並び替えのプルダウンについては商品ID内で並び替えをする、これはgasのアプリと同じ仕組みだが理解できる？」（2026-10-18）
- Opus「今の GAS はまとまりが英語名・まとまり同士は英語名のアルファベット順。商品のまとまりを発売日の早い順（古い日付が上）に並べ、プルダウンの並び替えはまとまりの中だけで効く形にしてよいか」→ PO「y」（2026-10-18）

## 目的（利用者に見える変化）
在庫表（/inventory）と閲覧ページを開いたとき、商品のまとまりが発売日の古い順に上から並ぶ。プルダウンで「価格が安い順」などを選ぶと、まとまりの順はそのままで、各商品の中の行だけが並び替わる。

## 変更前 → 変更後
### まとまりの順（全ての並び替えで共通。ただし下の例外2つを除く）
- 変更前: `english_title ASC`（英語名のアルファベット順。英語名が空の商品が先頭側に固まる）
- 変更後: `発売日 ASC（空欄は末尾）→ english_title ASC → japanese_title ASC → product_id ASC（在庫表のみ）`
  - 発売日は商品マスタの値（tcg_distribution_svc.py:330）なので、同じ商品の行は必ず同じまとまりに入る
  - english_title・japanese_title・product_id は「同じ発売日の商品どうしを混ぜない」ための区切り。閲覧ページは product_id を持たない（types.ts:11-27）ので題名2つまで
### まとまりの中の順
- 既定（sort=release_date）: sort_ord（result_order_sql の順＝状態ランク等。変更前と同じ）
- プルダウン・見出しで選んだ列: `{選んだ列} {向き} NULLS LAST → sort_ord`
### 例外
1. 見出し「発売日」をクリックして降順にしたとき: まとまりの順が発売日の新しい順になる（空欄は末尾のまま）。昇順に戻せば既定と同じ
2. 見出し「タイトル」（sort=name）: 変更前のまま（英語名→日本語名を同じ向きで。ADR-1014:37 の後半を維持）
### 既定値
- 在庫表: InventoryPage.tsx:111-112 と :331-332 の sortDir を "desc" → "asc"（API の order 既定は既に "asc"、inventory_offers.py:339）
- 閲覧ページ: viewerFilter.ts:13 DEFAULT_SORT_DIR を "desc" → "asc"
### プルダウンに既定の選択肢を足す
- 先頭に `release_date:asc`「発売日が早い順」を追加（在庫表 InventoryPage.tsx:53-54、閲覧ページ viewerFilter.ts:14-15）。既定のときプルダウンが空表示になる現状（InventoryPage.tsx:445）を解消し、他の並びを選んだ後に既定へ戻せるようにする
- 文言は ja.json / en.json に同じキーで追加（ADR-027）。en は "Release date (oldest first)"

## 実装指示（Generator 向け）
1. backend/app/routers/inventory_offers.py:271-277 の ORDER BY を次に置き換える（sort_col・order_dir は既存のホワイトリスト由来の断片のみ。利用者入力を連結しない）
   - `group = "NULLIF(d.release_date, '') {ASC|DESC} NULLS LAST, d.english_title ASC, d.japanese_title ASC NULLS LAST, d.product_id ASC"`
     - 発売日の向きは sort が release_date のときだけ order_dir、それ以外は常に ASC
   - name: 変更前の式のまま
   - release_date: `ORDER BY {group}, d.sort_ord ASC`
   - それ以外: `ORDER BY {group}, {sort_col} {order_dir} NULLS LAST, d.sort_ord ASC`
   - d に product_id が無い場合は、配信行の定義（tcg_distribution_svc）を変えずに済む参照方法を探し、無ければ product_id を外して題名2つで止め、BLOCKED ではなく報告に明記する。配信行の列（GAS 14列）は変えない
2. frontend/src/pages/viewer/viewerFilter.ts sortRows を同じ規則にする（product_id なし。空の発売日は末尾、題名比較は既存の Collator を使う）。DEFAULT_SORT_DIR を "asc"
3. InventoryPage.tsx の既定・リセットの sortDir を "asc"。プルダウン先頭に release_date:asc を追加（在庫表と閲覧ページの両方。選択肢の定義が共有されているならその1か所）
4. ja.json / en.json に文言キーを追加
5. ADR-1014 に「改訂 2026-10-18」節を追記（本設計の決定要旨。:37 の行は書き換えず、改訂で上書きする旨を書く）し、`node scripts/generate-adr-index.js` を実行して docs/adr/README.md を更新
6. 試験
   - backend: ORDER BY の組み立て（release_date asc/desc・price・name の4通り）の文字列を固定する単体試験。既存の並び試験があれば期待値を更新
   - frontend: viewerFilter の sortRows（発売日違いの2商品＋発売日空の1商品＋同じ商品内の価格違い2行で、既定・価格順・発売日降順の3通りの並びを固定）。InventoryPage の既定 sortDir とプルダウン先頭

## 触らない範囲
- 配信行の定義と GAS 出力14列（tcg_distribution_svc.distribution_rows_sql）、result_order_sql、絞り込み、まとめ（merge_same_post）、列の見た目、API の応答形、DB・migrations、GAS 在庫一覧（別途 PO 確認）

## 代替案
- A. 英語名を第1キーのまま、英語名の空を埋める（データ整備）: 867 件の整備が要り、PO の「発売日順」を満たさないので不採用
- B. まとまりのキーを product_id だけにする: 閲覧ページに product_id が無く（types.ts:11-27）、配信行の列を変えることになるため不採用。題名2つ＋（在庫表のみ）product_id で代替

## リスクと対処
- 同じ発売日・同じ題名の別商品は、閲覧ページでは同じまとまりに見える（在庫表は product_id で分かれる）。発生頻度は未測定。実害が出たら配信行に product_id を足す別便
- 発売日の比較は文字列（YYYY-MM-DD 形式なら日付順と一致）。形式外の値があれば順が崩れる → 実装時に本番の発売日の形式を ADR-1024 読み取りで確認し報告

## 受入条件
| 基準 | 検証方法 |
|---|---|
| 既定で、まとまりが発売日の古い順・空欄は末尾 | backend 単体試験（ORDER BY 文字列）・viewerFilter 試験 pass。本番 API を既定で叩き先頭50行の release_date が非減少・空欄が後ろ（ADR-1024 読み取りではなく画面の API 応答で確認） |
| プルダウンで価格順を選ぶと、まとまりの順は変わらず商品内だけ価格順 | viewerFilter 試験・backend 単体試験 pass |
| 見出し「発売日」降順で新しい順、「タイトル」は変更前のまま | 同上 |
| プルダウン先頭に「発売日が早い順」が出て既定で選ばれている | InventoryPage 試験 pass、PO 目視 |
| i18n・型・lint・トークン | i18n 検査・tsc（既存4件）・eslint・ruff/pytest・check-ui-governance pass |
| ADR 索引 | CI「ADR index is up to date」pass |
| 本番反映 | デプロイ success、配信物に新文言キー、PO 目視 |

## 外部・過去事例の参照と我々への応用
- 過去事例（社内）: GAS 在庫一覧 ~/tcg-viewer-1hc-release/index.html:1386-1420 の「まとめてから中で並べる」二段の並べ方。まとまりの中で選択列を比べる部分はそのまま踏襲し、まとまり同士の順だけを英語名から発売日に替える
- 過去事例（社内）: ADR-1014:37（2026-10-14）で英語名を第1キーにした結果、英語名が空の商品（867/1398）が先頭に固まり、PO が「Golden Box がアビスアイの下」と報告した。まとまりのキーを空になり得る任意項目にしない教訓として、発売日（空は末尾に固定）→題名の順にする
- 外部事例: 該当事例は使わない。理由: 並び順は社内の GAS と PO の運用が正本で、外部の数値根拠で決める性質のものではないため

## 維持の仕組み
- 守り手: backend の ORDER BY 単体試験と viewerFilter の sortRows 試験（CI で毎回実行）。並びの規則は ADR-1014 改訂 2026-10-18 が正本
