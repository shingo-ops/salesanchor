# recon: 試運転（shadow）の画面・API・書き込みの経路を外す（段1a）

- 基準: origin/main = 3c451d5e01138b6c52aa149693442f0a34d3eb3b（worktree 作成時点。`git rev-parse HEAD`）
- 設計: [design.md](design.md)
- 本番の事実の出典: リポジトリ外の記録（~/CC報告ファイル-keep/review-page-20261013/recon-facts.md） の A・B 節（本店コードの基準は dbef8b19。今回の洗い出しは 3c451d5e0 で再実施）

## 1. 既存 ADR の検索結果

- `git grep -i shadow origin/main -- docs/adr` : 試運転の画面・API を決めた ADR は 0 件。
- 触れているのは `docs/adr/ADR-1004-llm-usage-ledger.md:16,25,26,28,30,48` のみ（費用の台帳。`extraction_shadow_runs` の token/cost 列は残置、表の DROP は別途 PO 本人の GO が必要 :28）。
- `docs/adr/FEATURE-INDEX.md` に shadow / accuracy-management-v7 の項目は 0 件。
- 他の ADR の shadow は box-shadow（見た目の影）で無関係（ADR-054:232、ADR-057:20、ADR-073:48）。

## 2. 外した対象（file:line は origin/main 3c451d5e0 時点）

backend
- backend/app/routers/tcg_shadow_review.py 全体（GET /tcg/shadow-results、/bottlenecks、POST /keyword-preview）
- backend/app/services/tcg_shadow_review_svc.py 全体
- backend/app/routers/tcg_shadow_accuracy.py 全体（/tcg/shadow-accuracy/summary, /posts, /posts/{id}）
- backend/app/services/tcg_shadow_accuracy_svc.py・backend/app/services/shadow_accuracy_signals.py 全体
- backend/app/services/extraction_shadow_svc.py 全体（表への INSERT・run_shadow_for_job・has_required_supplier_rule）。ただし `load_product_entries` は移した（§3）
- backend/app/tools/shadow_backfill.py 全体
- `backend/app/main.py:126-127`（import）・`:703-710`（include_router 2件）
- `backend/app/tasks/tcg_extraction.py:31`（import）・`:615-640`（EXTRACTION_SHADOW_ENABLED=="1" のときの呼び出し）
- `docker-compose.yml:215`（`EXTRACTION_SHADOW_ENABLED=${EXTRACTION_SHADOW_ENABLED:-0}`。本番 celery-worker の値は 0）
- 試験: test_extraction_shadow_svc.py・test_extraction_shadow_tables_pg.py・test_shadow_backfill.py・test_tcg_extraction_shadow_skip.py・test_tcg_shadow_accuracy.py・test_tcg_shadow_accuracy_pg.py・test_tcg_shadow_review.py・test_tcg_shadow_review_pg.py・test_tcg_shadow_review_svc.py を削除。test_tcg_gemini_extraction.py の shadow の 3 試験と補助関数、test_line_analysis_v102_svc.py:330-331 の shadow の設定を削除

frontend
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx` の shadow・詰まり部分（タブ・state・effect・列・Modal・型）。タブは「本番の確認待ち」「投稿」の 2 つに
- `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.test.tsx` の shadow・詰まりの試験（2 件）。代わりに「タブが 2 つだけ」の試験を追加
- `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:24,165`（ShadowAccuracyPanel）、`frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:14,88`（accuracy-management-v7）
- ShadowAccuracyPanel.tsx/.css/.test.tsx・ShadowAccuracyPosts.tsx・ShadowAccuracySummary.tsx・shadowAccuracyTypes.ts 全体
- frontend/src/locales/{ja,en}.json: `shadowReview.*` 全体、`needsReview.tabs.shadow/bottlenecks`、`analysisRules.sidebar.accuracyManagementV7`、`shadowAccuracy.*`（`source` 以外）
- `frontend/api-contract/openapi.json`: 外した 6 API を再生成で除去

## 3. 残すもの（意図して残した参照）と理由

| 残した参照 | 理由 |
|---|---|
| `load_product_entries` | 本番 v102 が使う（`backend/app/services/gemini_raw_copy_v102_product_first.py:306`）。中身を変えずに同ファイルへ移した（旧 extraction_shadow_svc.py:86）。試験の差し替え（`pf.load_product_entries` の monkeypatch）は同じ名前で通る |
| `llm_usage_events` と列 `extraction_shadow_run_id`、`backend/app/services/llm_budget.py:154-326`、purpose `line_extraction_shadow` | 費用の台帳（345 行）。ADR-1004。FK なし |
| `frontend/src/pages/super-admin/components/LlmUsageSection.tsx:152` と locales の `line_extraction_shadow` | 台帳の表示 |
| `backend/app/tools/prompt_ab.py` | 試験の道具。表 `extraction_shadow_runs` を読む SQL（旧 :104-108）だけ `extraction_jobs` に変えた（§4） |
| `backend/app/services/gemini_extraction_svc.py` の `call_gemini_raw_copy`・`parse_raw_copy_response`、`tcg_work_reference.RAW_COPY_PROMPT_VERSION` | `backend/app/tools/prompt_ab.py:41-43` が v7 設定で使う。設計に外す指定が無い |
| ShadowSourcePane.tsx/.css/.test.tsx と locales `shadowAccuracy.source.*` | 「投稿」タブの V102PostEditModal（`frontend/src/features/tcg-analysis-review/V102PostEditModal.tsx:18,229`）が使う |
| 「投稿」タブ・`tcg_v102_posts` | 設計 §3 |
| `POST /tcg/products/{id}/search-keywords`（`backend/app/routers/tcg_product_master.py:251`）・`/exclude-keywords`（:280） | 商品マスタ Drawer（ProductMasterDrawer.tsx:302）が使う |
| 表 `extraction_shadow_results`・`extraction_shadow_runs` と migration `20260928_110000`、`scripts/run_all_migrations.sh:843`、`.github/workflows/migration-test.yml`・`.github/workflows/migration-guard.yml`、`scripts/migration-guard/dryrun-exclusions.tsv:38` | 段1b（GO の後） |
| `backend/app/services/tcg_work_reference.py:20`・`backend/app/services/gemini_extraction_svc.py:144,462,686` のコメントの「試運転」の語 | 関数は prompt_ab が使う。コメントの修正は設計外 |
| docs/ 配下の過去の設計・調査 | 履歴 |

## 4. prompt_ab.py の扱い

- 旧: `--runs-file` に `extraction_shadow_runs.id` を並べ、`_JOB_IDS_SQL`（旧 :104-108）で run id → `extraction_job_id` を引いた。
- 新: `--runs-file` に `extraction_jobs.id` を並べ、同じ関数 `fetch_job_ids` が `extraction_jobs` を読んで id をそのまま返す（SQL だけ変更）。
- 変えていないもの: 引数名 `--runs-file`、出力 JSONL のキー `run_id`・`job_id`（`run_id` には job id が入る）、台帳への書き込み（purpose `line_extraction_shadow`、source_ref `prompt_ab:<test_id>`）、試験（`fetch_job_ids` を monkeypatch しているため無修正で通る）。
- 影響: 過去の run id のファイルは使えなくなる（段1b で表が消えるため、いずれにせよ使えない）。

## 5. 本番の行数（調査の事実 A-4 より）

- extraction_shadow_runs 368 行・extraction_shadow_results 7063 行（最終書き込み 2026-10-01）
- llm_usage_events: line_extraction_shadow 4367 行（うち extraction_shadow_run_id 入り 345 行）
- EXTRACTION_SHADOW_ENABLED: celery-worker `printenv` = 0

## 6. 未確認

- 本番バンドルでタブが 2 つになること（デプロイ後に確認。段1a の PR ではコードのみ）
- 段1b（表の DROP）の前例・登録の扱い（`scripts/run_all_migrations.sh:843` は IF NOT EXISTS で再作成される）は、段1b の設計で調べる
- 本店 `/Users/tanizawashingo/salesanchor` の docs/ への参照切れ（docs 内のリンクで外したファイルを指すもの）は未走査

段1b 追加調査: /Users/tanizawashingo/CC報告ファイル-keep/review-page-20261013/drop-recon-1b-v2.md

## 7. 本番カタログ確認（2026-10-13 10:21 UTC）

- 実行: 設計者が prod1 jarvis_db に SELECT のみ。生出力: `/Users/tanizawashingo/CC報告ファイル-keep/review-page-20261013/drop-recon-1b-prod-catalog.txt`
- RLS: `extraction_shadow_runs`・`extraction_shadow_results` とも `relrowsecurity` = f、`relforcerowsecurity` = f
- policy: `pg_policies` 0件
- trigger: 8件すべて `tgisinternal` = t（`RI_ConstraintTrigger_*`＝FK が自動で作る内部 trigger）。人が作った trigger 0件
- FK: `extraction_shadow_runs_extraction_job_id_fkey`（→ extraction_jobs）、`extraction_shadow_results_run_id_fkey`（→ extraction_shadow_runs）、`extraction_shadow_results_product_id_fkey`（→ products）の3本のみ。外部からこの2表を参照する FK 0件
- view（`pg_rewrite` 経由の依存）: 0件
- 関数本文での参照: 0件
- 行数: extraction_shadow_runs 368 / extraction_shadow_results 7063
