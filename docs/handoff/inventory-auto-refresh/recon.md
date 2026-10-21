# recon: 在庫表を開いたまま自動で最新にする（在庫表の高速化 便3）

基準: origin/main 57da62446（2026-10-18 fetch 後）。生出力: /tmp/CC報告ファイル/inventory-speed/bin3/recon2/・/tmp/CC報告ファイル/inventory-speed/bin3/impact/

## 既存 ADR の検索
- `git grep -i realtime docs/adr/`・`docs/adr/FEATURE-INDEX.md` で該当: ADR-1016（即時反映の標準）。在庫表は ADR-1014（在庫表は配信行を出す）。ADR-1015（A 区分）。
- ADR-1016 の決定6（`docs/adr/ADR-1016-realtime-change-signal-standard.md:23-25`）: チャンネルは rt:t:{tenant_id} と rt:global。「global は super admin だけが受け取る」。会社共通データを一般利用者に届ける範囲は ADR・`docs/handoff/realtime-standard/design.md` に記述なし。

## 事実（file:line）
### 合図の送り手・受け手
- 送り手: `backend/app/realtime/publisher.py:19-21` `CHANNEL_GLOBAL="rt:global"`・`CHANNEL_TENANT_PREFIX="rt:t:"`・`CHANNEL_PATTERN="rt:*"`。`backend/app/realtime/publisher.py:31-36` `_channel_for` は global と tenant 以外は None（送らない）。合図の中身は `{"topic","origin"}` だけ（`backend/app/realtime/publisher.py:39-40`）。
- 受け手: `backend/app/realtime/hub.py:33-41` `_targets` は rt:global なら `conn.is_super_admin`、rt:t:{id} なら会社一致、それ以外 False。hub は `rt:*` を1本で購読（`backend/app/realtime/hub.py:81`）。
- 接続: `backend/app/routers/realtime_events.py:58` GET /api/v1/events/stream。`backend/app/routers/realtime_events.py:80` `Connection(tenant_id=..., is_super_admin=...)`。
- 画面の土台: `frontend/src/lib/realtime/RealtimeProvider.tsx:61-93` はログイン中の全利用者で接続する（super admin 限定の分岐なし）。`frontend/src/components/DesktopShell.tsx:203`・`frontend/src/components/MobileShell.tsx:198` で包む。/inventory はその中（`frontend/src/App.tsx:207`）。
- フック: `frontend/src/hooks/useRealtimeRefresh.ts:13` `REALTIME_DEBOUNCE_MS = 1_500`、`frontend/src/hooks/useRealtimeRefresh.ts:15` `useRealtimeRefresh(topics, reload)`。自分の origin は無視（:51）、裏タブは保留（:28-30, :39-44）、再接続で1回（:47-49）、Provider 外は何もしない（:22）。
- topic 定数: `frontend/src/lib/realtime/topics.ts:2-4` `TOPICS = { tcgReview: "tcg.review" }`。照合試験 `backend/tests/test_realtime_topics.py:55-60` は「topics.ts の値の集合 == WRITE_ROUTE_TOPICS の topic の集合」。

### 在庫表が変わる経路と今の合図
- 在庫表 API: `backend/app/routers/inventory_offers.py:323-436`（products.view）。行は `backend/app/services/tcg_distribution_svc.py:304-372`（public スキーマの analysis_results ほか）。
- 書き込みの主経路は Celery の抽出 `tcg.extract_source_message` と、人の直し後のやり直し `tcg.v102_reanalyze_after_correction`。どちらも終わりで `_publish_review_changed()`（`backend/app/tasks/tcg_extraction.py:724-731`、`publish_change_sync("tcg.review", "global")`）を呼ぶ（`backend/app/tasks/tcg_extraction.py:756`・`:830`）。
- review-ack・revoke・value-override（v102）は保存後に `enqueue_v102_reanalyze` を積む（`backend/app/routers/item_corrections.py:215`・`:249`・`:293`）ので、やり直し完了で上の合図が出る。corrections・`backend/app/routers/tcg_v102_posts.py:175`・`backend/app/services/tcg_review_csv_svc.py:283` も同じ。
- 合図が出ない経路: マスタ（products・conditions・suppliers など）を直す API、配信設定の更新（`backend/app/realtime/topics.py` で `_PENDING`）、v6 の投稿の直し3経路（value-override の v6 分岐 `backend/app/routers/item_corrections.py:293` の else、状態直しの v6 分岐 `backend/app/routers/item_corrections.py:124-131`、corrections の v6 分岐 `backend/app/routers/item_corrections.py:184-188`。いずれも即時 UPDATE のあと配信予約だけ積む）、時間経過で窓（`backend/app/services/tcg_distribution_svc.py:217-227`）から外れる行。
- 画面: `frontend/src/pages/inventory/InventoryPage.tsx:175-224` の自前 `load`（react-query なし）。成功時だけ items を差し替える（:210）。読み込み表示は場所を確保した `visibility` 切替（:524-530）。古い応答は `loadSeqRef` で捨てる（:171, :209）。InventoryPage は今は合図を受けない（スライドの `frontend/src/features/inventory/InventoryRowDrawer.tsx:85` だけが tcg.review を受ける＝super admin でスライドを開いたときだけ）。

### 頻度（本番 reader、2026-10-18 20:51-20:53 JST、SELECT のみ）
- public.analysis_results の更新は24時間で 25,045 行。08-09時に計 23,351 行が集中、他は 0〜325 行/時。変更のあった「分」は 163（集中時間帯を除くと 77）。生出力 `/tmp/CC報告ファイル/inventory-speed/bin3/recon2/F_hourly.txt`・`F_minutes.txt`。
- 人の直しの記録（item_corrections.corrected_at）は24時間で2件（10-17 21時・22時 各1件、v6 と v102 の合計）。出典は同じ F_hourly.txt。状態直しの経路が別の表に書くかは未確認。

### 影響する試験
- `backend/tests/test_realtime_middleware.py`（:120 他社に届かない・:129 global は super admin のみ）、`backend/tests/test_realtime_topics.py`（:27・:41・:55-60）、`backend/tests/test_analysis_failed_record.py:124` と `backend/tests/test_reextract_v6_with_v102_pg.py:52`（`_publish_review_changed` を差し替え）。
- frontend: `frontend/src/hooks/useRealtimeRefresh.test.tsx`、在庫表の試験5本（`frontend/src/pages/inventory/InventoryPage.noechopatch.test.tsx`・`frontend/src/pages/inventory/InventoryPage.rowdrawer.test.tsx`・`frontend/src/pages/inventory/InventoryPage.settings.test.tsx`・`frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx`・`frontend/src/pages/inventory/InventoryPage.tablelayout.test.tsx`、全て RealtimeProvider なしで描画＝フックは何もしない）。

## 未確認
- 本番で一般利用者の SSE 接続が実際に張られているかの数（ログ未確認）。design.md の K6b で観測する（見分けられなければ保留）。
- 08-09時の大量更新の原因。
