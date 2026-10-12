# recon: 試作版 v102 で、発送日の文字が拾われているのに捨てられている（便PO3）

基準 origin/main（2026-10-12、49acb712f）。本番は読み取りなし（置き換え試験はキャッシュ replay、queries 0）。社外秘：投稿の原文・仕入元の名前はこの文書に書かない。生出力（手元）: /tmp/CC報告ファイル/preorder-design/shipnote/（ship_values.csv・note_ja_grep.txt・test/）。
カード: docs/handoff/v102-ship-note/card-PO3.md／設計: docs/handoff/v102-ship-note/design.md

## 既存 ADR
- `git grep -il "note_ja" docs/adr/` で、v102 の note_ja の扱いを決める ADR は無し。旧系の注記は tcg_note_master（docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:26 のマスタ群の1つ）で、v102 はこれを使わない。

## 発送日の文字の作り方（origin/main）
- backend/app/services/gemini_raw_copy_v101.py:963 `"ship": _ship_for(item, roles, shared, lines, ctx)`。backend/app/services/gemini_raw_copy_v101.py:809-826 `_ship_for`：その件だけの行で発送の語を含む価格行・発送行から集め、無ければ共有行（見出しの直下の発送日の行）から。同じ文は1つ、複数は " / " でつなぐ。空は backend/app/services/gemini_raw_copy_v101.py:61 `_NONE = "none"`。型は常に str。
- 行ごとの切り出しは backend/app/services/gemini_raw_copy_v101.py:764 `_ship_text`（括弧の中身・価格の前後の発送の文字）。括弧が片側だけ残る値がある。

## 保存と表示
- backend/app/services/line_analysis_v102_svc.py:617-648 `_analysis_values` は note_ja を常に None（:645）。upsert は backend/app/services/line_analysis_v102_svc.py:669 `note_ja = EXCLUDED.note_ja`。本番の呼び出し元は backend/app/services/line_analysis_v102_svc.py:896（_write_results）の1か所。
- note_ja を読むところ（全走査 note_ja_grep.txt 81 行）：配信 backend/app/services/tcg_distribution_svc.py:265（COALESCE で素通し）・:55 列名 Note_JA・:313 出力。在庫一覧 GAS（repo 外 tcg-client-viewer、Code.js:18・index.html:487「備考」）は表示のみ。backend/app/services/tcg_analysis_review_svc.py:226,:283 と backend/app/services/tcg_import_progress.py:32,:133 は表示のみ。backend/app/services/tcg_condition_review_svc.py:124 はレビュー版のハッシュ材料（computed_at も入っており失効は増えない）。backend/app/services/inventory_aggregation.py は public.inventory を読み analysis_results を読まない。is_current・配信の絞り込み・needs_review は note_ja を使わない。
- 列は TEXT（migrations/20260921_110000_pipeline_tables_public.sql:302）。

## 観測（置き換え試験、2,693 件）
- ship が空でない件 233（In Stock 231・Pre-order 2）。最大 36 字・改行 0・" / " つなぎ 3件。値は 29 種、上位は 発送日要相談 55・発売日発送 29・発送日相談 20。
- 括弧が片側だけの値：閉じだけ残る 7件・開きだけ残る 1件。
