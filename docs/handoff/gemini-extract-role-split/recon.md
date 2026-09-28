# Recon: gemini-extract-role-split

- 起点SHA: origin/main = ae783c7f583e2d5628c19d999ed7ce6c7944e9b8（`git -C /Users/tanizawashingo/salesanchor rev-parse origin/main` 実測）
- 作業方式: worktree作成が上限（100個）超過で失敗したため、read-onlyでorigin/mainをscratchpadに展開して閲覧（`git archive origin/main | tar -x`）。ローカル main working tree（650005f29、origin/mainより267コミット遅れ）は未着手・未変更。
- executor-preflight.sh: 未実行（worktreeが存在しないため。executorではなくrecon専用のためskip）。

## A. ADR search

【事実】`git grep -il -E 'gemini|extraction|supplier_prompt|analysis_results|search_keyword' -- docs/adr/`（origin/main, `git -C /Users/tanizawashingo/salesanchor` 実行）でヒットしたADR:
- `docs/adr/ADR-085-supplier-prompts.md` — 仕入先別Geminiプロンプト管理レイヤ（MVP）。**実際の解析への配線は本ADRで未実施**（後述）
- `docs/adr/ADR-093-inventory-table-product-master-redesign.md` — 在庫表/オファー/商品マスタ再設計。Phase 3b で区分・発送日のルールベース自動判定を追加
- `docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md` — 取り込み・解析パイプライン設計（ADR-SA-06）
- `docs/adr/ADR-1001-deprecate-tcg-products-unify-to-public.md` — tenant_004.tcg_products 廃止・public.products 統合
- `docs/adr/ADR-1002-unify-product-id-and-fix-migration-compat.md` — 商品ID INTEGER統一
- `docs/adr/ADR-110-sa-translation-subsystem.md` — 会話ログ翻訳（本タスクと直接関係薄い）
- `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`
- `docs/adr/ADR-155-product-master-ssot-csv-app.md`
- `docs/adr/ADR-158-product-level-supersession.md` — **Status: Proposed（ドキュメント表記）だが実装済み**（migration 20260924_120000, PR #3747, is_current 列。テストコメント多数で裏付け）
- `docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md`

指名された他ADR（キーワードgrepではヒットしないが直接読んで確認、file:1行目でタイトル確認）:
- `docs/adr/ADR-027-ui-internationalization.md` — UI i18n強制
- `docs/adr/ADR-067-design-token-enforcement.md` — デザイントークン強制
- `docs/adr/ADR-113-two-mode-dev-flow.md` — 2モード開発フロー
- `docs/adr/ADR-135-release-stowaway-prevention.md` — リリース相乗り防止
- `docs/adr/ADR-136-cc-bot-github-identity.md` **と** `docs/adr/ADR-136-company-stats-ssot.md` — **番号重複**（ADR-136が2ファイル存在。CLAUDE.mdが指す「ADR-136」がどちらか要確認 → 未確認）
- `docs/adr/ADR-144-ui-component-governance.md` — UI共通部品ガバナンス

【事実】`docs/handoff/use-gemini-product-code/design.md` は origin/main に存在しない（`git ls-tree` で不検出。パス誤りまたは削除済み → 未確認、team-leadの元指示にあったファイル名を確認要）。

### ADR-085 詳細（仕入先別プロンプト、原文引用）
- Status: `Accepted（MVP=管理レイヤのみ。パーサ統合は Proposed）`
- 実装範囲: `public.supplier_prompts`（supplier_id UNIQUE, migration `087_create_supplier_prompts.sql`）+ CRUD API + UI
- **原文引用（重要）**: 「取り込んだプロンプトを**実際の Gemini 解析に使う配線は本 PR では行わない**」「これは別 ADR / 別 PR で、ひとしさんの方針確認のうえ実装する」
- 非破壊方針: `knowledge_rules` / `supplier_aliases` は削除しない

### ADR-158 詳細（Product-Level Supersession、原文引用）
- Status表記は `Proposed`（2026-09-24, PO+Opus決定）だが、`analysis_results.is_current` は既に migration 済み・複数テスト（`test_tcg_condition_review.py:77-78`, `test_tcg_distribution_pg.py:88-90`, `test_tcg_work_matching_integration.py:293-294,689-690`, `test_tcg_result_order.py:134-136`）で「PR #3747」として言及・実装確認できる。**ドキュメントのStatus表記と実装状態に乖離あり（要指摘）**
- Decision: `analysis_results` に `is_current BOOLEAN NOT NULL DEFAULT TRUE`。配信クエリは `ar.is_current=TRUE` で判定（`sm.is_active` から変更）
- 影響範囲表に明記: `tcg_analyzer_svc.py`(`_merge_supplier_products()`), `tcg_distribution_svc.py`(配信クエリ3箇所), `tcg_condition_review_svc.py`


補足: `docs/handoff/use-gemini-product-code/design.md`（origin/main に存在。先の `git ls-tree` 検索コマンドの誤りで見落とし、直接パス指定で再確認）は、v5プロンプトの `resolved_product_code` を pid_basis='GEMINI' として採用する小粒度の改善（`tcg_analyzer_svc.py:1331` 付近）。ADR-1001の延長。実装済み（CIテスト2件で守られている）。ADR-158の商品コード関連部分を置き換える対象として team-lead指示にあったが、範囲は狭い（pid_basis文字列の決定ロジックのみ）。

## B. Gemini抽出パス

【事実】呼び出しフロー: `backend/app/tasks/tcg_extraction.py:_run_extraction()` → `gemini_extraction_svc.extract_message()` → `call_gemini_extraction()` → Gemini API → `parse_extraction_response()`。

- `_run_extraction`（`tcg_extraction.py:223`〜）はSQLで pending job 取得と同時に **仕入元抽出ルール**（`suppliers.extraction_price_format` 等7カラム）と `supplier_channels`経由の `supplier_id` を取得（`tcg_extraction.py:229-249`, 具体的には`s.extraction_price_format`等が`:231-238`）。
  - 取得列: `s.extraction_price_format, s.extraction_qty_format, s.extraction_order_pattern, s.extraction_default_unit, s.extraction_notes, s.extraction_state_format, s.extraction_example_text`
  - `supplier_context` はこの辞書（どれか値があれば non-None）
  - `knowledge_links` は `public.supplier_knowledge_links` JOIN `public.knowledge_rules`（`sid`条件、is_active=TRUE 両方）から取得（`tcg_extraction.py:286-296`、`kl_rows = session.execute`は`:289`）
- プロンプト設定は **DB必須・フォールバックなし**: `gemini_extraction_svc._load_db_prompts()`（`gemini_extraction_svc.py:91-134`付近）が `public.extraction_prompt_config`（`prompt_key IN ('base_extraction','work_id_extraction')`, `is_active=TRUE`）から取得。**`base_extraction` または `work_id_extraction` が未登録なら `RuntimeError` を送出**（`gemini_extraction_svc.py:128,133`（base_extraction欠落は128、work_id_extraction欠落は133）。ハードコード定数へのフォールバックは無い（コード上のコメントに「DB からプロンプト設定を取得（DB 必須・フォールバックなし）」と明記、`gemini_extraction_svc.py:83`）。
  - migration: `migrations/20260926_080000_create_extraction_prompt_config.sql`（`prompt_key VARCHAR UNIQUE`, `prompt_text`, `is_active`, `version` 等）
- モデル/温度: `_GEMINI_MODEL = "gemini-3.1-flash-lite"`（`gemini_extraction_svc.py:233`）, `temperature=0`（`:370`, payload dict内）
- `work_reference`（作品・商品マスタ参照）が渡されると v6プロンプト（`work_id_extraction` テキスト使用）、渡されないとv3相当（`base_extraction`）。プロンプトバージョン定数: `PROMPT_VERSION = "raw-extraction-v3-work-p1"`（`gemini_extraction_svc.py:80`）、`WORK_ID_PROMPT_VERSION = "raw-extraction-v6-rawcode-p1"`（`tcg_work_reference.py:13`）
  - `WORK_ID_PROMPT_VERSIONS = frozenset({"raw-extraction-v4-work-id-p1","raw-extraction-v4-work-id-p2","raw-extraction-v5-product-p1", WORK_ID_PROMPT_VERSION})`（`tcg_work_reference.py:14`）
  - `PRODUCT_ID_PROMPT_VERSIONS`（v5以降resolved_product_code持ち）、`RAW_CODE_PROMPT_VERSIONS`（v6のみraw_product_code持ち）も同ファイルに定義
- **パーサ（列数）**: `parse_extraction_response(response_text, raw_text, version=...)`（`gemini_extraction_svc.py:415-547`）
  - `expected_columns = {2: 7, 3: 9, 4: 10, 5: 11, 6: 12}[version]`（`gemini_extraction_svc.py:445`）
  - version 2-6のみ許可（`if version not in (2,3,4,5,6): raise ValueError`、`gemini_extraction_svc.py:443`）
  - ヘッダー文字列を version に応じて段階的に連結して構築（v3+: `｜RAW_WORK_NAME｜RAW_WORK_SOURCE_LINE_SPAN`追加、v4: `｜RESOLVED_WORK_ID`追加、v5: `｜RESOLVED_PRODUCT_CODE`追加、v6: `｜RAW_PRODUCT_CODE`追加）（`gemini_extraction_svc.py:446-453`付近）
  - **v7列追加の機構**: 上記2箇所（`expected_columns`辞書に`7: N`追加、ヘッダー文字列にv7時の列名追加）＋ items dict構築部（`cols[9]/[10]/[11]`で4/5/6を分岐しているのと同じパターンで`cols[12]`等を追加）＋ `extract_message()`内の`version=6 if work_reference is not None else 3`のバージョン選択ロジック更新、が必要（既存のv2→v6追加パターンを踏襲すれば実装可能。実コードでは行追加のみで済む設計になっている）
  - ヘッダー欠落・列数不一致（v3+）は `ValueError` を送出（=ジョブ全体エラー）。データ行個別のパースエラーは `parse_errors` に積んで継続（`gemini_extraction_svc.py:546`（ヘッダー欠落）、データ行エラーは同ファイル内`except ValueError`で`parse_errors.append`）
- 入力サイズ記録: `backend/app/services/tcg_extraction_record_svc.py` の `AttemptRecorder.before_send()`（`:69-99`）が `extraction_attempts.input_bytes` に記録。`MAX_BYTES = 8_388_608`（8MB、`:21`）超過で `RecordError("INPUT_TOO_LARGE")`。同様に `RESPONSE_TOO_LARGE`（`:153`）, `PARSED_TOO_LARGE`（`:160`）あり。

## C. 仕入先ルール（現状の置き場所）

【事実】仕入先ルールは現在 **2箇所** に分散（design.mdの「仕入元ルールの2か所」の指摘と一致）:

1. `public.suppliers` テーブルの `extraction_*` カラム（`extraction_price_format`, `extraction_qty_format`, `extraction_order_pattern`, `extraction_default_unit`, `extraction_notes`, `extraction_state_format`, `extraction_example_text`）— **抽出パスで実際に読まれ、プロンプトに注入される**（`gemini_extraction_svc._build_supplier_context_note()`, `:233-296`付近）
2. `public.supplier_prompts`（`supplier_id UNIQUE`, `prompt TEXT`, migration `087_create_supplier_prompts.sql`）— ADR-085 MVP。CRUD は `backend/app/routers/super_admin_suppliers.py:600-644` のみ。**`supplier_prompts` は抽出パス（`tcg_extraction.py`, `gemini_extraction_svc.py`）のどこからも読まれていない**（`grep -rn "supplier_prompts" backend/` で確認、CRUDルーター2箇所とスキーマ定義1箇所のみヒット）。

さらに `public.supplier_knowledge_links` + `public.knowledge_rules`（`category`: `block_delimiter`/`skip_condition`/`status_keyword`、`pattern_type`: exact/substring/prefix/regex）も抽出パスで読まれ `_build_supplier_context_note()` の knowledge_links 引数として注入される（`gemini_extraction_svc.py:236-317`, knowledge_links注入部分は同関数内）。**Pre-extraction filter**（`tcg_extraction.py:_apply_pre_extraction_filter()`, `:164-`）は `knowledge_rules` の `message_exclude` / `message_exclude_no_digit` カテゴリを別途使用（メッセージ全体をGemini呼び出し前にフィルタ）。

→ **重複/分散の実態**: `suppliers.extraction_*`（7カラム、構造化ルール）と `supplier_prompts`（1カラム、フリーテキストプロンプト）は**別スキーマ・別読み出し経路**で、統合されていない。design.md §5-2「仕入元ルールの置き場所は supplier_prompts に一本化する。いま使っている suppliers.extraction_* は移して統合する」は**未着手**（コード上、統合の形跡なし）。

【未確認】`supplier_prompts` の登録済み行数（design.mdは「いま32件」と記載）、`suppliers.extraction_*` に値が入っている仕入先数。DB実データ照会が必要（本セッションはDB接続手段未確認、後述J）。


## D. Analyzer（tcg_analyzer_svc.py, 1691行）

【事実】`ENGINE_VERSION = "name-first-v9-product-all-terms"`（`tcg_analyzer_svc.py:58`）

主要関数と行番号:
- `select_product_candidates()` — `:392`
- `resolve_work_evidence()` — `:423`（**注: team-lead元指示は`tcg_product_guards.py`にあると記載していたが誤り。同ファイルにあるのは`work_heading_evidence()`（`tcg_product_guards.py:30`）のみ。`resolve_work_evidence`は`tcg_analyzer_svc.py`内**）
- `resolve_unit()` `:590` / `resolve_unit_v2()` `:759`
- `resolve_condition()` `:616` / `resolve_condition_v2()` `:787`
- `resolve_status_v2()` `:1138`（`load_status_master()`は`:1093`付近、`public.tcg_status_master`テーブル参照、`WHERE enabled=TRUE ORDER BY effect ASC, priority ASC`）
- `match_pid_with_work()` — `:550`
- `build_review_reasons()` — `:1072-1086`。reason codes: `pid_unresolved`（pid未解決）, `multi_candidate`（候補2件以上）, `note_unmatched`（memoがあるがnote_jaに反映されず`consumes_empty_memo`も真でない場合）
- `analyze_extraction_job(session, extraction_job_id)` — `:1182`（エントリポイント）

`pid_basis` の値パターン（`grep -n 'pid_basis = '`実測）: `SK:{keyword}`（`:404`）, `MULTI({parts}):要確認`（`:411`）, `RAWCODE_OVERRIDE`（`:1439`）, `GEMINI`（`:1444`, ADR-1001延長のuse-gemini-product-code設計で導入）, `RAWCODE`（`:1462`）, `GEMINI_EXCLUDED|RAWCODE`（`:1464`）, `GEMINI_EXCLUDED|RAWCODE_EXCLUDED|{kw_basis}`（`:1477`）, `RAWCODE_EXCLUDED|{kw_basis}`（`:1479`）, `GEMINI_EXCLUDED|`prefix（`:1491`）, `FALLBACK|`prefix（`:1494`）, `GEMINI|`prefix（`:1497`）, `WORK_HEADER:L{n}|`prefix（`:1501`）。**Gate1(RAWCODE)/GEMINI/keyword系が併存しており、pid_basisは組み合わせ可能な接頭辞体系**（team-lead元指示の想定と一致）。

## E. analysis_results / extraction_items / extraction_attempts 全スキーマ

【事実】権威あるDDLは `migrations/20260921_110000_pipeline_tables_public.sql`（全417行、tenant_004→public移行時の集約DDL。冪等 `CREATE TABLE IF NOT EXISTS`）。以降の追加migrationで列追加。

### extraction_items（`migrations/20260921_110000_pipeline_tables_public.sql:93-105`, per-item）
`id UUID PK, extraction_job_id UUID FK→extraction_jobs, line_start, line_end INTEGER, raw_product_name/raw_quantity/raw_price/raw_unit/raw_state/raw_memo TEXT, created_at, raw_work_name, raw_work_source_line_span TEXT, resolved_work_id INTEGER, resolved_product_code TEXT`。
その後 `migrations/20260917_010000_add_product_code_to_extraction.sql`, `migrations/20260926_010000_add_raw_product_code.sql` で列追加（raw_product_code等、詳細は未読了・未確認）。**per-item（1商品明細=1行）**。

### extraction_attempts（`migrations/20260921_110000_pipeline_tables_public.sql:112-149`, per-attempt）
`id UUID PK, extraction_job_id FK, source_message_id, parent_attempt_id UUID UNIQUE, started_at, response_received_at, finished_at, phase TEXT CHECK IN('started','received','completed','failed'), input_payload JSONB, input_sha256, input_bytes BIGINT NOT NULL, requested_model TEXT NOT NULL, prompt_version TEXT NOT NULL, code_version, response_text, response_sha256, response_bytes, parsed_items JSONB, parsed_bytes, item_count, validation_result JSONB NOT NULL DEFAULT '{}', error_code`。
CHECK制約: `phase='completed'` の場合のみ `finished_at IS NOT NULL` 必須。`phase != 'completed'` OR (input_payload/response_text/response_received_at/parsed_items/item_count が全てNOT NULL かつ error_code IS NULL)。
`migrations/20260927_130000_add_extraction_token_cost_columns.sql` でトークン/コスト列追加（詳細未読了・未確認）。
**per-attempt（1回のGemini呼び出し=1行）**。`validation_result JSONB` は1試行あたり1つのJSON列 — team-lead元指示にあった「記録の置き場所」候補だが、現状は `AttemptRecorder.record_error_detail()`（`tcg_extraction_record_svc.py`内）経由でエラー詳細を書くための列であり、判定根拠の一般的な記録用途では未使用（**設計変更の対象になりうるが現状はエラー用途限定、要design検討**）。

### analysis_results（`migrations/20260921_110000_pipeline_tables_public.sql:189-250`付近（VIEW guard分岐あり）, per-extraction_item, UNIQUE制約あり）
`id UUID PK, extraction_item_id UUID NOT NULL REFERENCES extraction_items(id) ON DELETE CASCADE, pid_resolved BOOLEAN NOT NULL, pid_basis VARCHAR(100), unit_canonical, unit_resolved BOOLEAN NOT NULL, condition_canonical, condition_basis, quantity_normalized NUMERIC(14,2), price_normalized NUMERIC(14,2), note_ja TEXT, status VARCHAR(50), exclusion TEXT, needs_review BOOLEAN NOT NULL, review_reasons TEXT, engine_version VARCHAR(50) NOT NULL, computed_at, updated_at, unit_inferred/unit_basis/unit_confidence/unit_infer_reason TEXT, product_id INTEGER REFERENCES products(id), unit_id INTEGER, condition_id INTEGER NOT NULL, work_id INTEGER, is_current BOOLEAN NOT NULL DEFAULT TRUE, UNIQUE(extraction_item_id)`。
**`UNIQUE(extraction_item_id)` により1つのextraction_itemにつき解析結果は常に1行（上書きUPSERT）。並行して別バージョンの結果を保持する仕組みは無い**（`review_reasons`はTEXT型で単一文字列、候補一覧の配列保存機構なし）。
`is_current` は `migrations/20260924_120000_add_analysis_results_is_current.sql` で追加（ADR-158）。**用途は「同一仕入元内の商品単位の新旧切替」（メッセージ単位supersessionの代替）であり、パイプラインバージョン間の並行比較（shadow run）用途ではない**。

### analysis_run_snapshots（`migrations/20260921_110000_pipeline_tables_public.sql:287-308`付近, per-analysis_run, 履歴/監査用）
`id UUID PK, run_id UUID FK→analysis_runs, analysis_result_id UUID, extraction_item_id UUID, pid_resolved, pid_basis, unit_id UUID, unit_canonical, unit_resolved, condition_id UUID, condition_canonical, condition_basis, quantity_normalized, price_normalized, note_ja, status, exclusion, needs_review, review_reasons, engine_version, computed_at, updated_at, snapshotted_at, product_id INTEGER`。

【事実・重要】`analysis_run_snapshots` の実際の書き込み元は `backend/app/services/tcg_product_master_svc.py:_run_reanalyze_sync()`（`:548-` 付近）のみ（`grep -rn "analysis_run_snapshots" backend/app` で他に書き込みなし）。用途は「手動API再解析(`run_type='R1_API'`)の**直前状態のバックアップ**」であり、コード内コメント原文（`tcg_product_master_svc.py`付近）:「再解析（UPSERT — 元には戻せないので before を返す）」。つまり**この仕組みは「新方式を裏で走らせて本番結果とは別に記録する」ためのものではなく、「本番UPSERTの直前スナップショット（不可逆操作の監査ログ）」**。`tcg_analyzer_svc.py`自体（自動抽出フロー）は`analysis_runs`/`analysis_run_snapshots`に一切書き込まない（`grep -n "analysis_runs\|analysis_run_snapshots" tcg_analyzer_svc.py` → 0件）。

**→ team-lead元指示(1)「shadow-run結果を新テーブル無しで記録できるか」への回答**:
【事実】既存の`is_current`（商品supersession用）、`analysis_run_snapshots`（手動再解析の直前バックアップ用）は共に**目的が異なり、シャドー実行（新旧2系統を並行して走らせ比較する）用途には転用できない**。理由: (a) `analysis_results`は`UNIQUE(extraction_item_id)`のため同一itemに新旧2案を同時に持てない。(b) `analysis_run_snapshots`は「これから上書きする直前の状態」を控えるための構造で、"新方式の結果" を保存する設計にはなっていない（product_id等はあるがGemini新方式特有の出力列は無い）。(c) `extraction_attempts`は抽出（Gemini呼び出し）ごとの記録であり、`analyze_extraction_job`（照合ロジック）の出力は保存対象外。
**設計上の選択肢**（未確定、判断が必要）: ① `extraction_attempts.validation_result`（既存JSONB列）に判定ロジックの試運転結果もJSONで詰め込む（新テーブル不要だが列の意味が「エラー詳細」から「試運転記録」に拡張される）、② `analysis_run_snapshots`に`run_type='SHADOW'`のような新run_typeを追加し書き込み専用で使う（新テーブル不要、ただし現状の用途（直前バックアップ）と混在させる設計判断が必要）、③ 新テーブル新設（design.md §7-2で「新しい表は作らない方向で recon する」と指示されているため回避したいが、上記①②は既存列の意味変更を伴う）。**この選択はSSOTに関わる決定であり、Sonnetの権限外（design.md記載どおりOpus/PO判断）**。

## F. analysis_results 読み手一覧

【事実】`grep -rln "analysis_results" backend/app`（origin/main）で17ファイルがヒット:
`routers/super_admin_suppliers.py`, `routers/tcg_analysis_review.py`, `routers/tcg_parallel_report.py`, `routers/tcg_product_import.py`, `routers/tcg_product_master.py`, `schemas/central_masters.py`, `services/item_corrections_svc.py`, `services/tcg_analysis_dashboard_svc.py`, `services/tcg_analysis_review_svc.py`, `services/tcg_analyzer_svc.py`, `services/tcg_condition_review_svc.py`, `services/tcg_diagnostics_svc.py`, `services/tcg_distribution_svc.py`, `services/tcg_import_progress.py`, `services/tcg_parallel_report_svc.py`, `services/tcg_product_master_svc.py`, `services/tcg_sold_out_results_svc.py`, `services/tcg_supplier_quality_svc.py`, `services/tcg_unit_recovery_svc.py`, `services/tcg_work_comparison_svc.py`, `tasks/tcg_extraction.py`, `tasks/tcg_mirror.py`
（**17ファイル・21箇所超、想定より広い影響範囲。個別file:lineでの`is_current`フィルタ有無の全数確認は未実施 — 未確認、design検討時は全数grep必須**）
配信クエリ（`tcg_distribution_svc.py`、`WHERE`句実測 `:249`前後）: `ar.pid_resolved=TRUE AND ar.is_current=TRUE AND cr.needs_review IS FALSE AND ar.exclusion IS DISTINCT FROM 'excluded' AND ar.unit_resolved=TRUE AND ar.price_normalized IS NOT NULL AND sm.line_posted_at IS NOT NULL`。design.md記載の「商品・単位・価格が決まったものだけ配信」（`tcg_distribution_svc.py:250-256`という行番号記載）は実測とおおむね一致（数行のズレはコメント込みの目算差、内容は一致）。

## G. キーワード保存

【事実】現行SSOT（`migrations/20260919_020000_master_ssot_public_tables.sql:301-306`）:
`public.product_search_keywords(id INTEGER IDENTITY PK, keyword TEXT NOT NULL, position INTEGER NOT NULL, product_id INTEGER NOT NULL REFERENCES products(id), updated_at)`
`product_exclude_keywords` も同様パターンで存在（`migrations/20260925_120000_add_product_exclude_keywords.sql`、詳細列は未読了）。
旧テナントスコープ版（`tenant_004`/`tenant_001`, UUID PK）は `migrations/20260831_110000_create_tcg_analysis_tables_t004.sql:157-185`, `migrations/20260906_120000_create_tcg_tables_t001.sql:289-316` にあるが、`migrations/20260921_130000_drop_tenant004_master_copies.sql` で削除対象（ADR-1001/1002のpublic統合の一環、詳細未読了）。
Writer: `tcg_product_master_svc.py`（`INSERT INTO public.product_search_keywords` 実測、`:524-534`付近）+ 対応するsuper_admin routerエンドポイント（file:line未特定・未確認）。
作品マスタ（type_master）: `public.type_master`（`tcg_work_reference.py:79`で参照、`is_active`列あり、`name_ja`/`name_en`）。
条件マスタ: `public.conditions`（`analysis_results.condition_id`のFK先、`migrations/20260921_110000...sql:227`）。
ステータスマスタ: `public.tcg_status_master`（`tcg_analyzer_svc.py`内`load_status_master()`が参照、列: `status_id, canonical, search_pattern, exclude_pattern, priority, match_type, effect, enabled`）。
Note master: 個別テーブルは未発見（`note_ja`はTEXT自由記述、マスタテーブル経由ではない可能性 — 未確認、追加grep要）。

## H. 発送日（shipping date）

【事実】既存の発送日ロジックは**別パイプライン**（`backend/app/services/inventory_parser.py`、在庫表インポート用ルールベースパーサ、ADR-093 Phase 3b）にある。Gemini抽出パイプライン（`tcg_extraction.py`/`gemini_extraction_svc.py`）側ではなく、在庫表アップロード解析側の機能。
`inventory_parser.py`内の該当箇所（grep実測行）: `:107`（コメント「区分/発送日の行内自動判定」）, `:240`（コメント見出し）, `:245`（「発送日（予約品）。順序重要」）, `:522-524`（`ship_timing`関数docstring）, `:713`（行レベル判定コメント）, `:1089`（「発送日はLLMプロンプトを拡張せず、ルールベース検出」）。
【事実】`extraction_items`/`analysis_results`（E節のスキーマ全列）に**shipping_date相当のカラムは現状存在しない**（両テーブルのDDL全列を確認済み、該当列なし）。design.md「発送日は、在庫解析の読み取り方を参考にして原文から読む」はこの`inventory_parser.py`のルールベース判定を指すと解釈できる（file:line根拠あり、意味解釈は妥当性が高いが断定ではない — 未確認: 設計者の意図確認）。

## I. フロントエンド（軽度確認・未完了部分あり）

【未確認】`NeedsReviewListPage.tsx`, `ExtractionErrorLogPanel.tsx`, `tcg_analysis_review.py`ルーターのレスポンス形、デザイントークン適用状況は本セッションでは未着手（時間制約により後続recon課題として残す）。`docs/CC_UI_GOVERNANCE.md`（ADR-144）の存在は確認済み（CLAUDE.mdに参照あり）が内容未読了。

## J. 件数・ボリューム

【未確認】1日の抽出件数、`extraction_prompt_config`/`supplier_prompts`/`suppliers.extraction_*`の実データ行数はDBアクセスが必要。本セッションではDB接続手段（`~/.ssh/salesanchor-claude`制限鍵経由のSELECT可否）を未検証。design.md「まだ分からないこと」に「1日の件数」が明記されており、team-lead元指示のJ節と設計側の認識は一致（=未計測は既知のギャップ）。

## K. テスト

【事実】origin/mainのテストファイル一覧（grep実測、`backend/tests/`）: `test_tcg_completion_safety.py`, `test_tcg_condition_review.py`, `test_tcg_distribution_pg.py`, `test_tcg_extraction_record_integrity_pg.py`, `test_tcg_extraction_record_pg.py`, `test_tcg_gemini_extraction.py`, `test_tcg_result_order.py`, `test_tcg_work_comparison_pg.py`, `test_tcg_work_id.py`, `test_tcg_work_matching_integration.py`, `test_tcg_product_guards.py`, `test_inventory_parser_llm.py`, `test_pre_extraction_filter.py`（ADR-158関連コメント多数、is_current PR #3747の裏付けに使用）。
CI実行コマンド・必須ジョブは本セッション未確認（`.github/workflows/`未読了、後続課題）。

## L. worktree状態（PO向け・件数のみ、削除操作なし）

【事実】`bash scripts/reaper-worktree.sh`（dry-run、`--execute`無し、削除は一切実行していない）の実測結果（生出力: `/private/tmp/claude-501/.../scratchpad/worktrees.txt`）:
- 走査対象 worktree 数: **100件**（`git worktree list`の表示上限か、または実行時点のカウント。冒頭ログに「対象 worktree 数: 100 件」と明記。実際の`git worktree list`総数は本コマンド実行後で114件超だった可能性があり、reaperの内部カウントと不一致の可能性 — 未確認、要再カウント）
- 🔒 IN_PROGRESS/REVIEW 未マージ（削除しない）: **33件**
- ⚠️ 未保存あり（削除しない・人の判断が必要）: **50件**
- 🔄 未マージ（IN_PROGRESS/REVIEW以外、削除しない）: **16件**
- 👻 GHOST（フォルダ消失・要手動確認）: **1件**（`release-time-handling-lint`）
- 🗑️ 削除対象（安全条件クリア＝マージ済み・未保存なし）: **1件**（`release/extraction-table-columns`）
- 合計: 33+50+16+1+1 = 101（走査対象100件との差分1は目視合算誤差の可能性 — 未確認）
**削除は一切実行していない**（dry-runのみ、`--execute`フラグなし）。


## F2. analysis_results 読み手 全17ファイルの is_current / pid_resolved フィルタ有無

【事実】各ファイルの `analysis_results` 参照箇所（file:line、origin/main実測）と、`is_current` / `pid_resolved` フィルタの有無:

| ファイル | analysis_results参照行 | is_current フィルタ | pid_resolved フィルタ |
|---|---|---|---|
| `routers/super_admin_suppliers.py` | `:801`（JOIN、削除用チェック） | 無 | 無 |
| `routers/tcg_analysis_review.py` | `:22,108,125`（`fetch_analysis_results`呼び出しのみ、実クエリは svc 側） | — (svc委譲) | — (svc委譲) |
| `routers/tcg_parallel_report.py` | `:34`（コメントのみ、実処理は svc） | — | — |
| `routers/tcg_product_import.py` | `:411,423,425`（削除時 `product_id=NULL` UPDATE） | 無 | 無 |
| `routers/tcg_product_master.py` | `:297-311`（コメント内、baseline退避手順の記述） | 無（記述のみ、実処理はsvc） | 無 |
| `schemas/central_masters.py` | `:439`（コメントのみ、スキーマフィールド定義） | — | — |
| `services/item_corrections_svc.py` | `:66-69` UPDATE（`pid_resolved = TRUE`設定、書き込み側） | 無 | **書込**（TRUEに設定） |
| `services/tcg_analysis_dashboard_svc.py` | `:62,86,101,125,292,477,700-705` 複数クエリ | **一部あり**（`:704` `WHERE ar.is_current=TRUE AND ar.pid_resolved=TRUE`）。他の集計クエリ（`:62,101,292,477`等）は**is_current条件なし**（全期間・全バージョン集計の可能性） | 一部あり（`:456-466,704-705`） |
| `services/tcg_analysis_review_svc.py`（要確認一覧の実データ源） | `:35,80-97,217,273,288` | **無し**（is_currentでの絞り込みgrepヒットなし） | **あり**（`:80,87,90,97,217`、needs_review判定に使用） |
| `services/tcg_analyzer_svc.py`（自身が is_current を更新する側） | `:1344-1620`（UPSERT本体）, `:1738-1791`（supersession merge処理） | **UPSERT本体（:1344-1620）ではis_current条件なし（新規行はDEFAULT TRUEで作成、既存行upsertはis_current変更せず）**。Supersession判定（`:1738-1791`）では旧行選定に`ar.pid_resolved=TRUE`（`:1745,1764,1778`）を使い、`is_current`自体を`SET`（`:1787`）— つまりこの関数が**is_current の書き手** | あり（1745,1764,1778, supersession対象の絞り込み） |
| `services/tcg_condition_review_svc.py` | `:185,238,246,283,289` | 無し（is_currentのgrepヒットなし） | JSON経由で`pid_resolved`参照（`:142,149`、`cr_data.ar->>'pid_resolved'`） |
| `services/tcg_diagnostics_svc.py` | `:110` | 無し | 無し |
| `services/tcg_distribution_svc.py`（配信本体） | `:238,254-255,319,325-326,343-368,420` | **あり**（`:255,326,368` = `ar.is_current=TRUE`、配信対象3クエリ全て） | あり（`:254,325,343-357` 複数条件分岐） |
| `services/tcg_import_progress.py` | `:37,127` | 無し | 無し |
| `services/tcg_parallel_report_svc.py`（compat-v1 vs name-first-v1 比較） | `:185,178-286` | 無し | あり（`:178,205,224-237,265-286`、比較指標として使用） |
| `services/tcg_product_master_svc.py`（再解析API + 商品削除時UPDATE） | `:56-70,589-704`（`_run_reanalyze_sync`） | 無し | あり（`:56,70,589,613,647,661,693,704`） |
| `services/tcg_sold_out_results_svc.py` | `:45` | 無し | 無し |
| `services/tcg_supplier_quality_svc.py`（品質モニタリング） | `:46` | 無し | あり（`:24,35,39`、NOT ar.pid_resolved でカウント） |
| `services/tcg_unit_recovery_svc.py`（in `tenant_schema`変数、旧tenant_004スキーマの可能性） | `:281,457,640,796,873,925,991,1044,1061,1146,1175` | 無し | あり（`:275,298,315-316,791,814,825`） |
| `services/tcg_work_comparison_svc.py` | `:127` | 無し | あり（`:227,256`、比較指標） |
| `tasks/tcg_extraction.py` | `:10`（コメントのみ） | — | — |
| `tasks/tcg_mirror.py`（管理者向けミラー/エクスポート機能） | `:191,198,203,225` | 無し | 無し |

**要点（事実）**: `is_current=TRUE` で明示的にフィルタしているのは **`tcg_analyzer_svc.py`（is_currentの書き手自身）、`tcg_distribution_svc.py`（配信本体・全3クエリ）、`tcg_analysis_dashboard_svc.py`（一部クエリ:704のみ）** の3ファイルだけ。**レビュー画面（`tcg_analysis_review_svc.py`）、条件レビュー（`tcg_condition_review_svc.py`）、品質モニタリング（`tcg_supplier_quality_svc.py`）、並行比較（`tcg_parallel_report_svc.py`）、単位復旧（`tcg_unit_recovery_svc.py`）、商品マスタ再解析（`tcg_product_master_svc.py`）は is_current を一切見ていない** — ADR-158の「レビュー・品質クエリは変更なし（最新メッセージの抽出結果を見る目的で is_active を継続使用）」という設計意図と一致する部分もあるが、`is_active`（source_messages側）ではなく単に**フィルタ自体が無い**箇所（`tcg_diagnostics_svc.py`, `tcg_import_progress.py`, `tcg_sold_out_results_svc.py`, `super_admin_suppliers.py`, `tcg_product_import.py`）もあり、これらはis_current=FALSE化された旧supersession行も無条件に含めている可能性がある（**未確認、要個別設計レビュー**）。


## I2. フロントエンド詳細

### NeedsReviewListPage.tsx（`frontend/src/pages/super-admin/NeedsReviewListPage.tsx`, 184行）
- import（すべて`components/`金型）: `PageLayout`, `DataTable`+`DataTableColumn`（`:9-10`）, hooks: `useSuperAdmin`, `api/ApiError`
- API呼び出し: `GET /tcg/analysis-results?status_tab=NEEDS_REVIEW&offset=...&limit=20`（`:5`コメント, `:76`実装）
- 表示列（`DataTableColumn`, `:114-146`）: `raw_product_name`（t("needsReview.productName")）, `provider`（needsReview.supplier）, `review_reasons`（needsReview.reviewReasons、`condition_review.review_reasons`優先、無ければ`review_issues`配列をi18nキー変換）, `created_at`（needsReview.createdAt、`gemini["span"]`から日時整形）
- i18nキー使用: `needsReview.productName/supplier/reviewReasons/createdAt/pidUnresolved/multiCandidate/noteUnmatched/noItems`, `common.loading/fetchError`, `superAdmin.supplierQuality.superAdminOnly`, `nav.superAdminNeedsReview`
- `review_issues`の値マッピング（`:129-135`）: `PRODUCT_ID_UNRESOLVED→pidUnresolved`, `PRODUCT_MASTER_UNREGISTERED→multiCandidate`, `CONDITION_REVIEW_REQUIRED→noteUnmatched`

### ExtractionErrorLogPanel.tsx（`frontend/src/pages/super-admin/components/ExtractionErrorLogPanel.tsx`, 318行）
- ファイル冒頭コメントに自己申告あり（`:9-11`）: 「ADR-027: 全UI文字列はt("key")経由」「ADR-067: 色・サイズはデザイントークンのみ」「ADR-144: Card/DataTable/Badge/Modal/Button 金型のみ使用」
- import（`components/`金型）: `Card`, `DataTable`+`DataTableColumn`, `Button`, `Badge`+`BadgeVariant`, `Modal`, `ContentToolbar`（`:15-21`）
- API呼び出し: `GET /tcg/extraction-errors?offset=...&limit=50`（`:83-85`）, `POST /tcg/diagnostics/retry-extraction`（`:117`、選択行の再試行）
- 表示列（`:134-190`）: `supplier_name`, `error_category`（Badge色分け, `CATEGORY_VARIANT`辞書 `:53-62`でカテゴリ→BadgeVariant対応。カテゴリ値は`gemini_rate_limit/gemini_http_error/gemini_timeout/gemini_unknown/system_timeout/system_db_error/system_input_error/logic_parse_error/logic_conflict`、`tcg_extraction.py:_SYSTEM_ERROR_CATEGORIES`および`gemini_extraction_svc._classify_error()`の分類コードと一致）, `error_message`, `error_detail`, `prompt_version`, `created_at`
- i18nキー: `analysisRules.errorLog.*`（`fetchError, supplier, errorCategory, category.unknown, errorMessage, errorDetail, promptVersion, createdAt, title, retrySelected, noErrors, loadMore, retryConfirm, retrySuccess, retryError`）, `common.loading`

### 解析結果レビューAPI（`backend/app/routers/tcg_analysis_review.py` + `backend/app/services/tcg_analysis_review_svc.py`）
Pydanticレスポンススキーマ（`tcg_analysis_review.py:37-90`）:
- `GeminiFields`（`:37-44`）: `name, quantity, price, unit, state, memo, span`（全てstr、Gemini原文書き写し値）
- `SystemFields`（`:47-61`）: `work_id, work_name, product_title, product_uuid, product_id, pid_resolved, pid_basis, unit, unit_resolved, condition, status, note, exclusion`（**全てstr型 — booleanのpid_resolved/unit_resolvedも文字列化されて返る**）
- `ConditionReviewFields`（`:63-70`）: `condition_id(str|None), review_version, needs_review(bool), review_reasons, confirmed(bool), classification`
- `AnalysisResultItem`（`:72-81`）: `extraction_item_id, source_message_id, provider, raw_text, gemini(GeminiFields), system(SystemFields), review_issues(list[str]), condition_review(ConditionReviewFields|None)`
- `AnalysisResultsResponse`（`:83-90`）: `items, total, item_total, offset, limit, providers, works(list[dict])`
- エンドポイント: `GET /tcg/analysis-results`（`:103-108`, status_tabパラメータは`_STATUS_TABS = {ALL, NEEDS_REVIEW, PRODUCT_MASTER_UNREGISTERED, SUPPLIER_UNREGISTERED, PRODUCT_ID_UNRESOLVED, NORMAL_COMPLETED}`、`:98-101`）
- svc側`fetch_analysis_results()`（`tcg_analysis_review_svc.py:145-`）のSQLは`ar.pid_resolved, ar.pid_basis, ar.unit_canonical, ar.unit_resolved, ar.note_ja, ar.status, ar.exclusion`等を直接SELECT（列名は`:217-224`）。**`is_current`はSELECT対象にもWHERE条件にも含まれない**（F2節の記載と一致）。

### キーワード追加エンドポイント
- 検索キーワード: `POST /api/v1/tcg/products/{product_id}/search-keywords`（`tcg_product_master.py:246-249`, summary「商品マスタ検索キーワード追加（PARITY-03 Phase 3 B-5）」）。Request: `AddKeywordRequest{new_keyword: str}`（`:117-118`）。実処理は`add_search_keyword()`（`tcg_product_master_svc.py:474-`、`INSERT INTO public.product_search_keywords`は`:527`）
- 除外キーワード: **専用の単体追加エンドポイントは存在しない**（`grep -n "exclude-keyword" tcg_product_master.py` → ルートパスとしてはヒットなし）。`exclude_keywords`は商品登録時のリクエストボディ（`body.exclude_keywords: str`、`:82,99,231`、カンマ区切り一括指定）でのみ設定可能。**search-keywordsとexclude-keywordsでAPI設計が非対称**（検索は1件追加API、除外は登録時一括のみ）。

## K2. テストコマンド・CI・既存テスト

【事実】
- pytestコマンド: `backend/Makefile:30-31` — `test:\n\tpytest -q --tb=short`（コメント「DB サービス必須: docker compose up -d postgres redis」）
- pytest設定: `backend/pyproject.toml:45-55`（`[tool.pytest.ini_options]`, `asyncio_mode="auto"`, `testpaths=["tests"]`）
- CI: `.github/workflows/test.yml`（`name: Backend Tests`）。jobs: `detect-changes`(`:32`), `lint-backend`(`:59`), `pytest-run`(`:114`), `pytest`(`:250`)
- Required checks（`docs/BRANCH_PROTECTION_SETUP.md`記載、**日付に注意**）:
  - Legacy Branch Protection（4件、doc内「2026-05-31にしんごさん承認のもと実行済み」以降の状態、`:287-291`）: `models.py に新 Column → deploy.yml にマイグレーション追記必須`, `マイグレーションSQL 実行テスト（実DB）`, `pytest (SQLite + PostgreSQL RLS)`, `Lint & Dark Mode Check (ADR-067)`
  - develop Ruleset（ID: 16619490、13件、`:298-312`）: 上記4件と重複含め `pytest (SQLite + PostgreSQL RLS)`, `テナントスキーマ整合性チェック`, `マイグレーションSQL 実行テスト（実DB）`, `models.py に新 Column → deploy.yml にマイグレーション追記必須`, `ADR-072 tenant schema lint (strict mode)`, `Lint & Dark Mode Check (ADR-067)`, `Playwright E2E (chromium)`, `gitleaks`, `CLAUDE.md line count check`, `ADR index is up to date`, `process-artifacts gate`, `dangling-route gate`, `UI governance gate`(2026-06-25追加)
  - **【未確認】この一覧はdevelop Rulesetを指しており、CLAUDE.md記載の現行ブランチ運用（release/*→main、developは残置のみ）に対応するmain向けRulesetの最新一覧は本ドキュメント内で確認できていない（ドキュメントが古い可能性、要再確認）**

既存テストカバレッジ:
- パーサ（`parse_extraction_response`）: `backend/tests/test_tcg_gemini_extraction.py`（`test_parse_extraction_response_basic/single_line_span/clamp_max/wrong_cols_skipped/empty_response/header_only`, `:124-198`; `test_v3_format_failure_saves_no_partial_items`, `test_v3_partial_save_when_valid_and_invalid_lines_mixed`, `test_v3_product_span_collected_in_parse_errors`, `test_v3_work_evidence_roundtrip_without_repair`, `test_work_master_reaches_prompt_without_database_ids`, `:459-501+`）
- analyzer商品マッチング: `backend/tests/test_tcg_work_matching_integration.py`（36テスト関数、`:395-1243`。代表: `test_onepiece_code_positive_with_verified_work`(`:501`), `test_raw_heading_and_box_guard_through_analysis`(`:969`), `test_work_id_v4_database_roundtrip_and_review_filter`(`:997`), `test_space_product_match_saved_in_isolated_database`(`:1066`), `test_cardset_exclusion_additive_idempotent_and_matching`(`:1149`)）
- `backend/tests/test_tcg_product_guards.py`（120行, `ProductGuardTests`クラス`:22`, `MatchingConnectionTests`クラス`:85`）— `work_heading_evidence`のユニットテスト

## M. マスタテーブル

【事実】
- `public.conditions`（コンディションマスタ）: `migrations/20260919_020000_master_ssot_public_tables.sql:145`, `migrations/20260921_100000_add_analysis_master_fk.sql:42`（同名テーブルが2migrationに登場 — 後者は前者を前提としたFK追加または冪等再定義の可能性、列詳細は未読了・未確認）
- `public.type_master`（作品マスタ、旧`tcg_type_master`から改名）: 定義は3箇所に登場（`migrations/20260921_070000_rename_tcg_type_master_to_type_master.sql:25`が改名元、`migrations/20260922_010000_product_format_kind_id_and_products_type_master_id.sql:12`と`migrations/20260922_030000_product_format_game_links.sql:9`は同一DDL文字列 `CREATE TABLE IF NOT EXISTS public.type_master (id SERIAL PRIMARY KEY, code VARCHAR(50) NOT NULL UNIQUE, name_ja VARCHAR(100) NOT NULL, name_en VARCHAR(100), sort_order INTEGER NOT NULL DEFAULT 100, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at, updated_at)` の冪等CREATE TABLE IF NOT EXISTSが繰り返し埋め込まれている）
  - **列構成: `id, code, name_ja, name_en, sort_order, is_active, created_at, updated_at`。search_keyword/exclude_keyword/match_type等のキーワード列は存在しない。**
  - **見出しマッチングは`type_master`のキーワード列ではなく、`tcg_product_guards.py:work_heading_evidence()`内でコード直書きのロジックが`work["display_name"]`（=`name_ja`）と`work.get("alt_name")`（=`name_en`）を正規化して比較し、さらに「ワンピ」「one piece」という**ハードコードされた特例エイリアス**（`tcg_product_guards.py:44-46`）を1件だけ持つ形で実現されている。汎用的な検索ワード登録の仕組みは無い（design.mdの「見出しの行を作品の検索ワードと照らし合わせ」を実現するには、type_master側にキーワード保存の仕組みを新設する必要がある）**
- `public.tcg_status_master`（ステータスマスタ）: `migrations/20260919_020000_master_ssot_public_tables.sql:259`。列（`tcg_analyzer_svc.py:load_status_master()`のSELECT文実測）: `status_id, canonical, search_pattern, exclude_pattern, priority, match_type, effect`＋`enabled`（WHERE条件）。**`match_type`列を持つ（LITERAL/REGEX/DEFAULT、`tcg_analyzer_svc.py:_match_status_pattern()`で分岐）**
- note master: 専用テーブルは本セッションで未発見（`note_ja`はTEXT自由記述、`item_corrections`テーブル経由の手動補正のみ確認 — 未確認、追加recon要）

## N. 仕入先ルール カラム・スキーマ詳細（ADR-085関係）

【事実】
- `public.suppliers.extraction_*` 7カラムの追加migration:
  - `migrations/20260924_010000_add_supplier_extraction_rules.sql:2-7`: `extraction_price_format, extraction_qty_format, extraction_order_pattern, extraction_default_unit, extraction_notes, extraction_state_format`（全て`ALTER TABLE public.suppliers ADD COLUMN IF NOT EXISTS ... TEXT`）
  - `migrations/20260924_030000_add_extraction_example_text.sql:2`: `extraction_example_text TEXT`
  - **これらは2026-09-24付、`supplier_prompts`（migration 087、ADR-085本文に「2026-05-31」の日付記載）より約4ヶ月後に追加された、より新しい仕組み**
- `public.supplier_prompts`（migration `087_create_supplier_prompts.sql`）全DDL: `id SERIAL PK, supplier_id INTEGER NOT NULL UNIQUE REFERENCES suppliers(id) ON DELETE CASCADE, prompt TEXT NOT NULL DEFAULT '', is_active BOOLEAN NOT NULL DEFAULT TRUE, updated_by INTEGER, created_at, updated_at`。UNIQUE制約は`supplier_id`（1仕入先=1プロンプト）。
- **時系列からの推測（未確認・解釈）**: ADR-085（5月）で`supplier_prompts`という「フリーテキストプロンプト1本化」構想を作ったが、「実際の解析への配線は本PRで行わない」と明記した通り未接続のまま、9月に入って`suppliers.extraction_*`という「構造化フィールド7本」の別方式が新設され、**こちらが実際に配線された**（`gemini_extraction_svc._build_supplier_context_note()`で読まれる）。結果として、ADR-085が想定した「プロンプト管理層に一本化」というゴールとは異なる方向（構造化ルールの拡充）に実装が進んだと解釈できる。design.md §5-2「仕入元ルールの置き場所はsupplier_promptsに一本化する」は、**この経緯（9月に構造化フィールド方式が実際に採用され配線もされた）を踏まえると、方向性の再検討が必要な可能性がある**（PO/Opus判断事項、Sonnetからは選択肢の提示のみ）。


## V. 実現性検証（origin/main, SHA ae783c7f5）

### V1. products.work_id

【事実】現行スキーマ: `products.work_id INTEGER`（UUID→INTEGER再変換, `migrations/20260919_010000_master_ssot_work_id_recast.sql:107` `ALTER TABLE public.products ADD COLUMN work_id INTEGER`）。FK制約: `migrations/20260919_030000_master_ssot_fk_work_id.sql:29-33`（`fk_products_work_id FOREIGN KEY (work_id) REFERENCES public.tcg_type_master(id)`、後にtype_masterへ改名）。
**NOT NULL制約は無い**（再キャスト後の列定義`:107`に`NOT NULL`指定なし。旧UUID列に対する`migrations/20260916_130000_work_id_not_null.sql:41-42`のNOT NULL化は再キャスト前の話で、再キャスト後に再適用された形跡なし — `grep -rn "work_id" migrations/2026092*.sql` で新たなSET NOT NULLはヒットせず）。**つまり `work_id` は現状nullable**。
登録経路: `backend/app/services/tcg_product_master_svc.py:create_product()`（`:324-`）が `work_id: str | int` を**必須の関数引数**として受け取り、そのまま`INSERT INTO public.products (..., work_id, ...) VALUES (..., :work_id, ...)`（`:387-402`）。**work_idは自動推測ではなく呼び出し側（UI/人）が明示指定する値**。ルーター: `POST /api/v1/tcg/products`（`tcg_product_master.py:212 create_product_master`）。
【未確認】work_id欠損（NULL）商品の実件数はDBデータであり本セッションからは確認不能。ADR-155（CSV SSOT化、2026-09-16）以降、商品マスタ値の正規更新経路はCSV取り込みとアプリ画面の2経路のみで、マイグレーションでの値操作は`migration-guard.yml`チェック7で禁止（ADR-155該当箇所）。**リポジトリ内に商品マスタseed用CSVファイルは発見できず**（`find . -iname "*product*master*.csv"` 等で0件）— CSVは外部管理（Google Sheets等）の可能性が高く、リポジトリからは件数を確認できない。

### V2. tcg_product_guards.py（全72行、コード全文確認済み）

【事実】ファイル冒頭docstring: `"""Deterministic evidence from a single LINE message; no model calls."""`（LLM呼び出し無しを自己申告）。定義される関数は**2つのみ**:
```python
def single_card_marker(*fields: str) -> str | None:
    """Each field is independent: never concatenate pieces into a new marker."""
```
（`:10-16`。可変長str引数、任意の文字列群を受け取る汎用シグネチャ。SAR/AR/PSA等の単品判定記号を正規表現で検出）
```python
def work_heading_evidence(raw_text: str, line_start: int, line_end: int,
                          works: list[dict]) -> tuple[str, int] | None:
```
（`:30-31`。raw_text全文＋行範囲＋`works`辞書リスト`{id, display_name, alt_name, is_active}`を受け取る）
**両関数ともDB/LLM呼び出しを含まない純粋関数**（importと外部呼び出しは`re`, `unicodedata`のみ、`:2-3`）。**シグネチャ上はGemini固有オブジェクトを要求せず、任意の文字列・行番号・辞書リストを受け取れる**が、実際の呼び出し元（`tcg_analyzer_svc.py:559,1423`）ではGemini抽出済みフィールド（`raw_product_name, raw_state, raw_memo`＝extraction_itemsの列）を渡している。**「box guard」という専用関数は存在せず**、`single_card_marker`の戻り値と`_gemini_category`（Geminiのresolved_product_codeから導出したカテゴリ）を`tcg_analyzer_svc.py:1423`で組み合わせてbox/case判定に使っている（`if single_card_marker(...) and _gemini_category.casefold() in {"box","case"}:`）。

### V3. inventory_parser.py 発送日関数

【事実】関数シグネチャ（実測、`:518-541`）:
```python
def _extract_offer_type_ship_timing(line: str) -> tuple[str | None, str | None]:
```
モジュールレベル関数（クラス非依存）。docstring: 「行から (offer_type, ship_timing) を推定（ADR-093 Phase 3b）」。**純粋関数**: 参照するのは同ファイル冒頭で定義済みのモジュール定数`OFFER_TYPE_REGEXES`（`:242-244`）, `SHIP_TIMING_REGEXES`（`:245-250`）のみ（`re.compile`済み正規表現リスト、静的）。DB接続・LLM呼び出し・外部I/Oは一切なし。**他サービスからimportして副作用なく呼び出し可能**（ただし関数名が`_`始まりのモジュールプライベート命名規約のため、正式な外部公開インターフェースにする場合はリネームまたは薄いpublicラッパーが必要 — 慣習上の問題であり技術的には現状でもimport自体は可能）。
`OFFER_TYPE_REGEXES`は予約キーワード（`予約|ご予約|preorder|...`）で`offer_type='pre_order'`判定のみ、既定（在庫）は`None`。`SHIP_TIMING_REGEXES`は3パターン（2日前/1日前/発売日発送、`:245-250`）。

### V4. knowledge_rules / supplier_knowledge_links

【事実】
- `public.knowledge_rules`（`migrations/058_create_knowledge_rules.sql:25-36`）: `id SERIAL PK, category VARCHAR(50) NOT NULL, pattern_type VARCHAR(20) NOT NULL CHECK IN('regex','prefix','substring','exact'), pattern TEXT NOT NULL, normalized_to TEXT, priority INTEGER DEFAULT 100, language CHAR(2) DEFAULT 'ja', is_active BOOLEAN DEFAULT TRUE, description, created_by, created_at, updated_at`。migration冒頭コメント（`:8-9`）記載の当初想定category例: `expansion_code/rarity/language/exclude/split`。
- `public.supplier_knowledge_links`（`migrations/20260924_050000_create_supplier_knowledge_links.sql:4-10`）: `id SERIAL PK, supplier_id INTEGER FK→suppliers(ON DELETE CASCADE), knowledge_rule_id INTEGER FK→knowledge_rules(ON DELETE CASCADE), is_active, created_at, updated_at`。UNIQUE制約: `(supplier_id, knowledge_rule_id)`。
- **実際に使われているcategory値（コードから実測、当初想定のexpansion_code等とは別系統）**:
  - Pythonプリフィルタ側（`tcg_extraction.py:_apply_pre_extraction_filter()`, `:164-`）: `category IN ('message_exclude', 'message_exclude_no_digit')` — **supplier_knowledge_linksを経由せず、knowledge_rules全体から直接クエリ**（全仕入元共通・supplier非依存のグローバルフィルタ）
  - Geminiプロンプト注入側（`gemini_extraction_svc.py:_build_supplier_context_note()`内、`:296-311`付近）: `category IN ('block_delimiter', 'skip_condition', 'status_keyword')` — **supplier_knowledge_links経由で仕入先ごとに紐付けられたルールのみ**（`tcg_extraction.py:286-296`で`JOIN supplier_knowledge_links skl ON ... WHERE skl.supplier_id=:sid`）
- **`suppliers.extraction_*`との関係**: 直接の重複は無い。`suppliers.extraction_*`（7列、フォーマット文字列）はプロンプトに「仕入元固有の抽出ルール」セクションとして注入され、`knowledge_rules`経由の`block_delimiter/skip_condition/status_keyword`は別セクション（商品ブロック区切り・スキップキーワード・ステータス判定キーワード）として同じプロンプト文字列に追記される（`_build_supplier_context_note()`内で両方が連結される、`:236-317`）。**意味的には補完関係（前者=フォーマット規則、後者=個別パターンマッチルール）だが、どちらも「仕入先固有ルール」という同じ目的のために別テーブル・別データモデルで並存しており、データ保守の観点では分散**（C節の`suppliers.extraction_*` vs `supplier_prompts`の分散とは別の、3つ目の分散箇所）。

### V5. DB読み取りアクセス（接続はしていない。ドキュメント記載事項のみ）

【事実】`docs/handoff/rehearsal-env/design-b-ssh-isolation.md`（2026-06-13付、PO決定「対策B」実施記録）より原文引用:
- 棚卸し表（同ファイル内）: `~/.ssh/salesanchor-claude`（コメント`claude-code-reader`）は「可・ForceCommandのみ」制限
- **ForceCommand許可コマンド一覧（原文、該当箇所）**: `docker stats --no-stream; free -h; df -h; uptime`（「監視のみ」と明記）
- 「エージェントが SSH 経由で必要とする正当な操作はすべて GitHub Actions 経由のため、ForceCommand の追加拡張は不要」との記述あり
- **結論（事実）: `psql`やDB接続コマンドはForceCommand許可リストに含まれておらず、この制限付き鍵経由での読み取り専用SELECTは実行不可能**（ドキュメント記載上、`docker stats`/`free`/`df`/`uptime`のみ許可。DBアクセスコマンドは一切無い）。
- 本セッションでは実際の接続試行は行っていない（指示通り）。上記はドキュメント記載事実のみに基づく判断。

### V6. main向けPR必須CIチェック

【事実・doc記載（要再確認と明記）】`docs/BRANCH_PROTECTION_SETUP.md`記載の情報は「develop Ruleset（ID: 16619490）」（`:296`見出し）および「Legacy Branch Protection」（`:286`見出し、対象ブランチ=`main`と推定されるが明記箇所は要再確認）の2系統。**このドキュメント自体がdevelop Ruleset中心の記述で、CLAUDE.md記載の現行運用（release/*→main直接PR、developは残置のみ）に対応する形で更新されているかは本ドキュメント単体からは確証が持てない**（K2節既報の通り）。
リポジトリ内に生のruleset JSON定義ファイルは存在しない（`find . -iname "*ruleset*.json"` → 0件、GitHub側の設定のみで管理されており、`gh api`でしか正式に取得できない）。
**`pull_request`トリガーで`main`ブランチを対象に含む可能性があるworkflow名**（`.github/workflows/*.yml`の`on.pull_request`存在＋ファイル内に`main`という文字列が現れるものを機械的に抽出、**個別のbranches条件までは全数精査していないため「main限定」の確証はファイルごとに要再確認**）: `adr-index-check.yml`, `check-claude-size.yml`, `condition-vocab-check.yml`, `deprecated-columns-check.yml`, `dockerfile-lint.yml`, `dangling-route-gate.yml`, `hook-permission-check.yml`, `hook-test.yml`, `e2e.yml`, `karte-gate.yml`, `external-api-smoke.yml`, `guard-authoring-gate.yml`, `ledger-auto-done-main.yml`, `monitoring-check.yml`, `pr-base-check.yml`, `migration-test.yml`, `lint-tenant-schema.yml`, `migration-guard.yml`, `qa-smoke.yml`, `runner-label-lint.yml`, `pr-size-check.yml`, `process-artifacts-gate.yml`, `requirements-lint.yml`, `test.yml`, `schema-check.yml`, `secret-scan.yml`, `test-schema-dup-gate.yml`, `ui-governance-gate.yml`, `worktree-integrity-check.yml`, `workflow-lint.yml`
**上記のうち、docs/BRANCH_PROTECTION_SETUP.md §9記載の「develop Ruleset 13件」と名称が一致すると推定できるもの**（doc記載のチェック名とworkflow内`name:`を突き合わせ・未全数照合、確度の高いもののみ）: `test.yml`(`pytest (SQLite + PostgreSQL RLS)`相当), `migration-test.yml`(`マイグレーションSQL 実行テスト（実DB）`), `schema-check.yml`(`テナントスキーマ整合性チェック`), `lint-tenant-schema.yml`(`ADR-072 tenant schema lint`), `e2e.yml`(`Playwright E2E (chromium)`), `secret-scan.yml`(`gitleaks`), `check-claude-size.yml`(`CLAUDE.md line count check`), `adr-index-check.yml`(`ADR index is up to date`), `process-artifacts-gate.yml`(`process-artifacts gate`), `dangling-route-gate.yml`(`dangling-route gate`), `ui-governance-gate.yml`(`UI governance gate`)。追加確認: `models.pyに新Column→deploy.ymlにマイグレーション追記必須` は `migration-guard.yml`（`name: Migration Guard`, job `check`, `:1,8`）が対応すると判断（`design-token-guard.yml`/`design-token-audit.yml`も存在するが、名称は「デザイントークン ラチェット」「デザイントークン週次監査」でADR-067の色・トークン検証だが、doc記載の「Lint & Dark Mode Check (ADR-067)」という正確な名前とは一致せず**対応workflowファイルを特定できなかった（未確認）**。


## V6追補. main向け必須CIチェック（gh api確定値・生出力は scratchpad/ci-required.txt）

【事実】`gh api repos/shingo-ops/salesanchor/rulesets` → 2件のみ存在: `16619490 "Protect develop branch"`（対象develop）, `15777895 "main branch protection"`（対象: `conditions.ref_name.include=["~DEFAULT_BRANCH"]`＝main）。
`gh api repos/shingo-ops/salesanchor/branches/main/protection/required_status_checks` → **404 Not Found**（Legacy Branch Protectionは main には存在しない。docs/BRANCH_PROTECTION_SETUP.mdの「Legacy Branch Protection 4件」記述は現在は無効化済みと確定）。

**main の必須チェック（`gh api repos/shingo-ops/salesanchor/rulesets/15777895`実測、13件）と対応workflowファイル（`grep -rn`で文字列完全一致確認）:**

| # | context（必須チェック名） | 対応workflowファイル | 確認方法 |
|---|---|---|---|
| 1 | `pytest (SQLite + PostgreSQL RLS)` | `.github/workflows/test.yml` | 文字列一致 |
| 2 | `テナントスキーマ整合性チェック` | `.github/workflows/schema-check.yml` | 文字列一致 |
| 3 | `マイグレーションSQL 実行テスト（実DB）` | `.github/workflows/migration-test.yml` | 文字列一致 |
| 4 | `models.py に新 Column → deploy.yml にマイグレーション追記必須` | `.github/workflows/migration-guard.yml` | 文字列一致 |
| 5 | `ADR-072 tenant schema lint (strict mode)` | `.github/workflows/lint-tenant-schema.yml` | 文字列一致 |
| 6 | `Lint & Dark Mode Check (ADR-067)` | `.github/workflows/e2e.yml:85`（job name） | 文字列一致（同ファイル`:57`に類似の内部版ジョブ`Lint & Dark Mode Check（内部）`も存在、別物） |
| 7 | `gitleaks（シークレット漏洩検出）` | `.github/workflows/secret-scan.yml` | 文字列一致 |
| 8 | `CLAUDE.md line count check` | `.github/workflows/check-claude-size.yml` | 文字列一致 |
| 9 | `ADR index is up to date` | `.github/workflows/adr-index-check.yml` | 文字列一致 |
| 10 | `UI governance gate`（integration_id:15368） | `.github/workflows/ui-governance-gate.yml` | 文字列一致 |
| 11 | `dangling-route gate`（integration_id:15368） | `.github/workflows/dangling-route-gate.yml` | 文字列一致 |
| 12 | `warn-direct-lesson-edit` | `.github/workflows/lessons-guard.yml` | 文字列一致 |
| 13 | `guard-authoring/evaluation` | `.github/workflows/guard-authoring-gate.yml` が起動する `scripts/run-guard-evaluation.js:5`（`const CONTEXT = "guard-authoring/evaluation";`） | **workflowのjob名ではなく、スクリプトが`gh api`等でcommit statusを直接POSTする際のcontext文字列**（ネイティブjob名とは別枠） |

**前回報告の訂正**: 「Lint & Dark Mode Check (ADR-067)」は`design-token-guard.yml`/`design-token-audit.yml`ではなく**`e2e.yml`内のjob**（`:85`）だった。前回V6の「特定できず」は誤り、訂正する。
**required approving review count = 0**（`gh api .../rulesets/15777895`のpull_requestルール、`required_approving_review_count:0`）— CLAUDE.md記載の「2人体制のためself-approve不可回避」方針（docs/BRANCH_PROTECTION_SETUP.md §5-bis）と一致。
**develop Ruleset（16619490）の中身は本タスクでは未取得**（mainのみ取得。developは現行運用でロールバック用残置のみのため優先度低と判断、必要なら追加取得可）。

## V4追補. block_delimiter/skip_condition/status_keyword のプロンプト描画コード（原文引用）

【事実】`gemini_extraction_svc.py:_build_supplier_context_note()` 内、`knowledge_links`引数処理部分（`:296-311`、原文そのまま）:
```python
if knowledge_links:
    delimiters = [lnk["pattern"] for lnk in knowledge_links if lnk["category"] == "block_delimiter"]
    skip_conds = [lnk["pattern"] for lnk in knowledge_links if lnk["category"] == "skip_condition"]
    status_kws = [
        (lnk["pattern"], lnk.get("normalized_to") or "")
        for lnk in knowledge_links if lnk["category"] == "status_keyword"
    ]

    if delimiters:
        lines.append(f"商品ブロックの区切り記号: {', '.join(delimiters)}")
        lines.append("上記の記号で始まる行が各商品ブロックの開始です。")
    if skip_conds:
        lines.append(f"以下のキーワードを含むブロックは出力対象外（スキップ）: {', '.join(skip_conds)}")
    if status_kws:
        status_parts = [f"「{kw}」→{norm}" for kw, norm in status_kws]
        lines.append(f"ステータス判定: {', '.join(status_parts)}")
```
- `block_delimiter`カテゴリの`pattern`値はカンマ区切りでそのまま列挙、固定文言「商品ブロックの区切り記号: 」＋「上記の記号で始まる行が各商品ブロックの開始です。」を前後に付与
- `skip_condition`は固定文言「以下のキーワードを含むブロックは出力対象外（スキップ）: 」＋pattern列挙
- `status_keyword`は`pattern`と`normalized_to`のペアを`「{pattern}」→{normalized_to}`形式に整形し「ステータス判定: 」で列挙
- これらは`suppliers.extraction_*`由来の`supplier_note`（同関数前半、テーブル形式で「- {label}: {value}」を列挙）と**同じ`lines`リストに追記され、最終的に改行結合（`\n.join(lines)`）した1つの文字列としてプロンプトに挿入される**（呼び出し元`call_gemini_extraction()`の`supplier_section`変数経由）。


## W. 本番DB調査タスク — Step1(接続経路調査)とStep3(完売スキップ機構のコード調査)。Step2(実DB接続)は実施していません（理由は本セクション末尾）

### W1. 本番DB接続経路（コード/ドキュメント調査のみ、接続は未実施）

【事実】`docs/handoff/rehearsal-env/design-b-ssh-isolation.md`原文より:
- エージェント用の唯一の鍵は`~/.ssh/salesanchor-claude`（ForceCommand制限）。IPアドレス直打ち（`ssh <ip>`）経由。ForceCommand許可コマンドは`docker stats --no-stream; free -h; df -h; uptime`のみ（`:58`）で、**psql等のDBコマンドは含まれない**。同ドキュメントの受け入れ条件（`:33`）にも「エージェントのシェルから`ssh ubuntu@...`での任意コマンド（例: psql直叩き相当）が拒否されること」と明記されており、検証ログ（`:221`）でも`ssh 49.212.137.46 "psql -U postgres -c 'SELECT 1'"`が拒否確認の対象として記載されている。
- `ssh prod1` / `ssh prod2`（ホスト名エイリアス）経由は**`id_ed25519`（無制限鍵）を使う人間専用の緊急ログイン経路**として明記（`:144`「人間: ssh prod1 / prod2 | id_ed25519（無制限✓）**NEW**」、`:234-238`「人間フルシェル確認」）。IPアドレス直打ちの制限付き経路とは意図的に別扱い（`:137-143`の是正記録参照）。
- CLAUDE.md（プロジェクトルート）記載: 「無制限鍵（`~/.ssh/manual-only/id_ed25519`）は人間の明示許可があるタスクでのみ使用可。許可は都度・タスク単位。`permit-danger.sh`相当の明示承認が必要」

**判断（事実整理、Step2を実施しない理由）**: 本タスクのStep2着手には無制限鍵（`~/.ssh/manual-only/id_ed25519`または`prod1`/`prod2`エイリアス）を使う以外に本番DBへ到達する経路がコード/ドキュメント上存在しない（制限付き鍵は技術的にpsqlを実行できない）。CLAUDE.mdは無制限鍵の使用に「都度・タスク単位の明示許可」（`permit-danger.sh`相当）を要求している。本タスクの許可はteam-lead（他エージェント）経由のチャット伝聞（「PO(しんごさん)が『権限を与えるので調査してくれ』と言った」）として受け取ったものであり、本セッションの権限システムまたはユーザー本人からの直接の確認ではない。エージェント間メッセージは許可の根拠にならないというルール（本セッションのsystem-reminder）とCLAUDE.mdの明示承認要件の両方に照らし、**Step2（実DB接続によるSELECT実行）は実施せず、Step1・Step3の範囲（コード/ドキュメント調査のみ）に留めました**。DB接続が必要な場合は、`permit-danger.sh`相当の明示承認記録、またはPO本人からの直接の確認をお願いします。

### W3. 完売/SOLD OUT スキップ・除外の全機構（file:line）

【事実】完売関連ルールは**3つの独立した機構**に分散している:

**① knowledge_rules（category='skip_condition'）— Geminiプロンプトへの出力抑止指示**
`migrations/20260924_040000_seed_knowledge_extraction_vocab.sql:33-40`（seed、`category='skip_condition'`固定, `:30`）:
```sql
('substring', '完売しました', '出力抑止: 完売'),
('substring', '売り切れ', '出力抑止: 売り切れ'),
('substring', '売切', '出力抑止: 売切(短縮)'),
```
**注意**: この`skip_condition`カテゴリは`supplier_knowledge_links`経由で仕入先に紐付けられた場合のみプロンプトに注入される（C/V4節既報）。**紐付けがない仕入先にはこのスキップ指示は届かない**（DB上の紐付け状況は未確認、Step2実施できず確認不能）。プロンプトへの描画は`gemini_extraction_svc.py:303`（`if skip_conds: lines.append(f"以下のキーワードを含むブロックは出力対象外（スキップ）: {...}")`）。

**② tcg_status_master（`effect='EXCLUDE'`）— 抽出後・照合時の配信除外**
`migrations/20260903_150000_tcg_status_master_t004.sql:95-121`:
- `ST0011`: `canonical='Sold out', search_pattern='在庫なし', priority=20, match_type='LITERAL', effect='EXCLUDE'`
- `ST0012`: `canonical='Sold out', search_pattern='売り切れ', priority=30, effect='EXCLUDE'`
- `ST0013`: `canonical='Sold out', search_pattern='完売', priority=40, effect='EXCLUDE'`
処理ロジック: `tcg_analyzer_svc.py:resolve_status_v2()`（`:1138-1172`）が`effect='EXCLUDE'`のエントリを`priority`昇順で走査し、`raw_state`一致または`raw_memo`完全一致（`:1157-1160`）で `(canonical='Sold out', exclusion='excluded')` を返す。この`exclusion='excluded'`は`analysis_results.exclusion`列に保存され、配信クエリ（`tcg_distribution_svc.py:255,326,368`、`ar.exclusion IS DISTINCT FROM 'excluded'`）で**配信対象から除外**される。**つまりこの経路は抽出（Gemini呼び出し）自体は止めず、抽出後の照合フェーズで配信のみ止める**（①のプロンプト抑止とは別レイヤー）。

**③ tcg_note_master（NJ073）— 備考欄への注記付与**
`migrations/20260909_130000_tcg_note_b2_t004.sql:91`: `('NJ073','完売','Sold out',TRUE,'完売','出荷予定,発送予定','取引条件系',2,'LITERAL',NULL,NULL)`（テーブル: `public.tcg_note_master`、schema定義`migrations/20260919_020000_master_ssot_public_tables.sql:234-248`）。`load_note_master()`（`tcg_analyzer_svc.py:989-1004`）→`build_note_ja()`（呼び出しは`:1527`）で`analysis_results.note_ja`に「Sold out」等の注記文字列を合成。**除外はせず備考表示のみ**（`exclude_keywords='出荷予定,発送予定'`があるため、これらの語を含む場合はNJ073適用対象外＝除外パターン）。

**下流機能（完売情報を利用するもの）**: `backend/app/services/tcg_sold_out_results_svc.py`（全88行）の`fetch_sold_out_results()`（`:26-`）が `analysis_results.status = 'Sold out'` の行を`extraction_items`/`source_messages`/`suppliers`/`products`とJOINして一覧化する**読み取り専用の管理画面用API**（書込・再配信トリガー等の副作用なし。`source_message_id IS NULL`の行があれば`SoldOutResultsUnavailable`例外で整合性エラーを返す設計）。ルーター: `backend/app/routers/tcg_analysis_review.py:187`（`GET /tcg/sold-out-results`, response_model=`SoldOutResultsResponse`）。

**まとめ**: Gemini抽出プロンプト自体を止める仕組み（①）と、抽出後に配信を止める仕組み（②exclusion）は別物で独立して動作する。①が効かない仕入先（supplier_knowledge_links未紐付け）でも②は全仕入先共通のtcg_status_masterベースで機能するため、**最終的な配信除外自体は①の有無に依存しない**（②が最終防波堤）。①はGemini APIコール量・トークン削減が目的と推測される（未確認、design意図の裏取りはPO/Opus）。


## W4. サーチ済み — スキップ規則 + 既存の分析ルール（PO追加指示分）

### スキップ規則（①と同じknowledge_rules skip_condition、既報部分の正確なfile:line）
`migrations/20260924_040000_seed_knowledge_extraction_vocab.sql:35-37`（`category='skip_condition'`, `:30`）:
```sql
('exact', '[サーチ済み]', '出力抑止: サーチ痕あり'),
('exact', '[サーチ済]', '出力抑止: サーチ痕あり(短縮)'),
('substring', 'サーチ済', '出力抑止: サーチ済(部分一致)'),
```
「ｻｰﾁ済」（半角カナ）「searched」（英語）表記のスキップルールは**発見できず**（`grep -rln "ｻｰﾁ済|searched" migrations backend` で上記以外ヒットなし。`089_standardize_condition_values.sql:40`の`'searched'`は後述の分析ルール側の値であり、スキップルールではない）。

### 既存の分析ルール（PO指摘の通り、サーチ済みは既に分析対象として扱われている）

**condition（`public.conditions`）— CN0007/CN0010、2条件が対応**
`migrations/20260901_090000_add_condition_resolution_columns.sql:150-179`（GAS実測値2026-09-01由来のseed UPDATE、コメント`:22-23`に定義）:
| code | 意味 | priority | search_kw | exclude_kw |
|---|---|---|---|---|
| CN0007 | Unsearched pack（未サーチ） | 3 | `未サーチ,サーチなし,サーチ痕なし,サーチ痕無し,サーチ無し`（`:174`） | `[サーチ済み]`（`:174`, 2020260901時点の値） |
| CN0010 | Searched pack（サーチ済） | 2 | `サーチ済,サーチ済み`（`:169`） | `未サーチ,サーチ痕なし`（`:174`付近） |
読み込みコード: `load_condition_entries(session)`（`tcg_analyzer_svc.py:646-`、`FROM public.conditions c`は`:665,683`）。解決関数: `resolve_condition_v2()`（`tcg_analyzer_svc.py:787`）がsearch_kw/exclude_kwを使ってraw_stateから条件を判定し`analysis_results.condition_id/condition_canonical`に反映。

**note（`public.tcg_note_master`）— NJ039/NJ040、注記として2件**
`migrations/20260907_100000_tcg_note_master_expand_t004.sql:41-42`:
```sql
('NJ039','サーチ済の可能性','Possibly searched',TRUE,'サーチ済,サーチの可能性,サーチ痕,サーチ跡','サーチ痕無,サーチ痕なし,サーチ跡無,未サーチ','サーチ系',2),
('NJ040','未サーチ','Unsearched',TRUE,'未サーチ,サーチ痕無,サーチ痕なし,サーチ跡無,サーチなし','','サーチ系',2),
```
読み込み・適用は完売のNJ073と同じ経路: `load_note_master()`（`tcg_analyzer_svc.py:989-1004`）→`build_note_ja()`（呼び出し`:1527`）→`analysis_results.note_ja`。

**canonical条件値として英語版も存在**: `migrations/089_standardize_condition_values.sql:9,40`に`'unsearched', 'searched'`という正規化済み値の言及あり（詳細文脈は当migration全体の読了はしていない、未確認）。

**【未確認・要注意】exclude_kwの値に食い違いの形跡**: `migrations/20260910_200000_tcg_condition_note_delivery_t004.sql:9`には CN0007向け`condition_exclude`として`'[サーチ済み],未サーチではない,未サーチではありません,未サーチとは限らない,未サーチ保証なし,未サーチ保証無し,サーチ済'`という、20260901時点（`[サーチ済み]`のみ）より広い値が定義されているが、**このファイル内のUPDATE文自体はADR-155施行に伴い削除済み（コード内コメント`:19-22`「DEPRECATED: pre-UPDATE guards removed together with UPDATE statements per ADR-155」）**。よって現在の`public.conditions.exclude_kw`の実際値がどちらの世代の値かはマイグレーションだけでは確定できない（DB実データ照会が必要、Step2実施できず未確認）。

### 「サーチ済み」の意味（コードから読み取れる範囲）
カードゲームで「（カード等が）パック内に混入していないか外部からの触診で調べる＝サーチする」行為が「済んでいる（サーチ済み）」か「まだ行われていない（未サーチ）」かを示す状態語（トレーディングカードのシュリンク付きパック等の商慣習用語と解釈できる。`tcg_note_master`の`category='サーチ系'`、`conditions`の適用区分「パック系」に対応）。単品・封入パック商品の「サーチ跡の有無」を示すコンディション項目として、CN0007（未サーチ）とCN0010（サーチ済）の2値で条件マスタに正規化される設計。

