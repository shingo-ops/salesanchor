<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。 -->
# recon — review-edit-all-fields（要確認の比較表で9項目を直す）

**基準**: origin/main 8df481c0e（2026-10-15 fetch 後）。調査は Sonnet と Opus の読み取り、まとめは Opus。生出力は /tmp/CC報告ファイル/review-edit-fields/（01〜95。95 は v6 の調査）。
**ADR 検索**: item_corrections 専用の ADR は無い。関連は ADR-1014（要確認の作り）、ADR-158（is_current）、ADR-1001/1002（v102）、`docs/handoff/v102-prod-switch/design.md` §13。UI は `docs/adr/ADR-144-ui-component-governance.md` / `docs/adr/ADR-067-design-token-enforcement.md` / `docs/adr/ADR-027-ui-internationalization.md`、即時反映は ADR-1016。
**過去の判断**: `docs/handoff/review-fix-column/design.md` の 18・54・134 行に「数量・価格・単位・備考・商品名は保存の仕組みが無い。PO が後日判断」とある。今回の PO 回答がその後日判断にあたる。

## 1. 本番の数値（読み取りのみ。72・73）
- 要確認一覧の件数（ar 列だけの近似）: v102=155、v6=75。新しい投稿は1日に v102 が約70〜80件、v6 が1〜4件。
- tcg_status_master の canonical は Pre-order・Sold out・In Stock。effect は OUTPUT・EXCLUDE・RELEASE_AHEAD・DATE_AHEAD・HEADING・DEFAULT。
- units は10行（id 9〜18、すべて is_active=t）。kubun に「除外」「数量専用」を含む。
- item_corrections の field_name 別件数: manual_partial_update 462、product_id 387、note_ja 7、status 2、review_ack 1、exclusion 1、condition_* 各1。note_ja・status・exclusion は9月の古い行で、読み手は無い。manual_partial_update もコードに書き手・読み手が無い（95 §4）。

## 2. 人の判断の読み方（v102）
- 正本: `backend/app/services/v102_human_decisions_svc.py`
  - 30-41 行: field_name の定数。TRANSCRIPTION_FIELDS（40 行）、_DECISION_FIELDS（41 行）。
  - 76-85 行: Decisions は product_id・condition_id・ack_codes の3つ。is_empty（84 行）。
  - 127-136 行 _latest_valid: field ごとに最新の1行。書き写しの直しより前の行は無効。
  - 139-181 行 load_v102_decisions: 件ごとの有効な判断を返す。prompt_version では絞らない（どの件の id でも読める）。
  - 339-348 行 item_rejection: 件なし 404、v102 以外 409、source_message_id 不一致 422。
- 反映: `backend/app/services/line_analysis_v102_svc.py`
  - 657-691 行 _analysis_values: note_ja は常に None（686 行）。status と exclusion は item の status・status_effect（687 行）。unit_resolved は unit_id の有無（681 行）。
  - 603-610 行 _bounded_number: NUMERIC(14,2) に入らない値は None。
  - 694-717 行 _UPSERT_SQL: 再解析のたびに全列を上書きする。
  - 790-809 行 _apply_decisions: pid_basis=MANUAL、状態の差し替え、ack の理由を外す、の3つだけ。
  - 812-814 行 _has_human_judgement: 商品か状態の判断があるか（〆の相手の上書きを止める判定）。
  - 921-959 行 _write_results: 945 行で _apply_decisions → _apply_soldout_targets の順に重ねてから UPSERT。
  - 1169-1221 行 run_v102_analysis: 1202 行で load_v102_decisions を読む。
- 販売状況の決まり方: `backend/app/services/tcg_analyzer_svc.py` 1225-1250 行 load_status_master、1269-1305 行 resolve_status_v2。effect=EXCLUDE なら (canonical, 'excluded')、それ以外は (canonical, None)。
- 単位の表: 同ファイル 69 行 load_lookup_maps の unit_canonical_to_uuid（94 行で public.units を JOIN）。v102 は `backend/app/services/line_analysis_v102_svc.py` 192・200 行でこれを unit_ids として使う。

## 3. 保存の入口
- `backend/app/routers/item_corrections.py` 129-172 行 POST /tcg/items/{id}/corrections
  - condition_review があれば save_condition_review → v102 なら再解析を積む（140-151 行）。
  - それ以外は fields（field_name は自由文字列、検証なし）を save_corrections に渡す。v102 なら product の検査（422）と再解析を積む（158-171 行）。
- `backend/app/services/item_corrections_svc.py` 40-80 行 save_corrections: 1項目1行を追記。product_id のときだけ ar を即時 UPDATE（pid_basis='MANUAL'）。
- 書き写しの直し（PUT /tcg/v102/posts/{job_id}/items）は投稿の全件の一覧が必須で、数量・単価を直すと商品・状態・確認済みの判断が無効になる。比較表から1項目を直す経路には使えない。
- 通知: `backend/app/realtime/topics.py` 15 行 TOPIC_TCG_REVIEW、19-20 行に review-ack の2本。corrections は NO_SIGNAL（再解析が終わると tcg.review が出る）。

## 4. v6 の件（95）
- `backend/app/services/tcg_analyzer_svc.py` 1313 行 analyze_extraction_job。v102 は 1330-1334 行で振り分け。UPSERT は 1708-1790 行で全列を raw_* から再計算。
- 1489-1505 行: item_corrections に product_id 行が1つでもある件は、状態の列だけ reanalysis_condition で直し、他の列は上書きしない（skip）。
- 数量・単価・単位・備考・販売状況の人の値を読む所は無い。review_ack は v6 だと 409（上の item_rejection）。
- condition_review は v6 でも保存でき、ar を即時 UPDATE する。

## 5. 一覧 API
- `backend/app/services/tcg_analysis_review_svc.py` 204-250 行の SELECT、284-299 行の system の dict。
  - system に quantity・price（ar の *_normalized）は無い。比較表の数量・単価は gemini の値を出している。
  - 306 行 is_v102 は応答にある。
- 状態の選択肢: `backend/app/routers/tcg_analysis_review.py` 162-167 行 GET /tcg/conditions/review-options。

## 6. 画面（`frontend/src/features/tcg-analysis-review/`）
- `frontend/src/features/tcg-analysis-review/ItemComparison.tsx`
  - 20 行 AnalysisReviewItem の型（is_v102 は無い）。24 行 fieldOrder。
  - 33-40 行 systemCell: name/quantity/price は gemini の値、unit は system.unit、state は system.condition、ほかは system.note。
  - 48-63 行 buildComparisonRows: 行キーは name, quantity, price, unit, state, memo, sourcePosition, work, productId, saleStatus。
  - 70 行 FixColumn。未使用の ManualInput（42 行）が残っている。
- `frontend/src/features/tcg-analysis-review/reviewFixRows.ts` 22-33 行 fixRowsOf: productId・work は scope=product。state は isConditionReviewRelevant のときだけ scope=condition。RowScope は 11 行。
- `frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx`: 18 行 FixChoice、33-39 行 availableFixChoices、42-48 行 FixScope と CHOICES_OF_SCOPE。reassign は ReviewProductFixForm（商品名を検索して選ぶ → product_uuid を保存）。よって「商品名を選ぶと商品IDが入る」は既存の仕組みで満たせる。
- `frontend/src/features/tcg-analysis-review/ConditionReviewPanel.tsx`: 16-21 行 isConditionReviewRelevant は空箱関連と condition_unknown の件だけ真。49 行で偽なら null。選択肢は 43 行の review-options。
- `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`: 25 行 ReviewDrawerItem（is_v102 を持つ）、59 行 fixRowsOf、193-210 行で ItemComparison と ReviewFixWizard。
- 金型: Select / SelectControl、TextField / TextFieldControl（数値専用の部品は無い）、Textarea、Button、AsyncCombobox、ChoiceCardGroup、Callout。
- 文言: `frontend/src/locales/ja.json` と `frontend/src/locales/en.json`。接頭辞 reviewItem.*、tcgAnalysisReview.*、conditionReview.*。

## 7. 配信（在庫表と GAS）
- `backend/app/services/tcg_distribution_svc.py` 297-307 行で ar.note_ja・ar.status・ar.ship_ja を出す。336・448 行で exclusion='excluded' の件は配信しない。

## 8. 版のずれ（409）
- `backend/app/services/tcg_condition_review_svc.py` 165-172 行 review_version は、全 field_name の最新の訂正 id を含む。別の項目を直すと版が変わり、開いたままの状態の保存は 409 になる。

## 9. 試験
- backend: `backend/tests/test_v102_human_decisions.py`、`backend/tests/test_v102_human_decisions_pg.py`、`backend/tests/test_item_corrections.py`、`backend/tests/test_tcg_analysis_review.py`、`backend/tests/test_realtime_topics.py`。
- frontend: tcg-analysis-review 配下の ReviewItemDrawer・reviewFixRows・ItemComparison・ReviewFixWizard・ReviewProductFixForm の試験。
