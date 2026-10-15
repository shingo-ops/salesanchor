<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 在庫の閲覧専用ページ（GAS 在庫一覧の置き換え）

**対象ADR**: ADR-1016（草案・Proposed。`docs/adr/ADR-1016-inventory-viewer-separate-accounts.md`）  
**recon**: docs/handoff/gas-viewer-fresh-fast/recon.md ／ docs/handoff/gas-viewer-fresh-fast/security-recon.md  
**審査**: r1 REVISE（Blocking 2、Non-blocking 11。/tmp/CC報告ファイル/viewer_design_review.txt）→ r2 REVISE（Blocking 1、Non-blocking 9。/tmp/CC報告ファイル/viewer_design_review_r2.txt）→ r3 REVISE（Blocking 1、Non-blocking 7。/tmp/CC報告ファイル/viewer_design_review_r3.txt）→ r4 で全件に対応し、PO 決定 Q2a（メールのリンクでログイン）を反映 → r4 REVISE（Blocking 1、Non-blocking 6。/tmp/CC報告ファイル/viewer_design_review_r4.txt）→ r5 で全件に対応 → r5 APPROVE（Blocking 0、Non-blocking 6。/tmp/CC報告ファイル/viewer_design_review_r5.txt）→ 本版で N-34〜N-39 を反映した（KPI の重複の指摘は、実物に重複が無いため対応なし）  
**日付**: 2026-10-15  
**担当**: Planner（Claude Opus）  
**状態**: 設計案（草案）。PO 決定待ちの項目が残っているので、実装には進めない（§PO 決定待ち）。

---

## KGI（PO 決定、2026-10-14〜15 のチャットの要旨）

1. GAS 在庫一覧をアプリと同じ鮮度にする。目標は「開いてから表が出るまで1秒以内」。
2. 閲覧は自社サーバーの URL で行う。
3. 閲覧者はフォームで申し込む。トライアルは2週間だけ閲覧できる。本契約者は期限なく閲覧できる。
4. サーバーは1分に1回だけ表を作り、閲覧者全員に同じものを配る。鮮度は最大1分遅れでよい（PO y）。
5. 閲覧者には在庫表以外を一切見せない。閲覧者はアプリのユーザー（tenant_002）にせず、別の閲覧専用アカウントにする（PO Y、2026-10-15）。

## 現在地（recon の要点。根拠は origin/main 0c7852fd9 で照合した）

- GAS は Google の枠を読むだけで 3.3〜6.7 秒かかる。コードを直してもこの時間は縮まない（recon.md §2）。
- 在庫の行の定義は1か所にある（ADR-1014 の distribution_rows_sql）。中身は `backend/app/services/tcg_distribution_svc.py`:274-371 の distribution_rows_parts で、14 列を返す fetch_output_rows（:390-412）がこれを使う。fetch_output_rows はテナント文脈を自分では設定しない。
- 今の GAS が表示している列は 13 列（ALLOWED_HEADERS。GAS のコードはリポジトリ外にある）。
- アプリのユーザーにすると、在庫を見るだけの権限にしても 614 本中 74 本の入口に届く（security-recon.md §2）。
- get_current_user（`backend/app/auth/dependencies.py`:116-239）がトークンを受け付ける経路は4本ある。
  - (a) スモーク用トークン
  - (b) Redis の `jwt:<sha>` キャッシュ。キャッシュに当たると署名を検証しない。
  - (c) iss が "salesanchor" のトークン。署名は `backend/app/auth/self_tokens.py`:86-132 で作り、検証する。
  - (d) Firebase
- 自社トークンには「種類」を表す欄（typ・aud）が無い（self_tokens.py:86-98）。
- 期限・契約・トライアルを持つ表は無い。
- Celery から fetch_output_rows を呼ぶ前例は `backend/app/tasks/tcg_extraction.py`:725-757（async engine を1回作って asyncio.run で回す。テナント文脈なし）。Redis に JSON を置く前例は `backend/app/tasks/dashboard.py`（周期 600 秒）。beat の周期で最短のものは 300 秒（`backend/app/celery_app.py`:137）。
- frontend の nginx は、すべてのパスを index.html に戻す（frontend/nginx.conf:23-25）。

---

## 設計（変更前 → 変更後）

### D1. 閲覧専用アカウントと、アプリと交わらないトークン（審査 B-1 への対応）
- 変更前：外部の人を入れるには、アプリのユーザー（public.users）にするしかない。
- 変更後：
  - 新しい表 public.viewer_accounts を作る。migration では表を作るだけで、データは入れない。
  - 列：id、email（一意）、line_name（LINE の表示名）、inventory_issue（在庫関連の課題。自由記述。TEXT。1000文字まで。任意か必須かは Q2g）、状態（pending ／ verified ／ trial ／ active ／ suspended の5値。verified は「メール確認済み・承認待ち」で、Q5 が自動トライアルなら使わずに trial へ進む。Q5 の答えで migration を作り直さずに済むよう、先に5値で作る）、email_verified_at、trial_expires_at、作成・更新の日時。
  - テナントは持たない。
  - ログインの方法：メールに届くリンクを押してログインする。パスワードは持たない（PO 決定 Q2、2026-10-15）。PO の条件は「リンクを知っていれば誰でも見られる形にはしない。登録フォームに入力した情報で管理する」。これを次の仕組みで守る。
    - ログイン用のリンクは、viewer_accounts に登録済みで、状態が active か「期限内の trial」の email にだけ送る。登録されていない email、pending・verified・suspended の email、期限切れの trial の email には送らない（審査 N-31）。どの場合も応答は同じ 200 にして、登録済みかどうかを外から分からないようにする。
    - リンクのトークンは、アカウントごとに毎回新しく作る。作り方は secrets.token_urlsafe(32) で、DB には sha256 だけを保存する。有効期限は15分で、一度使ったら消す。同じアカウントの未使用のログイン用トークンは、新しく作るときに消すので、有効なリンクは常に1本だけになる（審査 N-32）。そのため、リンクを他の人に転送しても、使い終わった後や15分を過ぎた後には開けない。
    - リンクを押した後、ページは登録した email の入力を求め、トークンと email の両方が合ったときだけログインできる。登録情報を知らない人は、転送されたリンクを15分以内に押しても入れない。PO の条件「登録フォームの情報で管理する」を、文字どおり仕組みにしたもの（審査 N-29。Q2c）。
    - 残るリスク：転送された人が、本人の email も知っていて、本人より先に15分以内に押した場合は入れる。これは仕組みでは完全には防げない。本人は「使用済み」の表示で気付ける。
    - リンクの形は `https://app.salesanchor.jp/viewer/#login=<トークン>`（確認メールは `#verify=<トークン>`）にする。`#` より後ろはサーバーに送られないので、nginx のアクセスログにトークンが残らない。ページの JS が POST でトークンを交換する。GET ではトークンを一切消費しない。メールの安全検査（Microsoft の Safe Links など）が届いた時点でリンクを開いても、トークンは使われない（審査 B-5）。
    - 交換で発行した12時間トークンは JSON の本文で返し、URL には載せない。ブラウザでは localStorage に置く（既存の firebase-auth.ts と同じ置き場）。キー名は `viewer_access_token` にし、アプリ本体のキーと分ける。/viewer/ はアプリ本体と同じオリジンなので、アプリ本体で XSS が起きれば閲覧者のトークンにも届く（逆も同じ）。閲覧者のトークンで届く API は6本だけなので、このリスクは受け入れる（審査 N-39）。
    - ページの JS は、`#` の後ろのトークンを読んだらすぐに history.replaceState で消す。履歴やブックマークに、トークン入りの URL を残さないため（審査 N-36）。
    - リンクを押すと、そのアカウントに結び付いた12時間のトークン（D1 のトークンの分け方の 1〜7）を発行する。トークンは毎回のリクエストでアカウントの状態を確認するので、停止（suspended）にすれば次のリクエストから見られなくなる。
    - 新しい表 public.viewer_login_tokens（id、viewer_account_id、token_sha256、purpose［login ／ verify_email］、expires_at、created_at）を作る。D5 の確認トークンもこの表を使う。トークンを消費するときは、token_sha256・purpose・expires_at > now の3つの条件で引く。purpose を省くと、確認用のトークンでログインできてしまうため。session で email が合わなかったときは、トークンを消さずに残し、IP ごとの失敗だけを数える。転送された人が間違えて押しても、本人のリンクが使えなくならないようにするため（審査 N-34）。ADR-1013 の表は public.users に紐づいているので流用しない。
- トークンの分け方（ここで決める。Generator には判断させない）：
  1. iss は "salesanchor-viewer" にする（新しい定数。self_tokens.py の ISSUER とは別）。これで閲覧者のトークンは get_current_user の (c) に入らず、(d) の Firebase 検証で 401 になる（dependencies.py:187-198）。
  2. 署名鍵は、新しい環境変数 AUTH_VIEWER_JWT_SECRET にする。アプリの鍵とは分けるので、壁は iss と鍵の二重になる。secret を本番に追加するときは、PO の確認を取る（secrets の変更にあたるため）。
  3. sub は "viewer:<id>" の形にする。email のクレームは入れない。これで、回数制限（rate_limit.py:39-50）とセッション追跡（session_guard.py:45-55）がアプリのユーザーと同じ枠に混ざらない（審査 N-10）。
  4. 新しい dependency の get_current_viewer は、iss "salesanchor-viewer" と閲覧者用の鍵の両方を要求する。アプリのトークンは 401 にする。
  5. Redis のキャッシュは `jwt:` の名前空間を使わない。cache_jwt_result と get_cached_jwt を閲覧者側から呼ばない。署名の検証結果をキャッシュするときは `viewer_jwt:` を使う。アカウントの状態と trial_expires_at はキャッシュせず、毎回 DB を読む（審査 N-30）。
  6. ログアウトでは、既存のブラックリスト（is_token_blacklisted と blacklist_token）を使ってよい。拒否する側の仕組みなので安全。ただし blacklist_token の ttl の既定値は 3600 秒（cache.py:141）なので、トークンの exp までの残りの秒数を必ず渡す（審査 N-12）。
  7. 更新用トークン（refresh）は持たない。アクセス用トークンの寿命は 12 時間にし、切れたら再ログインしてもらう。
  8. 総当たり対策（審査 N-15・N-28）：パスワードが無いので、守りは次の2つに整理する。①リンクを送る login は、同じ email に1時間に3回までにする（メールの連打を防ぐ）。②交換（session）と verify-email に無効なトークンや合わない email が来たら、既存の check_auth_rate_limit と record_auth_failure（cache.py:292、:309）で IP ごとに数え、10回で15分ロックにする（self_tokens.py:28-29 と同じ数）。トークンは256ビットの乱数なので、総当たりでは当たらない。IP は D5 と同じく X-Real-IP から取る（既存の _get_client_ip は X-Forwarded-For の先頭を使うので使わない。審査 N-27）。nginx の login ゾーン（10r/m）は、`location = /api/v1/viewer/login`・`location = /api/v1/viewer/verify-email`・`location = /api/v1/viewer/session` の完全一致の3ブロックで当てる。前方一致にすると inventory まで 10r/m になるので使わない（前例は nginx/nginx.conf:112 の完全一致。審査 N-22）。
- 期限の判定：リクエストのたびに、DB の状態と trial_expires_at を見る（主キーで1行を読むだけ）。pending、verified、suspended、期限切れの trial は 403 にする。

### D2. 閲覧用 API
- 新しい router `viewer` を作る。入口の allowlist は次の6本だけにする（審査 N-18、B-5）。
  - signup・verify-email・login・session の4本は、既存の _require_app_origin（auth.py:199-201）と同じ検査を通す。Origin が rp_origin と一致しなければ 403 にする。ほかのサイトからの申込やメールの連打を、安く防げる（審査 N-38）。
  - POST /api/v1/viewer/signup（D5）
  - POST /api/v1/viewer/verify-email（D5）
  - POST /api/v1/viewer/login（email を受け取り、ログイン用のリンクをメールで送るだけ。応答は常に 200）
  - POST /api/v1/viewer/session（本文の token と email を受け取り、12時間トークンを返す。交換だけを行う）。1つの入口には1つの働きだけを持たせる。login は送るだけ、verify-email は状態を進めるだけ、session は交換するだけにする。
  - POST /api/v1/viewer/logout（get_current_viewer が要る。blacklist_token が False を返したら 503 にする。既存の auth と同じ扱い。cache.py:146。審査 N-24）
  - GET /api/v1/viewer/inventory（get_current_viewer が要る）
- この6本は1か所の定数（VIEWER_ROUTE_ALLOWLIST）に書き、router とテストの両方がそれを参照する。集合を2か所に書かない（審査 N-23）。
- inventory は、Redis の作り置き（D3）をそのまま返す。在庫の表は読まない。応答の形は `{"updated_at": ISO8601, "rows": [...]}`。
- 返す列は、今の GAS と同じ13列にする（PO 決定 Q1=y、2026-10-15）。13列は、投稿日時・Mark・Japanese Title・English Title・Condition・Unit Price・Quantity・Note_JA・Status・Release Date・提供者・Series・Search Keywords。fetch_output_rows の14列から Ship_JA を除いたもの。JSON のキーは _GAS_COLUMNS の英字（tcg_distribution_svc.py:251-254）から ship_ja を除いた13個にし、表示名は i18n で付ける。キーの集合は固定し、テストで「完全に一致すること」を確認する（審査 N-25）。

### D3. 1分ごとの作り置き（SSOT を守る）
- celery beat に、60.0 秒周期のエントリ "refresh-viewer-inventory" を足す。
- タスクの作りは tcg_extraction.py:725-757 にならう。async engine を作り、fetch_output_rows を呼んで、最後に dispose する。
- テナント文脈は設定しない。GAS への配信（_run_auto_distribution）と同じ条件にし、見え方も今の GAS と同じにする（審査 N-1）。
- 結果は D2 で決めた列だけに絞った JSON にして、Redis のキー `viewer:inventory:v1` に置く。TTL は 24 時間にする。タスクが3分止まってもキーが消えず、閲覧者には「最終更新」が古いことで鮮度が伝わる（審査 B-3）。
- キーが無いとき（Redis の再起動直後など）は、GET /viewer/inventory が 503 を返す。ページには i18n の「準備中です」を出す。
- これは正本の一時的な写しで、書き手はこのタスク1つだけにする。DB の表やシートには写しを作らない（SSOT）。
- 止まるときの扱い（審査 N-3、B-3）：
  - max_age_hours が設定されていないときは、空の rows と updated_at を書く。アプリの /inventory が同じ条件で空を返すので、それに揃える（inventory_offers.py:323-328）。
  - 再解析の途中でも作る（アプリの在庫表と同じ）。
- 失敗したときは前回の値を残す。updated_at も TTL も変えない。
  - 失敗の回数は Redis のキー `viewer:inventory:fail_count` に incr で持つ。成功したとき（空の rows を書いたときも含む）は 0 に戻す。Celery の worker は2プロセスで動くので（docker-compose.yml:209）、プロセスの中の変数では数えない（審査 N-26）。
  - 3回目の失敗で1回だけ知らせる。回復するまでは毎分は送らない。知らせる経路は、既存の send_discord_notification(tenant_id=4, event_type="tcg_distribution_error") の経路で知らせる（tcg_distribution_svc.py:1066-1081 と同じ。新しい経路は作らない）。

### D4. 閲覧ページ（軽い別の入口）
- Vite の入力に `viewer/index.html` を足す。ビルドすると dist/viewer/index.html になり、frontend/nginx.conf の `$uri/` で当たる（frontend/nginx.conf:23-25）。
- frontend/nginx.conf に `location = /viewer/index.html` と `location = /viewer/` を足し、本体の index.html と同じ `Cache-Control: no-cache, must-revalidate` を付ける（frontend/nginx.conf:7-12 と同じ理由。デプロイ後に古い index が残って白画面になるのを防ぐ。審査 N-13）。
- 配る URL は `/viewer/`（末尾にスラッシュ）に固定する。`/viewer` で来たときの転送先を Playwright で確かめる。ポート 8080 が混ざったら `port_in_redirect off; absolute_redirect off;` を足す（審査 N-14）。
- 外側の nginx は、D1-8 の login ゾーンを足すところだけ変える。
- ページの状態は次の4つにする（審査 N-35）。文言はすべて i18n にする。
  - ① ログインの申込（email を入れる → POST login）
  - ② リンクから来たときの email の確認（POST session）
  - ③ 在庫表と「最終更新 HH:MM」
  - ④ 案内（準備中、リンクが使用済み、期限切れ）
- 下の 300KB の上限は、この4つの状態を全部含めた大きさとする。部品は既存の金型（`frontend/src/components/`）とデザイントークンだけを使う（ADR-144、ADR-067）。金型に無い部品が要るときは、先に金型として登録する。
- 文字はすべて i18n にする（ADR-027）。
- アプリ本体（約 2.5MB）は読み込まない。viewer の JS は、圧縮前で合計 300KB 以下を上限にする。

### D5. 申込フォームとトライアル
- 公開の POST /api/v1/viewer/signup を作る。
  - honeypot の欄に値が入っていたら、200 を返すが行は作らない。
  - 同じ email は 1時間に3回、同じ IP は 1時間に10回までにし、超えたら 429 を返す。
  - IP は nginx が付ける X-Real-IP から取る。X-Forwarded-For をそのまま信用しない（security-recon.md の指摘）。
  - すでに登録されている email で申し込まれたときも、同じ 200 を返す。行が pending なら、古い確認トークンを無効にして新しい確認メールを送る（email ごとの回数制限の内側で）。確認メールを見逃した人がやり直せるようにするため（審査 B-4）。verified・trial・active・suspended なら何もしない。メールも送らない。応答の違いから、登録済みかどうかが外から分からないようにする（審査 N-19）。
- 申込で pending の行を作り、確認メールを送る。verify-email が成功したら trial に変え、trial_expires_at を確認時刻＋14日にする（PO 決定 2026-10-15 Q5「Y」：自動で始め、起点はメールの確認が済んだ時刻）。
- 確認用のトークンは、secrets.token_urlsafe(32) で作る。DB には sha256 のハッシュだけを保存する。24時間で失効し、一度使ったら消す（審査 N-17）。
  - SMTP が本番で使えるかどうかは【未確認】（計画票 0）。使えないときは、PO に方式を相談する。
- 本人確認が済まないまま 7日たった pending の行は、毎日のタスクで消す。
- 本契約への切り替えと停止の操作は Q3 で決める。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 閲覧者のトークンで既存の全 APIRoute（VIEWER_ROUTE_ALLOWLIST の6本を除く）を全 method で叩くと、すべて 401 になる | CI pytest test_viewer_isolation：app.routes を列挙する。パスの変数は 1 か固定の UUID で埋める。get_current_user は override しない。patch は _init_firebase と is_token_blacklisted→False と check_auth_rate_limit→False だけにし、get_cached_jwt は patch しない |
| get_current_viewer を一度通った後でも、同じトークンで既存の API を叩くと 401 になる（Redis 経由の抜け道がない） | 同上の別ケース |
| アプリのユーザーのトークンで GET /api/v1/viewer/inventory を叩くと 401 になる | CI pytest |
| 閲覧者のコードが cache_jwt_result と get_cached_jwt を呼んでいない | CI pytest（viewer のモジュールの中身を検査する） |
| pending・verified・suspended・期限切れの trial は 403、期限内の trial と active は 200 になる | CI pytest（時刻を固定する） |
| inventory の rows のキーの集合が、Q1 で決めた列の集合と完全に一致する | CI pytest（`set(keys) ==` 固定の集合） |
| 作り置きの行が、テナント文脈なしで呼んだ fetch_output_rows を列で絞ったものと一致する | CI pytest（同じ seed） |
| beat に refresh-viewer-inventory があり、周期が 60.0 秒である | CI pytest |
| タスクが失敗した後、Redis の値と updated_at が変わらない。3回続けて失敗したら通知が1回だけ呼ばれ、4回目では呼ばれない。成功すると fail_count が 0 に戻る | CI pytest（mock。fail_count は Redis で数える） |
| pending の email で signup し直すと新しい確認メールが送られ、古いトークンは使えない | CI pytest |
| GET /api/v1/viewer/inventory を1分に20回叩いても 429 にならない | Evaluator（curl） |
| Redis が使えないときの logout は 503 になる | CI pytest（mock） |
| honeypot に値があると行が作られない。同じ email の4回目は 429 になる | CI pytest |
| 7日たった pending の行は消え、trial の行は残る | CI pytest |
| ja.json と en.json のキーが一致する | 既存の CI（i18n チェック） |
| viewer の JS が、圧縮前の合計で 300KB 以下 | CI でビルドした後に dist/viewer の資産の大きさを合計する |
| app.salesanchor.jp/viewer/ が閲覧ページの title を返す | Evaluator（Playwright） |
| Redis のキーが無いとき、inventory は 503 を返す。max_age_hours が設定されていないときは、空の rows が書かれる | CI pytest |
| ログアウトした後、時刻を2時間進めても、同じトークンで inventory を叩くと 401 になる | CI pytest（時刻を固定する） |
| 無効なトークンで session に10回失敗した IP は、11回目が 429 になる。同じ email への login は4回目からメールを送らない | CI pytest |
| リンク先を GET で2回開いた後でも、POST の session と verify-email でトークンが使える（GET ではトークンを消費しない） | CI pytest |
| Origin が違う POST login は 403 になる | CI pytest |
| トークンが正しくても、email が登録と違えば session は 401 になる。そのあと正しい email を入れれば、同じトークンで入れる | CI pytest |
| 確認用（verify_email）のトークンでは session に入れない | CI pytest |
| 新しいログイン用トークンを作ると、前の未使用のトークンは使えなくなる | CI pytest |
| 登録済みの email で signup しても、応答は新規のときと同じで、メールは送られない | CI pytest |
| 確認トークンは24時間を過ぎると無効になり、2回目は使えない | CI pytest |
| ログイン用のリンクは、active と期限内の trial の email にだけ送られる。未登録・pending・verified・suspended・期限切れの trial の email にはメールが送られず、応答は同じ 200 | CI pytest（メール送信を mock にする） |
| 申込：メールか LINE 名が空なら 422。Discord ID の欄は無く、送られてきても保存しない | CI pytest |
| 申込：在庫関連の課題が1000文字を超えたら 422。保存した文字列は画面にそのまま文字として出し、HTML として解釈しない | CI pytest |
| ログイン用のリンクは15分で無効になり、一度使ったら2回目は 401 になる | CI pytest（時刻を固定する） |
| suspended にした後は、発行済みの12時間トークンでも inventory が 403 になる | CI pytest |
| GET /viewer/ の応答に Cache-Control: no-cache が付いている。/viewer でも同じページに着く | Evaluator（curl と Playwright） |
| 開いてから表が出るまでの時間が、本番の中央値で 1 秒以内 | Evaluator（Playwright で本番を5回計測する。始点は navigationStart、終点は表の最初の行が DOM に出た時刻。キャッシュなしの初回で計測し、生の値を残す） |
| 金型とトークンを守っている | `node scripts/check-ui-governance.js` |

---

## 技術 How・KPI

- KPI
  - 表示までの時間：中央値 1.0 秒以下。
  - 閲覧 API のサーバー時間：50ms 以下を目標にし、実測で確定する。
  - 在庫の読み取り：1分に1回で一定にする。閲覧者が何人いても増えない。閲覧者の状態の確認（主キーで1行を読む）だけは、リクエストのたびに行う（審査 N-16）。
- 技術の選択：閲覧者をアプリのユーザーと分ける。
  - 理由1：閲覧者が届く入口が、74 本から6本に減る。
  - 理由2：API を後から足しても、閲覧者に漏れる経路が仕組みとして生まれない（security-recon.md §6）。

---

## 弊害・トレードオフ

- 新しい認証にバグがあるリスク → 署名の仕組みは self_tokens と同じ作り方にし（鍵と iss だけ変える）、分離テストを CI で固定し、security-reviewer の審査を必須にする。
- secret が1つ増える → 本番への追加は PO の確認を取ってから行う。
- 鮮度は最大1分遅れる → PO が了承済み。
- 個人情報（メール・LINE 名・在庫関連の課題）を新しく自社の DB に持つ → 保存期間と削除の方法は Q7 で決める。
- GAS の利用者は、新しいページへの移行が要る → Q4 で決める。

---

## 計画票（PO 決定と審査の後）

| ステップ | 内容 | 担当 |
|---------|------|------|
| 0 | 実装前の確認を事実で埋める。①本番の SMTP。②fetch_output_rows の所要時間。③本番で配信行が指す products.tenant_id の分布（人間が SELECT を実行する。NULL 以外があれば、見え方の差を PO に報告する）。④app.salesanchor.jp の前に Cloudflare などのプロキシがいるか（審査 N-20。いるなら set_real_ip_from と real_ip_header を D4 に足す） | Sonnet（調査）＋PO（DB 読み取り・DNS の確認） |
| 1 | 表とトークンと分離テスト（D1）。守り手のテストを作る | Sonnet |
| 2 | 作り置きと閲覧 API（D2・D3） | Sonnet |
| 3 | 閲覧ページ（D4） | Sonnet |
| 4 | 申込、トライアル、pending の掃除、管理の操作（D5） | Sonnet |
| 各段 | コード審査（Fable）、セキュリティ審査、マージ。secret の追加は PO の確認を取る | Opus |

---

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）：GAS の在庫一覧は、Google の枠だけで 3〜7 秒かかる（recon.md §2）。応用：閲覧ページを Google の枠の外に置く。
- 過去事例（社内）：ADR-097・126・127 で、署名トークン付きの公開登録フォームを作った。応用：公開の入口は署名と回数制限で守る。
- 過去事例（社内）：GAS への配信を Celery から作る前例（tcg_extraction.py:725-757）。応用：同じ接続条件で作り置きを作る。
- 外部事例：該当なし。数値の根拠は社内の実測だけで足りるため。

## 維持の仕組み

- 守り手: 人手で守る（段1の PR で backend/tests/test_viewer_isolation.py を作り、この行をそのファイルパスに書き換える。このテストは全ルートを自動で列挙するので、API を足すたびに検査の対象になる）
- 在庫の行の定義は、ADR-1014 の1か所のまま変えない。

## 継続

- 完了後の監視：作り置きタスクが続けて失敗した回数（D3 の Discord 通知）。タスクがそもそも動かない場合（worker の停止）は失敗として数えられないので、updated_at から10分以上たったら知らせる仕組みを足す（経路は段2で既存のものから選ぶ。審査 N-26）。ほかに、閲覧 API の p50、閲覧者の数（trial と active）。
- 次のフェーズ：GAS の停止（Q4）。社内ユーザーの権限の穴は別の設計で扱う（下の「別件」）。

---

## PO 決定待ち（1つずつ聞く）

- ~~Q1. 閲覧ページに出す列~~ → **決定済み**：今の GAS と同じ13列（PO y、2026-10-15）。D2 に反映した。
- ~~Q2a. ログインの方法~~ → **決定済み**：メールのリンクで入る。登録フォームの情報で管理し、リンクを知っているだけでは見られない形にする（PO、2026-10-15）。D1 に反映した。
- Q2b.【決定 2026-10-15 PO】原文「トライアルではメール、LINE名、DISCORD IDのみ、本契約に進むときに詳しい情報を別途フォームで取得する」。申込フォームはメール・LINE 名・Discord ID の3つ（後に Q2f でメールと LINE 名の2つに変更）。本契約用の詳しい情報フォームは今回の対象外（別の便で設計する）。
- Q2d.【決定 2026-10-15 PO】原文「数字のID、SAの顧客対応と同様に顧客管理で利用するため」。数字のIDで受け取る。閲覧者の行はテナントの取引先（companies）には写さない（SSOT）。本契約で取引先とつなぐ方法は、本契約フォームの便で設計する。
- Q2e.【決定 2026-10-15 PO】原文「Discord ID だけ任意、ただし間違えて送られてくる可能性があるので数字以外は受け付けないようにしてくれ」。メールと LINE 名は必須、Discord の数字のIDは任意。入力があるときは、既存の検証と同じ `^\d{17,20}$`（backend/app/routers/discord_ticket_config.py:48）に合わない値を 422 で拒み、画面は i18n の案内文を出して送信させない。空欄は NULL で保存する。
- Q2f.【決定 2026-10-15 PO「Y」】Q2d・Q2e を置き換える。申込フォームはメールと LINE 名の2つだけにし、Discord ID は聞かない。Discord の数字のIDは、顧客ごとの専用URL（Discord でログイン→identify と guilds.join で ID を取得→ボットがサーバーに加える）で自動取得する。この仕組みと、ID の保存先（既存の顧客管理の列にそろえるか）は本便の対象外とし、別の仕事として設計する。調査の記録は /tmp/CC報告ファイル/viewer_discord_autoid_facts.txt（公式資料：docs.discord.com/developers/topics/oauth2、resources/guild、events/gateway-events）。
- Q2g.【決定 2026-10-15 PO】原文「在庫関連の課題も自由記述で最初のフォームに入力させる」。申込フォームはメール・LINE 名・在庫関連の課題（自由記述）の3つ。課題を任意にするか必須にするかは確認中。
- Q2c. リンクを押した後に email を入力し直してもらう形（D1。設計の既定案）でよいか。PO の条件「登録フォームの情報で管理する」から設計で既定にした。PO が別の形を望めば変える。
- Q3.【決定 2026-10-15 PO】原文「Y,私もしくはあなたが切り替えできるようにする。私がやる場合はフロントエンドから切り替えをするがあなたに任せる場合はSSHを使用する」。切り替え（trial→active）と停止（→suspended）、停止の解除ができるのは PO と Claude だけ。
  - PO の経路：super admin 画面。API は既存の require_super_admin（backend/app/auth/dependencies.py:491）で守り、画面は pages/super-admin/ 配下に置く（既存例 backend/app/routers/super_admin_phase_switch.py:65・:89）。
  - Claude の経路：【事実】制限付き鍵 salesanchor-claude で実行できるのは監視の4コマンドだけで、DB の読み書きはできない（docs/adr/ADR-079-claude-code-monitoring-access.md:57、docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58-59・:220-224）。DB 書き込みには無制限鍵が要り、CLAUDE.md:29-30 により作業ごとに PO の GO が要る。そこで、SQL を手で書かず、backend コンテナ内の専用スクリプト（引数は email と変更後の状態だけ。PO の画面と同じサービス関数を呼ぶ）を無制限鍵で実行する。GO 原文は依頼文と記録に転記する。
  - GO の発行者（PO 決定 2026-10-15、原文「N,仕様に関しては壁打ちして決めているので仕様から逸脱していないGOは全てOPUSに権限委譲する」）：本設計どおりの切り替え（対象1人の状態を trial→active、→suspended、suspended→元の状態のいずれかに変える）は、Opus が「POの委任に基づくClaude Opus発行」として GO を出す（委任の正式記録 docs/handoff/go-record-transcription/opus-delegation.md と同じ書き方）。複数人の一括変更・削除・本設計に無い状態の変更など、仕様から外れる操作は Opus が止めて PO に聞く。
  - どちらの経路でも、変更前後の状態・実行者（PO／Claude）・日時を記録に残す（保存先は段2で既存の監査ログから選ぶ）。
  - 生の調査記録：/tmp/CC報告ファイル/viewer_ssh_recon.txt
- Q4. GAS の在庫一覧をいつ止めるか（移行の期間）。
- Q5.【決定 2026-10-15 PO「Y」】メールの確認が済んだ時点で自動的にトライアルを始め、14日はその時刻から数える。人の承認は挟まない。verified は今回使わない（5値は残す）。
- Q6. 同じ人が別のメールで（会社名は聞かないため、判定を LINE 名で行うかを含めて）申し込み直したとき、もう一度トライアルを認めるか。
- Q7. 閲覧者の個人情報を保存する期間と、削除の方法。LP のプライバシーポリシーに追記するか。
- Q8.【決定 2026-10-15 PO「Y」】置き場所は app.salesanchor.jp/viewer/ にする。
- Q9.【決定 2026-10-15 PO「Y」】今の取引先は申込なしで active として最初に登録する。PO から一覧（22件、メールの重複0件・形式不正0件）を受け取った。個人情報なので、リポジトリと PR には載せず、リポジトリ外の ~/CC報告ファイル-keep/viewer-initial-accounts/initial_active_list.tsv（権限600、項目は申込日時・LINE 名・メールの3つだけ）に置く。登録は段4の公開前に、Q3 の Claude の経路（無制限鍵＋専用スクリプト。migration ではデータを入れない）で行う。登録の前に一覧を PO に見せる。

## 別件（本設計の外）

- 社内ユーザーの権限の穴（会話ログの読み取り、招待トークンの発行など。security-recon.md §2）。別の設計で扱い、PO に相談する。
