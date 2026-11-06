# 実装カード: 配信シートを15列（PO 指定の並び＋商品ID）にする

- 設計: [design.md](design.md)（Opus 自己審査 APPROVE 条件つき: [review-architect.md](review-architect.md)）。調査: [recon.md](recon.md)。決定: ADR-1066。
- PO の実装承認: 2026-11-06「2」（作ってよい。すぐ反映する）。
- ブランチ: `release/dist-columns-product-id`（このブランチに積む。新しいブランチは作らない）。危険パス（migrations・deploy.yml・本番 scripts）なし。
- 試験は Mac で流さない。CI で確かめる。行番号は origin/main c481f5e7d。

## やること（この順）

1. `backend/app/services/tcg_distribution_svc.py:48-64` の `DIST_HEADERS` の定義を、design §4-2 の1のコードそのままに置き換える（`_SHEET_LAYOUT`・`DIST_HEADERS`・`_SHEET_COLUMNS`）。
2. 同 `:252` の `_GAS_COLUMNS` の上の注釈を「閲覧ページの写しと試験が使う並び（14列）。配信シートの並びは `_SHEET_LAYOUT`（ADR-1066）」に直す。`_GAS_COLUMNS` の中身は変えない。
3. 同ファイルに関数 `_cell(row, column)` を足す: `column == "product_id"` のとき、値が None なら `""`、それ以外は `str(値)`。ほかの列は `row[column]` をそのまま返す。
4. 同 `:428` `fetch_output_rows` に、キーワード専用の引数 `columns: tuple[str, ...] = _GAS_COLUMNS` を足す（`*` の後ろ・既存の引数の後ろ）。`:450` を `return [[_cell(row, column) for column in columns] for row in rows]` にする。docstring の「14列（DIST_HEADERS）」を「既定は14列（_GAS_COLUMNS）。配信シートは columns=_SHEET_COLUMNS」に直す。
5. 同 `:933` `build_distribution_rows(db)` に、キーワード専用の引数 `columns: tuple[str, ...] = _GAS_COLUMNS` を足し、`:991` の `fetch_output_rows(...)` に `columns=columns` を渡す。
6. 同 `:1015`（`run_distribution` の中）を `build_distribution_rows(db, columns=_SHEET_COLUMNS)` にする。
7. 試験を直す:
   - `backend/tests/test_tcg_distribution.py:346-357`: `DIST_HEADERS` が次のリストと完全一致することを確かめる形に直す: `["投稿日時","Status","Mark","Japanese Title","English Title","Condition","Unit Price","Quantity","Ship_JA","Note_JA","提供者","Release Date","Series","Search Keywords","商品ID"]`。`_GAS_COLUMNS[12] == "search_keywords"` の行は残す。
   - 同 `:360-368`: そのまま（`_GAS_COLUMNS[-2:]` は変わらない）。テスト名・docstring に「閲覧ページ用の並び」と書き足すだけ。
   - `backend/tests/test_tcg_result_order.py:353-360`: `distribution.DIST_HEADERS` の確かめを上の15列の完全一致に直す。行（`row[...]`）の確かめは変えない。
8. 試験を足す（design §6・K5）:
   - `backend/tests/test_tcg_distribution.py` に: `_SHEET_COLUMNS` の各列名が、`inspect.getsource(svc._distribution_final_select)` の SELECT に出ていること。`len(_SHEET_LAYOUT) == 15`。`_cell({"product_id": 466088}, "product_id") == "466088"`・`_cell({"product_id": None}, "product_id") == ""`。
   - `backend/tests/test_distribution_rows_builder.py:134` の隣に: `run_distribution` が `build_distribution_rows` を `columns=svc._SHEET_COLUMNS` で呼ぶこと（`mock_build.await_args.kwargs["columns"]`）。
   - `backend/tests/test_tcg_result_order.py` の `_single_output_row` の近くに pg 試験: 同じデータで `fetch_output_rows(db)` と `fetch_output_rows(db, columns=distribution._SHEET_COLUMNS)` を取り、行数が同じ・15列・15列目が商品の id の文字・2列目が Status の値・共通の14列の値が列名ごとに全行一致。DB の取り方はそのファイルの既存の `fetch` の型に合わせる。
9. 提出前: `bash scripts/dev/check-before-submit.sh` を流し、生の結果をファイルに残してパスを報告する。
10. commit（1つでよい。末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）→ push。PR は作らない（Opus が作る）。

## 触らない

- SQL（`distribution_rows_parts`・`_distribution_final_select`・`distribution_rows_sql`）。
- `backend/app/tasks/viewer_inventory_cache.py`・閲覧ページ API・frontend。
- `backend/app/line_import_admin.py`・要確認タブの書き込み・`_write_tab_sync`・`_write_to_target_sync`。
- migrations・.github・scripts・docs（このカードに無いファイル全部）。要りそうなら止めて `NEEDS_DECISION:` で報告する。

## 想定される分かれ道

- 行番号がずれている → 関数名・変数名で場所を探す。中身が設計と違えば止めて報告する。
- `fetch_output_rows` を位置引数で呼んでいる所があり、新しい引数とぶつかる → 引数はキーワード専用なのでぶつからないはず。ぶつかれば止めて報告する。
- 既存の試験が、`build_distribution_rows` を `assert_awaited_once_with(db)` のように引数まで確かめていて赤になる → その試験の確かめを `columns=svc._SHEET_COLUMNS` 付きに直す（`run_distribution` 経由の物だけ）。閲覧ページの写し（引数なし）の試験は直さない。
- pg 試験の DB の作り方が分からない → 同じファイルの既存の pg 試験をまねる。作れなければ pg 試験を足さずに `NEEDS_DECISION:` で報告する。

## 終わりの報告

- 最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 問い`。HEAD の sha・変更ファイル一覧（`git diff --name-only origin/main...HEAD`）・各検査の終了コードを付ける。
