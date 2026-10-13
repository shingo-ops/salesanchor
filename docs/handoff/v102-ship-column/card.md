# card: 発送日の専用列（v102）実装カード

設計: docs/handoff/v102-ship-column/design.md（§3・§3b、§3c で §2 の `_merge_supplier_products` の変更と K3・K7 のテストは取り下げ）／recon: docs/handoff/v102-ship-column/recon.md。基準 origin/main 8a421f22c。KGI K1〜K8 は PO 承認済み（2026-10-12）。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-v102-ship-column（ブランチ release/v102-ship-column）。本体フォルダ /Users/tanizawashingo/salesanchor は変えない。

## 1. migration（新規2本・値の操作なし・ADR-1007）
- migrations/20261013_130000_add_analysis_results_ship_ja_ship_en.sql
  - `ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS ship_ja TEXT;`
  - `ALTER TABLE public.analysis_results ADD COLUMN IF NOT EXISTS ship_en TEXT;`
  - COMMENT 2つ（ship_ja：発送日（v102）。備考マスタの分類「発送時期系」でそろえた形、当たらない部分は拾った文字。違えば同じ投稿の中で別の件として配信／ship_en：ship_ja の英語。全部の部分がマスタに当たったときだけ入る。配信シートには出さない）。
- migrations/20261013_130100_add_tcg_note_master_label_template_en.sql
  - `ALTER TABLE public.tcg_note_master ADD COLUMN IF NOT EXISTS label_template_en TEXT;` ＋ COMMENT（REGEX の行の英語の書式。$1 などの捕捉を展開。空なら label_en）。
- scripts/run_all_migrations.sh の末尾（今の :912 の次）に2行 `run_sql migrations/<file>` を同じ順で追記。
- 書き方は migrations/20261011_150000_add_analysis_results_price_basis.sql に合わせる（冒頭コメント「構造のみ。値の操作は含めない（ADR-1007）。冪等。」）。

## 2. backend/app/services/tcg_analyzer_svc.py
- `_note_matches(raw_memo: str, note_entries: list[dict], *, raw_state: str = "") -> list[tuple[dict, re.Match[str] | None]]` を新設し、`build_note_ja`（:1057-1093）の当たり判定（LITERAL/STATE_LITERAL の match_keyword、REGEX の除外 match_one_kw → re.search、re.error の警告ログ）をそのまま移す。`build_note_ja` は `_note_matches` の結果から今と同じ文字列を返す（LITERAL→label_ja、REGEX→`_expand_note_label(label_template or label_ja, m)`、","でつなぐ、無ければ None。空入力・空マスタの早期 return も今のまま）。v6 の出力は1文字も変えない。
- 定数 `SHIP_NOTE_CATEGORY = "発送時期系"`（備考マスタの category 値を指す）。
- `load_ship_master(session) -> list[dict]`：`SELECT id, label_ja, label_en, search_keywords, exclude_keywords, priority, match_type, search_pattern, label_template, label_template_en FROM public.tcg_note_master WHERE enabled = TRUE AND category = :category ORDER BY priority ASC, id ASC`。辞書の形は load_note_master と同じキー＋ `label_en`・`label_template_en`。例外は握りつぶさない。0 行なら `logger.warning`。
- `build_ship_labels(ship: str | None, ship_entries: list[dict]) -> tuple[str | None, str | None]`：design §3b-4 のとおり。入力は ship_note 済みの文字列（None はそのまま (None, None)）。" / " で分け、部分ごとに `_note_matches(part, ship_entries)`。
  - 当たった部分：ja＝各当たりの ja（LITERAL→label_ja、REGEX→`_expand_note_label(label_template or label_ja, m)`）を "," でつなぐ。en＝各当たりの en（LITERAL→label_en、REGEX→label_template_en があれば `_expand_note_label(label_template_en, m)`、無ければ label_en）を ", " でつなぐ。
  - 当たらない部分：ja＝部分の文字のまま、en＝なし。
  - ship_ja＝部分の ja を " / " でつなぐ（同じ値は最初の1つだけ）。ship_en＝全部の部分に en があるときだけ " / " でつなぐ（同じ値は1つ）、1つでも無ければ None。
- `_merge_supplier_products`（:1744-1879）
  - candidates の本物の行に `ar.ship_ja, ei.gemini_index, ei.line_start` を足す。仮の行（:1833-1845）は親の `ar.ship_ja` と、親の extraction_items の `gemini_index, line_start`（親の行と同じ鍵）を足す。
  - ranked を次にする：
    ```
    SELECT c.id,
           (RANK() OVER (PARTITION BY c.product_id, c.condition_id
                         ORDER BY c.received_at DESC, c.computed_at DESC) = 1
            AND ROW_NUMBER() OVER (PARTITION BY c.product_id, c.condition_id, COALESCE(c.ship_ja, '')
                         ORDER BY c.received_at DESC, c.computed_at DESC, (c.id IS NULL),
                                  c.gemini_index NULLS LAST, c.line_start NULLS LAST, c.id) = 1
           ) AS should_be_current
    FROM candidates c
    ```
  - touched_triples・extra_pairs の型・UPDATE 文・呼び出し元3つは変えない。関数の docstring に新しい規則を1〜2行で足す。

## 3. backend/app/services/line_analysis_v102_svc.py
- `load_v102_masters` が返す masters に `"ship_entries": analyzer.load_ship_master(session)` を足す。
- `_analysis_values`（:648 付近）：`ship_ja, ship_en = analyzer.build_ship_labels(ship_note(item.get("ship")), masters["ship_entries"])`。`"note_ja": None`、`"ship_ja": ship_ja`、`"ship_en": ship_en`。masters の受け取り方は今の関数の引数の形に合わせる（引数が無ければ呼び出し元 `_write_results` から渡す。他の呼び出し元があれば全部直す）。
- `_UPSERT_SQL`（:681-703）：ship_ja・ship_en を INSERT 列・VALUES・`DO UPDATE SET ship_ja = EXCLUDED.ship_ja, ship_en = EXCLUDED.ship_en` の3か所に足す。
- `ship_note` は変えない。

## 4. backend/app/services/tcg_distribution_svc.py
- `DIST_HEADERS` の末尾に `"Ship_JA"`（14列目）。SELECT に `COALESCE(ar.ship_ja, '') AS ship_ja`、返却リストの末尾に ship_ja。他の列・順・WHERE・書き込み（:493-550）は変えない。ship_en は出さない。

## 5. 備考マスタの管理（label_template_en を足す）
- backend/app/routers/super_admin_note_master.py：`_NOTE_COLS`（:101-105）、`_NOTE_UPDATABLE`（:107-118）、POST の INSERT 列、CSV export のヘッダーと値（:261 付近）、CSV import の UPDATE/INSERT（:349-367 付近）。
- backend/app/routers/note_master.py：同じ箇所（列一覧 :110・:117、INSERT :167-169、export :267-282、import :370-387）。
- backend/app/schemas/central_masters.py:612-656（TcgNoteMaster の Base/Update/Response）に `label_template_en: str | None = None`（Update は Optional）。
- frontend/api-contract/openapi.json を既存の再生成手順で作り直す（.github/workflows/api-contract-check.yml:35,50-53 が検査する手順をそのまま使う）。
- frontend/src/pages/super-admin/components/NoteMasterPanel.tsx と frontend/src/pages/note-master/NoteMasterPage.tsx：型・初期値・編集値・payload に label_template_en。入力欄は既存の label_template の `TextField` ブロック（Panel :325-329、Page :337-341）を複製して label を `t(\`${f}.labelTemplateEn\`)`。生 input・色直値・自作部品は使わない（ADR-144）。一覧の列は増やさない。
- frontend/src/locales の ja.json と en.json に同じキー `labelTemplateEn` を、既存 labelTemplate キーの隣に両方追加（ja「英語の書式（REGEX）」、en「English template (REGEX)」）。
- 既存の checkbox（Panel :296、Page :308）は触らない。

## 6. テスト
新規・変更（名前はこのとおり）:
- backend/tests/test_tcg_keyword_matching.py
  - `test_build_note_ja_output_unchanged_after_note_matches_split`（既存の build_note_ja テストが全部そのまま通ることに加え、LITERAL/REGEX/除外/re.error の4例で切り出し前と同じ値）
  - `test_build_ship_labels_literal_regex_and_unmatched_parts`（「【10/16発送】」→ ("10/16発送", label_template_en の展開)、「届き次第発送」→ ("入荷次第発送", "Ships upon arrival")、「発送日相談 / 移し替えて発送予定」→ ja は "発送日要相談 / 移し替えて発送予定"・en は None、None → (None, None)。マスタ行はテスト内で作る）
  - `test_ship_note_category_constant_matches_seed_migrations`（SHIP_NOTE_CATEGORY が migrations/20260907_100000_tcg_note_master_expand_t004.sql と 20260909_130000_tcg_note_b2_t004.sql に category 値として現れる）
- backend/tests/test_line_analysis_v102_svc.py：`test_analysis_values_puts_ship_text_in_note_ja_and_none_stays_empty`（:764）を `test_analysis_values_puts_ship_in_ship_ja_and_ship_en_and_leaves_note_ja_empty` に置き換え。:231 の note_ja 検査は None のまま通ること。
- PG（_merge_supplier_products。置き場所は backend/tests/test_v102_soldout_extra_targets_pg.py か新規 backend/tests/test_v102_ship_column_pg.py）
  - `test_k2_same_post_different_ship_are_all_current`
  - `test_k3_same_post_same_ship_keeps_one_current`
  - `test_k4_newer_post_demotes_older_post_even_with_different_ship`
  - `test_k7_same_rank_picks_lowest_gemini_index_every_time`（2回流して同じ行）
  - 既存の is_current のテスト（test_v102_soldout_extra_targets_pg.py・test_v102_human_decisions_pg.py:207・test_v102_transcription_pg.py:356・test_tcg_work_matching_integration.py:506,795・test_tcg_completion_safety.py:144）は無変更で通ること。
- 配信の列数：backend/tests/test_tcg_distribution.py:350（13→14）、:351（`DIST_HEADERS[-1] == "Ship_JA"`、`DIST_HEADERS[12] == "Search Keywords"`）、backend/tests/test_tcg_result_order.py:104・:328（13→14）、:344-348（先頭13列は従来どおり）。新規 `test_fetch_output_rows_has_ship_ja_as_14th_column`。
- テスト用 schema に新しい列を入れる：
  - backend/tests/test_tcg_work_matching_integration.py の `migrate()`（:315-317 付近、tenant_004 側 :717-719 付近）で新 migration 2本を流す（または同じ ALTER を足す）。
  - backend/tests/test_line_analysis_v102_pg.py:41-47 の v102 fixture で新 migration を流す。:68 で差し替える masters に `"ship_entries": []` を足す（当たりを試すテストでは行を入れる）。
  - backend/tests/test_tcg_condition_review.py:45 の fixture（:91 で is_current を足している所）に ship_ja・ship_en を足す。
  - 新しい並びは `extraction_items.gemini_index` を読む。この列は migrations/20261009_180000_v102_engine_columns.sql だけが足すため、共有 fixture `test_tcg_work_matching_integration.py` の `migrate()`（:315-332、tenant_004 側 :717-731）と `test_tcg_condition_review.py:45` の fixture（:67-91）に、その migration の extraction_items 部分（gemini_index）を流すか同じ ALTER を足す。
  - test_tcg_sold_out_results.py・test_tcg_import_progress_pg.py・test_line_import_devices_pg.py は merge・配信・解析を呼ばない（設計審査で grep 0 件）ため追加不要。test_tcg_completion_safety.py は共有 fixture を使うので共有側の追加で足りる。
  - analysis_results または tcg_note_master を自前で作る他の fixture を全部探し（`git grep -n "analysis_results" backend/tests` と `tcg_note_master`）、merge・配信・load_ship_master を通るものに同じ追加をする。少なくとも test_tcg_sold_out_results.py:107・test_tcg_import_progress_pg.py:46・test_line_import_devices_pg.py:26 を確認し、追加したか不要かを理由つきで報告。
- フロント：既存の NoteMaster のテストがあれば label_template_en を足して通す。`npm run lint`・型検査・i18n キー一致の検査を通す。

## 7. 触らない
- v6 の判定と備考（build_note_ja の出力）、`ship_note`、`_ship_for`、analysis_run_snapshots の複写（tcg_product_master_svc.py:668-725）、tcg_analysis_review_svc.py:229,291・tcg_import_progress.py:32,133 の note_ja 表示、GAS（repo 外）、備考マスタのデータ（行の追加・変更はしない）。

## 8. 完了の確認（担当が実行して生出力を残す）
- `./scripts/dev/executor-preflight.sh`
- backend：上のテストファイル全部と backend 全体の pytest（PG テストを含む、リポジトリの標準の走らせ方）。
- frontend：lint・型検査・テスト・i18n 検査・openapi の差分検査。
- `git diff origin/main --stat` が §1〜§6 のファイルと docs/handoff/v102-ship-column/ だけ。
