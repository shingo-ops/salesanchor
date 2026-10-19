# design: 在庫表を開いたまま、在庫が変わったら自動で最新にする（在庫表の高速化 便3）

recon: docs/handoff/inventory-auto-refresh/recon.md ／ 関連 ADR: ADR-1016（改訂を足す）・ADR-1014・ADR-1015

## 目的（PO の言葉）
PO の依頼（2026-10-18）「開いたまま自動更新」。PO 決定 2026-10-18「y」: 「在庫表を開いたまま、在庫が変わったら自動で最新に入れ替わるようにするか」→ ADR-1016 を「在庫が変わった合図をログイン中の全員に届ける」形に改めて進める。

## 区分
A（ADR-1015: `backend/app/tasks/` と ADR 本文を触る・今は無い状態を作る）。PO の方向決定「y」（2026-10-18）を受け、GO は POの委任に基づく Claude Opus 発行（ADR-1003）。migrations・deploy.yml・scripts・nginx は触らない（危険 PR ではない）。

## 方式の選択
| 案 | 中身 | 判定 |
|---|---|---|
| A 会社共通の合図 rt:shared を足す | 会社共通データ（public スキーマで全社の利用者が同じものを見る）の合図だけを、全接続に届ける | 採用 |
| B rt:global を全員に配る | global は super admin 向けの要確認画面などにも使っている。全員に配ると「global は super admin だけ」（recon・ADR-1016 決定6）が崩れ、今後 global に足す合図も全員に漏れる | 不採用 |
| C 全社の rt:t:{id} に1つずつ送る | 会社の一覧を Celery 側で引く必要があり、会社が増えるたびに送る数が増える。会社追加時の漏れも起きうる | 不採用 |
| D 画面が数十秒ごとに読みに行く（ポーリング） | ADR-1016 の代替案で既に不採用。変わっていないときも読みに行く | 不採用 |

A を選ぶ理由: 合図は名前（topic）と origin だけでデータを含まない（`backend/app/realtime/publisher.py:39-40`）。データは既存の在庫表 API が権限（products.view）を見て返す。だから全接続に届けても、他社のデータは漏れない。範囲を別のチャンネルに分けるので、global の約束は変わらない。

## 変更前 → 変更後（触るファイルはこれだけ）
### backend
1. `backend/app/realtime/publisher.py`
   - :21 の下に `CHANNEL_SHARED = "rt:shared"` を足す。
   - `_channel_for`（:31-36）に `if scope == "shared": return CHANNEL_SHARED` を足す（global の判定の次）。
2. `backend/app/realtime/hub.py`
   - import に CHANNEL_SHARED を足す。
   - `_targets`（:33-41）の先頭に `if channel == CHANNEL_SHARED: return True` を足す（会社共通データの合図は全接続へ。ADR-1016 改訂 2026-10-18 とコメント）。
3. `backend/app/realtime/topics.py`
   - :13 の下に `SCOPE_SHARED = "shared"` を足す。
   - :15 の下に `TOPIC_TCG_INVENTORY = "tcg.inventory"` を足す。
   - WRITE_ROUTE_TOPICS の後に、裏の処理だけが出す topic の表を足す:
     ```python
     # 書き込み API ではなく裏の処理（Celery）だけが出す topic → 範囲（ADR-1016 決定5）
     TASK_TOPICS: dict[str, str] = {
         TOPIC_TCG_INVENTORY: SCOPE_SHARED,
     }
     ```
   - WRITE_ROUTE_TOPICS の3行・NO_SIGNAL_ROUTES は変えない。
4. `backend/app/tasks/tcg_extraction.py` の `_publish_review_changed`（:724-731）
   - try の中、`publish_change_sync("tcg.review", "global")` の次に `publish_change_sync(TOPIC_TCG_INVENTORY, TASK_TOPICS[TOPIC_TCG_INVENTORY])` を足す（import は関数内で topics から）。
   - docstring を「要確認の一覧と在庫表が変わったことを合図する」に改める。
   - 呼び出し元（:756・:830・`backend/app/tools/reextract_v6_with_v102.py:538,619,781`）は変えない。
### frontend
5. `frontend/src/lib/realtime/topics.ts`: `tcgInventory: "tcg.inventory",` を足す。
6. `frontend/src/hooks/useRealtimeRefresh.ts`
   - 引数に `options?: { debounceMs?: number }` を足す。既定は REALTIME_DEBOUNCE_MS（今の2つの呼び出し元は挙動不変）。
   - `setTimeout(fire, REALTIME_DEBOUNCE_MS)` を `setTimeout(fire, debounceMs)` にし、useEffect の依存に debounceMs を足す。
   - 冒頭コメントの「1.5 秒」を「既定 1.5 秒（呼び出し元で変えられる）」に改める。
7. `frontend/src/pages/inventory/InventoryPage.tsx`
   - import を2行足す（:31 の下）:
     ```ts
     import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
     import { TOPICS } from "../../lib/realtime/topics";
     ```
   - モジュールの上に定数を置く:
     ```ts
     // ADR-1016 改訂 2026-10-18: 在庫が変わった合図で読み直す。抽出が続く時間帯でも 5 秒に 1 回まで。
     // 同じ合図が全員に同時に届くので、ページごとに 0〜3 秒ずらして読み直しが一度に集まらないようにする
     const INVENTORY_TOPICS = [TOPICS.tcgInventory] as const;
     const INVENTORY_REFRESH_DEBOUNCE_MS = 5_000;
     const INVENTORY_REFRESH_JITTER_MS = 3_000;
     ```
   - コンポーネントの中（state 宣言の並び）に、ページを開いた時に1回だけ決めるまとめ時間を置く:
     ```ts
     const [refreshDebounceMs] = useState(
       () => INVENTORY_REFRESH_DEBOUNCE_MS + Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS),
     );
     ```
   - `load` の useEffect（:226-229）の直後に:
     ```ts
     useRealtimeRefresh(INVENTORY_TOPICS, () => {
       if (filtersLoaded) void load();
     }, { debounceMs: refreshDebounceMs });
     ```
   - 画面の文字・部品・CSS は足さない（i18n キー・デザイントークンの追加なし）。読み込み表示は既存の場所確保つき表示（:524-530）をそのまま使う。

### 試験
8. `backend/tests/test_realtime_middleware.py` に `test_shared_signal_to_every_connection` を足す: `hub.dispatch("rt:shared", ...)` が super admin でない会社1・会社2・super admin の3接続すべてに届く。既存の :120・:129 は変えない。
9. `backend/tests/test_realtime_topics.py`
   - :57 を `backend = {t for t, _s in WRITE_ROUTE_TOPICS.values()} | set(TASK_TOPICS)` にする。
   - `test_task_topics_are_shared_or_global` を足す: TASK_TOPICS の範囲は "shared" か "global" だけ（会社 ID の無い裏の処理から tenant を出さない）。
   - publisher の `_channel_for("shared", None) == "rt:shared"` を確かめる試験を足す（置き場はこのファイル）。
10. `_publish_review_changed` が `("tcg.review","global")` と `("tcg.inventory","shared")` を1回ずつ出すことの試験を足す（`publish_change_sync` を差し替えて記録。置き場は `backend/tests/test_realtime_topics.py`）`app.tasks.tcg_extraction` と `app.realtime.publisher` は試験関数の中で import する（収集時の重い import は他の試験を 403 にする前例 `backend/tests/test_realtime_topics.py:13-15`）。
   - `test_write_routes_have_no_shared_scope` も足す: WRITE_ROUTE_TOPICS に範囲 shared の行が無い（shared は TASK_TOPICS に明記したものだけ、を機械で止める）。
11. `frontend/src/hooks/useRealtimeRefresh.test.tsx` に「debounceMs を渡すとその時間でまとめる」「渡さないと 1.5 秒」の試験を足す。
12. 新しい試験 `frontend/src/pages/inventory/InventoryPage.autorefresh.test.tsx`: 偽の RealtimeContext で包み、
    - tcg.inventory の合図→5秒後に `/inventory?` がもう1回呼ばれる
    - 5秒の間に3回合図→読み直しは1回
    - 自分の origin の合図→読み直さない
    - tcg.review の合図→読み直さない
    （`Math.random` を 0 に固定して 5 秒で判定する）
    既存の在庫表試験5本は変えずに緑のまま（Provider 外ではフックが何もしない）。

## 触らない範囲
- WRITE_ROUTE_TOPICS の既存3行・NO_SIGNAL_ROUTES・middleware（`backend/app/middleware/realtime.py`）・`backend/app/routers/realtime_events.py`・`backend/app/auth/`
- 在庫表 API と SQL（`backend/app/routers/inventory_offers.py`・`backend/app/services/tcg_distribution_svc.py`）
- 閲覧ページ（`frontend/src/pages/viewer/`、別の仕組みで60秒ごとに作り置き。ADR-1019）
- スライド（`frontend/src/features/inventory/InventoryRowDrawer.tsx`）・要確認画面
- migrations・deploy.yml・scripts・nginx・tasks の他ファイル

## ADR
ADR-1016 に「改訂 2026-10-18」節を足す（本文の決定1〜9は書き換えない）:
- 決定6に3つ目のチャンネル rt:shared を足す。会社共通データ（public スキーマにあり、どの会社のログイン利用者も同じものを見る在庫表など）が変わった合図だけを流し、全接続に届ける。合図は名前と origin だけで、データは既存 API が権限を見て返すので他社のデータは漏れない。rt:global は今までどおり super admin だけ。
- shared の合図は products.view の有無に関係なく全接続に届く。届くのは topic と届いた時刻だけ（Celery からは origin も空）で、在庫の中身は届かない。
- shared を使える topic は topics.py に shared と明記したものだけ（今は tcg.inventory）。裏の処理だけが出す topic は topics.py の TASK_TOPICS に置く。
- 決定7のまとめる時間はページごとに変えられる（在庫表は5秒）。
- PO 決定 2026-10-18「y」を記す。
その後 `node scripts/generate-adr-index.js` で `docs/adr/README.md` を作り直す。

## 受入条件
|基準|検証方法|
|---|---|
|K1 rt:shared の合図が super admin でない利用者の接続に届く|pytest `test_shared_signal_to_every_connection`|
|K2 rt:global は今までどおり super admin だけ、rt:t は他社に届かない|既存 pytest :120・:129 が緑|
|K3 抽出とやり直しの終わりで tcg.inventory（shared）が1回出る|pytest（publish の記録）|
|K4 在庫表は tcg.inventory を受けて5秒後に1回だけ読み直す。自分の合図・tcg.review では読み直さない|vitest `frontend/src/pages/inventory/InventoryPage.autorefresh.test.tsx`|
|K5 既存の在庫表試験5本・合図の試験・型検査・lint・CI 必須チェックが緑|PR の CI|
|K6 本番で、super admin のアカウントで在庫表をタブ前面のまま開き触らない間に、抽出の完了（worker ログの `tcg.extract_source_message` の succeeded）から10秒以内に /api/v1/inventory の GET が1件以上増える（配線が本番でつながっている確認）|デプロイ後、worker ログの完了時刻と backend アクセスログの GET 時刻を照合（主）。PO の画面目視（行が入れ替わる）|
|K6b 本番で、super admin でない利用者の画面にも届く（今回の本題）|反映後、super admin でない利用者が在庫表を開いている時間帯に、backend ログで利用者を見分けて K6 と同じ照合をする。ログで利用者を見分けられない場合は「未観測・保留」と記録し、合格扱いにしない（その場合の確認は、super admin でないアカウントで PO が画面を開いて目視）。試験上の保証は K1|
|K7 本番反映後24時間で /api/v1/inventory の 5xx が0件、応答時間の中央値が1.0秒以下（反映前の便2後 0.406秒、出典 /tmp/CC報告ファイル/inventory-speed/bin2/prod3/q50.json）|Prometheus `http_request_duration_seconds` と status 別件数|

## リスクと対処
- 負荷の見積り（基準値は本番 Prometheus 7日、生出力 /tmp/CC報告ファイル/inventory-speed/bin3/load/summary.txt）:
  - 同時接続: `sse_connections_active` は stream=inbox しか出ていない（ADR-1016 の通り道はこの指標に載っていない）。代わりの目安として inbox の7日最大 9（10/12 17-18時 JST）を「同時にアプリを開いている画面の上限」とみなす。
  - 最悪の見積り: 9画面が全部在庫表を開き、抽出が切れ目なく続く場合、読み直しは 9画面 × 5〜8秒に1回 ＝ 毎秒約1.1〜1.8件。1回は約0.4秒（便2の本番中央値 0.406秒）。
  - 今の利用: /api/v1/inventory は7日で約106件（再起動での取りこぼしがあり下限）。1分最大32件。
  - 一斉に読み直す問題: ページごとにまとめ時間を 5〜8秒の間でずらす（`INVENTORY_REFRESH_JITTER_MS`）。
  - 抽出が集中する時間帯（recon: 08-09時に約2.3万行）でも、1ページにつき5秒に1回まで（K4）。
  - 見張り: K7 で反映後の応答時間と 5xx を測る。悪化したら revert する。
- 合図が出ない経路（今回の対象外。次の合図か再接続で追いつく）:
  - 時間経過で窓から外れる行
  - マスタ直し・配信設定の変更（topics.py で `_PENDING`）
  - v6 の投稿の直し3経路（`backend/app/routers/item_corrections.py:124-131`・`:184-188`・`:293` の else）。v6 は旧解析で、直しの記録は24時間で2件（recon 頻度。item_corrections 表の件数で v6 と v102 の合計）。router に手で publish を書くのは ADR-1016 決定4で原則しないため、足さない
- 表を見ている途中で行が入れ替わる・読み込み中の表示が出る: PO が「在庫が変わったら自動で最新に入れ替わる」を選んだ（2026-10-18「y」）ので受け入れる。読み込み表示は場所を確保した表示で、表の位置はずれない（:524-530）
- 読み直しの失敗 → 既存の `load` と同じでエラー表示。表は残る（:210 は成功時だけ差し替え）。
- 戻し方: 本 PR を revert（DB 変更なし）。

## 外部・過去事例の参照と我々への応用
- 該当なし：既存の ADR-1016（SSE・名前だけの合図・まとめて読み直し）の範囲を1つ足すだけで、仕組みは社内で本番稼働中（段階1 #4290）。効果の根拠は外部事例ではなく本番の計測（K6）にするため、外部事例の参照は不要と判断

## 維持の仕組み
守り手: `backend/tests/test_realtime_topics.py`（topic の集合の照合・TASK_TOPICS の範囲・publish の記録）、`backend/tests/test_realtime_middleware.py`（届け先）、`frontend/src/pages/inventory/InventoryPage.autorefresh.test.tsx`（在庫表の読み直し）。
