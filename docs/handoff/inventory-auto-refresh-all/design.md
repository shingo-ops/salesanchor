# design: 在庫表を、マスタ編集・v6 訂正・24時間枠からの脱落でも自動で最新にする（在庫表の高速化 便4）

recon: docs/handoff/inventory-auto-refresh-all/recon.md ／ 関連 ADR: ADR-1016（改訂を足す）・ADR-1014・ADR-1015 ／ 前の便: docs/handoff/inventory-auto-refresh/design.md（便3）

## 目的（PO の言葉）
- PO（2026-10-18）「更新された情報があれば常に最新情報を画面に出してほしいのだが更新時のトリガーで実現できる？」
- PO 決定（2026-10-18）「y」: 「この3つの経路（マスタ・配信設定の編集／v6 の訂正／24時間の枠から外れる）も自動で画面に反映するよう、設計を始めますか」
- 直接の SQL 書き込みは対象外のまま（ADR-1016 決定9）。

## 区分
A（ADR-1015）。`backend/app/middleware/realtime.py` と ADR 本文を触り、今は無い状態を作るため。GO は POの委任に基づく Claude Opus 発行（ADR-1003）。migrations・deploy.yml・scripts・nginx は触らない（危険 PR ではない）。

## 利用者に見える変化
| きっかけ | 今 | 変更後 |
|---|---|---|
| 抽出・v102 再解析の完了 | 5〜8秒で読み直す（便3） | 変わらない |
| 商品・状態・単位・仕入元・作品種別・検索語・配信設定の編集、v6 の訂正、CSV・LINE 取込の確定 | 読み直さない。手で再読み込みが要る | 編集が成功してから5〜8秒で、表の行を読み直す |
| 行が24時間（または設定の時間）の枠から外れる | 画面に残り続ける | 外れた時刻から通常 0〜3 秒、最大 63 秒以内に読み直して消える |
| 文言・色・レイアウト | — | 変えない |

対象外:
- 作品種別のタブ名（`frontend/src/pages/inventory/InventoryPage.tsx:247-254` で最初に1回だけ取る）は、次に画面を開いたときに反映する。行の中身は読み直す。
- 閲覧ページ（`backend/app/routers/viewer.py:233` の別の作り置きを読む）と GAS 在庫一覧。

## 方式の選択
### (1) 書き込みの口から在庫の合図を出す
| 案 | 中身 | 判定 |
|---|---|---|
| A 新しい表 INVENTORY_SIGNAL_ROUTES を topics.py に足す | 在庫表が読む表に書く経路の集合。2xx のとき middleware が tcg.inventory を shared で出す。既存の WRITE / NO_SIGNAL の「ちょうど片方」の規則（試験 :34-39）は変えずに併用する | 採用 |
| B WRITE_ROUTE_TOPICS の値を (topic, scope) のリストに変える | 型を変えるので、既存試験 6 本と middleware の全分岐が変わる。shared 禁止の試験（:76-79）を外すことになり、他の topic にも shared が混ざりうる | 不採用 |
| C 各ルートの処理に publish を手で書く | ADR-1016 で不採用（書き忘れを機械で止められない） | 不採用 |
| D DB トリガー | ADR-1016 で不採用 | 不採用 |

A を選ぶ理由:
- 便3 の決まり「WRITE_ROUTE_TOPICS には shared を置かない」はそのまま守れる。
- shared を出せる経路は、名前の付いた1つの表に限られる。その表は試験で検査できる。
- 合図は名前だけで、データは含まない。origin も空（None）で送る。データは既存 API が権限を見て返す（ADR-1016 改訂 2026-10-18）。

### (2) 24時間枠からの脱落
| 案 | 中身 | 判定 |
|---|---|---|
| A API が「次に行が枠から外れるまでの秒数」を返し、画面はその時刻に読み直す | 秒数はサーバーの NOW() で計算するので、利用者の PC の時計ずれに左右されない。読み直しの間隔は最短 60 秒 | 採用 |
| B 画面が数分おきに読みに行く（ポーリング） | ADR-1016 で不採用。変わっていないときも読む | 不採用 |
| C 画面が各行の posted_at と window_hours から計算する | 見えているページの 50 行しか知らない。ほかのページの行・まとめた行・絞り込み候補が外れても気づけない。PC の時計ずれも入る | 不採用 |
| D サーバーが枠を外れる時刻に合図を出す（Celery の定期実行） | 定期実行を 1 つ足し、外れる行を毎回数える処理が要る。会社ごと・絞り込みごとの差を見られない | 不採用 |

最短 60 秒の理由: 抽出は 24h で 24905 行（recon §5）あり、行が枠から外れる時刻は数秒おきに来うる。最短の間隔を設けないと、読み直しが続けて起きる。60 秒にすると、開いている 1 画面あたりの追加の読み込みは最大で毎分 1 回になる。

## 対象の経路（INVENTORY_SIGNAL_ROUTES に入れる 45 本）
行番号は `backend/app/realtime/topics.py`（origin/main 66ef0cc58）のもの。選ぶ規則は「在庫表が読む表（recon §1）に書き、その成功で表示が変わりうる経路」とする。別名（aliases）の経路は外した。書き先は public.condition_aliases と public.unit_aliases（`backend/app/routers/conditions.py:547-580`、`backend/app/routers/super_admin_units.py:252-296`）で、在庫表の SQL はこれらを読まないため（審査で確認）。

- 一般の権限（11本）
  - /api/v1/conditions（4本）: POST、POST import/commit、DELETE {condition_id}、PATCH {condition_id}（:89-95 のうち aliases の2本を除く）
  - /api/v1/products（3本）: POST、DELETE {product_id}、PATCH {product_id}（:197-199）
  - /api/v1/units（4本）: POST、POST import/commit、DELETE {unit_id}、PATCH {unit_id}（:400-401・:403-404）
- super admin（34本）
  - conditions（4本）: :255-261 のうち aliases の2本を除く
  - suppliers（4本）: POST、POST import/commit、DELETE {supplier_id}、PATCH {supplier_id}（:320・:322・:324-325）
  - tcg/types（3本）: :333-335
  - units（4本）: :341-347 のうち aliases の2本を除く
  - distribution/settings（1本）: PUT（:359）
  - extraction-jobs reanalyze（1本）: :363
  - items corrections（1本）: :366
  - review-ack・review-ack/revoke・value-override（3本）: WRITE_ROUTE_TOPICS（:21-23）。tcg.review の global に加えて出す。
  - tcg/line-devices/import（1本）: :369
  - line-import（4本）: POST、POST android、POST {import_job_id}/commit、POST {import_job_id}/resolve（:372-375）
  - tcg/products（6本）: POST、POST create、DELETE detail/{product_id}、PUT detail/{product_id}、POST import/commit、POST {product_id}/search-keywords（:376・:378-381・:384）
  - review/csv/commit（1本）: :385
  - v102/posts items（1本）: PUT（:387）

入れないもの:
- import/preview と check-duplicates: 書かない確認用。
- exclude-keywords: 在庫表は除外語を読まない。
- suppliers の discord-routing・extraction-rules・knowledge-links: 在庫表は読まない。
- quantity-units: 在庫表の SQL に出ない。
- テナントの /api/v1/suppliers: テナントの表で、在庫表は読まない。
- line-devices の approve・start・revoke: 機器の登録だけ。
- retry-extraction と error-reports の reanalyze: 裏の再解析が完了時に合図を出す（`backend/app/tasks/tcg_extraction.py:758`。retry-extraction は extract_source_message_task を積み（`backend/app/services/tcg_diagnostics_svc.py:176`）、そのタスクが `backend/app/tasks/tcg_extraction.py:832` で合図を出す）。
- conditions・units の aliases（6本）: 上に書いた理由による。
- purchase-orders の receive・unreceive: products.quantity だけを書く（`backend/app/routers/purchase_orders.py:265`・:301）。在庫表はこの列を読まない。
- product-categories（一般・super admin）: `public.tcg_product_categories` だけを書き、削除は論理削除（`backend/app/routers/super_admin_product_categories.py:8`）。在庫表の SQL はこの表を JOIN しない（`backend/app/services/tcg_condition_review_svc.py:98` は products の列の値を読むだけ）。

一般の権限の口を入れる理由: public の共通表に書くので、他社の在庫表の表示も変わりうる。通常の利用者は RLS で共用の行に書けない（`backend/app/routers/products.py:516-527`）。合図には名前しか入らず、origin も空にする。他社に伝わるのは「何かが変わった時刻」だけで、中身は伝わらない。抽出完了の合図（便3）も全接続に届いており、これと同じ扱いになる。

## 変更前 → 変更後（触るファイルはこれだけ）
### backend
1. `backend/app/realtime/topics.py`
   - TASK_TOPICS の後に、次の集合を足す。
     ```python
     # 在庫表が読む共通の表（public）に書く経路。2xx のとき middleware が tcg.inventory を shared で出す
     # （ADR-1016 改訂 2026-10-19）。WRITE_ROUTE_TOPICS / NO_SIGNAL_ROUTES のどちらに載るかとは別に持つ
     INVENTORY_SIGNAL_ROUTES: frozenset[tuple[str, str]] = frozenset({
         ...上の 45 本を (method, path) で...
     })
     ```
   - WRITE_ROUTE_TOPICS・NO_SIGNAL_ROUTES・TASK_TOPICS の中身は変えない。
   - :26 の TASK_TOPICS のコメントを「裏の処理（Celery）が出す topic と範囲。tcg.inventory は書き込み API からも INVENTORY_SIGNAL_ROUTES 経由で同じ範囲で出る」に直す。
2. `backend/app/middleware/realtime.py`
   - import に INVENTORY_SIGNAL_ROUTES、TOPIC_TCG_INVENTORY、TASK_TOPICS を足す。範囲は直書きせず、`TASK_TOPICS[TOPIC_TCG_INVENTORY]` から引く（配線の正本を1か所に保つ）。
   - :53-57 を、次の形に変える。
     - 経路のキー `key = (scope["method"], route_path)` を作る。
     - `entry = WRITE_ROUTE_TOPICS.get(key)` と `inventory = key in INVENTORY_SIGNAL_ROUTES` を求める。
     - 両方とも無ければ return。
   - origin の取り出し（今の :64-68）は、tenant の判定より前に移す。
   - entry があれば、今までどおり処理する。tenant のときに rt_tenant_id が無ければ、その合図だけを出さない。
   - inventory が真なら、`_spawn(publish_change(TOPIC_TCG_INVENTORY, TASK_TOPICS[TOPIC_TCG_INVENTORY], tenant_id=None, origin=None))` を足す。origin は空にする。全接続に届く合図に、編集した人のタブの識別子を載せないため（ADR-1016 改訂 2026-10-18「届くのは topic と時刻だけ」と合わせる）。編集した本人のタブも読み直すが、5〜8 秒のまとめがあるので問題にならない。
   - 2xx 以外は、今までどおり何も出さない。
3. `backend/app/routers/inventory_offers.py`
   - `_build_inventory_view_sql` に引数 `expiry: bool = False` を足す（既定値があるので、既存の呼び出し5か所はそのまま動く）。q_total・q_page・q_facet の3枝すべてで、`__ord` の次に列 `__expiry_s` を足す。
     - q_total: expiry が真なら `(SELECT CEIL(EXTRACT(EPOCH FROM (MIN(d.posted_ts) + make_interval(hours => :expiry_hours) - NOW())))::bigint FROM {facet_src} d)`。偽なら `NULL::bigint`。CEIL（切り上げ）にするのは、行が外れる前に読み直してしまう無駄を避けるため。
     - q_page・q_facet: `NULL::bigint`。
     - docstring の列並びを「__kind, __total, …, __ord, __expiry_s, __f_* の5列」に直す。
   - facet_src（まとめなし・利用者の絞り込みなし）を使う理由:
     - まとめた行の中身が外れても、まとめの件数が変わる。
     - 絞り込み候補も、同じ集合から作っている（:315-319）。
     - rows_f だけでは、この2つの変化に気づけない。
     - 絞り込みで隠した行が外れたときにも読み直すが、間隔は最短 60 秒（画面側）なので負荷は増えない。
   - 呼び出し側（:372-397 付近）の変更:
     - `expiry = bool(window_hours)` を渡す。ここで使う window_hours は :372-375 のローカル変数（実効の窓）で、応答の `window_hours`（:435、max_age_hours のまま）とは別物。実効の窓は次のとおり。
       - fresh_only=false: max_age_hours。0 のときは絞らないので期限なし（expiry は偽）。
       - fresh_only=true: `min(max_age_hours, 24)`。max_age_hours=0 のときは 24（:375）。expiry は常に真。
     - expiry が真のときは params に `"expiry_hours": window_hours` を足す。
     - 結果の処理ループ（:401-413）で、kind が total の行から `expiry_s = row["__expiry_s"]` を取る。
   - 応答（return :426-437）に `next_expiry_in_seconds=expiry_s` を足す（None は「外れる行なし」）。max_age_hours が None で早く返す枝（:366-370）は None にする。
4. `backend/app/schemas/inventory_offers.py` の InventoryListResponse（:187-203）
   - `next_expiry_in_seconds: int | None = None` を足す（このファイルの書き方に合わせる）。
   - 説明は「いま出ている行（まとめ前・絞り込み前）のうち最も早く時間の枠から外れる行まで、あと何秒か。負は既に外れている。None は外れる行なし」。

### frontend
5. 新規 `frontend/src/hooks/useExpiryRefresh.ts`
   ```ts
   /**
    * ADR-1016 改訂 2026-10-19: 行が時間の枠から外れる時刻に 1 回読み直す。
    * - seconds が null なら何もしない
    * - 待ち時間 = clamp(seconds, 60, 86_400) 秒 + 0〜3 秒のずれ（最短 60 秒で連続読み直しを防ぐ・setTimeout の上限内）
    * - 裏のタブの間は保留し、表に戻ったとき保留があれば 1 回だけ呼ぶ（useRealtimeRefresh と同じ）
    * - seconds か resetKey が変わる（＝読み直した）たびに張り直す
    */
   export function useExpiryRefresh(seconds: number | null, reload: () => void, jitterMs: number, resetKey: number): void
   ```
   - 定数は `EXPIRY_MIN_S = 60`、`EXPIRY_MAX_S = 86_400`。
   - 中身は useRealtimeRefresh と同じ形にする（reloadRef、timer、pending、visibilitychange）。
   - 依存は `[seconds, jitterMs, resetKey]`。
6. `frontend/src/pages/inventory/InventoryPage.tsx`
   - :49-50 の型に `next_expiry_in_seconds?: number | null;` を足す。
   - state `nextExpirySeconds`（初期値 null）を足す。:223-224 の隣で `setNextExpirySeconds(d.next_expiry_in_seconds ?? null)` とする。
   - :242-244 の下に、次を足す。
     ```ts
     useExpiryRefresh(nextExpirySeconds, () => { if (filtersLoaded) void load(); }, expiryJitterMs, loadCount)
     ```
     - expiryJitterMs は refreshDebounceMs と同じく useState の初期化で `Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS)` とする。
   - `loadCount`（読み込みが終わるたびに +1 する state）を resetKey に渡す。同じ秒数が続けて返っても、タイマーを張り直すため。
     - 成功でも失敗でも +1 する（load の finally で更新する）。古い応答として捨てたときは +1 しない（loadSeq で判定）。
     - 失敗のときは nextExpirySeconds を変えないので、同じ秒数で張り直す。最短 60 秒なので、失敗が続いても読み直しは毎分 1 回までになる。
   - 文言・CSS・色の変更はない。

### ADR
7. `docs/adr/ADR-1016-realtime-change-signal-standard.md` に「改訂 2026-10-19」を、「改訂 2026-10-18」の後に足す（Opus が書く）。
   - 本文の決定1〜9と、前の改訂は書き換えない。

### 試験
8. `backend/tests/test_realtime_topics.py` に足す試験:
   - `test_inventory_signal_routes_exist_and_are_writes`: 45 本が実在し、書き込みメソッドである。
   - `test_inventory_signal_routes_count`: 45 本ちょうどで、上の一覧と一致する（一覧は試験内に書く。増減は設計の改訂を通す）。
   - 既存の :76-79（WRITE に shared なし）は変えない。
9. `backend/tests/test_realtime_middleware.py` に足す試験:
   - INVENTORY_SIGNAL_ROUTES の経路が 2xx を返すと、("tcg.inventory","shared") を 1 回出す。
   - 4xx では出さない。
   - value-override のように両方の表に載る経路では、("tcg.review","global") と ("tcg.inventory","shared") の2回を出す。
   - tcg.inventory の合図の origin は、x-client-id ヘッダがあっても None になる。tcg.review の合図の origin は今までどおりヘッダから入る。
   - INVENTORY_SIGNAL_ROUTES は frozenset なので、`monkeypatch.setattr(mw, "INVENTORY_SIGNAL_ROUTES", frozenset({...}))` で差し替える（既存の :18-26 は辞書なので setitem を使っている）。
10. 在庫 API の試験。PG が要るので CI で動かす。既存の `backend/tests/test_inventory_distribution_rows_pg.py` の fixture にならう。
    - posted が NOW()-23h の行があり、窓が 24 のとき、next_expiry_in_seconds は 3600±120 になる。
    - fresh_only=false かつ max_age_hours=0 のときは None になる。
    - fresh_only=true かつ max_age_hours=0 のときは、24h を基準に計算する（posted が NOW()-23h の行で 3600±120）。
    - 行が 0 件のときは None になる。
    - fresh_only=true で max_age_hours=48 のときは、24h を基準に計算する。
    - 在庫一覧の SQL は SQLite では実行されない（`backend/tests/test_inventory_list_view.py:1-9` は 422 の確認だけ）。実際の SQL は `backend/tests/test_inventory_distribution_rows_pg.py`（PostgreSQL）で確かめる。
    - `backend/tests/test_inventory_distribution_rows_pg.py:348` は "__" の付いた列名を完全一致で確かめている。期待値の `"__ord"` の次に `"__expiry_s"` を足す（このファイルは触るファイルに入る）。
    - 実装中に見つかった追加（2026-10-19）: `backend/tests/test_inventory_distribution_rows.py:116-119` の `_VIEW_SQL_BEFORE` は、SQL 全体の長さと SHA256 を固定している。列を足すと必ず変わるので、新しい値に更新する（このファイルも触るファイルに入る）。試験の意図（fresh_only=false の SQL が変わらないこと）は保ち、列の追加以外が変わっていないことは PG 試験の total・page・facet の一致で確かめる。
    - 審査で見つかった追加（2026-10-19、コード審査 REVISE R1）: 応答の形に `next_expiry_in_seconds` を足すので、API の形の控え `frontend/api-contract/openapi.json` を `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` で作り直す（このファイルも触るファイルに入る。必須チェック「API contract is up to date」が守る）。
11. 新規 `frontend/src/hooks/useExpiryRefresh.test.tsx` に足す試験:
    - seconds=120 のとき、120 秒＋ずれの後に reload を 1 回呼ぶ。
    - seconds=5 のとき、60 秒より前には呼ばない。
    - null のときは呼ばない。
    - 隠れタブの間は保留し、表に戻ったときに 1 回呼ぶ。
    - resetKey が変わると、タイマーを張り直す。
    - 外したとき（unmount）にタイマーを消す。

## 負荷の見込み
- 便3 の実測では、同時に開いている在庫表は最大 9 画面（docs/handoff/inventory-auto-refresh/design.md）。
- 書き込みの合図: 商品・検索語・仕入元の更新は 24h で数十件（recon §5）。5〜8 秒のまとめがあるので、1 画面あたりの読み直しは書き込み 1 回につき最大 1 回。
- 枠からの脱落: 1 画面あたり最大で毎分 1 回。9 画面で毎分 9 回、0.15 回/秒。
- 在庫 API の中央値は 0.41〜0.51 秒（便2 の実測）。MIN の集計は facet_src を 1 回読むだけで、この集合は facet の DISTINCT で既に作っている。追加の時間は K7 で測る。

## リスクと対処
| リスク | 対処 |
|---|---|
| 一覧の書き漏れで、ある経路の編集が反映されない | 一覧は試験で数を固定する。経路を足すときは、設計の改訂で表に入れる。漏れが見つかれば同じ表に足すだけで済む |
| 一般の権限の利用者の編集で、他社の画面も読み直す | 合図は名前だけで、届くのは「時刻」だけ。まとめ時間で連打をならす |
| 枠の脱落で読み直しが続く | 最短 60 秒、ページごとに 0〜3 秒のずれ |
| `__expiry_s` の列を足すことで UNION ALL の列がずれる | 3枝すべてに同じ位置で足す。既存の在庫表の試験（SQLite と PG）が通ることを K3 で確かめる |
| PC の時計ずれ | 秒数はサーバーの NOW() で計算し、画面は相対時間で待つ |

## 受入条件
| 基準 | 検証方法 |
|---|---|
| K1 45 本の表があり、実在する書き込みで、数が一致する | pytest `backend/tests/test_realtime_topics.py` |
| K2 2xx のとき tcg.inventory を shared で出す。4xx では出さない。両方の表に載る経路は2回出す | pytest `backend/tests/test_realtime_middleware.py` |
| K3 next_expiry_in_seconds が、3600±120・None（fresh_only=false かつ max_age_hours=0）・None（0件）・fresh_only=true の24h基準（max_age_hours=0 と 48 の両方）になる。既存の在庫表試験も通る | CI の pytest（PG を含む） |
| K4 画面が最短60秒・上限86400秒で読み直し、隠れタブでは保留し、null では動かない | vitest `frontend/src/hooks/useExpiryRefresh.test.tsx` と既存の在庫表の試験 |
| K5 CI の必須チェックが全て緑。tsc・eslint・ruff も含む | gh pr checks |
| K6 本番で、対象の経路の 2xx の書き込みから 10 秒以内に、在庫表を開いていた他の接続の GET /api/v1/inventory がある | nginx のログで照合する。デプロイ後 72h に該当が無ければ「未観測・保留」と書く |
| K7 デプロイ後 24h で /api/v1/inventory の 5xx が 0 件、中央値が 1.0 秒以下（基準 0.406 秒、bin2/prod3/q50.json） | 便3 と同じ方法（/tmp/CC報告ファイル/inventory-speed/slow10/q.sh） |
| K8 本番で、画面の既定と同じ fresh_only=true の条件で、`:expiry_hours` に実効の窓 W（= 本番の max_age_hours が 0 なら 24、それ以外は min(max_age_hours, 24)）を入れた SELECT（q_total の `__expiry_s` 式）の値が、null か「0 ≤ 値 ≤ W×3600」を満たす。配信 JS に `next_expiry_in_seconds` の文字列がある | reader 鍵で SELECT だけを実行する。max_age_hours は同じ鍵で distribution settings を読む。reader 鍵（ai_ro のビュー経由）で head の SQL がそのまま動かないときは、ビューの名前に置き換えて同じ式を組む。組めなければ「未観測・保留」と書き、K3 で判定する。配信 JS は curl と grep で確かめる |

## 維持の仕組み
- 守り手: backend/tests/test_realtime_topics.py（45本の数と実在を固定する。CI の pytest で毎回走る）。
- 一覧は INVENTORY_SIGNAL_ROUTES の 1 か所だけに置く（データの分散なし）。数の試験があるので、変えるときは設計の改訂を通す。
- 新しい書き込みの経路は、既存の試験（:34-39）で WRITE か NO_SIGNAL への記載が必ず求められる。在庫表が読む表に書く経路の場合は、この表にも入れるかを ADR-1016 改訂の規則で判断する。
- 戻し方: この PR を revert する。DB の変更は無い。

## 外部・過去事例の参照と我々への応用
外部事例は該当なし。過去事例（自社）は便3（docs/handoff/inventory-auto-refresh/design.md、#4516）で、抽出の完了に rt:shared の合図を足し、5〜8秒で読み直す形が本番で動いた。応用として、今回は同じ合図と同じまとめ時間を、書き込みの経路にも広げる。理由: 変更は自社の既存の仕組み（ADR-1016 の合図・便3 の rt:shared）を足すだけで、外部の数値を根拠にする判断が無い。負荷は自社の実測（便2・便3）で見積もった。

## GAS 在庫一覧との揃え
対象外。GAS 在庫一覧には SSE の接続が無く、この仕組みを使えない（feedback_app_inventory_gas_parity の「省く理由」）。

## 審査記録
- 1回目（2026-10-19、reviewer・opus）: REVISE。骨格（経路の選び方、middleware の位置、__expiry_s、フック）は正しいと判定された。指摘は次の16点で、全て反映した。
  - 1 SQL の括弧を直し、CEIL にした。
  - 2 `expiry: bool = False` にし、pg 試験 :348 を触るファイルに加えた。
  - 3 SQLite の一文を事実で書き直した。
  - 4 aliases の6本を外し、51本を45本にした。
  - 5 在庫の合図の origin を None にした。
  - 6 範囲を TASK_TOPICS から引くようにし、:26 のコメントを直した。
  - 7 ADR の決定番号を 3・4 に直した。
  - 8 タブ名を対象外と明記した。
  - 9 行番号を直した。
  - 10 失敗後も張り直す形に決めた。
  - 11 試験の差し替え方を setattr にした。
  - 12 完了条件の秒数と K8 を、○×が一つに決まる形にした。
  - 13 閲覧ページを対象外と明記した。
  - 14 purchase-orders を「入れないもの」に加えた。
  - 15 recon の未確認を事実で埋めた。
  - 16 tcg_extraction.py:832 を加えた。
- 2回目（2026-10-19、reviewer・opus）: REVISE（軽微）。前回の16点は全て解消していると確認された。必須の2点を反映した。
  - R1 K8 の窓を実効の窓 W に固定し、fresh_only=true と `:expiry_hours`=W を明記した。reader 鍵で組めないときの扱いも書いた。
  - R2 試験10と K3 の「None」に、fresh_only=false の条件を付けた。fresh_only=true かつ max_age_hours=0 の場合も加えた。
  - product-categories は審査で確定した（書き込みは tcg_product_categories だけで DELETE は無く論理削除。在庫表の SQL はこの表を JOIN しない）。「入れないもの」に移し、実装役への確認依頼は外した。
- 判定（Opus）: 残りの指摘は任意の文言だけで、事業判断の要る点は無い。実装へ進める。
- 判定（Opus）: 事業判断が要る点は無い。2回目の審査に回す。
