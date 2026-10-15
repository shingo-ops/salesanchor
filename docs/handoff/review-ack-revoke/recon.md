<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。 -->
# recon — review-ack-revoke（確認済みの取り消し）

**基準**: origin/main d2fbd03e5（2026-10-15 fetch 後）。調査は Sonnet、まとめは Opus。生出力は /tmp/CC報告ファイル/review-ack-revoke/ と /tmp/CC報告ファイル/realtime-stage1/84〜87。
**ADR 検索**: `git grep -i "review_ack\|review-ack" origin/main -- docs/adr` は 0 件。item_corrections を含む ADR も 0 件。`docs/adr/FEATURE-INDEX.md` に要確認・item_corrections の項目は無い（最も近いのは 19 行の「取り込み / 解析」→ ADR-100 / ADR-014）。UI は ADR-144 / ADR-067 / ADR-027、即時反映は ADR-1016（`docs/handoff/realtime-standard/design.md`）。

## 1. 確定（review-ack）の流れ
- API: `backend/app/routers/item_corrections.py` 178-198 行。POST /api/v1/tcg/items/{extraction_item_id}/review-ack。権限は require_super_admin（187 行）。
  - 入力 ReviewAckRequest（94-104 行）は {source_message_id, codes(min_length=1)}。応答 ReviewAckResponse（107-109 行）は {ok, saved}。
  - 順序（189-197 行）: find_job_of_item → review_ack_rejection → save_review_ack → enqueue_v102_reanalyze(job_id)。
- 断る規則: `backend/app/services/v102_human_decisions_svc.py` 295-318 行。順に、外せない理由は 422、未登録コードは 422、件なしは 404、v102 以外は 409、source_message_id の不一致は 422。
- 保存: 同ファイル 245-265 行 save_review_ack。
  - 250 行: 現在の review_reasons を読む（_CURRENT_REASONS_SQL、FOR UPDATE、70-72 行）。
  - 252-253 行: load_v102_decisions で前の有効な ack_codes を読む。
  - 254-256 行: 前の codes と今回の codes の和集合を {"v":1,"codes":[…]} にする。
  - 257-263 行: item_corrections に 1 行 INSERT する。264 行で commit。UPDATE と DELETE はしない。
- 読み手①（Python）: 同ファイル 139-181 行 load_v102_decisions。
  - review_ack の最新 1 行だけを採用する（127-136 行）。それより後に書き写し直しの行があれば無効になる。
  - _ack_codes（108-116 行）は、{"v":1,"codes":[]} のとき 111-112 行の条件が偽になる。そのため warning を出さずに 116 行で frozenset() を返す。170 行の `if codes:` が偽になり、「確認済みなし」として扱われる。
- 読み手②（SQL）: `backend/app/services/tcg_condition_review_svc.py` 190-206 行の LATERAL cr_review_ack。
  - 最新 1 行について、v=1、codes が空文字を含まない文字列配列、`codes @> ["excluded"]` のときだけ excluded_acked が真になる。
  - codes が [] なら偽になる。
  - 使う場所は 229・236 行（理由 excluded を外す）と 248 行（出力）。
- 再解析での反映: `backend/app/services/line_analysis_v102_svc.py` 790-809 行 _apply_decisions。ack_codes を review_reasons から外す。残りが無ければ needs_review は False になる。
- ほかの書き込み入口: CSV（`backend/app/services/tcg_review_csv_svc.py` 177・257 行）も同じ関数を使う。
- 取り消しの API は無い。ReviewAckRequest の min_length=1 のため、空の codes は 422 で断られる（`backend/tests/test_v102_human_decisions.py` 301 行）。

## 2. 再解析とリアルタイム通知
- `backend/app/tasks/tcg_extraction.py` の各処理:
  - enqueue_v102_reanalyze（727-733 行）は、タスク（802-818 行）を積む。
  - reanalyze_v102_job（706-724 行）は run_v102_analysis → commit → publish_change_sync("tcg.review","global")（696-703 行）→ 配信予約、の順に動く。
- 通知の表: `backend/app/realtime/topics.py` 18-20 行で、review-ack は (tcg.review, global)。
- 表に載せ忘れると CI が赤になる: `backend/tests/test_realtime_topics.py` 27・35・41・56 行。
- 画面: `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx` 79 行の useRealtimeRefresh([TOPICS.tcgReview]) が、一覧を読み直す。

## 3. DB
- public.item_corrections の定義: `migrations/20260921_110000_pipeline_tables_public.sql` 320-334 行。
  - field_name に CHECK も enum も無い。DB 側で UPDATE や DELETE を禁止する仕組みも無い。
  - 「追記だけで残す」は運用の決まり。根拠は `backend/app/services/item_corrections_svc.py` 4-5 行と `docs/handoff/v102-prod-switch/design.md` 276 行。
- 確認済みの記録は item_corrections にしか無い。analysis_results.review_reasons は、ack を反映した結果にすぎない。
- 本番の実測（2026-10-15、87-item-state.txt）
  - 01:50Z 以降に入った review_ack は 1 行だけ（id=1610、test-admin、codes ["excluded"]）。
  - その件の analysis_results は exclusion='excluded'、needs_review=f、review_reasons は空。

## 4. 画面
- 要確認ページ: `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`
  - タブは "production" | "posts"（26 行）。Tabs の金型を使う（12・180-187 行）。
  - production は GET /tcg/analysis-results?status_tab=NEEDS_REVIEW&limit=20（89-95 行）。
  - drawerItemId を持っておき、最新のデータから引き直して ReviewItemDrawer に渡す（70-73・174-178 行）。一覧から外れた件には removedFromList を渡す（217 行）。
- 一覧 API: `backend/app/routers/tcg_analysis_review.py` 110-136 行。
  - _STATUS_TABS は ALL・NEEDS_REVIEW・PRODUCT_MASTER_UNREGISTERED・SUPPLIER_UNREGISTERED・PRODUCT_ID_UNRESOLVED・NORMAL_COMPLETED。範囲外の値は ALL になる。
  - WHERE は `backend/app/services/tcg_analysis_review_svc.py` 55-112 行 _build_where（タブごとの分岐は 81-96 行）。
  - 共通の FROM は 38-48 行の review_joins（cr_review_ack を含む）。
  - 応答の 1 件（266-314 行）には、review_ack の有無を示す項目が無い。
- ドロワー: `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.tsx`
  - props は 27-34 行。ackedCodes は 45 行、ackedNotice は 46 行。
  - confirmKeep（72-90 行）は postReviewAck を送り、成功したら Callout info「確認済みにしました。解析をやり直しています」（125 行）を出す。
  - ConfirmModal は 154-171 行。
- 確定したあと、その件をこのドロワーで開き直せる場所は無い。
  - ReviewItemDrawer を使っているのは NeedsReviewTabsPanel だけで、一覧は NEEDS_REVIEW に限られる。
  - 仕入先詳細（SupplierDetailView）は ProductMasterDrawer を開く。
- API 呼び出し: `frontend/src/features/tcg-analysis-review/reviewActions.ts` 45-50 行 postReviewAck。
- 金型
  - Callout は action を受け取れない。children は受け取れる。
  - Toast（`frontend/src/components/loading/Toast.tsx`）も action を受け取れない。
  - Button の variant は primary・secondary・ghost・danger・outline・tab、size は sm・md・lg（`frontend/src/components/Button.tsx` 7-8 行）。
  - ConfirmModal と Tabs がある。
- i18n: reviewItem の名前空間（ja.json と en.json の 3766 行から）。ack、acked、ackFailed、ackConfirm{title,message,confirm}、removedFromList。

## 5. 試験
- backend
  - `backend/tests/test_v102_human_decisions.py` 224-303 行（API。fixture は ack_env 230-248 行、monkeypatch で差し替える）。
  - `backend/tests/test_v102_human_decisions_pg.py`（PG 試験。CI でだけ動く）。
  - `backend/tests/test_realtime_topics.py`。
- frontend
  - `frontend/src/features/tcg-analysis-review/ReviewItemDrawer.test.tsx`（215-300 行）。
  - `frontend/src/features/tcg-analysis-review/reviewActions.test.ts`。
  - `frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.drawer.test.tsx`。
- 手元での実行結果
  - test_v102_human_decisions.py は緑。
  - test_realtime_topics.py は、argon2 が手元に無いため 3 件が失敗した（環境の問題）。
  - frontend は node_modules が無く、まだ動かしていない。
