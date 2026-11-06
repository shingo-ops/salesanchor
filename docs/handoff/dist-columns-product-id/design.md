---
mode: handoff
---

# design: 配信シートの列の並びを変え、商品IDを足す

> この文書は何か（専門用語なしの1行）:
> お客さんのシートへ送る在庫の表を、PO が決めた15列の並びに変え、最後に商品IDを足すための設計。

- 現状の記録: [recon.md](./recon.md)（docs/handoff/dist-columns-product-id/recon.md）
- 関係 ADR: ADR-1014（在庫の行の定義は1か所）、ADR-1019（閲覧ページの列）、ADR-1023、ADR-099。ADR-1066 を起こした（§8）。
- 状態: **設計案作成済み・設計審査済み（自己審査 APPROVE 条件つき: [review-architect.md](./review-architect.md)）・PO 実装承認済み（2026-11-06「2」作ってよい。すぐ反映する）・実装カード: [card.md](./card.md)・決定: ADR-1066**

## 1. 目的（PO の言葉から）

- PO（2026-11-06・チャット）「マスタデータを送るのはなるべく最終手段にしたい、IDを在庫集計データに送ることは出来る？」
- PO（2026-11-06・チャット）「全配信データの構造を変更したい、並びは、投稿日時,Status,Mark,Japanese Title,English Title,Condition,Unit Price,Quantity,Ship_JA,Note_JA,提供者,Release Date,Series,Search Keywords,商品ID」
- 奥の目的: のりゆきさんの見積シートで、商品ごと・状態ごとに値段を自動で入れる（段階3の GAS）。そのとき、名前の揺れに左右されずに商品を突き合わせるため、商品の番号を在庫の表に載せる。商品の一覧表（マスタ）そのものはお客さんに渡さない。

## 2. 対象と対象外

- 対象: 全配信先の「在庫集計」タブの見出しと列の並び（14列→15列）。
- 対象外:
  - 配信する行の中身・件数・並び順（ADR-1014 のまま）。
  - 閲覧ページ（アプリ）の写しと API の項目（ADR-1019 の 14列＋offer_type のまま。商品IDは出さない）。
  - 在庫一覧の GAS（見出しの名前で読むので触らない。recon §5）。
  - 要確認タブの書き込み（`_write_tab_sync` を共有するが、見出しは別の定義）。
  - 段階3の見積 GAS（別の設計）。

## 3. 変更前と変更後

| 列 | 変更前（14列） | 変更後（15列・PO 指定） |
|---|---|---|
| A | 投稿日時 | 投稿日時 |
| B | Mark | Status |
| C | Japanese Title | Mark |
| D | English Title | Japanese Title |
| E | Condition | English Title |
| F | Unit Price | Condition |
| G | Quantity | Unit Price |
| H | Note_JA | Quantity |
| I | Status | Ship_JA |
| J | Release Date | Note_JA |
| K | Series | 提供者 |
| L | 提供者 | Release Date |
| M | Search Keywords | Series |
| N | Ship_JA | Search Keywords |
| O | （なし） | 商品ID |

- 商品IDの値: `public.products.id`（例: 466088）。文字として書く（Unit Price・Quantity と同じ扱い。RAW 書き込みで文字のまま入る）。

## 4. 作り方（選んだ案）

### 4-1. 案の比較

| 案 | 中身 | 良い点 | 悪い点 |
|---|---|---|---|
| A（採用） | シート用の並び（見出しと列名の組）を1つ定義し、配信のときだけその並びで行を作る。閲覧ページ用の並び（`_GAS_COLUMNS`）は今のまま | 閲覧ページ・API・既存の試験（位置で読む約20か所）が変わらない。並びの正本がシート用に1か所 | 並びの定義が「シート用」「閲覧ページ用」の2つになる |
| B | `_GAS_COLUMNS` 自体を新しい15列の並びにする | 定義が1つ | 閲覧ページの写しに商品IDが入る（ADR-1019 と食い違う）。位置で読む試験を約20か所直す。差分が大きく誤りやすい |
| C | 14列はそのまま、商品IDだけ末尾に足す | 変更が最小 | PO が指定した並びと違う |

### 4-2. 変更の中身（案A・ファイル:行は origin/main c481f5e7d）

1. `backend/app/services/tcg_distribution_svc.py:48-64` `DIST_HEADERS` を、見出しと列名の組の表から作る形に置き換える。

   変更前:
   ```python
   # 出力ヘッダー（確定・14列）
   DIST_HEADERS = [
       "投稿日時", "Mark", ... , "Ship_JA",
   ]
   ```
   変更後:
   ```python
   # 配信シートの列（見出し, 行の列名）。並びは PO 決定（2026-11-06）。正本はここ1か所。
   _SHEET_LAYOUT = (
       ("投稿日時", "posted_at"),
       ("Status", "status"),
       ("Mark", "mark"),
       ("Japanese Title", "japanese_title"),
       ("English Title", "english_title"),
       ("Condition", "condition"),
       ("Unit Price", "unit_price"),
       ("Quantity", "quantity"),
       ("Ship_JA", "ship_ja"),
       ("Note_JA", "note_ja"),
       ("提供者", "provider"),
       ("Release Date", "release_date"),
       ("Series", "series"),
       ("Search Keywords", "search_keywords"),
       ("商品ID", "product_id"),
   )
   DIST_HEADERS = [header for header, _ in _SHEET_LAYOUT]
   _SHEET_COLUMNS = tuple(column for _, column in _SHEET_LAYOUT)
   ```
2. `backend/app/services/tcg_distribution_svc.py:252-256` `_GAS_COLUMNS` は変えない。上の注釈だけ「閲覧ページの写しと試験が使う並び（14列）。配信シートの並びは `_SHEET_LAYOUT`」に直す。
3. `backend/app/services/tcg_distribution_svc.py:428-450` `fetch_output_rows` に、キーワード専用の引数 `columns: tuple[str, ...] = _GAS_COLUMNS` を足す。行を作る式を次に変える。

   変更前（`:450`）:
   ```python
   return [[row[column] for column in _GAS_COLUMNS] for row in rows]
   ```
   変更後:
   ```python
   return [[_cell(row, column) for column in columns] for row in rows]
   ```
   `_cell` は `product_id` のときだけ `""` か `str(値)` にし、ほかの列は `row[column]` をそのまま返す（今と同じ値）。
4. `backend/app/services/tcg_distribution_svc.py:933` `build_distribution_rows(db)` に同じ引数 `columns=_GAS_COLUMNS` を足し、`:991` の `fetch_output_rows(...)` へそのまま渡す。
5. `run_distribution`（`:1015`）だけ `build_distribution_rows(db, columns=_SHEET_COLUMNS)` で呼ぶ。閲覧ページの写し（`backend/app/tasks/viewer_inventory_cache.py:78`）は引数なしのまま（14列）。
6. `_write_to_target_sync`（`:695`）は変えない（`DIST_HEADERS` が新しい並びになるだけ）。
7. 試験を直す・足す（§6）。

### 4-3. 触らない範囲

- SQL（`distribution_rows_parts`・`_distribution_final_select`）。商品IDは今も SELECT に出ている（recon §2）。
- `backend/app/tasks/viewer_inventory_cache.py`・閲覧ページ API・フロント画面。
- `backend/app/line_import_admin.py`（件数しか使わない）。
- 在庫一覧の GAS（1hc・1Tb）。
- 要確認タブの書き込み・配信先の登録・DB の表。

## 5. 影響とリスク

| リスク | 起きること | 対処 |
|---|---|---|
| R1 お客さんのブックの式が列の位置（F列＝値段など）で読んでいる | 反映の直後から、そのお客さんの式が別の列を読み、値段の表がずれる | 実装の前に PO が5つの配信先の持ち主に「在庫集計タブを位置で読む式があるか」を確かめる（§9 の確認1）。山崎涼太郎さんの「価格表」は在庫集計タブ以外が読めず未確認（recon §6） |
| R2 在庫一覧の GAS が位置で読んでいる | 在庫一覧の画面の列がずれる | 手元の5版はすべて見出しの名前で読む（recon §5）。反映後に K4 で画面を確かめる |
| R3 閲覧ページに商品IDが漏れる | ADR-1019 と食い違う | 案A で写しの並びを分ける。K3 の試験で写しのキーが変わらないことを確かめる |
| R4 商品IDが空の行 | 見積 GAS が突き合わせできない行が出る | `pid_resolved = TRUE` の行だけ配信（recon §2）。K2 で空の数を数える（0件が合格） |
| R5 配信の行数・中身が変わる | 在庫の数がお客さんごとに変わる | 行の作り方は変えない。K5 で変更前後の行数を比べる |

- 戻し方: 実装 PR を戻す（git revert）PR をマージして反映する。次の配信でシートは14列の並びに書き直される（毎回全部消して書くため。recon §1）。DB の変更は無いので、戻しにデータの作業は要らない。

## 6. 試験

- 直す:
  - `backend/tests/test_tcg_distribution.py:346-357`・`:360-368`: `DIST_HEADERS` は15列・PO の並びと完全一致・末尾は「商品ID」。`_GAS_COLUMNS` は今のまま14列（閲覧ページ用）であることを確かめる形に直す。
  - `backend/tests/test_tcg_result_order.py:353-362`: `DIST_HEADERS` の並びの確かめを新しい15列に直す。行（`fetch_output_rows` の既定＝14列）の確かめは変えない。
- 足す:
  - `fetch_output_rows(db, columns=_SHEET_COLUMNS)` の行が15列で、15列目が商品の id の文字、2列目が Status の値（pg 試験。`backend/tests/test_tcg_result_order.py` の `_single_output_row` を使う）。
  - `run_distribution` が `build_distribution_rows` を `columns=_SHEET_COLUMNS` で呼ぶ（mock。`backend/tests/test_distribution_rows_builder.py:134` の型）。
  - `viewer_inventory_cache` が `build_distribution_rows` を引数なしで呼び、写しのキーが `_GAS_COLUMNS ∪ {offer_type}` のまま（既存の `backend/tests/test_viewer_inventory_cache.py:86` が守る。変えない）。
  - `_SHEET_COLUMNS` の各列名が `_distribution_final_select` の出す列に含まれる（列名の打ち間違いを止める）。

## 7. 受入条件

| 基準 | 検証方法 |
|---|---|
| K1 配信シートの1行目が PO 指定の15列と完全一致（○×） | 反映後の最初の配信のあと、山崎涼太郎さんの「価格表」の在庫集計タブ1行目を Drive の読み取りで見る（Opus）。配信テストのシートも同じ |
| K2 全行の「商品ID」が空でない（空 0件で○） | K1 と同じ読み取りで O 列を数える。あわせて reader 鍵で配信先の `last_distributed_count` と行数が一致 |
| K3 閲覧ページの写しの項目が変わらない（○×） | CI の `backend/tests/test_viewer_inventory_cache.py` が緑。反映後に閲覧ページの列の数が今と同じ（PO 目視・画面1枚） |
| K4 在庫一覧（GAS）の画面の列と値が今と同じ（○×） | 反映後に在庫一覧を開き、ハドウシーカー（BOX）の1行で Status・値段・数・発送が正しい列に出る（PO 目視） |
| K5 並びを変えても行の数と値が変わらない（差 0件で○） | pg 試験: 同じデータで `fetch_output_rows(db)`（14列）と `fetch_output_rows(db, columns=_SHEET_COLUMNS)` を取り、行数が同じで、共通の14列の値が列名ごとに全行一致。本番の件数は解析のたびに動くので比べない |
| K6 商品IDが正しい商品を指す（3件中3件で○） | K1 の読み取りから3行を選び、reader 鍵で `public.products` の名前と Japanese Title が一致 |
| K7 CI が緑 | PR の確かめがすべて緑 |

## 8. ADR

- 新しい ADR「配信シートの列は15列・商品IDを含む」を起こす（実装 PR に入れる）。中身:
  - 決定: 配信シートの見出しと並びは `_SHEET_LAYOUT` が正本。15列目に商品の id を載せる。商品の一覧表そのものは送らない。
  - Why: お客さん側の GAS が名前の揺れに左右されずに商品を突き合わせるため。マスタを渡すと、商品の情報がまとめてお客さんの手に渡るため（PO「最終手段」）。
  - 閲覧ページの列（ADR-1019）は変えない。ADR-1014・1023 の「14列は変えない」は当時の変更の範囲の話で、この ADR で配信シートは15列に改める、と書く。
- `node scripts/generate-adr-index.js` で索引を作り直す。

## 9. PO に確かめること

- 確認1（実装の前）: 5つの配信先（のりゆき・武・無料トライアルシート・山崎涼太郎・配信テスト）に、在庫集計タブを列の位置で読む式や仕組みがあるか。特に山崎涼太郎さんの「価格表」。あれば、反映の日を持ち主に伝えてから出す。
- 確認2: 実装の承認（この設計で作ってよいか）。

## 10. 維持の仕組み

- 並びの正本は `_SHEET_LAYOUT` の1か所。見出しと列名を組で持つので、片方だけ直すずれが起きない。
- 試験が「PO 指定の15列と完全一致」を確かめる。並びを変えると CI が赤になる。変えるときは ADR を直してから試験を直す。
- 閲覧ページの写しは `_GAS_COLUMNS`（14列）で別に守る。商品IDが閲覧ページに出ないことは既存の試験が守る。
- 守り手: Opus（設計統括）。試験 backend/tests/test_tcg_distribution.py が並びを守る。列の並びを変えてよいのは PO の決定だけ。

## 11. 外部・過去事例の参照と我々への応用

- 直接の外部事例は使わない。理由: 自社の配信シートの列の並びを変える作業で、成否は自社の読み手（GAS・お客さんの式）が列の位置に頼るかどうかだけで決まる。それは recon §5・§6 の実物の確認と §9 の確認1で判定する。
- 一般的な知見として、列を名前で読む読み手は並び替えに強く、位置で読む読み手は壊れる。だから在庫一覧の GAS は名前で読む作りになっている（recon §5）。
