# recon: 状態「Bulk」の新設（便1）

基準: origin/main b4f00fa67（fetch 後）。パスは worktree 相対ではなくリポジトリ直下からの相対（フルパス＝リポジトリ内パス:行）。元資料: ~/CC報告ファイル-keep/accuracy-20261014/g28-bulk-price/{DESIGN_V3.md,REVIEW_V3.md,bulkstate/FACTS.md}（Opus 調査・Sonnet 調査。本番は SELECT のみ）。

## 1. 事実（DESIGN_V3 §0 より）
- 【事実】配信は直近48時間の投稿だけ。本番 max_age_hours=48。今のバルク系の配信は0行。48時間以内の現行行は v102 の Error 8行のみ（全件 needs_review=true）。根拠: bulkstate/FACTS.md §B9。
- 【事実】v9 等の旧行337行は全件48時間を過ぎている。v102 の再解析は prompt_version が v102 の job だけが対象（backend/app/tasks/tcg_extraction.py:706 reanalyze_v102_job）。→ 古い行の補正は不要。補正台本は作らない。

## 2. コードの現在地（origin/main b4f00fa67）
- backend/app/services/gemini_raw_copy_v102_product_first.py:48 PRODUCT_KUBUN_SET（箱系・セット系の定数。:47-48 付近に同じ書き方で足す）
- backend/app/services/gemini_raw_copy_v102_product_first.py:79 CONDITION_ERROR_CODE = "CN0012"
- backend/app/services/gemini_raw_copy_v102_product_first.py:85 BASIS_UNIT_UNKNOWN = "R4:単位既定:単位不明"
- backend/app/services/gemini_raw_copy_v102_product_first.py:551 _undecided_condition（FLAG_SINGLE かつ単位不明 → Error）
- backend/app/services/gemini_raw_copy_v102_product_first.py:561-573 _resolve_condition。引数に product_kubun がある（:561）。バルク系は :565 の箱系・セット系の集合に入らず :571-573 に来る。:572 が _undecided_condition。呼出は :663。
- backend/app/services/tcg_analyzer_svc.py:809 resolve_condition_v2。:909 が最終 FLAG_SINGLE（basis "R4:単位既定:単位不明"）。search_kw が空だと一致しない（:336 if not search_kw_str）。DEFAULT は常に当たる（:797）。
- backend/app/services/tcg_analyzer_svc.py:652 load_condition_entries は is_active かつ priority>0 の行だけ読む。
- backend/app/services/line_analysis_v102_svc.py:621 _condition_columns は canonical でマスタ行を引き、無ければ FLAG_SINGLE に落とす → priority>0・is_active=true が必須。
- backend/app/services/tcg_distribution_svc.py:236-239 配信の状態条件: canonical が FLAG_ で始まらず effect が EXCLUDE でない行だけ通る → Bulk（OUTPUT・非 FLAG_）は通る。
- backend/app/services/v102_buyback_unit_svc.py:49 _UNIT_DEFAULT_PREFIX = "R4:単位既定"。買取換算の候補は basis がこれで始まる行だけ → R6 は対象外（意図どおり）。
- backend/app/services/tcg_result_order.py:9-17 RESULT_CONDITION_ORDER（Bulk 未掲載）、:25 の ELSE で未掲載は最後尾。

## 3. マスタ（本番 SELECT・2026-10-16）
- public.line_conditions は15行。code CN0014 は0行。id は identity。OUTPUT 行の priority は 1(2行)・2(6行)・3(3行)・4(2行)・10(1行)。列は bulkstate/FACTS.md §A1（tenant_id・condition_def_id・unit_id・note を含む16列）。
- 表名は改名後の line_conditions（migrations/20260922_080000_rename_line_analysis_tables.sql:72）。前例 docs/handoff/v102-prod-switch/data/conditions/*.sql は改名前の public.conditions で書かれている（形式は同じ。表名だけ line_conditions にした）。
- 商品区分 id=9 PC_BULK kubun_type「バルク系」（bulkstate/FACTS.md §A1）。

## 4. 既存 ADR の検索（結果: /tmp/CC報告ファイル/g28bin1/adr_search.txt と同内容）
- git grep -il 'バルク\|Bulk' origin/main -- docs/adr → ADR-067（デザイントークン。無関係）のみ。
- git grep -il 'FLAG_SINGLE\|line_conditions' origin/main -- docs/adr → 0件。
- docs/adr/FEATURE-INDEX.md に状態・Bulk の項目は無い。
- 関連として扱う ADR: ADR-1007（値は SQL で入れる）、ADR-1014、ADR-1019、ADR-027（新しい文言なし）、ADR-1015（区分 A）。ADR-1020 は別件（共用商品の必須項目）で番号を使用中のため、本件は ADR-1021。
- 番号確認: origin の全 branch と open PR で ADR-1021 は未使用。

## 5. 未確認
本番 GAS の実体、Piece にしたときの単価チェックの誤検知（便2）、note の英語列（便2）。
