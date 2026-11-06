---
mode: handoff
---

# recon: 配信シートの列の並びを変え、商品IDを足す — 現在地

> この文書は何か（専門用語なしの1行）:
> お客さんのシートへ送る在庫の表の「列の並び」が、今どこで決まり、どこが並びに頼っているかを、実物で確かめた記録。

- 基準: `git fetch` 後の `origin/main`（c481f5e7d、2026-11-06）。worktree `release/dist-columns-product-id`。
- 設計: [design.md](./design.md)

## 0. 既存 ADR の検索

- `git grep -n "14列\|14 列" origin/main -- docs/adr docs/specs` の結果:
  - `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:26` 「`fetch_output_rows` / `fetch_preview_data` の引数・GAS 出力列（14列）は変えない。」
  - `docs/adr/ADR-1014-inventory-view-shows-distribution-rows.md:47` 「配信行の定義・GAS 出力14列・API 応答形は変えない。」
  - `docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:6` 閲覧ページの列は「今の本番の GAS と同じ14列」に offer_type を足す。
  - `docs/adr/ADR-1023-condition-value-rank.md:73` 「列・GAS 出力の14列は変えない。」
- 読み方【事実】: 3つの ADR は、それぞれの変更の範囲として「14列は変えない」と書いている。14列を恒久に固定する決定は書いていない。ただし今回は列の数と並びを変えるため、新しい ADR で決定を残す必要がある（design §8）。
- 関係する ADR: ADR-099（SA 在庫モデル・在庫のまとめ方）、ADR-1014（在庫の行の定義は1か所）、ADR-1019（閲覧ページ）。

## 1. 列の並びを決めている場所（1か所）

- `backend/app/services/tcg_distribution_svc.py:48-64` `DIST_HEADERS`（シート1行目の見出し・14列）
  - 今の並び: 投稿日時, Mark, Japanese Title, English Title, Condition, Unit Price, Quantity, Note_JA, Status, Release Date, Series, 提供者, Search Keywords, Ship_JA
- `backend/app/services/tcg_distribution_svc.py:252-256` `_GAS_COLUMNS`（行の値をどの列から取るか・14個。`DIST_HEADERS` と同じ並び）
- `backend/app/services/tcg_distribution_svc.py:450` `fetch_output_rows` が `[[row[column] for column in _GAS_COLUMNS] for row in rows]` で並べる。
- `backend/app/services/tcg_distribution_svc.py:695` `_write_to_target_sync` が `_write_tab_sync(..., DIST_HEADERS, rows)` でシートへ書く。
- `backend/app/services/tcg_distribution_svc.py:670-672` 書き方は「全部消して見出し＋行を書く」（`worksheet.clear()` → `append_rows(..., value_input_option="RAW")`）。毎回シート全体を書き直す。

## 2. 商品IDは今すでに SQL から出ている

- `backend/app/services/tcg_distribution_svc.py:343` `ar.product_id AS product_id`
- `backend/app/services/tcg_distribution_svc.py:295` 最終 SELECT が 14列のあとに `product_id` を出す（`posted_ts, row_key, product_id, supplier_id, ...`）。
- `backend/app/services/tcg_distribution_svc.py:369-370` 配信行は `ar.pid_resolved = TRUE` の行だけ。【事実】商品が決まった行だけが配信される。【推測】product_id が空の行は出ない（`pid_resolved` と `product_id` の対応は DB 制約ではまだ確かめていない＝【未確認】。design K2 で実物を数える）。
- 値の型: `ar.product_id` は整数。ほかの数の列（Unit Price・Quantity）は `::text` で文字にして出している（`:292-293`）。

## 3. 行の並び（_GAS_COLUMNS）を使っている場所

| 場所 | 使い方 | 並びに頼るか |
|---|---|---|
| `backend/app/tasks/viewer_inventory_cache.py:20,42` | `dict(zip(_GAS_COLUMNS, row))` で列名つきに直し、閲覧ページの写しを作る | 列名で読む。`_GAS_COLUMNS` と行が同じ並びである限り安全 |
| `backend/app/services/tcg_distribution_svc.py:933-1000` `build_distribution_rows` | 配信とビューアの写しの共通の入口。`fetch_output_rows` を呼ぶ | 並びを作る側 |
| `backend/app/line_import_admin.py:117` | `fetch_output_rows` の件数（`len(rows)`）だけ使う | 頼らない |
| `backend/app/services/inventory_aggregation.py:221` | 「提供者」等を列名の候補で読む（`_get_value(source, ("supplier_name","provider","supplier","提供者"))`） | 頼らない |
| `scripts/seed_inventory_from_output.py:131-137` | 見出しの名前で列を探す | 頼らない |

- 全件の grep 生出力: `/tmp/CC報告ファイル/noriyuki-dist/recon_consumers.txt`（43行）

## 4. 並びを直接確かめている試験

- `backend/tests/test_tcg_distribution.py:346-357` 14列・`DIST_HEADERS[12]=="Search Keywords"`・`DIST_HEADERS[-1]=="Ship_JA"`・`_GAS_COLUMNS[12]=="search_keywords"`
- `backend/tests/test_tcg_distribution.py:360-368` `_GAS_COLUMNS[-2:] == ("search_keywords","ship_ja")`
- `backend/tests/test_tcg_distribution.py:159-185` 書き込みの先頭行が `DIST_HEADERS`
- `backend/tests/test_tcg_result_order.py:337-362` `fetch_output_rows` の行が14列・位置で値を確かめる・`DIST_HEADERS[:12]`・`[12]`・`[13]`
- `backend/tests/test_viewer_inventory_cache.py:48-49,86,236,282` `_GAS_COLUMNS` で行を作る・キーが `_GAS_COLUMNS ∪ {offer_type}`
- `backend/tests/test_inventory_distribution_rows_pg.py:4,98,149` `fetch_output_rows` の出力が変更前の SQL と1文字も同じ（T1）
- そのほか `fetch_output_rows` を位置で読む試験: `test_tcg_condition_review.py`・`test_tcg_work_matching_integration.py`・`test_tcg_completion_safety.py`・`test_v102_human_decisions_pg.py`・`test_line_analysis_v102_pg.py`（いずれも `fetch_output_rows(db, ...)` を呼ぶ。行番号は §3 の grep 出力）

## 5. シートを読む GAS（在庫一覧の画面）

- 手元の写し5つすべてが、見出しの名前で列を探している（位置で読まない）:
  - `~/tcg-viewer-1hc-release/Code.js:70` `sheetHeader.indexOf(col)`（許可リスト13列）
  - `~/tcg-viewer-1tb-head/コード.js:71` 同（14列）
  - `~/tcg-client-viewer/src/Code.js:68`・`~/tcg-inventory-viewer-prod-1hc/Code.js:69`・`~/tcg-inventory-viewer-1tb/コード.js:69` 同
- 【事実】どの版も許可リストにある名前だけを取る。「商品ID」は許可リストに無いので、画面には出ない。
- 【未確認】本番に入っている版そのもの（clasp で今の版を取り寄せての確認）はしていない。手元の古い版から新しい版まで5つとも同じ読み方なので、本番の版も同じと見ている（推測）。実装後に画面で確かめる（design K4）。

## 6. 配信先（2026-11-06 の DB）

- 生出力: `/tmp/CC報告ファイル/noriyuki-dist/targets_before.tsv`
- 配信先は5つ: のりゆき（新）・武（新）・無料トライアルシート・山崎涼太郎・配信テスト。
- 山崎涼太郎のブック「価格表」: Drive の読み取りで「在庫集計」タブ A1:N1315 を確かめた。1行目は今の14列の並び。【未確認】ほかのタブや式がこのタブを列の位置（A列・F列など）で読んでいるか。読み取りの結果には「在庫集計」の表しか出てこなかった。
- のりゆきのブック: Drive の読み取りは「見つかりません」で読めない。中身は【未確認】。
- 無料トライアルシート・配信テスト: 中身は【未確認】。

## 7. 外部の決まりごと

- Google Sheets の書き込みは gspread の `append_rows(value_input_option="RAW")`。RAW は文字をそのまま入れる（数式・数字として解釈しない）。【未確認】Context7 での確認はまだ。今回は書き方を変えないので、設計の合否には関わらない。
