# 実装カード 便B: v102 を本番の流れに組み込む（既定は v6・本番の挙動は変えない）

- 設計: [design.md](./design.md) §4-1・§4-2（extraction_items・extraction_jobs の列のみ）・§4-4・§4-5（再解析の振り分けのみ）・§5 便B
- recon: [recon.md](./recon.md)
- 発行: 2026-10-09 Claude Opus。PO の実装承認: 2026-10-09「PRマージ、デプロイまで完走させてくれ」
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-v102-prod-switch-design（ブランチ release/v102-prod-switch-design、origin/main 起点）。本店（~/salesanchor）では作業しない

## 0. 着手前（読むだけ。結果を報告に貼る）

1. worktree 内で `./scripts/dev/executor-preflight.sh || exit 1`。`git fetch origin && git rebase origin/main` は**しない**（作業開始時の起点のまま。必要なら止まって報告）。
2. 次を実物で確認し、file:line で報告に書く。**1つでもカードの前提と違えば、実装せずに NEEDS_DECISION で止まる**:
   - (a) `_v102_row_fields`（backend/app/tools/prompt_ab.py）が返す v102_items の各件が、Gemini の items の何番目に当たるかを**確実に**辿れるか。受理された件の順序・落とした件の gemini_index（gemini_raw_copy_v101.py の _rejected_row）・_extract_v102 の F1〜F5 や reassign で件が増減・合併・分割しないかを読んで判定する。辿れない場合は止まる。
   - (b) analyzer の resolve_condition_v2 が未解決のとき FLAG_SINGLE の id をどの関数で得ているか（tcg_analyzer_svc.py:803-903）。v102 の condition 文字列（'none'・'不明' を含む）から同じ方法で condition_id を得られるか。
   - (c) v102 が空箱（Empty box）を扱っているか（gemini_raw_copy_v102_product_first.py・gemini_raw_copy_v101.py で empty_box / 空箱 / CN0011 を grep）。扱っていなくても実装は続け、報告に事実を書く（足さない）。
   - (d) analyze_extraction_job（tcg_analyzer_svc.py:1205）の呼び出し元の全一覧（git grep）。
   - (e) _merge_supplier_products の引数と呼び方（tcg_analyzer_svc.py:1724, :1732）。
   - (f) 抽出タスクの時間制限（Celery の soft_time_limit / time_limit、celery_app.py と tasks/tcg_extraction.py）と、停滞回収の閾値（tcg_extraction_recovery.py の15分）。v102（thinking high）の1投稿の所要時間の実績が手元 JSONL（~/CC報告ファイル-keep/stage-*/ の elapsed_sec）にあれば最大値・中央値を集計して報告（本文は出さない）。
   - (g) record_usage_event_sync の引数（prompt_ab.py:615 の呼び方）と、purpose='line_extraction' が CHECK 集合にあること（llm_budget.py:162 付近）。
   - (h) 新 migration を本番で流す登録先: scripts/run_all_migrations.sh 末尾の「ここから追加」節の形式と、.github/workflows/migration-guard.yml のチェック1・2が今回の変更（models.py は触らない）で何を要求するか。

## 1. 変更内容（最終形）

### 1-1. migration（構造のみ。INSERT/UPDATE/DELETE を書かない＝ADR-1007）
新規 `migrations/20261009_180000_v102_engine_columns.sql`:
```sql
-- 便B（docs/handoff/v102-prod-switch/design.md §4-2）。構造のみ。値の操作は含めない（ADR-1007）。
ALTER TABLE public.extraction_items ADD COLUMN IF NOT EXISTS source_lines INTEGER[];
ALTER TABLE public.extraction_items ADD COLUMN IF NOT EXISTS gemini_index INTEGER;
ALTER TABLE public.extraction_jobs ADD COLUMN IF NOT EXISTS gemini_unsure JSONB;
ALTER TABLE public.extraction_jobs ADD COLUMN IF NOT EXISTS review_reasons TEXT;
COMMENT ON COLUMN public.extraction_items.source_lines IS 'v102: Gemini が書き写した原文の行番号（1始まり・昇順・飛び番あり）。v6 は NULL';
COMMENT ON COLUMN public.extraction_items.gemini_index IS 'v102: Gemini の items の順番（0始まり）。v6 は NULL';
COMMENT ON COLUMN public.extraction_jobs.gemini_unsure IS 'v102: Gemini の unsure 申告（応答のまま）。v6 は NULL';
COMMENT ON COLUMN public.extraction_jobs.review_reasons IS 'v102: 投稿単位の要確認の理由コード（カンマ区切り）。v6 は NULL';
```
タイムスタンプが既存と重なれば重ならない値にする。scripts/run_all_migrations.sh の「ここから追加」節の末尾に既存の形式で1行登録。

### 1-2. 新規 `backend/app/services/line_analysis_v102_svc.py`（v102 の本番部品の唯一の置き場）
- 定数（ここだけで定義）: `ENGINE_ENV = "LINE_ANALYSIS_ENGINE"`, `ENGINE_V6 = "v6"`, `ENGINE_V102 = "v102"`, `V102_ENGINE_VERSION = "v102-f_c"`, `V102_THINKING_LEVEL = "high"`, `V102_PROMPT_KEY`（prompt_ab.py:333 の V102_PROMPT の値をここへ移す）。
- `get_engine() -> str`: 環境変数を読み、`"v102"` のときだけ ENGINE_V102、それ以外（未設定・空・不明値）は ENGINE_V6。不明値は logger.warning。
- prompt_ab.py から**移す**（prompt_ab.py 側は同名で import し直し、prompt_ab_recompute.py・既存テストの参照が壊れないようにする。振る舞いは1文字も変えない）:
  - `load_prompt_from_db`、`V102_PROMPT`（＝V102_PROMPT_KEY の別名）
  - `_v102_row_fields` の本体 → `run_v102_pipeline(response_text, ctx, masters)`（prompt_ab の `_v102_row_fields` は run_v102_pipeline を呼ぶだけにする）
  - v102 で仕入元の旧7欄を外す処理（prompt_ab.py:396-400 付近）と、`_load_v10_masters(product_first=True)` 相当のマスタ読み込み。prompt_ab が捨てている unit_canonical_to_uuid（load_lookup_maps()[2]）も返せるようにする（prompt_ab の挙動は変えない）。
  - `_gemini_review` / `_with_gemini_review` 等、run_v102_pipeline が使う補助関数。
- `run_v102_extraction(session, extraction_job_id) -> dict`（Gemini 段）:
  1. load_extraction_context。指示書は load_prompt_from_db(V102_PROMPT_KEY)。prompt_version = `f"v102:{V102_PROMPT_KEY}:{sha256(prompt_text)[:12]}"`。
  2. call_gemini_raw_copy_v8(raw_text, prompt_text=…, supplier_context=旧7欄を外したもの, knowledge_links=ctx.knowledge_links, thinking_level=V102_THINKING_LEVEL, include_thoughts=True, use_schema=True, temperature=None, response_schema=V102_RESPONSE_SCHEMA, new_system_rules=ctx.new_system_rules)。値は prompt_ab の v102 試験（PO 採用 2026-10-08）と同じにする。
  3. 費用: record_usage_event_sync(purpose="line_extraction", source_ref=f"extraction_job:{id}", …)。応答を受けた後、保存の成否に関わらず1回。
  4. 保存: 同じ job の extraction_items を DELETE（既存 tcg_extraction.py:472-478 と同じ）→ 応答 JSON を読む。読めない／dict でない／items が list でない → 件なし、extraction_jobs.review_reasons='response_unreadable'。読めたら items の i 番目ごとに1行 INSERT: id=uuid4、gemini_index=i、source_lines=lines（整数のリストのときのみ、それ以外 NULL）、line_start/line_end=source_lines の min/max（NULL なら NULL）、raw_price=price（str のときそのまま、None は NULL、それ以外 json.dumps）、raw_quantity 同様。raw_product_name ほか他の raw_* は NULL。extraction_jobs.gemini_unsure=応答の unsure（キーが無ければ NULL）、prompt_version を更新。
  5. Gemini 呼び出しの例外は呼び出し元へ再送出（既存の status='error' の扱いに乗せる）。
- `run_v102_analysis(session, extraction_job_id) -> dict`（システム段。Gemini を呼ばない）:
  1. extraction_items を gemini_index 順に読み、`{"items":[{"lines":source_lines,"price":raw_price,"quantity":raw_quantity}…]}`（gemini_unsure が NULL でなければ `"unsure"` を付ける）を json.dumps(ensure_ascii=False) で組み立て、run_v102_pipeline に渡す。
  2. 0-(a) で確かめた対応で、v102 の各件を extraction_items の行へ対応付け、design §4-4 の表どおりに analysis_results を UPSERT（ON CONFLICT (extraction_item_id) DO UPDATE。列は analyzer の UPSERT と同じ集合）。review_reasons = 件の `review` の kind と `gemini_review` の kind を、出た順で重複なしにカンマ結合（空なら NULL・needs_review=FALSE）。note_ja=NULL。engine_version=V102_ENGINE_VERSION。condition_id は 0-(b) の方法。work_id は products.work_id。
  3. extraction_jobs.review_reasons = v102_flags の post_review の kind と、v102_flags の gemini_review の kind（gemini_unsure_invalid 等）を重複なしでカンマ結合（空なら NULL）。
  4. _merge_supplier_products を analyzer と同じ呼び方で呼ぶ（is_current、ADR-158）。
  5. run_v102_pipeline の例外、または対応付けの失敗は、extraction_jobs.review_reasons に 'extract_exception' を入れて logger.exception。件（extraction_items）は消さない。呼び出し元へは再送出しない。
  6. 戻り値は analyze_extraction_job と同じ形のキー（total / pid_resolved / unit_resolved / needs_review）。

### 1-3. 振り分け
- `backend/app/tasks/tcg_extraction.py` の抽出本体（`_run_recorded_extraction` 付近）: `get_engine() == ENGINE_V102` のとき、v6 の extract_message → extraction_items INSERT の代わりに run_v102_extraction、TCG_AUTO_ANALYZE=1 なら analyze_extraction_job の代わりに run_v102_analysis。status（done/empty/error）・試行の記録・自動配信（TCG_AUTO_DISTRIBUTE）・停滞回収は既存の流れに乗せる（件 0 なら empty）。v6 の分岐は1行も変えない。EXTRACTION_SHADOW_ENABLED（v7 試運転）は v6 のときだけ動かす。
- `analyze_extraction_job`（tcg_analyzer_svc.py:1205）の先頭: その job の prompt_version が `v102:` で始まるなら run_v102_analysis に委ねて結果を返す（関数内 import で循環を避ける）。これで再解析 API など全呼び出し元が投稿の記録で振り分けられる。
- `docker-compose.yml` の celery-worker の environment に `LINE_ANALYSIS_ENGINE: ${LINE_ANALYSIS_ENGINE:-v6}` を既存の TCG_AUTO_* の並びで1行。

### 1-4. テスト（Gemini は呼ばない。応答は手で作った架空の原文・架空の応答のみ。実在の仕入元データ・指示書本文を使わない）
- get_engine: 未設定・空・"v6"・"V102"・"x" → v6、"v102" → v102。
- K8: 同じ架空の応答で、prompt_ab._v102_row_fields の結果と run_v102_analysis が書いた analysis_results（product_id・pid_resolved・unit_canonical・condition_canonical・price_normalized・quantity_normalized・review_reasons）が一致（PostgreSQL テスト）。
- run_v102_extraction（Gemini をモック）: extraction_items に source_lines（飛び番）・gemini_index、extraction_jobs.prompt_version が `v102:` 始まり、llm_usage_events に purpose='line_extraction' が1行（K7）。
- 応答が読めない → 件 0・extraction_jobs.review_reasons='response_unreadable'。
- 要確認の件は fetch_output_rows に出ない（K3）。
- v102 の job の再解析（analyze_extraction_job）で v6 の処理が走らない。v6 の job は従来どおり。
- 既定（環境変数なし）で抽出タスクが v6 の経路を通る。
- 既存テスト（test_prompt_ab*.py・test_gemini_raw_copy_v10*.py ほか）が全部そのまま通る。

## 2. 触らない
v6 の判定ロジック、v7 試運転、試作版の判定ロジック（gemini_raw_copy_v101.py・gemini_raw_copy_v102_product_first.py・_context_work.py・_score_select.py の中身）、指示書（DB）、仕入元ルール、配信、要確認画面・API、frontend、deploy.yml、.github/workflows/。

## 3. 完了条件
- worktree 内で backend の pytest（PostgreSQL 付きの *_pg を含む。ローカルで PostgreSQL が無ければその事実を書く）を実行し、生出力の末尾を報告。
- commit（Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com> は付けない。git user のまま）→ push → `gh pr create --draft --base main`（テンプレート起点。`### 標準ワークフロー確認` に recon: docs/handoff/v102-prod-switch/recon.md、設計: docs/handoff/v102-prod-switch/design.md、対象ADR: ADR-154, ADR-158, ADR-1004, ADR-1007、触るファイル・削除するファイルは `git diff --name-only origin/main...HEAD` と `--numstat` の実測から平打ち）。docs/handoff/v102-prod-switch/ の recon.md・design.md・card-B.md も同じ PR に含める。PR 作成前に `gh auth status` が shingo-cc であること。
- GO記録は書かない（設計者が書く）。マージしない。CI の完了を待たない（PR の URL を報告して終わる）。
- 報告: カードの各項目の ○×、0 の事実（file:line）、テストの生出力、PR URL。最終行 DONE / BLOCKED: / NEEDS_DECISION:。

## 4. 止まる条件
フック・権限に止められた（言い換えず文面を貼って止まる）／0 の前提が違う／カードに無いファイルを触る必要／選択肢が2つ以上で決まらない／既存テストが落ちて原因がカードの範囲外。
