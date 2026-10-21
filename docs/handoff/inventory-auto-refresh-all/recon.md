# recon: 在庫表を、マスタ編集・v6 訂正・24時間枠からの脱落でも自動で最新にする（在庫表の高速化 便4）

基準: origin/main 66ef0cc58d2372e314925c008929e3240ce6724a（fetch 後、`git show origin/main:<path>` で読んだ）。調査は Sonnet が2回行った。生出力は /tmp/CC報告ファイル/inventory-speed/bin4/recon/ にあり、要点は同じ場所の SUMMARY.md。

## 既存 ADR の検索
- ADR-1016（即時反映の標準）: 決定6（チャンネル）・決定7（まとめ時間）・決定9（直接 SQL は対象外）と、便3 の「改訂 2026-10-18」（rt:shared・TASK_TOPICS・書き込みルートの表に shared を置かない）が対象。`docs/adr/ADR-1016-realtime-change-signal-standard.md`
- ADR-1014（在庫表の表示）: 24時間の窓。改訂(3) で「24時間以内」は配信行の計算の内側で絞る。
- ADR-1015: 区分。`backend/app/middleware/realtime.py` と ADR を触るので A。

## 1. 在庫表が読む表
【事実】
- 行の元は analysis_results。ほかに extraction_items、extraction_jobs、source_messages、supplier_channels、public.suppliers、public.products、public.line_units、public.type_master、product_search_keywords、public.conditions（実体は line_conditions）、item_corrections を読む。
- 出典は `backend/app/services/tcg_distribution_svc.py:304-372` と `backend/app/services/tcg_condition_review_svc.py:138-270`。
- 窓の時間は tcg_distribution_settings の max_age_hours で決まる（`backend/app/services/tcg_distribution_svc.py:179-212`）。
- 行の条件は `backend/app/services/tcg_distribution_svc.py:367-375`。版（v6/v102）の絞り込みは無い（grep で 0 件）。

## 2. いま合図が出る書き込み
【事実】
- `backend/app/realtime/topics.py:20-24` の WRITE_ROUTE_TOPICS は 3 本で、どれも tcg.review の global。
  - review-ack
  - review-ack/revoke
  - value-override
- 型は「1経路 → (topic, scope) の1組」。1つの経路に複数の topic は持てない。
- tcg.inventory の shared を出すのは Celery だけ。`backend/app/tasks/tcg_extraction.py:724-733` の `_publish_review_changed` を呼ぶのは次の 3 つ。
  - extract_source_message
  - reanalyze_v102_job
  - tools/reextract_v6_with_v102.py
- middleware（`backend/app/middleware/realtime.py:37-69`）は、書き込みメソッドが 2xx を返し、かつ WRITE_ROUTE_TOPICS に載っている経路のときだけ合図を出す。
- 試験（`backend/tests/test_realtime_topics.py`）の主な主張:
  - :34-39 全書き込みは WRITE か NO_SIGNAL の「ちょうど片方」に載る。
  - :42-45 表に載る経路は実在する。
  - :48-60 WRITE の super admin 経路は global にする。
  - :76-79 WRITE に shared は置かない。

## 3. 在庫表の表に書くのに合図が出ない書き込み（topics.py では NO_SIGNAL の `_PENDING`）
【事実】行番号は `backend/app/realtime/topics.py` のもの。
- 一般の権限の口
  - /api/v1/conditions（:89-95）は `public.conditions` VIEW に書く。権限は conditions.create / update / delete / view（`backend/app/routers/conditions.py:210`・:273・:327・:452）。
  - /api/v1/products（:197-199）は public.products に書く（`backend/app/routers/products.py:82-86`）。
  - /api/v1/units（:400-404）は `public.units` VIEW に書く。権限は suppliers.view（`backend/app/routers/units.py:127`）。
- super admin の口
  - conditions（:255-261）
  - suppliers（:320-329）
  - tcg/types（:333-335）
  - units（:341-347）
  - distribution/settings（:359）
  - extraction-jobs reanalyze（:363。同期の v6 再解析）
  - items corrections（:366）
  - tcg/line-devices/import（:369）と line-import（:372-375）。public.suppliers と supplier_channels に書く（`backend/app/routers/tcg_line_import.py:500`・:509・:532）。
  - tcg/products（:376-384）
  - review/csv/commit（:385）
  - v102/posts items（:387）
- v6 の訂正は analysis_results をすぐ書き換え、schedule_distribution だけを積む（`backend/app/routers/item_corrections.py:124-133`・:182-187・:292-296）。合図は出ない。
- 合図を出さない Celery
  - recover_stale_extraction_jobs は extraction_jobs の status だけを書く。続く再解析が合図を出す。
  - 配信系は tcg_distribution_targets とシートにだけ書く。在庫表が読む表には書かない。
- tcg-mirror-daily-write は DB を読むだけ（`backend/app/tasks/tcg_mirror.py:32`。書き先はシート）。

## 4. 時間だけで変わる表示
【事実】
- 窓の条件は `sm.line_posted_at >= NOW() - make_interval(hours => :max_age_hours)`（`backend/app/services/tcg_distribution_svc.py:220-227`）。0 か None のときは絞らない。
- 「24時間以内」は `min(max_age_hours, 24)`（`backend/app/routers/inventory_offers.py:372-375`）。
- 応答には window_hours（max_age_hours）と各行の posted_at がある（`backend/app/schemas/inventory_offers.py:129-160`・:187-203）。期限の欄は無い。
- 件数・ページ・絞り込み候補は、`backend/app/routers/inventory_offers.py:280-320` の1文で UNION ALL の3枝として返る。
  - 件数は rows_f（絞り込み後）から取る。
  - 候補は facet_src（まとめなし・絞り込みなし）から取る。
  - どちらにも posted_ts（= sm.line_posted_at）列がある。
- 画面に時間で読み直す仕組みは無い。`frontend/src/pages/inventory/InventoryPage.tsx` を通読したところ、setInterval は無く、setTimeout は検索とフィルタ保存の 250ms だけだった。
- `frontend/src/hooks/useRealtimeRefresh.ts` は隠れタブでは保留し、表に戻ったときに1回だけ読み直す。

## 5. 直近7日の書き込み量（reader 鍵、SELECT のみ。D1.out・D2.out）
| 対象 | 7日 | 24h |
|---|---|---|
| analysis_results computed_at | 30220 | 24905（再解析の一括を含む） |
| products updated_at | 132 | 9 |
| product_search_keywords updated_at | 320 | 22 |
| suppliers updated_at | 10 | 3 |
| line_conditions updated_at | 12 | 0 |
| item_corrections | 3 | 0 |
| tcg_distribution_settings | 0 | 0 |

## 未確認
- （確認済み）`public.units` と `public.conditions` は、改名のときに作った互換用の VIEW である（`migrations/20260922_080000_rename_line_analysis_tables.sql:32`・:83）。
- 本番の TCG_AUTO_DISTRIBUTE の値（配信の積み込みにだけ関係する。在庫表には関係しない）。
- 手動の psql 書き込み（ADR-1016 決定9 で対象外）。
