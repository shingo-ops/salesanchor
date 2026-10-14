<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。 -->
# Phase 3 design — realtime-standard（即時反映をアプリ全体の標準にする）

**状態**: PO 承認済み（2026-10-15）・実装未着手  
**recon**: `docs/handoff/realtime-standard/recon.md`  
**ADR 案**: `docs/adr/ADR-1016-realtime-change-signal-standard.md`（Proposed）

## 0. PO の言葉（2026-10-14〜15）

- 「こういった更新があったときにアプリに即時反映させることは出来る？」
- 「データの読み込み速度は落とさずに変更点や更新があったら即時反映させたい…実現させることは出来るか？実現するためには何が必要化？」
- 「全てのページにおいてこの仕組みを横展開してアプリ全体の標準仕様とすることは出来る？」
- 進め方の案（通り道を1本にする／保存したら合図を出すことを ADR で標準にする／送り忘れを自動チェックで止める／要確認ページから始める／DB の直接修正は対象外）への返答は「Y」。

## 1. KGI と KPI（PO が画面で○×を判定できる粒度）

| # | 成功条件 | 判定 |
|---|---|---|
| G1 | 要確認ページを2つの画面（別のタブや別の端末）で開く。片方で「このままで良い」を確定すると、もう片方の一覧から、その行が5秒以内に消える。再読み込みのボタンは押さない。 | ○× |
| G2 | G1 のとき、もう片方の表は空にならず、「読み込み中」の全面表示も出ない。表を出したまま差し替わる。 | ○× |
| G3 | 要確認一覧を最初に開く速さが、変更前の1.2倍以内。基準: 本番で変更前後をそれぞれ5回測った中央値。 | 数値 |
| G4 | 新しい書き込み API を足したとき、その API が「合図の対応表」に無く、「合図を出さない理由」も書かれていなければ、CI が赤になる。 | ○× |
| G5 | 自分の保存では、自分の画面は二重に読み直さない。読み直しは保存の処理の中で1回だけ行う。 | ○×（ネットワークの記録で確認） |
| G6 | 既存の受信箱とリードの即時反映が、変更前と同じように動く。 | ○× |

KPI（合図を受けた画面が読み直す回数と、サーバーの負担）
- 合図が連続して来たら、1.5秒の間に来たものをまとめて、読み直しは1回にする。
- タブが裏にある間は読み直さない。表に戻ったときに、その間に合図が来ていた場合だけ1回読み直す。

## 2. 対象と対象外

対象（この設計で決めて、段階1で作るもの）
- 共通の通り道（SSE）を1本にし、合図の形を1つに決める。
- API の書き込みが成功したら、合図を自動で送る仕組み。
- 裏の処理（Celery）が書き換えたときに、明示的に合図を送る関数。
- 画面側で使う共通の部品（Provider とフック）。
- CI のチェック（G4）。
- 最初に当てる画面: 要確認ページ（`frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx`）。

対象外
- DB を直接 SQL で直したとき（運用スクリプトを含む）。これは合図が出ない。理由は §7 R5。
- 既存の受信箱とリードの通り道を新しい通り道へ移すこと。段階3で別のカードにする。
- データの中身を合図で送ること。合図は「何が変わったか」の名前だけにする。
- 他のページへの展開。段階2で、使う頻度の高い順に1画面ずつカードを作る。

## 3. 変更前と変更後

| 観点 | 変更前（recon の行番号） | 変更後 |
|---|---|---|
| 通り道 | 受信箱とリードの2本だけ（recon §1） | GET /api/v1/events/stream の1本に、どのページも相乗りする。既存の2本は段階3まで残す。 |
| 合図の中身 | 固定の文字列 "update"（sse_pubsub.py:74） | `{"topic":"tcg.review","origin":"<client-id>"}`。topic は §4 の対応表の名前。 |
| 合図を送る場所 | 書き込み処理に手で書いた5か所（recon §1） | 書き込み API は middleware が自動で送る。裏の処理は publish_change(topic, scope) を明示的に呼ぶ。 |
| Redis との接続 | publish のたびに接続し、購読も1本ごとに接続する（sse_pubsub.py:72-76, :85） | publish は共有の接続プールを使う。購読はプロセスにつき1本にし、受け取った合図をメモリの中で各画面の接続に配る。 |
| 会社の分け方 | inbox:{tenant_id} などのチャンネル | 会社ごとのチャンネル rt:t:{tenant_id} と、会社をまたぐ共用データ用の rt:global（super admin だけが受け取る）。 |
| 画面側 | useSSE を画面ごとに呼ぶので、呼んだ数だけ通り道が開く（recon §1） | Shell に RealtimeProvider を1つ置き、通り道は1本にする。各画面は useRealtimeRefresh(topics, reload) を呼ぶだけ。 |
| 読み直し | 手で再読み込みする | 合図をまとめてから、表を残したまま読み直す（NeedsReviewTabsPanel.tsx:82 の作りを使う）。 |

## 4. 仕組みの詳細

### 4-1. 合図の対応表（ここだけが正本 = SSOT）
- 置き場所: backend/app/realtime/topics.py（新規）。
- 中身は「ルートのテンプレート（例 /tcg/items/{item_id}/review-ack）とメソッド → topic と範囲（tenant か global）」の一覧と、「合図を出さないルート → 理由」の一覧。
  - 照合のキーは、URL 文字列の前方一致ではなく、FastAPI がリクエストごとに入れる request.scope["route"].path にする（fastapi/routing.py:807,1001。審査で確認済み）。CI の G4 検査も app.routes の path を使うので、同じキーで突き合わせられる。
  - 段階1の初期の行（実際のルート。審査で確認済み）
    - POST /tcg/items/{id}/review-ack（`backend/app/routers/item_corrections.py`:178-179）→ ("tcg.review", global)
    - 要確認一覧の読み直し先は GET /tcg/analysis-results（`backend/app/routers/tcg_analysis_review.py`:116）。
- 「このままで良い」を保存すると、その行はすぐ要確認から外れる。一覧の SQL が、保存された確認（review_ack）を毎回読んで除外しているからである（`backend/app/services/tcg_condition_review_svc.py`:190-206, :229, :236）。2026-10-14 の倉田さんの件で、保存を消したら行が画面に戻ったことも確かめた。だから再解析を待たずに、保存の直後の合図だけで G1 を満たせる。
- CI では、super admin 専用のルート（require_super_admin に依存するもの。`backend/app/auth/dependencies.py`:491）が範囲 global になっているかも照合する。共用データを tenant に分類してしまい、合図が届かない事故を防ぐため。
- 画面側が使う topic 名は、frontend/src/lib/realtime/topics.ts に置く。backend の一覧から生成した定数である。手で書かず、CI で backend と一致するかを照合する。

### 4-2. 書き込み API の自動合図
- backend/app/middleware/realtime.py（新規）で行う。
- 対象は POST/PUT/PATCH/DELETE で、状態コードが200〜299のものだけ。4xx は送らない。この条件は監査の 500 未満（audit.py:106-139）とは違う。
- パスを対応表で引き、topic と範囲を決める。
- 会社 ID の取り方: get_current_tenant（`backend/app/auth/dependencies.py`:242）に request: Request を足し、request.state.rt_tenant_id = safe_id を記録する。middleware は応答のあとでこの値を読む。
  - 値が無いときは、会社別の合図を送らない（安全側に倒す）。範囲が global の topic は、会社 ID が無くても送る。
  - 審査で確かめたこと: Starlette 0.52.1 のソースでは、request.state は scope["state"] を包んでいる（requests.py:186-189）。middleware と下の処理は同じ scope を使う（middleware/base.py:106, :144）。だから、依存関数が入れた値を応答後に読める。
  - 【未確認】本番で固定している starlette==1.3.1（backend/requirements.txt:2）でも同じか。段階1の最初の pytest で確かめ、読めなければ止めて再設計する。
  - super admin 専用のルートは get_current_tenant を通らない（dependencies.py:491）。だから会社 ID は入らず、範囲 global の合図だけが出る。
- 画面は全リクエストに X-Client-Id（タブごとに決める乱数）を付ける。middleware はこの値を origin として合図に入れる。CORS の allow_headers（backend/app/main.py:216）に X-Client-Id を足す。
- publish は応答の本文を送り終えてから行う（BackgroundTask か asyncio.create_task。応答を遅らせない）。失敗しても書き込みの結果は変えない（fail-open。既存の sse_pubsub.py:77-80 と同じ）。

### 4-3. 裏の処理の合図
- app.realtime.publish_change(topic, scope, tenant_id=None) を呼ぶ。Celery のタスクは同期で動く（tcg_extraction.py:696-713 は同期セッション）。既存の sse_pubsub は非同期の Redis だけを使う（sse_pubsub.py:12）。だから、同期版の publish_change_sync も用意する。
- 合図は、データを書き終えた場所で出す。仕事を積むだけの場所（例: tcg_line_import_svc.py:761 の .delay()）では出さない。
- 段階1では、要確認に関係する次の2か所の末尾に入れる。
  - 解析のやり直し（reanalyze_v102_job、`backend/app/tasks/tcg_extraction.py`:696-720）
  - 1通の取り込み解析（extract_source_message_task、`backend/app/tasks/tcg_extraction.py`:775）
- 残りの裏の処理（recon §3 の43行）は、段階2で画面を広げるときに、その画面に関係するものから入れる。

### 4-4. 通り道（SSE）
- GET /api/v1/events/stream（新規 router）。
- 認証は既存と同じで、Authorization ヘッダーを使う。
- 受け取るのは、自分の会社のチャンネルと、super admin なら global。
- 30秒ごとにハートビートを送る。接続数の上限は1ユーザー5本（タブ数の目安）。
- nginx には、既存と同じ設定（proxy_buffering off、read_timeout 3600s）で、この1本用の location を足す。app 側と api 側の両方に足す。
  - これは nginx の変更なので、危険 PR として PO の GO が要る（CLAUDE.md の「危険PRのGO手順」、ADR-135）。§6 を参照。
  - 【未確認】既存の /api/ location（nginx.conf:151-163、read_timeout 120s）でも、30秒のハートビートと X-Accel-Buffering: no（leads.py:2923）があれば通るかもしれない。通らないときに備えて、段階1は nginx の追加を含めた形にする。

### 4-5. 画面側
- frontend/src/lib/realtime/RealtimeProvider.tsx（新規）
  - DesktopShell と MobileShell に1つずつ置く。
  - 再接続は useSSE と同じく指数バックオフにする。
- frontend/src/hooks/useRealtimeRefresh.ts（新規）
  - topics が合う合図だけを拾い、origin が自分なら無視する。
  - 1.5秒の間に来た合図をまとめる。document.hidden の間は保留し、visibilitychange で表に戻ったら1回読み直す。
  - 再接続できたときは、途中で合図を取りこぼしたかもしれないので、1回読み直す。
- 要確認ページの段階1の変更は、reloadKey を進める1行を足すだけにする。表を消さない読み直しは今の作りのまま使う（NeedsReviewTabsPanel.tsx:82）。

## 5. 代替案と選んだ理由

| 案 | 内容 | 採否と理由 |
|---|---|---|
| A. 一定間隔で読み直す（ポーリング） | 30秒ごとなど | 不採用。即時にならない。要確認の読み直しは1回数秒かかるので（recon §5）、開いている間ずっと負担がかかる。 |
| B. WebSocket | 双方向の通信 | 不採用。必要なのはサーバーから画面への一方向だけ。nginx の SSE 設定と認証の型がすでにある（recon §2）。 |
| C. データの中身も合図で送る | 画面が差分を当てる | 不採用。会社の分け方と権限を合図の側でも二重に守る必要があり、データの持ち方が分散する（PO の「データを分散させない」に反する）。読み直しは既存の API 1本だけで行う。 |
| D. 各ルーターに手で publish を書く | 今の5か所のやり方 | 不採用。360件の書き込みで書き忘れが起きる。G4 を機械で守れない。 |
| E. DB の変化を拾う（LISTEN/NOTIFY・トリガー） | DB 直接修正も拾える | 今回は不採用。表ごとのトリガーという新しい仕組みが要り、migration が増える。段階4の検討にとどめる。 |
| 採用 | 通り道1本＋合図は名前だけ＋middleware で自動送信＋対応表を CI で検査 | 既存の作り（AuditMiddleware、SSE の nginx 設定、表を消さない読み直し）をそのまま活かせる。 |

## 6. 段階計画

| 段 | 中身 | PO の GO |
|---|---|---|
| 0 | この設計と ADR-1016 を docs PR にする | 設計の承認（今回お願いする） |
| 1 | 共通の土台（backend の realtime と middleware、通り道、frontend の Provider とフック、CI チェック）、nginx の location 追加、要確認ページへの適用 | nginx を含む。`backend/app/auth/` と新しい API もあるので A 区分（ADR-1015）。危険 PR として GO #番号 が要る |
| 2 | 他のページに1画面ずつ広げる（使う頻度の高い順）。裏の処理の合図も追加する | 画面と対応表だけ（frontend と backend の routers・services・realtime）なら ADR-1003 の委譲で進める。`backend/app/tasks/`（裏の処理）や `.github/` を触る便は A 区分（ADR-1015:17）なので PO の GO を取る |
| 3 | 受信箱とリードを新しい通り道に移し、古い通り道2本を消す | nginx の変更なので GO が要る |

## 7. リスクと対処

- R1. 合図のたびに一覧を読み直して、サーバーが重くなる。
  - 対処: 1.5秒まとめる。裏にあるタブは読み直さない。自分の保存は無視する。
  - 測り方: 段階1のあと、本番の要確認 API が1分あたり何回呼ばれたかを、反映前後で比べる。
- R2. 他の会社の合図が届く。
  - 対処: チャンネルを会社 ID で分ける。会社 ID が取れないときは送らない。global は super admin だけが受け取る。
  - 試験: 会社1の書き込みで会社2の接続に合図が来ないこと。
- R3. 通り道が増えて、接続数が上限にかかる。
  - 対処: 1タブ1本。HTTP/2 なのでブラウザの6本制限は受けない（recon §2）。
- R4. Redis が止まる。
  - 対処: fail-open にして、書き込みは成功させる。画面はつなぎ直したときに1回読み直す。
- R5. DB を直接直したときに合図が出ない。
  - 対処: 対象外と ADR に明記する。運用で直したあとは、画面で再読み込みしてもらう。
- R6. ワーカーを2つ以上に増やしたとき。
  - 対処: 購読はプロセスごとに1本で、Redis を経由して全プロセスに届く作りなので、そのまま動く。接続数の上限はプロセスごとに数えるので、ADR に注記する。
- R7. 【未確認】本番が Cloudflare を経由しているか。
  - 既存の SSE 2本が本番で動いているので、同じ設定なら通る見込みだが、段階1の受入確認（G1）で実機を見て確かめる。

## 8. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| G1 2画面のうち片方で確定すると、もう片方から5秒以内に行が消える | 本番で Playwright のタブを2つ開いて操作し、スクリーンショットと時刻を残す |
| G2 読み直しのときに表が空にならない | 同じ記録の中で、読み直し中も表の行が残っていることを確認する |
| G3 最初に開く速さが1.2倍以内 | 変更前後で、本番の要確認 API の応答時間を5回ずつ測り、中央値を比べる |
| G4 対応表にない書き込み API があると CI が赤 | pytest で、全ルートを列挙して対応表と照合する。わざと漏らしたブランチで赤になることを示す |
| G5 自分の保存で二重に読み直さない | vitest で、origin が自分の合図では reload が呼ばれないこと。本番のネットワーク記録でも確認する |
| G6 受信箱とリードの即時反映が変わらない | 既存の試験 test_sse_pubsub.py が緑。本番で受信箱に新着が出ることを確認する |
| R2 他の会社に合図が漏れない | pytest で、会社1の publish が会社2の購読に届かないこと |
| §4-2 の未確認事項 | pytest で、依存関数が入れた request.state の値を middleware が読めること（starlette==1.3.1 で、段階1の最初に確認する） |
| 接続上限 | pytest で、1ユーザー6本目の接続が 503 になり、既存の5本は切れないこと |
| 再接続のあとの読み直し | vitest で、再接続できたときに reload が1回だけ呼ばれること |
| 裏にあるタブの保留 | vitest で、document.hidden の間に合図が来ても reload は0回、表に戻ったときに1回であること |
| super admin ルートの範囲 | pytest で、require_super_admin に依存する書き込みルートが、対応表で global になっていること |
| 応答を遅らせない | pytest で、publish が応答の本文を送ったあとに行われること（publish を遅くしても、応答時間が変わらない） |

## 9. 外部・過去事例の参照と我々への応用

- 過去事例（この repo）
  - 受信箱とリードの SSE（recon §1）は本番で動いていて、nginx の設定と認証の型が実績になっている。
  - ただし、合図が "update" だけなので、ページを増やすたびにチャンネルと通り道が増える作りだった。今回はこれを1本にまとめる。
- 外部の考え方
  - 「合図で知らせて、データは画面が取りに行く」というやり方は、変更の合図だけを送る一般的な方式で、データの正本を API 1か所に保てる。
  - 【未確認】具体的な他社の数値は集めていない。この設計の成否は、§8 の自前の測定で判断する。外部の数値は根拠にしない。

## 10. 維持の仕組み

- 守り手: backend/tests/test_realtime_topics.py（段階1で作る CI 検査。全ての書き込みルートが、対応表か「出さない理由」の一覧に載っていることを確かめる）

- 合図の対応表は backend/app/realtime/topics.py の1か所だけに置く。画面側の topic 名は、そこから生成して CI で照合する。
- 書き込み API を新しく足すときは、対応表に足すか、「出さない理由」を書く。書かなければ CI が赤になる（G4）。
- 新しいページが即時反映を使うときは、useRealtimeRefresh を1行呼ぶだけにする。独自の通り道を作ることは ADR-1016 で禁止する。
- ADR-1016 を docs/adr/FEATURE-INDEX.md に載せ、指さなくても見つかるようにする。

## 11. 設計審査

- 審査役: Fable（architect）。同じ AI 系統による審査であり、独立した第三者のレビューではない。
- 1回目（2026-10-15）: REVISE。必須の修正は6件。
  1. 対応表の初期の行を実際のルートに直す。
  2. 裏の処理の合図を、データを書き終えた場所に移す。同期版も用意する。
  3. 段階2の tasks/ は A 区分にする。
  4. 照合のキーを scope["route"].path にそろえる。
  5. 接続上限・再接続・裏タブの受入条件を足す。
  6. ADR-136 の参照先を直す。
  - 6件とも、上の各節に反映した。
- 2回目（2026-10-15）: APPROVE。
  - 非ブロッキングの指摘が3件あった。
    - ADR の文言をそろえる。反映済み。
    - starlette 1.3.1 と Cloudflare は未確認。§8 で段階1の最初に確認する。
    - 段階1の PR 本文では、危険パスを1つずつ書き出す。
  - 承認された範囲: §2 の段階1。
  - 実装の条件:
    - 既存の SSE 2本、受信箱、リードには触らない。
    - request.state を共有できるかの pytest を最初に書き、失敗したら止める。
- PO 承認: 2026-10-15、「この設計をアプリ全体の標準として採りますか」に PO が「Y」。段階1の実装に進む。本番反映の前に、PO の「GO #番号」を取る。
