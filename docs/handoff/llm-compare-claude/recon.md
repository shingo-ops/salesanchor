# 解析AIを Claude Haiku・Sonnet に替えたときの精度比べ — recon

状態: 調査済み（2026-10-30、Opus 統括・担当 Sonnet が読み取り）。設計は design.md（同じフォルダ）。本番接続・本番変更なし。

## PO の依頼（原文）
- 「grok botに任せたり出来る？api料金を払うよりgrok botやcodexに任せたほうが精度が高くてコストも変わらないのであれば導入したい」
- 「3. 両方を順に設計する（1が先）」（段階1 = 精度比べ、段階2 = tenant001・tenant004 だけ読める入り口）
- 「codexを本採用するかは未定なのでまずはclaudeで精度が変化するか確認したい、haikuとsonnetにやらせてみて」
- 「使用したToken量も記録」
- 「geminiと同じ条件でやらせること、同条件での差分を確かめるため」
- 比べる正解: 9項目の正解表の組に「1」（2026-10-30）
- 成功の決め方に「1」（2026-10-30）: 正答率・サブスクで動くか・回数の上限・1件の時間・費用（円）・本番に書いた件数0件を並べる。線は「正答率が Gemini 以上」「毎日の量を上限に当たらずに解ける」「費用が今以下」。
- 守る指示: 公式サイトを調べない。道具を実際に動かした結果で証拠を作る。

## 基準
- origin/main = b334e2448（worktree 作成時）。生の調査結果: /tmp/CC報告ファイル/llm-compare/recon-raw.md, recon-raw-2.md, recon-raw-3.md, recon-raw-4.md
- 既存 ADR（`git grep -il` docs/adr/、FEATURE-INDEX.md:20）: ADR-1043（正解表を本番DBの専用表に置く）、ADR-1004（LLM使用量台帳）、ADR-1024（AI用読み取り専用DB）、ADR-1042（読み取りの窓口）、ADR-1045（仕入元の原文の書き写しを機械で止める）、ADR-014、ADR-085、ADR-100、ADR-1050。`LINE_ANALYSIS_ENGINE`・`gold_v1` を含む ADR は 0 件。「解析AIの乗り換え・エンジン比較」を扱う ADR は無い。

## 今の解析（事実）
### AI が受け持つ部分
- 本番の呼び出しは backend/app/services/line_analysis_v102_svc.py:474-531 `_call_gemini` → backend/app/services/gemini_raw_copy_v8.py の call_gemini_raw_copy_v8。
- モデル gemini-3.1-flash-lite（backend/app/services/gemini_extraction_svc.py:283）。鍵は環境変数 GEMINI_API_KEY（gemini_extraction_svc.py:262）。
- 設定: thinking_level "high"（line_analysis_v102_svc.py:102）、include_thoughts True・JSON 出力（:503-507）、temperature 未指定、response_schema V102_RESPONSE_SCHEMA（定義 backend/app/services/gemini_raw_copy_v101.py:106-107）。
- 答えの形: {items:[{lines:[int], price:str, quantity:str}], unsure:[{line:int, candidates:[int]}]}。取り出しは line_analysis_v102_svc.py:424-446（_parse_items, _item_rows）。
- 指示書: line_analysis_v102_svc.py:101 V102_ENGINE_VERSION="v102-f_dm"、:103 V102_PROMPT_KEY="raw_copy_v101_f_dm"。本文は DB public.extraction_prompt_config id=397、7773字、sha256 84afd2e4…8b0c（docs/handoff/v102-prompt-fdm/recon.md:23）。手元の写し ~/CC報告ファイル-keep/accuracy-gold-20261020/box-error189/T5T6/heading-fix/test/write_fdm/raw_copy_v101_f_dm.txt の sha256 が一致（担当の実測）。
- 入力の組み立て: build_prompt_v8（gemini_raw_copy_v8.py:124-139, :202-205）。指示書 + 仕入元の決まり（suppliers.extraction_layout_rules / extraction_hard_cases、knowledge_rules の block_delimiter）+「原文:\n[L0001]…」の文字列1本。組み立てた文字列は call_gemini_raw_copy_v8 の戻り値（:233-）に入らない。本番の _call_gemini は recorder.before_send に渡す（line_analysis_v102_svc.py:480-491）が、prompt_ab の道では使われない。
- 後段（商品・状態・単位・予約・値段の正規化）は DB のマスタを読む決まりの処理（line_analysis_v102_svc.py:216 load_v102_masters、:354-402 run_v102_pipeline）。AI は関わらない。

### 試験の道具（本番に解析結果を書かない道）
- backend/app/tools/prompt_ab.py: 入力は extraction_jobs.id の一覧。call_gemini_raw_copy_v8 を本番と同じ関数で呼ぶ（:555）。後段は run_v102_pipeline で計算だけして書かない。書き込み先は出力 JSONL と llm_usage_events（:596-600、purpose=line_extraction_shadow、source_ref=prompt_ab:<test_id>）のみ。--max-cost-usd で停止。
- 本番との設定差: --thinking-level high を付けて初めて同じ（既定は指定なし）。再試行は --retry-transient。それ以外（モデル・include_thoughts・temperature・JSON の形・指示書・組み立て）は同じ（recon-raw-4.md の表）。
- JSONL の欄: run_id, job_id, config, repeat, prompt_name, prompt_source, prompt_sha256, response_text, thought_summaries, usage_raw, item_count, errors, v102_items, v102_flags, elapsed_sec（prompt_ab.py:586-593）。組み立てた文字列そのものは残らない。
- 過去の実行手順: ~/CC報告ファイル-keep/accuracy-gold-20261020/box-error189/T5T6/heading-fix/test/RUNBOOK_fdm.md（本番サーバーの別の箱 `docker compose run --rm --no-deps`、全手順を PO が ! で実行、費用上限 4.00USD）。
- 採点用の形への変換: 同フォルダ validate/fhd_snapshot.py（286行、箱の中で読み取りのみ、14列 TSV。リポジトリ外）。

### 正解表と採点
- 正解表 gold_v1: 本番 DB ai_ro.public__accuracy_gold_rows / _versions（scripts/accuracy/fetch_gold.py:41-58）。手元 ~/CC報告ファイル-keep/accuracy-gold-20261020/gold/gold_v1.tsv、sha256 は gold_v1.sha256 と一致。**100投稿・1494行**（以前「101投稿」と書いたのは誤り。根拠 db-load/gold_v1/raw_20261023212806_verify.out "rows=1494 posts=100"）。
- 原文の全文: 同 sample/posts/<投稿id>.txt 100件（投稿id は正解表と完全一致、2026-10-20 取得）。仕入元の決まりの束は手元に無い（本番 DB にある）。
- 採点: scripts/accuracy/score_v102.py。DB 接続なし（:8-14）。入力 --gold / --snapshot-dir（<投稿id>.tsv 14列 :18-21）/ --out-dir（:335-338）。
  - AI の答えだけで決まる項目: E1 行のまとまり（:168-172）、E2・E3 の AI 段（値段・数量の書き写し :231-242）、C1 読み落とし（:207-218, :299、少ないほど良い）、余分（:300、少ないほど良い）。E1〜E3 の率は対応が付いた件だけが分母（:156-158, :212-217）。
  - 後段を通した結果が要る項目: E2・E3 のシステム段（:243-244）、A1〜A5（:246-278）、A4 予約（:279-280）。
- 手元の Gemini の写し（sample/snapshot/）は旧指示書 f_ct（scripts/accuracy/fetch_snapshot.py の既定 v102-f_ct）。今の本番は f_dm なので、そのままでは比べられない。
- 投稿id → job id: ai_ro.public__extraction_jobs の source_message_id → id（make_runs_map.py と同じ読み方）。

### 使用量と費用
- public.llm_usage_events（migrations/20260930_150000_create_llm_usage_events.sql:33-39）: prompt_tokens, cached_content_tokens, candidates_tokens, thoughts_tokens, tool_use_prompt_tokens, total_tokens, cost_usd。
- 費用の式 backend/app/services/llm_budget.py:211-227: 入力 × 入力単価 + (出力 + 考えた分) × 出力単価。単価 :76-80 gemini-3.1-flash-lite 入力 $0.25 / 100万、出力 $1.50 / 100万。

### claude CLI（2.1.314、手元で実測、/tmp/CC報告ファイル/llm-compare/cli-probe/）
- `claude -p … --model haiku|sonnet --output-format json --tools "" --setting-sources "" --strict-mcp-config --no-session-persistence --system-prompt …` が rc=0。モデルは claude-haiku-5-5 / claude-sonnet-5-5。
- 出る欄: usage.input_tokens / output_tokens / cache_creation_input_tokens / cache_read_input_tokens / output_tokens_details.thinking_tokens、total_cost_usd（costBasis "list" = 定価換算でサブスクの実請求ではない）、duration_ms、duration_api_ms、num_turns、is_error、result。
- 入力は合計 約585〜606 トークン。CLAUDE.md 群（数千トークン級）は入っていない。
- JSON の形を縛る口 `--json-schema <schema>` がある（cli-probe/help.txt:127）。--effort は low/medium/high/xhigh/max（help.txt:84-85）。temperature を変える口は無い。
- 壁時計 約13秒/回（内部 約5.4秒）。起動の固定時間が大きい。

## 未確認
- [?] U1: 大きな入力（指示書 約8000字＋原文）で --json-schema が守られるか、1件の時間。→ 実施の最初の1件で確かめる（design.md §6 手順4）。
- [?] U2: --effort と Gemini の thinking_level high の対応は仕様で一致しない。→ 同名の high にそろえ、差として記録する。
- [?] U3: サブスクの回数の上限の値。公式を調べない指示のため、実際に回して上限に当たるかで測る。
- [?] U4: サブスクで事業の解析を回すことが利用規約上よいか、仕入元の文字列をこの道で Anthropic へ送ってよいか。公式を調べない指示のため未確認。試しを始める前の PO 判断とする（design.md §8-3）。
- U5（決着）: prompt_ab は順番に1件ずつ呼ぶ（二重 for、prompt_ab.py:516-523、並行の import なし :20-88）。並びは「投稿ごとに repeat 1→2→3」。一時的な失敗では同じ関数が再び呼ばれる（:550-573）。
