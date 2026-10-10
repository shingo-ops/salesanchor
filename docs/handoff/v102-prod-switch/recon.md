# recon: 本番の LINE解析を試作版（v102：Gemini が原文を書き写し、システムが解析）へ切り替える

- 作成: 2026-10-09 Claude Opus（設計担当・ccopusgo）。調査は Sonnet に委任し、結果を Opus が統合。
- 状態: **recon（現在地の把握）のみ。設計・PO承認・実装は未着手。**
- 基準: origin/main `fb036a2388c2ac5bd53c0fc217c7c943efc54ff0`（2026-10-09T16:09:44+09:00）。
  - 調査 A〜C は `d88bc73b658fba309056f8b79e311c8aa574a900` で実施。以下に挙げた対象パス（backend の解析・配信・要確認・試作版・`docker-compose.yml`・`migrations/`・`docs/specs/line-analysis-tuning/README.md`・`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`）は d88bc73..fb036a2 で差が無いことを `git diff --stat` で確認済み。
- 社外秘: 指示書の本文・仕入元の原文は書かない（key 名・列名・件数のみ）。
- PO の依頼（2026-10-09）: 「本番の解析を、試作版（Gemini が原文抽出、システムが解析）に切り替える設計」。Gemini 抽出部分は Gemini 抽出担当セッションが受け持つ。配線と DB の SSOT 遵守・データ分散禁止、フロントはデザイントークン／デザインシステム遵守。

## 0. 既存の決定（PO 決定・ADR）

| # | 内容 | 根拠 |
|---|---|---|
| D1 | 本番の解析は v6。「今本番で動かしているものは触らない」 | docs/specs/line-analysis-tuning/README.md:17 |
| D2 | 切替順: 試作版のシステムの解析側を整備 → 本番を切り替える（PO 2026-10-07） | docs/specs/line-analysis-tuning/README.md:21 |
| D3 | f_c 合格の条件: 写した価格・数量が行の原文に無ければ要確認に回し理由を添える／人が直したらその場でその件を配信し直す仕組み／整数でない価格の書き方に対応 | docs/specs/line-analysis-tuning/README.md:58 |
| D4 | 新システムの結果は新表を作らず analysis_results に1本化 | docs/specs/line-analysis-tuning/README.md:60 |
| D5 | thinking_level は high | docs/specs/line-analysis-tuning/README.md:61 |
| D6 | 配信は needs_review=false の行に限定 | docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:70 |
| D7 | 商品単位の可視性は analysis_results.is_current で制御 | docs/adr/ADR-158-product-level-supersession.md:21-33 |
| D8 | LLM 費用は public.llm_usage_events に1応答1行、書込は record_usage_event に集約 | docs/adr/ADR-1004-llm-usage-ledger.md:25-29 |
| D9 | GO 委任（常時委譲・例外あり。DROP を含む migration 等は PO 本人の GO） | docs/adr/ADR-1003-go-delegation-to-opus.md:12-50、docs/handoff/go-record-transcription/opus-delegation.md:7-41 |
| D10 | Gemini の要確認も要確認ページに入れる。Gemini かシステムかが画面で見え、DB にも記録（PO 2026-10-09、Gemini 抽出担当セッション経由の引き継ぎ。正式文書への記載は未確認） | 引き継ぎ（社外秘・手元）§3 |

### 0-1. 本セッションでの PO 決定（2026-10-09、PO 原文）

| # | 対象 | PO 原文 |
|---|---|---|
| P1 | G7（直したら配信し直す） | 「工程ごとに用意、geminiの抽出を確認して修正したら→後工程のシステム解析に回して再開させる機能とシステム解析の要確認を確認して修正したら配信のリストに回して追加で配信する機能。」 |
| P2 | G6（理由コードの i18n と出どころ列） | 「合意」 |
| P3 | G5（出どころの持ち方） | 案「DB に理由コードの表を1つ作り、コードごとに出どころ（gemini/system）と画面の言葉を1行で持つ。analysis_results は今の review_reasons だけ（列を足さない）。新しいコードは必ずどちらか一方の出どころで登録する」に対し「合意、y」 |

- ADR 検索: `git grep -n -i -E 'v102|raw_copy|試作|analysis_results|needs_review|review_reasons|llm_usage|extraction_prompt_config' origin/main -- docs/adr/`。「本番の解析を新システムへ切り替える」決定を記した ADR は **0件**。docs/adr/FEATURE-INDEX.md で該当する行は :19（取り込み/解析/パイプライン → ADR-100 / ADR-014）のみ。

## 1. 本番（v6）の配線

1. 入口は LINE トーク書き出しファイルの手動取り込み API のみ: backend/app/routers/tcg_line_import.py:127 → backend/app/services/tcg_line_import_svc.py:511 import_line_export。重複判定 import_jobs.raw_sha256（同:566）。
2. source_messages INSERT（tcg_line_import_svc.py:431）、旧版は superseded_by＋is_active=FALSE（:451-462）、extraction_jobs を status='pending' で INSERT（:466）。
3. Celery: extract_source_message_task（backend/app/tasks/tcg_extraction.py:643）→ _run_extraction（:327）。
4. Gemini v6: extract_message（tcg_extraction.py:433）→ call_gemini_extraction（backend/app/services/gemini_extraction_svc.py:365）。指示書は _load_db_prompts（:92、key base_extraction / work_id_extraction :125-126）。版は WORK_ID_PROMPT_VERSION="raw-extraction-v6-rawcode-p1"（backend/app/services/tcg_work_reference.py:13）固定。v6/v7 の分岐はコードに無い。
5. モデル "gemini-3.1-flash-lite"（gemini_extraction_svc.py:283）、設定 {"temperature": 0}（:417）、thinking 指定なし。
6. extraction_items: 同じ job の既存行を DELETE（tcg_extraction.py:472-478、FK CASCADE で analysis_results も消える）→ INSERT（:486-526）。
7. TCG_AUTO_ANALYZE=1 のとき analyze_extraction_job（tcg_extraction.py:553-564 → backend/app/services/tcg_analyzer_svc.py:1205）。extraction_item 単位の UPSERT（:1593-1689）。最後に _merge_supplier_products（:1724 呼出、:1732-1830）で is_current を更新。
8. TCG_AUTO_DISTRIBUTE=1 のとき自動配信（tcg_extraction.py:566-569）。手動配信 backend/app/routers/tcg_distribution.py:169,181。
9. 試運転 v7（raw_copy_extraction）は EXTRACTION_SHADOW_ENABLED=1 のときのみ extraction_shadow_runs/results に書く（tcg_extraction.py:575-600）。analysis_results には書かない。
10. 既定値: docker-compose.yml:103,214 TCG_AUTO_ANALYZE `:-1`、:104,216 TCG_AUTO_DISTRIBUTE `:-0`、:215 EXTRACTION_SHADOW_ENABLED `:-0`。**本番 .env の実値は未確認。**
11. 停滞回収: backend/app/tasks/tcg_extraction_recovery.py:253（running 15分超→pending :76-96）。

### 1-1. extraction_items（migrations/20260921_110000_pipeline_tables_public.sql:93-109 ＋ migrations/20260926_010000_add_raw_product_code.sql:9）
id UUID PK / extraction_job_id UUID NOT NULL FK ON DELETE CASCADE / line_start, line_end INTEGER（1-based、gemini_extraction_svc.py:564）/ raw_product_name, raw_quantity, raw_price, raw_unit, raw_state, raw_memo TEXT / created_at / raw_work_name / raw_work_source_line_span / resolved_work_id INTEGER / resolved_product_code TEXT / raw_product_code TEXT。

### 1-2. analysis_results（migrations/20260921_110000_pipeline_tables_public.sql:214-243）
- extraction_item_id NOT NULL UNIQUE（:242）。product_id INTEGER REFERENCES public.products(id) NULL 可（:237）。unit_id INTEGER（:238）。condition_id INTEGER NOT NULL（:239）。work_id INTEGER（:240）。is_current BOOLEAN NOT NULL DEFAULT TRUE（:241）。pid_resolved / unit_resolved BOOLEAN NOT NULL。needs_review BOOLEAN NOT NULL。review_reasons TEXT（カンマ区切り）。engine_version NOT NULL。
- 変数名 product_uuid は名残で中身は整数（tcg_analyzer_svc.py:85, :1526, :1668）。
- engine_version の書込は1か所・1種類 "name-first-v9-product-all-terms"（tcg_analyzer_svc.py:58, :1684）。
- condition_id は resolve_condition_v2（:803-903）が必ず値を返す（未解決は FLAG_SINGLE CN0008 :902-903）。
- review_reasons は build_review_reasons（:1095-1109：pid_unresolved / multi_candidate / note_unmatched）＋empty_box 系（:1561-1567）、needs_review は :1582。
- price_normalized は _parse_numeric（:919-939）。数字以外を削って連結する実装のため、コード上「1.5万円」→1.5、「12,000円〜13,000円」→1200013000 になる（**コードの読解。実行での確認は未実施**）。

### 1-3. 要確認の判定（backend/app/services/tcg_condition_review_svc.py:139-178 review_joins）
- cr.needs_review = `cardinality(other_reasons) > 0 OR unknown_review OR empty_reason IS NOT NULL`（:165-166）。
- other_reasons は ar.review_reasons のカンマ分割＋派生（pid_unresolved / unit_unresolved / price_unresolved / excluded）。除外は空文字・EMPTY_REASONS・純肯定語メモの note_unmatched・条件が逆の派生コードのみ（:140-152）。
- **事実: ar.review_reasons に新しいコードを1つ入れれば cr.needs_review は真になり、配信から外れ（backend/app/services/tcg_distribution_svc.py:262）、要確認画面の本番タブに出る（backend/app/services/tcg_analysis_review_svc.py:78-81）。**

### 1-4. 配信（backend/app/services/tcg_distribution_svc.py）
- fetch_output_rows（:189）の条件（:260-270）: pid_resolved / is_current / cr.needs_review IS FALSE / exclusion IS DISTINCT FROM 'excluded' / unit_resolved / price_normalized IS NOT NULL / line_posted_at IS NOT NULL / FLAG_ 除外 / max_age_hours。
- 止め弁: analysis_runs 未完了（:696-715）、extraction_jobs に pending/running/extracted（:728-755）があれば中止。
- run_distribution の呼出は backend/app/routers/tcg_distribution.py:169,181、line_import_admin.py:163、tcg_extraction.py:699、自動 :566-569 の4系統のみ。

### 1-5. 人の訂正（「直したら配信し直す」）
- product_id 訂正: backend/app/routers/item_corrections.py:81 → item_corrections_svc.py:59-73（product_id / pid_basis='MANUAL' / pid_resolved=TRUE を UPDATE。needs_review・review_reasons・is_current は更新しない）。
- 状態の訂正: tcg_condition_review_svc.py:283-292（condition を UPDATE し needs_review/review_reasons を再計算）。
- 再解析: backend/app/routers/tcg_product_master.py:362 → tcg_product_master_svc.py:803 → analyze_extraction_job。
- **事実: どの訂正経路からも配信は呼ばれない。D3 の「直したらその場でその件を配信し直す仕組み」は現状存在しない。**

### 1-6. 要確認画面
- frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx（親 AnalysisRulesPage、frontend/src/App.tsx:330）。本番タブ GET /tcg/analysis-results?status_tab=NEEDS_REVIEW（backend/app/routers/tcg_analysis_review.py:104-136、require_super_admin）。
- 列: 商品名 / 仕入元 / 確認理由 / 日時（frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:326-368）。**出どころ（Gemini/システム）の列は無い。**
- 確認理由の表示（:337-354）: condition_review.review_reasons が空でなければ**カンマ区切り文字列をそのまま表示（i18n なし）**。空のときだけ review_issues の3種を needsReview.* キーで訳す。未知コードは生の文字列が出る。
- 金型: DataTable, Tabs, Modal, Select, TextField, Button, Card（:13-19）。i18n needsReview.* は ja.json / en.json のキー一致。
- API の gemini 辞書は extraction_items の raw_* 列、system 辞書は analysis_results / products / type_master（tcg_analysis_review_svc.py:258-286）。

### 1-7. 費用
- 本番解析は purpose="line_extraction" で記録（backend/app/services/tcg_extraction_record_svc.py:189, :228）。呼び出し例外時は記録しない（:225-226）。
- 単価 gemini-3.1-flash-lite 入力 $0.25/1M・出力 $1.50/1M（backend/app/services/llm_budget.py:76-80）。
- 予算判定 check_budget（llm_budget.py:401）の呼出は翻訳（message_translator.py:529,552,681）のみ。**本番 LINE解析には予算での自動停止が無い。**

## 2. 試作版（v102）の配線

1. 入口は CLI のみ: backend/app/tools/prompt_ab.py:710 main → :641 parse_args（--config v102 :644）→ :513 run_ab。v102 関連の import 元は prompt_ab.py・prompt_ab_recompute.py・tests のみ。routers / tasks / Celery からは 0件（調査C 02b_importers_all.txt）。
2. 入力: extraction_shadow_runs.id（--runs-file、prompt_ab.py:93-97, :643）→ load_extraction_context（backend/app/tasks/tcg_extraction.py:312、SQL :225-247。extraction_jobs × source_messages × supplier_channels × suppliers）。仕入元ルールは suppliers.extraction_layout_rules / extraction_hard_cases（tcg_extraction.py:241-242）、旧7欄は v102 で除外（prompt_ab.py:396-400, :696-697）。
3. 指示書: key raw_copy_v101_f_c（prompt_ab.py:333）を load_prompt_from_db（:346 定義、:361/:365）で public.extraction_prompt_config から読む。本番 v6/v7 の読み込み関数（gemini_extraction_svc.py:92 / :141）とは別。
4. Gemini: call_gemini_raw_copy_v8（backend/app/services/gemini_raw_copy_v8.py:182）＋ V102_RESPONSE_SCHEMA（backend/app/services/gemini_raw_copy_v101.py:64-87：items[{lines,price,quantity}]＋任意 unsure[{line,candidates}]）。thinking_level は CLI 引数（prompt_ab.py:647-648）、コード内の既定値なし。
5. システム解析: parse_v101_response（v101.py:187）→ extract_v101_items（:1177）→ _extract_v102（:1123）→ _extract_one（:810）→ resolve_product_first（backend/app/services/gemini_raw_copy_v102_product_first.py:470）、_apply_context_work（v101.py:1022）。価格・数量は resolve_price_quantity（backend/app/services/extraction_judgement_svc.py:599。小数・「万」対応 :374-487）。
6. 出力: JSONL（prompt_ab.py:607-613）。DB に書くのは費用台帳のみ（:615 record_usage_event_sync、purpose="line_extraction_shadow"）。
7. 1件の項目（v101.py:846-863）: product_id（整数 or None）, product_category, match_status, match_candidates, unit, unit_kubun, unit_basis, condition, condition_basis, status, status_effect, ship, price_normalized, quantity_normalized, price_line, lines, raw_price, raw_quantity, name, review, fixes ほか。
8. 要確認の理由コード（定義箇所）:
   - 件: item_shape_invalid / price_not_in_lines / duplicate_price_line（v101.py:169）、unit_unknown / category_unknown（:1048）、possible_footer_line / quantity_no_number（:1047）、heading_ship_with_own_ship（:1049）、product_not_in_master / product_multiple / condition_unknown / condition_multiple_candidates（v102_product_first.py:67-71）、迷う行 ship / condition（v101.py:473-485, :561）。
   - 投稿（post_review）: no_items / possible_missing_item（v101.py:1050）、response_unreadable（prompt_ab.py:299）、extract_exception（:309）。
   - Gemini: gemini_unsure / gemini_unsure_invalid（v101.py:229）。
   - **出どころ（source）の項目は無い**（grep 0件）。
9. 失敗時: 1件失敗で全体停止（prompt_ab.py:597-604）。マスタが空なら停止（v102_product_first.py:257-270）。
10. テスト: 試作版関連 11ファイル・`def test_` 394（調査C 07_tests.txt。実行はしていない）。

## 3. 本番に繋ぐときに欠けているもの（事実）

| # | 欠け | 根拠 |
|---|---|---|
| G1 | 本番入口（Celery タスクから v102 を呼ぶ経路）が無い | §2-1 |
| G2 | v102 の結果を extraction_items / analysis_results に書く経路が無い（JSONL のみ） | prompt_ab.py:607-615 |
| G3 | v102 の件（lines 配列・取り出し済みの値）と extraction_items（line_start/line_end・raw_*）の変換が無い。analysis_results.extraction_item_id は NOT NULL UNIQUE のため、v102 の件ごとに extraction_items の行が要る | §1-1, §1-2 |
| G4 | v102 が出さない analysis_results の値: pid_resolved, pid_basis, unit_id, unit_resolved, condition_id（NOT NULL）, note_ja, exclusion, needs_review, work_id, engine_version | §1-2, §2-7 |
| G5 | 出どころ（Gemini/システム）を DB に残す場所が無い。review_reasons はカンマ区切り TEXT 1列 | §1-2, §2-8 |
| G6 | 要確認画面が新しい理由コードを訳さず生表示。出どころ列なし | §1-6 |
| G7 | 人が直したら配信し直す仕組みが無い（D3 の条件未充足） | §1-5 |
| G8 | 本番 LINE解析に予算での自動停止が無い | §1-7 |
| G9 | 本番の版を切り替える手段（設定）が無い。v6 は定数固定 | §1-4 |
| G10 | v102 の失敗時の扱いが本番向けでない（全体停止・再試行なし） | §2-9 |
| G11 | v102 の thinking_level 等の推奨値をコードに固定する場所が無い（CLI 引数頼み） | §2-4 |

## 3-1. 訂正・やり直し・配信の部品（調査F、fb036a2）

- 理由コードのマスタ表は無い（migrations の CREATE TABLE で該当は close_reasons のみ、migrations/20260613_020000_funnel_close_reasons.sql:50）。理由コードの生成・訳は分散: backend/app/services/tcg_analyzer_svc.py:1095-1109, :1565-1567、backend/app/services/tcg_empty_box_rules.py:15、backend/app/services/tcg_condition_review_svc.py:139-168、backend/app/services/tcg_analysis_review_svc.py:116-137、frontend/src/locales/en.json:3814-3818（pmgWorkflow.reviewReason）, :3853-3860（conditionReview.reasons）、frontend/src/features/tcg-analysis-review/reviewIssues.ts:5-13、frontend/src/features/tcg-import-workflow/ImportWorkflowPanel.tsx:42。
- item_corrections（migrations/20260921_110000_pipeline_tables_public.sql:321）: field_name 自由文字列・1欄1行の追記（backend/app/services/item_corrections_svc.py:40-55）。副作用は product_id のみ（:59-73）。condition_review は専用経路（tcg_condition_review_svc.py:279-292）。
- **Gemini の抽出値（extraction_items.raw_*）を人が直す経路は無い**（backend/app 内に extraction_items の UPDATE が 0件）。frontend/src/features/tcg-analysis-review/ItemComparison.tsx:35 の保存ボタンは disabled 固定。
- 再解析 API: POST /api/v1/tcg/extraction-jobs/{id}/reanalyze（backend/app/routers/tcg_product_master.py:320-365 → backend/app/services/tcg_product_master_svc.py:634, :803）。job 単位、Gemini を呼ばず DB の raw_* から再計算、analysis_runs で退避と完了記録（:689-797）。
- 再抽出 API: POST /api/v1/tcg/diagnostics/retry-extraction（backend/app/routers/tcg_diagnostics.py:90-110 → backend/app/services/tcg_diagnostics_svc.py:146-252）。status='error' のみ、items DELETE → pending → Celery 再投入。
- 配信の書き方: **シートは毎回全置換**（worksheet.clear → append_rows、backend/app/services/tcg_distribution_svc.py:515-518、上限 5000 行）。行単位の配信済み記録・配信ログは無い（tcg_distribution_targets の last_* のみ、:660-673）。fetch_output_rows は状態ベースで毎回全件を選ぶので、**要確認が解けた件は次の run_distribution で自動的に入る**。差分追記の部品は無い。未完了の抽出ジョブが1件でもあると配信全体が中止（:727-753）。
- 投稿単位の要確認: extraction_jobs に確認状態の列は無い（migrations/20260921_110000_pipeline_tables_public.sql:80-90）。本番の要確認一覧は analysis_results 起点のため、件が無い投稿は載らない（tcg_analysis_review_svc.py:35, :77-80）。v102 の post_review は JSONL にのみ存在。
- 要確認画面の本番タブは読み取り専用（frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:326-368, :452-468、onRowClick なし）。訂正 UI は別画面 frontend/src/features/tcg-analysis-review/SupplierDetailView.tsx（ConditionReviewPanel・ProductMasterDrawer）。ProductMasterDrawer は生の input/textarea/button（frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:201-221, :470, :479。ui-allow の有無は未確認）。

## 3-2. 設計に必要な部品の事実（調査G、fb036a2）

- 全体設定表は public.tcg_distribution_settings（key/value、migrations/20260921_110000_pipeline_tables_public.sql:354-359）のみ。tenant_features はテナント単位（migrations/20260627_120000_add_tenant_features_table.sql:6-12）。既存の機能切替は環境変数（backend/app/tasks/tcg_extraction.py:553, :567, :579、タスク実行ごとに読む）。
- 環境変数の届き方: docker-compose.yml に env_file は無く、サービスの environment: に列挙した変数だけ届く（celery-worker :213-216, :237）。deploy.yml は secrets 由来の列挙キーだけ .env に書く（.github/workflows/deploy.yml:258-316）。列挙外の TCG_AUTO_* 等は VPS の .env を手で書く運用。**新しい変数（未使用の名前）は .env に無いので docker-compose.yml の既定値がそのまま効く。**
- 部品はすべて同期・sqlalchemy.orm.Session: load_extraction_context（tcg_extraction.py:312）、_load_v10_masters（backend/app/tools/prompt_ab.py:222-237）、load_product_first_masters（backend/app/services/gemini_raw_copy_v102_product_first.py:238-265）、call_gemini_raw_copy_v8（backend/app/services/gemini_raw_copy_v8.py:182-238、RuntimeError を投げる）、parse_v101_response（backend/app/services/gemini_raw_copy_v101.py:187-226、純粋関数）、extract_v101_items（:1177-1214、純粋関数）、_v102_row_fields（prompt_ab.py:285-310、例外を握りつぶす）。
- Gemini クライアントは本番と共通の gemini_extraction_svc._get_genai_client（backend/app/services/gemini_extraction_svc.py:262-274、GEMINI_API_KEY・GEMINI_PROXY_URL）。
- 列の対応: unit の canonical → load_lookup_maps()[2] で unit_id（backend/app/services/tcg_analyzer_svc.py:1401 と同式。prompt_ab.py:230 では捨てている）。condition は canonical のみで id は cond_entries / cond_canonical_to_uuid で引く（tcg_analyzer_svc.py:696-707, :136-144）。status / status_effect は resolve_status_v2 と同じ値の集合（入力は件の行の連結、v101.py:818, :838）。note_ja 相当は v102 に無い。work_id は products.work_id（tcg_analyzer_svc.py:1250-1253）。
- lines は昇順・重複なしだが飛び番あり得る（v101.py:106-121, :213）。複数の件で同じ行を共有し得る（:434）。line_start/line_end の2整数に潰すと情報が落ちる。
- analyzer は INSERT 後に E3a/E5/E3b/E4（tcg_analyzer_svc.py:1693-1719）、reanalysis_condition（:1569-1582）、_merge_supplier_products（:1724, :1732）を行う。空箱の上書き（:1538-1544）を v102 が再現しているかは未確認。
- engine_version を条件にしている読み取りは backend/app/services/tcg_parallel_report_svc.py:187（compat-v1、並行比較レポート）のみ。配信・要確認・在庫一覧は条件にしていない。
- デプロイ: main への push で deploy.yml 起動（:3-6）。celery-worker 再作成（:392-397）は migrations（:518）より前。成功判定は /api/health を最大180秒、失敗時は前の SHA へ自動で戻す。.env はロールバックで戻らない。
- CI: backend pytest は PostgreSQL 16 付き（.github/workflows/test.yml:121-144、*_pg.py も実行）。必須チェック13件（docs/BRANCH_PROTECTION_SETUP.md:298-314）。

## 4. 未確認（推測で埋めない）

| # | 項目 | 確かめ方 |
|---|---|---|
| U1 | 本番 .env の TCG_AUTO_ANALYZE / TCG_AUTO_DISTRIBUTE / EXTRACTION_SHADOW_ENABLED の実値 | 本番の読み取り。制限付き鍵（salesanchor-claude）は固定4コマンドのみで SQL・環境変数は読めない（2026-10-09 17:08 JST 実測、/tmp/CC報告ファイル/switch-recon-20261009/H/access-check.txt）。PO の SELECT 実行か permit-danger が必要 |
| U2 | 配信設定 max_age_hours / include_flag_single の実値 | 同上 |
| U3 | 1日の投稿数（費用見積もり用）: `SELECT (line_posted_at AT TIME ZONE 'Asia/Tokyo')::date, COUNT(*) FROM public.source_messages WHERE is_active AND line_posted_at IS NOT NULL GROUP BY 1 ORDER BY 1 DESC;`（未実行） | 同上 |
| U4 | tenant_004.analysis_results の本番残存（backend/app/routers/tcg_product_master.py:343-352 がスキーマ名直書きで INSERT） | 同上 |
| U5 | _parse_numeric の誤変換が本番データで実際に起きている件数 | 本番の読み取り or テスト実行 |
| U6 | D10（Gemini の要確認を要確認ページへ・出どころを DB に記録）と source の決め方（PO に y/n 伺い中と引き継ぎに記載）の確定状況 | Gemini 抽出担当セッション／PO |
| U7 | open PR は gh の取得で 115件。gh の files が 100件超の PR は切り詰めの可能性 | 実装カード作成時に再確認 |

## 5. 衝突の可能性

- 試作版ファイルを触る open PR: 0件（調査C 08_open_pr_hits.txt）。
- 本番側で接続時に触るファイルと重なる open PR: #3548（backend/app/tasks/tcg_extraction.py）、#3248（backend/app/services/tcg_analyzer_svc.py）。
- 試作版ファイルは複数セッションが直す（引き継ぎ §6）。結果の形を変える PR は先に相手のセッションへ伝える。

## 6. 生出力の保存先（手元・社外秘を含み得るためリポジトリに置かない）
/tmp/CC報告ファイル/switch-recon-20261009/{A,B,C,D,E}/

## 7. 便E 段1（origin/main 基準）
- LINE_ANALYSIS_ENGINE の参照: docker-compose.yml:218（celery-worker、`:-v6`）／backend/app/services/line_analysis_v102_svc.py:47,93-100（get_engine、未設定は v6）／backend/app/tasks/tcg_extraction.py:471／backend/tests/test_line_analysis_v102_svc.py:42-55,264,275,295,306。compose の既定値を検査するテスト・CI は無い。
- v102 の流れ: backend/app/tasks/tcg_extraction.py:471-472 → :439 _run_v102_extraction → :448-451 run_v102_analysis（TCG_AUTO_ANALYZE=1）→ backend/app/services/line_analysis_v102_svc.py:792 _merge_supplier_products（is_current）→ backend/app/tasks/tcg_extraction.py:456-458 _enqueue_auto_distribute（TCG_AUTO_DISTRIBUTE=1）。v6 は backend/app/tasks/tcg_extraction.py:593-609 で同じ条件。prompt_version は backend/app/services/line_analysis_v102_svc.py:384-387,130（`v102:<prompt_key>:<sha256先頭12>`）。GEMINI_API_KEY は backend/app/services/gemini_extraction_svc.py:262。

### Opus 確認 2026-10-10（本番・読み取り専用、生出力）
```
dir=/home/ubuntu/salesanchor
0            # .env の ^LINE_ANALYSIS_ENGINE の件数
ENGINE=v6 AUTO_ANALYZE=1 AUTO_DIST=1   # celery-worker の現在値
GEMINI_KEY=present
     prompt_key      | is_active | len  |          updated_at
 raw_copy_v101_f_c   | t         | 5321 | 2026-10-07 23:13:07.604272+00
```


## 8. 便PQ の recon 要点（社外秘の原文なし・件数のみ。詳細: /tmp/CC報告ファイル/v102-pq-recon/recon.md、基準 origin/main 853be509c）
- v102 は価格・数量を原文の目印から取り直す: backend/app/services/gemini_raw_copy_v101.py:854-874 → backend/app/services/extraction_judgement_svc.py:599 `resolve_price_quantity`。Gemini の写しは検算にだけ使う。
- 本番 1,079件で数字があるのに NULL: 数量 9件（うち6件は要確認にならず配信）、価格 4件。原因は (a) 1行に「個」付きの数が2つ（backend/app/services/extraction_judgement_svc.py:636-638 multiple_values）、(b) 行頭「■」の在庫行が商品名に入り `_mask_product_name`（backend/app/services/extraction_judgement_svc.py:526-538）で消える。
- resolve_price_quantity の reasons（price_reasons）を読む本番コードは 0件。数量 NULL を要確認にする理由が無い。
- 要確認の流れ: backend/app/services/line_analysis_v102_svc.py:559（理由があれば needs_review=True）→ backend/app/services/tcg_distribution_svc.py:262（配信から除外）。読み取り時の price_unresolved: backend/app/services/tcg_condition_review_svc.py:144・:151。
