<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ -->
# recon — review-excluded-ack（origin/main 758d84e8d、2026-10-14）

## 既存 ADR の検索
- `docs/adr/ADR-144-ui-component-governance.md`（金型）、`docs/adr/ADR-067-design-token-enforcement.md`（トークン）、`docs/adr/ADR-027-ui-internationalization.md`（i18n）。要確認の除外・確認済みを定める ADR は見当たらない（docs/adr/FEATURE-INDEX.md と git grep -i "review_ack\|exclusion" docs/adr/）。

## §1 行を押しても開かない件（再現なし）
- 本番と同じ件（作品=ポケモン、商品ID=440301、Sold out、理由 excluded のみ）のデータで、ReviewItemDrawer 単体と NeedsReviewTabsPanel 全体を実 Chromium 1280/390 幅で試し、4 セルとも押すと直す欄（ReviewProductFixForm）が出た。
- Drawer は document.body への portal（`frontend/src/components/Drawer.tsx` 113-114 行）。DataTable の isInteractiveTarget（`frontend/src/components/DataTable.tsx` 100-104 行）には当たらない。
- 除外だけの件は選択肢が「付け替え」1つなので、質問を出さず付け替え欄が直接出る仕様。

## §2 画面
- 直す欄: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx` 116-130 行。scope=null のとき `reviewItem.fixHeading`（直す）と `reviewItem.pickRowHint` を出す。
- 確認済みは1理由ずつ送る: `frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx` 95-116 行（postReviewAck(item, [code])）、`frontend/src/features/tcg-analysis-review/reviewActions.ts` 45-50 行。
- 「このままで良い」を出す条件: `frontend/src/features/tcg-analysis-review/ReviewFixWizard.tsx` 26-33 行（ackable が偽でない理由）。
- 販売状況は `item.system.status`（`frontend/src/features/tcg-analysis-review/ItemComparison.tsx` 60 行で saleStatus 行に表示）。

## §3 backend
- 確認済みの保存: `backend/app/services/v102_human_decisions_svc.py` 243-258 行（item_corrections に field_name='review_ack'、human_value `{"v":1,"codes":[...]}`、件単位）。
- 読み: 同 135-185 行。field_name ごとに最新1行（125-132 行）、書き写し直し（TRANSCRIPTION_FIELDS、40 行）より後のものだけ有効。
- 再解析で理由を外す: `backend/app/services/line_analysis_v102_svc.py` 790-809 行。exclusion（687 行 `item.get("status_effect")`）には触らない。
- 一覧のビュー: `backend/app/services/tcg_condition_review_svc.py` 204 行で exclusion 非 NULL なら 'excluded' を毎回作る。211 行。review_ack は読まない。
- 要確認タブ: `backend/app/services/tcg_analysis_review_svc.py` 83-85 行・99-102 行に `ar.exclusion IS NOT NULL`。
- 配信: `backend/app/services/tcg_distribution_svc.py` 322・432 行 `cr.needs_review IS FALSE AND ar.exclusion IS DISTINCT FROM 'excluded'`。
- 除外の値: resolve_status_v2 は 'excluded' か None だけを返す（`backend/app/services/tcg_analyzer_svc.py` 1273-1305 行）。
- analysis_results に JSON 列なし・ORM なし（生 SQL）。

## §4 試験
- `backend/tests/test_v102_human_decisions.py`、`backend/tests/test_v102_human_decisions_pg.py`、`backend/tests/test_tcg_condition_review.py`、`backend/tests/test_tcg_analysis_review.py`、`backend/tests/test_review_reason_codes_svc.py`。

## §5 本番実測（読み取りのみ、2026-10-14）
- `SELECT exclusion, is_current, count(*) FROM public.analysis_results GROUP BY 1,2`: excluded/t 504、excluded/f 909、NULL/t 12846、NULL/f 29143。exclusion の値は 'excluded' と NULL だけ。生出力 /tmp/CC報告ファイル/excluded-values-prod.txt
- 理由別件数の SQL はファイル渡しが安全フックで止まり未取得。

## §6 速度の事前計測（本番・読み取りのみ、2026-10-14）
- 一覧の SQL 全体（/tmp/CC報告ファイル/excluded-ack-speed/*.sql）は、安全フックがファイル渡しを止めるため本番で流していない。
- 代わりに、追加した LATERAL と同じ索引引き（review_ack の最新1行＋書き写し直しの EXISTS）だけを、現行の全件（is_current 13,355 行）に付けて比べた。
  - 付けない: Execution Time 30.963 ms／付ける: 111.113 ms（差 約 80 ms、索引 idx_pub_item_corrections_extraction_item_id を使用）。生出力 /tmp/CC報告ファイル/excluded-ack-speed/prod_lateral_overhead.txt
  - 一覧1回の表示は3クエリなので、増えるのは最大でも約 0.24 秒。過去の実測（docs/handoff/review-speed/design.md、20件 2.25〜2.36 秒）に対して約 1.1 倍で、基準 1.2 倍以内。【未確認】今日の時点の一覧全体の所要時間は測っていない。
