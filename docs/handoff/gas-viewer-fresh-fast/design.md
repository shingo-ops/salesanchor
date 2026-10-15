---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 在庫の閲覧専用ページ（GAS 在庫一覧の置き換え）

> この文書は何か：GAS の在庫一覧の代わりに、お客さんが自社サーバーで在庫表だけを見られるページの作り方を決めた設計書。

- 親（設計仕様書）: [docs/specs/inventory-management/inventory-viewer/README.md](../../specs/inventory-management/inventory-viewer/README.md)

**対象ADR**: ADR-1019（草案・Proposed。`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md`）  
**recon**: docs/handoff/gas-viewer-fresh-fast/recon.md ／ docs/handoff/gas-viewer-fresh-fast/security-recon.md  
**審査**: r1 REVISE（Blocking 2、Non-blocking 11。/tmp/CC報告ファイル/viewer_design_review.txt）→ r2 REVISE（Blocking 1、Non-blocking 9。/tmp/CC報告ファイル/viewer_design_review_r2.txt）→ r3 REVISE（Blocking 1、Non-blocking 7。/tmp/CC報告ファイル/viewer_design_review_r3.txt）→ r4 で全件に対応し、PO 決定 Q2a（メールのリンクでログイン）を反映 → r4 REVISE（Blocking 1、Non-blocking 6。/tmp/CC報告ファイル/viewer_design_review_r4.txt）→ r5 で全件に対応 → r5 APPROVE（Blocking 0、Non-blocking 6。/tmp/CC報告ファイル/viewer_design_review_r5.txt）→ 本版で N-34〜N-39 を反映した（KPI の重複の指摘は、実物に重複が無いため対応なし）→ r5 の後に、PO 決定（Q2b〜Q9、期限の延長、ログイン記録）、外部事例、ルール点検（/tmp/CC報告ファイル/viewer_rules_check.md）への対応を足した → r6 REVISE（Blocking 7、Non-blocking 14。審査は Opus。/tmp/CC報告ファイル/viewer_design_review_r6.txt）→ 本版で B-2〜B-6 と N-1〜N-14 に対応した。B-1 は Q11、B-7 は履歴の名前の扱いとして PO 決定待ち → r7 REVISE（Blocking 1、Non-blocking 9。審査は Opus。/tmp/CC報告ファイル/viewer_design_review_r7.txt）→ 本版で B-1・N-1〜N-9 に対応し、PR #4293 で委任を PR の GO に絞ったことに合わせて操作の GO を PO 本人に直した（Q12 を追加）→ r8 APPROVE（Blocking 0、Non-blocking 9。審査は Opus。/tmp/CC報告ファイル/viewer_design_review_r8.txt）→ r8-N-1〜N-9 に対応した → r9 REVISE（Q14 で D4 をアプリと同じ部品に書き直した版。Blocking 3、Non-blocking 10。要点は review-fable.md の r9）→ 本版で B-r9-1〜3・N-r9-1〜10 に対応した → r10 REVISE（Blocking 1、Non-blocking 8。審査は Opus。/tmp/CC報告ファイル/viewer_r9/review_r10.txt）→ 本版で B-r10-1・N-r10-1〜8 に対応した → r11 REVISE（Blocking 1、Non-blocking 7。審査は Opus。/tmp/CC報告ファイル/viewer_r9/review_r11.txt）→ 本版で B-r11-1・N-r11-1〜7 に対応した → r12 APPROVE（Blocking 0、Non-blocking 3。審査は Opus。/tmp/CC報告ファイル/viewer_r9/review_r12.txt）→ N-r12-1〜3 を反映した。PO の承認（ADR-1019 は Proposed のまま）と §PO 決定待ち が残る  
**日付**: 2026-10-15  
**担当**: Planner（Claude Opus）  
**状態**: 設計案（草案）。PO 決定待ちの項目が残っている。段ごとの着手の可否は §PO 決定待ち の各項に従う（審査 r8-N-6）。

---

## KGI（PO 決定、2026-10-14〜15 のチャットの要旨）

1. GAS 在庫一覧をアプリと同じ鮮度にする。目標は「開いてから表が出るまで1秒以内」。
2. 閲覧は自社サーバーの URL で行う。
3. 閲覧者はフォームで申し込む。トライアルは2週間だけ閲覧できる。本契約者は期限なく閲覧できる。
4. サーバーは1分に1回だけ表を作り、閲覧者全員に同じものを配る。鮮度は最大1分遅れでよい（PO y）。ただし再解析・抽出の途中（保留）の間は除く。この間は GAS と同じく前回の表のまま止める（PO Q11=y、2026-10-15）。
5. 閲覧者には在庫表以外を一切見せない。閲覧者はアプリのユーザー（tenant_002）にせず、別の閲覧専用アカウントにする（PO Y、2026-10-15）。

## 現在地（recon の要点。根拠は origin/main 0c7852fd9 で照合し、2026-10-15 に origin/main 65ed8cd8b で再照合した。ずれた2か所は下で直した）

- GAS は Google の枠を読むだけで 3.3〜6.7 秒かかる。コードを直してもこの時間は縮まない（recon.md §2）。
- 在庫の行の定義は1か所にある（ADR-1014 の distribution_rows_sql）。中身は `backend/app/services/tcg_distribution_svc.py`:274-371 の distribution_rows_parts で、14 列を返す fetch_output_rows（:390-412）がこれを使う。fetch_output_rows はテナント文脈を自分では設定しない。
- 今の GAS が表示している列は 14 列（2026-10-14 に発送日を足して13から14になった。Q13。r9 で直した。ALLOWED_HEADERS。GAS のコードはリポジトリ外にある）。
- アプリのユーザーにすると、在庫を見るだけの権限にしても 614 本中 74 本の入口に届く（security-recon.md §2）。
- get_current_user（`backend/app/auth/dependencies.py`:116-239）がトークンを受け付ける経路は4本ある。
  - (a) スモーク用トークン
  - (b) Redis の `jwt:<sha>` キャッシュ。キャッシュに当たると署名を検証しない。
  - (c) iss が "salesanchor" のトークン。署名は `backend/app/auth/self_tokens.py`:86-132 で作り、検証する。
  - (d) Firebase
- 自社トークンには「種類」を表す欄（typ・aud）が無い（self_tokens.py:86-98）。
- 期限・契約・トライアルを持つ表は無い。
- Celery から配信を作る前例は `backend/app/tasks/tcg_extraction.py` の _run_auto_distribution（origin/main 65ed8cd8b では :736 から。async engine を1回作って asyncio.run で回す。テナント文脈なし）。ここが呼ぶのは run_distribution で、fetch_output_rows はその中で呼ばれる（`backend/app/services/tcg_distribution_svc.py`:934）。直接 fetch_output_rows を呼ぶ前例ではない。Redis に JSON を置く前例は `backend/app/tasks/dashboard.py`（周期 600 秒）。beat の周期で最短のものは 300 秒（`backend/app/celery_app.py`:137）。
- frontend の nginx は、すべてのパスを index.html に戻す（frontend/nginx.conf:23-25）。

---

## 設計（変更前 → 変更後）

### D1. 閲覧専用アカウントと、アプリと交わらないトークン（審査 B-1 への対応）
- 変更前：外部の人を入れるには、アプリのユーザー（public.users）にするしかない。
- 変更後：
  - 新しい表 public.viewer_accounts を作る。migration では表を作るだけで、データは入れない。
  - 列：id、email（一意）、line_name（LINE の表示名）、inventory_issue（在庫関連の課題。自由記述。TEXT。1000文字まで。任意＝空欄は NULL（Q2g）、状態（pending ／ verified ／ trial ／ active ／ suspended の5値。verified は「メール確認済み・承認待ち」。Q5 で自動トライアルに決まったので、今回は使わない（メールの確認が済んだら pending から trial へ直接進む）。将来、承認を挟む形に変えるときに migration を作り直さずに済むよう、5値で作る）、email_verified_at、trial_expires_at、作成・更新の日時。
  - テナントは持たない。
  - 本設計で作る4つの表（viewer_accounts・viewer_login_tokens・viewer_login_events・viewer_status_changes）の id は、すべて BIGSERIAL にする（既存の public の表と同じ。例：public.audit_log、migrations/20260921_110000_pipeline_tables_public.sql:405）。viewer_id など他の表を指す列は BIGINT ＋ FK（ON DELETE CASCADE。閲覧者の行を消したら、その人のトークン・記録・履歴も一緒に消える）。
  - 人の正本（ADR-1008）との境界：ADR-1008 の正本 public.users は「ログインして社内の業務をする人」（担当者・作成者など、人を指す列の参照先）。閲覧者は社外のお客さんで、アプリにはログインしない。このため users には入れず、viewer_accounts だけに持つ（1人1行。email の一意制約）。同じ人の email が users と viewer_accounts の両方に入らないようにする：申込（signup）の email が users.email にあるとき（大文字小文字は無視して比べる）は、行を作らずメールも送らない（応答は同じ 200）。登録用の専用スクリプト（Q9）でも同じ検査をし、users.email にある行は「飛ばした」に数える。社員はアプリ本体の在庫表を見る。逆向き（閲覧者の後で同じ email の社員を users に足す場合）は本便では扱わない（社員の追加はアプリ本体の操作で、閲覧者は少数のため、気付いたときに停止で対応する）。
  - email の正規化（審査 r6 N-6）：保存・比較・回数制限のキーのすべてで、前後の空白を除いて小文字にした値を使う。一意は `lower(email)` の一意索引で守る（保存の時点で小文字にしているが、DB でも守る）。正規化は1つの関数に書き、signup・login・session・登録スクリプトのすべてがそれを呼ぶ。
  - DB の SSOT の原則（docs/specs/db-ssot/README.md）に従い、同じ事実を2つの表に持たない。
  - 顧客管理（取引先 companies・担当者 contacts）には写さない。本契約のときに取引先とつなぐ方法は、本契約フォームの便で設計する。そのときは viewer_accounts から取引先を指す列（参照）で結び、email・LINE 名を取引先側に二重に持たない形を前提にする。
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
- inventory は、Redis の作り置き（D3）をそのまま返す。在庫の表は読まない。応答の形は `{"updated_at": ISO8601, "fresh_window_hours": 数, "rows": [...]}`（fresh_window_hours は D4 の「24時間以内」の時間数。r9 で追加）。
- 返す列は、今の本番の GAS と同じ14列にする（PO 決定 Q1=y と Q13=y、2026-10-15。r9 で13列から直した）。14列は、投稿日時・Mark・Japanese Title・English Title・Condition・Unit Price・Quantity・Note_JA・Status・Release Date・Series・提供者・Search Keywords・発送日（Ship_JA）。fetch_output_rows の14列そのまま。JSON のキーは _GAS_COLUMNS の英字14個（origin/main e1351e663 の tcg_distribution_svc.py:251-254：posted_at・mark・japanese_title・english_title・condition・unit_price・quantity・note_ja・status・release_date・series・provider・search_keywords・ship_ja）にし、表示名は i18n で付ける。これに、区分の `offer_type`（D4 の列の対応表。審査 r9 B-r9-2）を1つ足した15キーを返す。キーの集合は固定し、テストで「完全に一致すること」を確認する（審査 N-25）。

### D3. 1分ごとの作り置き（SSOT を守る）
- celery beat に、60.0 秒周期のエントリ "refresh-viewer-inventory" を足す。
- 重なり対策（審査 r6 N-4）：タスクの最初に Redis の `SET viewer:inventory:lock <任意の値> NX EX 55` を取る。取れなかった回は何もせずに終わり、成功にも失敗にも数えない（前の回がまだ動いているため）。worker が2プロセスでも、同じ1分に作るのは1回だけになる。
- タスクの作りは tcg_extraction.py の _run_auto_distribution（origin/main 65ed8cd8b では :736 から） にならう。async engine を作り、下の共通関数を呼んで、最後に dispose する。
- テナント文脈は設定しない。GAS への配信（_run_auto_distribution）と同じ条件にし、見え方も今の GAS と同じにする（審査 N-1）。
- Sold out の行は、配信の正本の中で除かれている（svc:241-248・:341）。閲覧ページの側では除く処理を書かない（審査 r6 N-2）。
- 照合の基準は「GAS に配信される行と同じ」にする。アプリの /inventory との一致は求めない（/inventory は max_age_hours が無いときに空を返すなど、条件が違う。inventory_offers.py:323-328）。
- 設定の取り方と「作ってよいか」の判定は、run_distribution と同じものを使う。2か所に同じ条件を書かないため、run_distribution の手順 0〜2（origin/main 0094e6d9a の `backend/app/services/tcg_distribution_svc.py`:861-943）を、新しい関数 `build_distribution_rows(db)` に切り出す。run_distribution と作り置きの両方がこれを呼ぶ。中身は次の順（今の run_distribution と同じ）：
  1. 安全装置 #8（analysis_runs に completed_at IS NULL がある）と #8b（extraction_jobs に pending・running・extracted がある）に当たったら、行を作らず「保留」を返す。
  2. load_distribution_settings（:178）→ include_flag_single（:920 と同じ式）→ _max_age_hours（:197）。None なら行を作らず「設定なし」を返す（MAX_AGE_UNSET_MESSAGE、:190）。
  3. fetch_output_rows(db, include_flag_single=…, max_age_hours=…)（:390。merge_same_post=False で固定）。
- fetch_output_rows はキーの無いリストを返す（:412）。作り置きは、各行を _GAS_COLUMNS（:251-254）と zip して辞書にし、14キーに offer_type（status_to_offer_type の結果）を足した15キーにする（r9。Q13=y、B-r9-2）。列の並びを別の場所に書き直さない。
- run_distribution の結果（戻り値の形・ログ・既存のテスト）は変えない。切り出しの前後で、既存の配信のテストがすべて通ることを受入条件にする。
- build_distribution_rows の仕様（審査 r6 B-3。Generator に判断させない）：
  - 置き場：`backend/app/services/tcg_distribution_svc.py` の中、run_distribution の直前。
  - 戻り値：`DistributionRowsResult`（dataclass。frozen）。欄は kind・rows・message の3つ。
    - kind は "ok"・"hold"・"unset"・"error" の4つ（Literal）。
    - rows は kind が "ok" のときだけ fetch_output_rows の戻り値そのまま。ほかは空のリスト。
    - message は今の4つの文言をそのまま持つ（文言を変えない）。hold の #8 は svc:877-880 の文言、hold の #8b は svc:905-908 の文言、unset は MAX_AGE_UNSET_MESSAGE、error は `f"出力データ取得失敗: {exc}"`（svc:942）。ok のときは空文字。
  - 例外：fetch_output_rows の例外は中で捕まえて kind="error" にする（今の svc:935 の try/except を中へ移す）。analysis_runs・extraction_jobs・load_distribution_settings の例外は、今と同じく捕まえずに外へ投げる（今の run_distribution もここは捕まえていない）。
  - ログ：build_distribution_rows はログを出さない。今の4つのログ（svc:881・:909 の warning、:923・:936 の error）は run_distribution の側に残す。作り置きのタスクは "[dist]" のログを出さない（毎分の hold で "[dist]" の warning が並ばないようにするため）。作り置きは unset・error のときだけ、自分のロガーで "[viewer-cache]" を付けて1行出す。
  - run_distribution の変更前後：
    - 変更前：svc:861-943 に、手順0（#8）・0-b（#8b）・1（設定）・2（fetch_output_rows）と、4つの早期 return（svc:882・:910・:924・:937）がある。
    - 変更後：`result = await build_distribution_rows(db)` を1回呼ぶ。kind が hold・unset・error なら、今と同じ水準のログ（hold は warning、unset・error は error。ログの本文は result.message をそのまま出す。error の message は `f"出力データ取得失敗: {exc}"` なので exc の内容を含む。DistributionRowsResult に exc の欄は足さない）を出し、今と同じ形の辞書（run_id None、started_at（今と同じく run_distribution の冒頭 svc:859 で取った値の isoformat）、output_count 0、results []、errors [{"target_id": None, "error": result.message}]）の5キーを返す。ok なら `rows = result.rows` として svc:945 以降へ進む。
    - 触らない範囲：svc:945 以降（output_count の計算、配信先の取得、書き込み、DB 記録、Discord 通知）と、関数の引数・docstring の手順の番号。
  - 作り置きの対応：ok → 書く。hold → 何もしない（前回の値と updated_at を残す。fail_count も変えない）。unset・error → 前回の値を残し、fail_count を1増やす。build_distribution_rows が外へ投げた例外（DB 接続の失敗など）と、Redis への書き込みの例外も、作り置きのタスクの中で捕まえて error と同じ扱いにする（前回の値を残し、fail_count を1増やす。審査 r7-N-3）。fail_count の incr 自体が Redis の障害で失敗したときは、ログを1行出して終わる（数えられない場合は、継続の「updated_at から10分」の監視で気付く）。
- 結果は D2 で決めた列だけに絞った JSON にして、Redis のキー `viewer:inventory:v1` に置く。TTL は 24 時間にする。タスクが3分止まってもキーが消えず、閲覧者には「最終更新」が古いことで鮮度が伝わる（審査 B-3）。
- キーが無いとき（Redis の再起動直後など）は、GET /viewer/inventory が 503 を返す。ページには i18n の「準備中です」を出す。
- これは正本の一時的な写しで、書き手はこのタスク1つだけにする。DB の表やシートには写しを作らない（SSOT）。
- 止まるときの扱い（審査 N-3、B-3）：
  - 再解析・抽出の途中（「保留」）は、前回の値を残す。updated_at も変えない。GAS のシートも、この間は前回の配信のままなので、見え方が GAS と同じになる。通知はしない（正常な待ち）。（r5 までの「再解析の途中でも作る」「設定なしなら空を書く」は、アプリの /inventory に合わせた案だった。照合の基準を GAS に揃えたので改めた。）**この扱いは PO 決定済み（Q11=y、2026-10-15）。** ideal-state の「アプリと同じ仕様」と KGI2 の「最終更新が1分以内」と、保留の間は表が止まることとが食い違うため（審査 r6 B-1）。Q11 は y に決まった（保留中は前回の表のまま止める）。
  - max_age_hours が設定されていない（「設定なし」）ときも、前回の値を残し、下の失敗として数える。run_distribution もこの場合はエラーとして扱う（:922-930）。
- 失敗したときは前回の値を残す。updated_at も TTL も変えない。
  - 失敗の回数は Redis のキー `viewer:inventory:fail_count` に incr で持つ。成功したとき（行が0件でも書けたとき）は 0 に戻す。「保留」は失敗にも成功にも数えない。Celery の worker は2プロセスで動くので（docker-compose.yml:209）、プロセスの中の変数では数えない（審査 N-26）。
  - 3回目の失敗で1回だけ知らせる。回復するまでは毎分は送らない。知らせる経路は、既存の send_discord_notification(tenant_id=4, event_type="tcg_distribution_error") の経路で知らせる（tcg_distribution_svc.py:1066-1081 と同じ。新しい経路は作らない）。

### D4. 閲覧ページ（軽い別の入口）
- Vite の入力に viewer/index.html を足す。ビルドすると dist/viewer/index.html になり、frontend/nginx.conf の `$uri/` で当たる（frontend/nginx.conf:23-25）。
- frontend/nginx.conf に `location = /viewer/index.html` と `location = /viewer/` を足し、本体の index.html と同じ `Cache-Control: no-cache, must-revalidate` を付ける（frontend/nginx.conf:7-12 と同じ理由。デプロイ後に古い index が残って白画面になるのを防ぐ。審査 N-13）。
- 配る URL は `/viewer/`（末尾にスラッシュ）に固定する。`/viewer` で来たときの転送先を Playwright で確かめる。ポート 8080 が混ざったら `port_in_redirect off; absolute_redirect off;` を足す（審査 N-14）。
- 外側の nginx は、D1-8 の login ゾーンを足すところだけ変える。
- ページの状態は次の6つにする（審査 N-35、r6 B-6）。文言はすべて i18n にする。
  - ① ログインの申込（email を入れる → POST login）
  - ② リンクから来たときの email の確認（POST session）
  - ③ 在庫表と「最終更新 HH:MM」
  - ④ 案内（準備中、リンクが使用済み、期限切れ）
  - ⑤ 申込（email・LINE 名・在庫関連の課題・隠し欄 → POST signup）
  - ⑥ メール確認の結果（`#verify=` から来たとき。POST verify-email の結果で、成功・使用済み・期限切れのどれかを出す）
- 下の 300KB の上限は、この6つの状態を全部含めた大きさとする。部品は既存の金型（`frontend/src/components/`）とデザイントークンだけを使う（ADR-144、ADR-067）。金型に無い部品は使わない（r9 の時点で、下の表の部品はすべて金型と共有部品にある）。
- 文字はすべて i18n にする（ADR-027）。
- 全体の CSS：viewer の main.tsx は frontend/src/index.css を読む（デザイントークンの定義。index.css:1 が tokens.css、:2 が components/field-size.css を読む）。アプリの components.css（App.tsx:116 でだけ読む）は読まない。【事実】金型のクラスは comp- で始まり components.css に依存しない。inventoryColumns.css は全10行でトークンだけを使う（審査 r9 N-r9-1）。
- アプリ本体（約 2.5MB）は読み込まない。viewer の JS は、圧縮前で合計 300KB 以下を上限にする。
- 作りの基準（r9 で書き直した。PO 決定 2026-10-15 Q14「アプリの在庫表も同じ作りにする」）：閲覧ページの在庫表は、アプリの在庫表（/inventory）と同じ金型・同じ共有部品で作る。アプリの在庫表は便1〜3（#4317・#4327・#4330、本番反映済み）で金型に載せ替え済み。閲覧ページはその実物をまねる。根拠は origin/main e1351e663 の実物（生の写しは /tmp/CC報告ファイル/viewer_r9/）と、docs/handoff/inventory-table-unify/design.md の「維持の仕組み」（閲覧ページも同じ部品を使う）。GAS と比べて違いが出るところは、アプリの実物を正とする（PO の12項目の回答の 5・6「アプリを正とする」と Q14）。
- 部品と金型の対応（金型はすべて origin/main の `frontend/src/components/` にあり、stories もある。r8 までの「金型なし・Q10 で決める」4つは、便1・便3 で金型に入ったので、ここで実在の金型に置き換えた）：

  | 画面の部品 | 使う金型・共有部品 | アプリの実物（origin/main） |
  |---|---|---|
  | シリーズのタブ（全て＋件数の多い順） | Tabs | タブが多いときは Tabs.css:24 の横スクロールだけ |
  | シリーズのプルダウン（スマホ） | Select | |
  | 検索（かな同一視・空白区切りは AND） | TextFieldControl type="search" | InventoryPage.tsx:428 |
  | 検索の正規化 | `normalizeForSearch`（frontend/src/features/inventory/searchNormalize.ts:6）を import する。viewer の中に正規化の関数を書かない | アプリはサーバーの SQL で同じ規則（共通ベクタ searchNormalize.vectors.json） |
  | 並べ替えのプルダウン（3択） | SelectControl（プレースホルダ付き） | InventoryPage.tsx:51・:470-472 |
  | 見出しを押して並べ替え | DataTable の sortKey・sortDir・onSort（DataTable.tsx:78-82）と列の sortable | |
  | 表 | DataTable に stickyHeader・fitToWidth・mobileCards を付ける（DataTable.tsx:121・:123・:125） | InventoryPage.tsx:612-614 |
  | 商品名の列の固定（PC） | 列の stickyLeft（DataTable.tsx:58） | inventoryColumns.tsx:63 |
  | スマホの縦カード | mobileCards と列の mobileOrder・mobileHidden（DataTable.tsx:60・:62） | inventoryColumns.tsx |
  | ページ送り | DataTable の page・hasNextPage・onPageChange・pageInfo（DataTable.tsx:101-111）。1ページ50件 | InventoryPage.tsx:48・:604-606 |
  | コンディションのバッジ | Badge ＋ `conditionBadgeVariant`（frontend/src/features/inventory/conditionBadge.ts:7）を import する | inventoryColumns.tsx:80 |
  | 提供者の絞り込み（選んだ人だけ出す） | MultiSelect（MultiSelect.tsx:22-35）。PC はツールバー、スマホは絞り込みの Drawer の中 | InventoryPage.tsx:476-485、InventoryFilterPanel.tsx:118 |
  | コンディションの絞り込み | MultiSelect（Drawer の中） | |
  | 24時間以内 | Button（aria-pressed）。既定はオン | InventoryPage.tsx:153・:443-454（Toggle の金型ではない。アプリと同じにする） |
  | 絞り込みのドロワー | Drawer | |
  | 価格・在庫の範囲 | TextFieldControl type="number" | |
  | クリア・適用のボタン | Button | |
  | 空の表示・読み込み中・エラー | EmptyState と Button（DataTable の emptyState） | |
  | 商品名の2段（上＝日本語、下＝英語） | 共有の CSS `frontend/src/features/inventory/inventoryColumns.css` の inventory-cell__title・inventory-cell__sub を import して使う | inventoryColumns.tsx:67-68 |

  - アプリ側の1か所の直し（段3の最初のコミット。審査 r9 B-r9-2）：【事実】アプリの予約の表示は、金型ではなく全体の CSS のクラス `<span className="badge badge-negotiating">`（inventoryColumns.tsx:105、色は components.css:245 の --info-bg・--info-text）。閲覧ページは components.css を読まないので、このクラスは使えない。アプリのこの1行を `<Badge variant="info" appearance="soft">` に替え、アプリと閲覧の両方を同じ金型にする（色のトークンは同じ。Badge.css:59）。ほかの画面の badge-negotiating（ShiftsPage・StaffReportsPage など）は触らない。【事実・見た目の変化（審査 r10 N-r10-3）】色と文字は同じだが、Badge にすると形が丸い錠剤になり、横の余白が 8px から 12px に、最小の高さが 24px になる。受入に「予約の行が .comp-badge--info で描かれる」vitest を1行足す。
  - 新しい金型は作らない。上の表で足りる（PO の許可が要る新規登録は無い。docs/CC_UI_GOVERNANCE.md:11-13）。
  - 列の定義は、viewer の中の1ファイル frontend/src/pages/viewer/viewerColumns.tsx（新規） に置く。アプリの `buildInventoryColumns`（inventoryColumns.tsx:45）はそのまま使わない。【事実】アプリの行の型 InventoryRow（inventoryColumns.tsx:12-35）は product_id・supplier_id・offer_type・merged_count など22項目で、閲覧の行（D2 の15キー）と形が違う。また中で本体の辞書のキー inventory.col.* と、アプリの全体の CSS のクラス `badge badge-negotiating`（:105）を使う。
  - そのかわり、2つの列の定義がずれないように、検査で縛る（片方だけ直る事故を防ぐ）。vitest frontend/src/pages/viewer/viewerColumns.parity.test.tsx（新規） を作り、viewer の列と、`buildInventoryColumns` の全列（colVisible は常に true）を、下の対応表で突き合わせる。対応する列どうしで、並び順・sortable・align・stickyLeft・mobileOrder・mobileHidden が一致しなければ失敗させる。

    | 閲覧の列（D2 のキー） | アプリの列の key | 中身 |
    |---|---|---|
    | mark | mark | |
    | japanese_title と english_title | name | 上段に japanese_title、下段に english_title（アプリと同じ） |
    | condition | condition | Badge |
    | status（と offer_type） | offer_type | アプリと同じ見え方にする（審査 r9 B-r9-2）。【事実】アプリは status を区分に写し（backend/app/routers/inventory_offers.py:104 の OFFER_TYPE_TO_STATUS、:113-115 の status_to_offer_type、:171）、In Stock は「在庫」の文字、Pre-order は予約のバッジ、対応に無い status だけをそのまま出す（inventoryColumns.tsx:102-108）。閲覧も同じ写しを使う：作り置きの各行に `offer_type`（in_stock・pre_order・null）を1つ足す。値は同じ status_to_offer_type で作る（段2で、status_to_offer_type・OFFER_TYPE_TO_STATUS・_STATUS_TO_OFFER_TYPE の3つを backend/app/services/tcg_distribution_svc.py へ移し、inventory_offers.py は同じ名前で import する。写しの表を2か所に持たない。審査 r10 N-r10-2。【事実】本体の参照は inventory_offers.py の :104・:105・:113・:115・:171・:246 の6行、テストは backend/tests/test_inventory_distribution_rows.py:111-118 の1関数で、io.<名前> として属性で読むので、router が import し直せば変えずに通る。既存のテストは変えない）。表示は、null なら status の文字（status が空なら「-」。アプリと同じ。inventory_offers.py:160・:183、inventoryColumns.tsx:103。審査 r11 N-r11-4）、pre_order なら Badge variant="info" appearance="soft"、in_stock なら i18n の「在庫」の文字 |
    | quantity | quantity | |
    | unit_price | unit_price | アプリと同じ整形（:146） |
    | provider と posted_at | supplier | 上段に提供者、下段に投稿日時（MM-DD HH:mm） |
    | note_ja | note | |
    | ship_ja | ship | |
    | release_date | release_date | |

    - アプリの unit（単位）の列は、閲覧の行に無い（Q1 で決めた GAS の列に入っていない）ので、対応表から外す。検査はこの1列だけを「閲覧に無い列」として許す。series と search_keywords は列にしない（series はタブ、search_keywords は検索だけに使う。PO の回答 6「TCG シリーズ列は不要」）。
  - 並び：アプリの実物と同じにする（審査 r9 B-r9-1 で直した）。【事実】アプリの並びはサーバーが決め、英語タイトルでまとめてから並べる（backend/app/routers/inventory_offers.py:276-280。商品名で並べるときは english_title と japanese_title を同じ向き、ほかは english_title の昇順を第1キーにして、選んだ列を第2キー、最後に元の並び sort_ord）。【事実・空欄（審査 r10 B-r10-1、r11 N-r11-2・3）】空欄を末尾に置くのは mark・release_date・quantity・unit_price の4列だけで、昇順・降順のどちらでも末尾（NULLS LAST、inventory_offers.py:280）。english_title・status・provider・japanese_title は COALESCE で ''（空の文字）にして比べるので、昇順では先頭、降順では末尾に来る。condition は cr.canonical で比べ、canonical が NULL の行は配信の条件で入らない（tcg_distribution_svc.py:294・:235・:237）ので、空の行は無い。第1キーの english_title も同じなので、英語名が空の行（inventory-table-unify/recon.md:79 の33商品）は既定の並びで先頭にまとまる。閲覧ページも同じにする（Q14。この見え方は PO に確かめる。§PO 決定待ち）。既定の選んだ列は発売日の降順（InventoryPage.tsx:117-118 の release_date desc）。閲覧ページもこのとおり手元で並べる。最後のキーは、作り置きの行の元の順（fetch_output_rows が返した順）にする。プルダウンは3択「価格が安い順」「在庫が多い順」「投稿が新しい」（:51 の unit_price asc・quantity desc・offered_at desc）。「新しい順」は置かない（PO 決定 2026-10-15）。PO の回答 2「デフォルトで発売日の新しい順」は、Q14（アプリと同じ作り）に従ってアプリの今の並びと同じにする。英語名でまとめる部分を含めてこの受け取り方でよいかは Q15 で確定する（審査 r11 N-r11-5）。
    - 列 → 比べる値（アプリの _SORT_COLUMNS、inventory_offers.py:119-131 に対応。審査 r9 N-r9-6）：mark→mark（空は末尾）、name→english_title と japanese_title、condition→condition、offer_type→status、quantity→quantity を数に、unit_price→unit_price を数に、supplier→provider、offered_at→posted_at、release_date→release_date（空は末尾）。【事実】作り置きの値はすべて文字列で、価格と数量が無いときは ''（tcg_distribution_svc.py:261-262）。'' は数にせず末尾に置く。文字の比べ方（審査 r10 B-r10-1。案A を採る）：【事実】本番 DB の並び順の設定は datcollate・datctype とも en_US.utf8、datlocprovider は c（glibc。生の値 /tmp/CC報告ファイル/viewer_r9/datcollate.txt）。ブラウザの Intl.Collator は ICU なので、glibc と完全には同じにできない。閲覧ページは `new Intl.Collator('en')`（numeric は付けない。数字を数として並べると PG と違うため）で比べ、'' は他のどの文字より前に置く。既知の差：記号・空白・大文字小文字の扱いが glibc と ICU で違う組は、順が入れ替わることがある。案B（作り置きの時点で DB の並び順の番号を付ける）は採らない：見出しの並べ替えで比べる文字の列が5つあり、列ごとに番号を持つと作り置きのキーが増え、15キーの受入と GAS との一致の検査が崩れるため。
    - 行のキー（DataTable の rowKey）：作り置きの行には一意の列が無い（:412 は14列だけ。審査 r9 N-r9-5）。受け取ったときの配列の位置を番号として行に付け、それを rowKey にする。
    - 表示の整形：価格は値が '' でなければ `¥` と3桁区切り（アプリの :146 と同じ形）、'' なら空。
  - 検索の対象は japanese_title・english_title・mark・search_keywords の4つ。アプリのサーバーの検索と同じ（docs/handoff/inventory-table-unify/design.md の 3-1、:200-202）。閲覧ページは全件を手元に持つので、入力のたびにブラウザの中で絞り込み、検索ボタンは置かない。
  - 絞り込み・検索・並べ替え・ページ送りは、すべて手元の行に対して行う（D2 の応答に全件が入っているため）。条件を変えたら1ページ目に戻す。
  - 24時間以内の時間数：【事実】アプリの値は定数 FRESH_WINDOW_HOURS = 24（backend/app/services/tcg_distribution_svc.py:212-213）で、在庫 API が応答に入れて（inventory_offers.py:360・:423）、絞り込みにも使う（:261-263）。閲覧ページも同じ定数を使い、別の数字を書かない：作り置きの JSON に `fresh_window_hours` として同じ定数を入れる（審査 r9 N-r9-2 で計画票0 ⑤を解決）。手元の絞り込みは、posted_at（タイムゾーン無しの日本時間の文字列 'YYYY-MM-DD HH:MM:SS'、svc:288-289）を +09:00 として読み、今の時刻から fresh_window_hours 時間以内の行だけを出す。posted_at が空の行は、オンのときは出さない（アプリの posted_ts >= の比較で NULL が落ちるのと同じ）。「今の時刻」は閲覧者の端末の時計になる（アプリはサーバーの時計。端末の時計がずれていれば、境目の行の出る・出ないが変わる。審査 r10 N-r10-7）。
  - 投稿日時の表示を「MM-DD HH:mm」にする（GAS と同じ）。Sold out の行は D3 のとおり作り置きの時点で入っていないので、ページでは除かない。
  - スマホ（767px 以下）の操作の配置は、アプリの在庫表と同じにする（提供者の MultiSelect はツールバーに出さず、絞り込みの Drawer に入れる。InventoryPage.tsx:476-485 の isMobile と同じ）。
  - アプリと意図して変えるのは2点：言語の切り替え（ja/en。GAS は日本語だけ、B67）と、最終更新の時刻の表示（B71）。「更新」ボタンは PO の回答が無いので、決まるまで作らない。
  - 申込とメール確認の画面（審査 r6 B-6）：

    | 画面の部品 | 使う金型 |
    |---|---|
    | email の入力 | TextField type="email" |
    | LINE 名の入力 | TextField |
    | 在庫関連の課題 | Textarea |
    | 送信 | Button |
    | 隠し欄（ハニーポット） | 金型なし（下の ui-allow） |
    | メール確認の結果（成功・使用済み・期限切れ） | EmptyState と Button |
  - ハニーポットの欄（D5）は、画面に見せない入力欄なので金型を使わない。生の input に `ui-allow: 申込のボット対策の隠し欄 (#4283)` を付ける。
- 置き場：
  - 入口の HTML は frontend/viewer/index.html。中の script は /src/pages/viewer/main.tsx を指す。
  - tsx はすべて frontend/src/pages/viewer/ の中に置く（ViewerPage.tsx など）。check-page-folder.js は pages の直下の .tsx だけを禁止し（:23-29）、check-ui-governance.js は pages 配下を検査する（:36）ので、閲覧ページも金型の検査の対象に入る。
  - frontend/vite.config.ts の build に `rolldownOptions.input`（main: index.html、viewer: viewer/index.html）を足す。【事実】入っている Vite は 8.0.16（origin/main の package-lock.json）。公式資料（vite.dev/config/build-options、2026-10-15 に確認）では `build.rollupOptions` は `build.rolldownOptions` の非推奨の別名と書かれているので、新しい名前を使う。前例は無いので、段3で `npm run build` の後に dist/index.html と dist/viewer/index.html の両方ができることを確かめる。
- 辞書（i18n）：
  - 閲覧ページの文言は、新しい辞書 frontend/src/locales/viewer/ja.json と en.json に置く。キーはすべて `viewer.` で始める。本体の ja.json（254KB）を閲覧ページに読み込むと 300KB の上限を超えるため。本体の辞書には `viewer.` のキーを置かない（同じ文言を2か所に持たない）。
  - 例外（審査 r6 B-5）：【事実】金型の中にも t() がある。Drawer.tsx:146 は t("suppliers.openFullPage")、Drawer.tsx:157・Sheet.tsx:141・Modal.tsx:134 は t("common.close") を使う（origin/main）。金型は変えない。閲覧ページが使う金型の中のキーだけは、viewer の辞書にも同じキー名で入れる（例：common.close）。同じ文言が本体と viewer の2か所に入るのはこの例外だけで、対象は「viewer の入口から import される、`frontend/src/pages/viewer/` の外のファイル（`frontend/src/components/` と `frontend/src/features/inventory/`）の t() のキー」に限る（r9 で features/inventory を足した。【事実】r9 の時点で viewer が import する searchNormalize.ts・conditionBadge.ts には t() が無い）。下の検査がこの集合を自動で数えるので、手で一覧を持たない。
  - 閲覧ページは frontend/src/pages/viewer/i18n.ts で、この2つの辞書だけを読み込む。本体の `frontend/src/i18n.ts` は読み込まない。
  - 検査 `frontend/scripts/check-i18n-missing-keys.js` を直す。今は、src の全ファイルの t("a.b") を本体の ja.json・en.json で探す（:16-19、:63-65）。直した後は、次の3つに書き分ける（審査 r7-N-4、r9 B-r9-3）。起点は viewer の入口 frontend/src/pages/viewer/main.tsx（新規） 1つだけにし、そこから import をたどった集合で分ける（テストのファイルは入口から import されないので、この集合に入らない）。たどるのは通常の import と動的な import() で、`import type` はたどらない（型だけで実行時に読まれないため）。①その集合のうち src/pages/viewer/ の中のファイルは、viewer の辞書だけで探す。②その集合のうち src/pages/viewer/ の外のファイル（frontend/src/components/・frontend/src/features/inventory/ のほか、たどった先にある constants・hooks・lib・components/loading なども含む。どこまで入るかは import をたどった結果で決まり、フォルダの名前では決めない。審査 r10 N-r10-6）は、本体の辞書と viewer の辞書の両方で探す。③それ以外のファイル（テストのファイル、例えば viewerColumns.parity.test.tsx と、それが import するアプリの inventoryColumns.tsx を含む）は、今までどおり本体の辞書だけで探す。そのため viewer の中のテストのファイルに t("viewer.…") のようにキーを文字で書くと③で落ちる。テストではキーを文字で書かず、画面の文字は viewer の辞書の JSON を import して読む（審査 r11 N-r11-6）。あわせて、viewer の ja と en のキーの集合が完全に一致することも検査する。
- ビルドの大きさと辞書の混入の測り方（審査 r6 B-4）：
  - 【事実】Vite は JS を dist/assets/ にまとめて出す。dist/viewer/ の下には JS は出ないので、「dist/viewer の JS」では測れない。
  - manifest は vite.config.ts には書かず、CI のビルドでだけ CLI の `--manifest` を付けて出す（審査 r7-N-6。vite.config.ts に書くと、本番のビルド＝frontend/Dockerfile:22 の出力にも manifest が入り、nginx がそのまま返すため）。ビルド後に dist/.vite/manifest.json を読み（置き場は公式資料 vite.dev/config/build-options の既定値）、入口 viewer/index.html の項目から file・imports・css をたどった集合を「viewer の資産」とする（dynamicImports もたどる。たどり方は公式資料 vite.dev/guide/backend-integration の importedChunks と同じ）。
  - 大きさ：この集合の JS の合計（圧縮前）が 300KB 以下。
  - 辞書の混入：この集合の JS の中に、目印の文字列が含まれない。目印は、本体の ja.json にだけある葉のキー名（入れ子の最後の名前。ASCII で、本体の辞書の外には現れにくい長い名前）を5つ選び、check-viewer-bundle.js の先頭の定数に置く（審査 r7-N-5。点つきの「a.b」の形はバンドルに文字列として現れないので使わない）。選んだ5つが本当に本体の辞書にあること、そして viewer の ja.json・en.json の葉のキー名には無いこと（金型の例外キーと重ならないこと）を、検査の最初に確かめる（辞書の変更で目印が消えたり viewer 側に入ったりしたら失敗させる。審査 r8-N-3）。
  - 検査のスクリプトは frontend/scripts/check-viewer-bundle.js に置く。実行する場所（審査 r7-B-1）：【事実】今の PR の CI にはフロントの本番ビルドが無い（.github/workflows/frontend-check.yml は npm ci・generate:api-types・check:all・tsc・unit tests・build-storybook だけ。本番ビルドは frontend/Dockerfile:22 のデプロイ時だけ）。そこで、.github/workflows/frontend-check.yml の check ジョブ（表示名 Frontend lint & custom checks、:10-11）の generate:api-types の後に、2つの手順「npx vite build --manifest」「node scripts/check-viewer-bundle.js」を足す。どちらも既存の手順と同じく working-directory: frontend を付ける（審査 r8-N-1）。ジョブ名と必須チェックの名前は変えない（Branch Protection の変更にならないように）。CI 設定の変更なので、段3の PR は ADR-1015 の B 区分に当たらず、GO の手順に従う。わざと viewer の中で本体の frontend/src/i18n.ts を import したときに、この検査が失敗することを段3で1回確かめ、生の出力を残す。

### D5. 申込フォームとトライアル
- 公開の POST /api/v1/viewer/signup を作る。
  - 項目（Q2f・Q2g の決定。Q2b・Q2d・Q2e の Discord ID は置き換え済みなので作らない）：
    - email：必須。254文字まで。形式の検査は既存の申込フォームと同じ方法にする（段1で既存の検査関数を指定する）。
    - line_name：必須。前後の空白を除いて1〜100文字。
    - inventory_issue：任意。1000文字まで。空欄は NULL。
    - 上の範囲を外れたら 422 を返し、画面は i18n の案内文を出して送信させない。
  - honeypot の欄に値が入っていたら、200 を返すが行は作らない。
  - 同じ email は 1時間に3回、同じ IP は 1時間に10回までにし、超えたら 429 を返す。
  - IP は nginx が付ける X-Real-IP から取る。X-Forwarded-For をそのまま信用しない（security-recon.md の指摘）。
  - すでに登録されている email で申し込まれたときも、同じ 200 を返す。行が pending なら、古い確認トークンを無効にして新しい確認メールを送る（email ごとの回数制限の内側で）。確認メールを見逃した人がやり直せるようにするため（審査 B-4）。verified・trial・active・suspended なら何もしない。メールも送らない。応答の違いから、登録済みかどうかが外から分からないようにする（審査 N-19）。
- 申込で pending の行を作り、確認メールを送る。verify-email が成功したら trial に変え、trial_expires_at を確認時刻＋14日にする（PO 決定 2026-10-15 Q5「Y」：自動で始め、起点はメールの確認が済んだ時刻）。
- 確認用のトークンは、secrets.token_urlsafe(32) で作る。DB には sha256 のハッシュだけを保存する。24時間で失効し、一度使ったら消す（審査 N-17）。
  - SMTP が本番で使えるかどうか（計画票 0 ①、2026-10-15 確認）：【事実】今の本番では送れない。本番 backend コンテナの SMTP_HOST・SMTP_PORT・SMTP_USER・SMTP_PASSWORD・MAIL_FROM が全部未設定で、送信の設定を読む backend/app/services/mail_config.py:28-34 は、どれかが空なら None を返して送らない。過去に送れていたかは、コンテナが作り直されていてログが無いため【未確認】。方式（SMTP の設定を入れるか、別の方法にするか）は PO に相談する。
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
| inventory の rows のキーの集合が、D2 の15キー（_GAS_COLUMNS の14個と offer_type）と完全に一致する。応答に fresh_window_hours があり、アプリの在庫 API の値と同じ | CI pytest（`set(keys) ==` 固定の集合。fresh_window_hours は定数 FRESH_WINDOW_HOURS（tcg_distribution_svc.py:212-213）と `==` で比べる。審査 r10 N-r10-4） |
| 作り置きの行から offer_type を除いた14キーが、同じ seed で run_distribution が GAS に渡す行（14列）と一致する | CI pytest（同じ seed。各行の offer_type を除いた辞書どうしを比べる。build_distribution_rows を両方が呼んでいることも確認する） |
| 対応表を services へ移した後も、既存のテスト test_offer_type_status_mapping_is_one_constant（test_inventory_distribution_rows.py:111-118）を変えずに通り、inventory_offers から同じ名前で読める | CI pytest（そのテストのファイルに差分が無いことを PR の diff で確かめる） |
| build_distribution_rows を切り出した後も、既存の配信のテストがすべて通る | CI pytest（既存のテストを変えずに実行） |
| analysis_runs か extraction_jobs に未完了があるとき、作り置きは前回の値と updated_at を変えず、fail_count も増えない。max_age_hours が無いときは前回の値を残し、fail_count が1増える | CI pytest |
| verify-email が成功すると状態が trial になり、trial_expires_at が「確認した時刻＋14日」になる | CI pytest（時刻を固定する） |
| 切り替え（trial→active）・停止・解除・延長の API は、super admin 以外のトークンでは 403 になる | CI pytest（require_super_admin） |
| 切り替え・停止・解除・延長のたびに viewer_status_changes に1行入り、action・from/to・actor が正しい。解除は最後の suspend の from_status に戻る。suspend の行が無い解除は 409 | CI pytest |
| Claude 用の専用スクリプトは、PO の画面と同じサービス関数を呼び、actor が claude で記録される | CI pytest（スクリプトの関数を直接呼ぶ） |
| 登録用の専用スクリプトは、登録・飛ばした・失敗の件数を出し、登録済みの email を飛ばす。2回続けて実行しても行が増えない | CI pytest（架空の3行のファイルで。本物の一覧は使わない） |
| PO の画面の目印①（同じ閲覧者が24時間で3つ以上の別 IP）と目印②（別の閲覧者どうしで同じ IP）が、条件どおりの行にだけ付く。ログイン履歴に日時・IP・端末が出る | CI pytest（API の応答）と Evaluator（Playwright で画面） |
| signup・verify-email・login・session の4本とも、Origin が違えば 403 になる | CI pytest（4本それぞれ） |
| CI の `npx vite build --manifest`（frontend-check.yml の check ジョブに足す手順）の後に dist/index.html と dist/viewer/index.html の両方ができ、manifest の viewer 入口からたどった JS に本体の辞書の目印の文字列が含まれない。viewer の中でわざと本体の i18n.ts を import すると検査が失敗する | CI（frontend-check.yml の check ジョブで check-viewer-bundle.js。失敗の確認は段3で1回、生の出力を残す）。本番と同じ設定のビルドで manifest が出ないことも段3で1回確かめる：段3のブランチで `npm run build`（vite.config.ts は本番と同じ。--manifest を付けない）を実行し、`test ! -e dist/.vite/manifest.json` の結果を生の出力で残す（審査 r8-N-2。本番 URL への curl は nginx.conf:23-25 の try_files で無くても 200 が返るので判定に使わない） |
| viewer の入口 main.tsx から import をたどった集合（import type は除き、動的な import() は含む）の t() のキー（例：金型の common.close）が viewer の辞書に無ければ検査が失敗する。viewer の ja と en のキーの集合が違えば失敗する | CI（check-i18n-missing-keys.js。わざと欠けたキーで失敗することを1回確かめる） |
| beat に refresh-viewer-inventory があり、周期が 60.0 秒である | CI pytest |
| build_distribution_rows が例外を投げたとき、また Redis への書き込み（SET）が例外を投げたとき、どちらも作り置きは前回の値を残し、fail_count が1増える | CI pytest（mock） |
| 保留でないときは、本番の閲覧 API が返す updated_at が今の時刻から60秒以内（Q11=y） | Evaluator（本番で curl。analysis_runs・extraction_jobs に未完了が無いことを同じ時刻に DB 読み取りで確かめ、生の出力を残す） |
| タスクが失敗した後、Redis の値と updated_at が変わらない。3回続けて失敗したら通知が1回だけ呼ばれ、4回目では呼ばれない。成功すると fail_count が 0 に戻る | CI pytest（mock。fail_count は Redis で数える） |
| pending の email で signup し直すと新しい確認メールが送られ、古いトークンは使えない | CI pytest |
| GET /api/v1/viewer/inventory を1分に20回叩いても 429 にならない | Evaluator（curl） |
| Redis が使えないときの logout は 503 になる | CI pytest（mock） |
| honeypot に値があると行が作られない。同じ email の4回目は 429 になる | CI pytest |
| 7日たった pending の行は消え、trial の行は残る | CI pytest |
| viewer の ja.json と en.json のキーの集合が一致する | CI（check-i18n-missing-keys.js に D4 で足す検査。本体の辞書どうしの比較は本設計の範囲外） |
| viewer の JS が、圧縮前の合計で 300KB 以下 | CI（frontend-check.yml の check ジョブで check-viewer-bundle.js。manifest の viewer 入口から imports・dynamicImports をたどった JS の合計） |
| run_distribution の4つの早期 return（#8・#8b・設定なし・取得失敗）の戻り値の辞書とログの水準が、切り出しの前後で同じ | CI pytest（4つそれぞれ。errors の文言を変更前の文言と比べる） |
| build_distribution_rows は、#8・#8b のとき kind="hold"、設定なしのとき "unset"、fetch_output_rows の例外のとき "error"、それ以外は "ok" を返し、ログを出さない | CI pytest（caplog で "[dist]" が出ないことを見る） |
| ロック viewer:inventory:lock が取られているとき、タスクは何も書かず、fail_count も変えない | CI pytest |
| signup の email は前後の空白を除いて小文字にしてから保存・比較される。「 A@x.com 」と「a@x.com」は同じ人として扱われる。users.email と同じ email（大文字小文字は無視）では行が作られない | CI pytest |
| app.salesanchor.jp/viewer/ が閲覧ページの title を返す | Evaluator（Playwright） |
| Redis のキーが無いとき、inventory は 503 を返す | CI pytest |
| ログアウトした後、時刻を2時間進めても、同じトークンで inventory を叩くと 401 になる | CI pytest（時刻を固定する） |
| 無効なトークンで session に10回失敗した IP は、11回目が 429 になる。同じ email への login は4回目からメールを送らない | CI pytest |
| リンク先を GET で2回開いた後でも、POST の session と verify-email でトークンが使える（GET ではトークンを消費しない） | CI pytest |
| トークンが正しくても、email が登録と違えば session は 401 になる。そのあと正しい email を入れれば、同じトークンで入れる | CI pytest |
| 確認用（verify_email）のトークンでは session に入れない | CI pytest |
| 新しいログイン用トークンを作ると、前の未使用のトークンは使えなくなる | CI pytest |
| 登録済みの email で signup しても、応答は新規のときと同じで、メールは送られない | CI pytest |
| 確認トークンは24時間を過ぎると無効になり、2回目は使えない | CI pytest |
| ログイン用のリンクは、active と期限内の trial の email にだけ送られる。未登録・pending・verified・suspended・期限切れの trial の email にはメールが送られず、応答は同じ 200 | CI pytest（メール送信を mock にする） |
| 申込：メールか LINE 名が空なら 422。Discord ID の欄は無く、送られてきても保存しない | CI pytest |
| 申込：在庫関連の課題が1000文字を超えたら 422。保存した文字列は画面にそのまま文字として出し、HTML として解釈しない | CI pytest |
| 延長：期限切れの trial に N=7 を指定すると、trial_expires_at が「記録した時刻＋7日」になり、inventory が 200 になる。N が0以下か整数でなければ 422。active・suspended・pending・verified には延長できない（409） | CI pytest（時刻を固定する） |
| ログイン記録：session の成功・失敗、login の要求、申込のたびに、閲覧者の行がある場合だけ viewer_login_events に1行入り、client_ip が X-Real-IP の値になる。閲覧者の行が無い email（未登録の login、合わない email の session）では行が入らない。91日前の行は毎日の処理で消える | CI pytest |
| ログイン用のリンクは15分で無効になり、一度使ったら2回目は 401 になる | CI pytest（時刻を固定する） |
| suspended にした後は、発行済みの12時間トークンでも inventory が 403 になる | CI pytest |
| GET /viewer/ の応答に Cache-Control: no-cache が付いている。/viewer でも同じページに着く | Evaluator（curl と Playwright） |
| 開いてから表が出るまでの時間が、本番の中央値で 1 秒以内 | Evaluator（Playwright で本番を5回計測する。ログイン済み（12時間トークンが保存済み）の状態で開く。ログインの操作の時間は含めない。始点は navigationStart、終点は表の最初の行が DOM に出た時刻。キャッシュなしの初回で計測し、生の値を残す） |
| 金型とトークンを守っている | `node scripts/check-ui-governance.js` |
| 閲覧ページの検索は features/inventory/searchNormalize.ts の normalizeForSearch を import して使い、viewer の中に正規化の関数を持たない。共通ベクタ（searchNormalize.vectors.json）の全件で、viewer の絞り込み関数が期待どおりに当たる | CI vitest（viewer の絞り込み関数のテストでベクタを読む）。`git grep -n "normalize(" frontend/src/pages/viewer` が normalizeForSearch の呼び出しだけ |
| 閲覧の列の定義（viewerColumns.tsx）とアプリの列の定義（buildInventoryColumns）が、D4 の対応表の列どうしで、並び順・sortable・align・stickyLeft・mobileOrder・mobileHidden が一致する。アプリの列を変えて viewer を変えないと失敗する | CI vitest（viewerColumns.parity.test.tsx。わざとアプリの1列の mobileOrder を変えて失敗することを段3で1回確かめ、生の出力を残す） |
| 区分の列：status が In Stock の行は「在庫」の文字、Pre-order の行は Badge（info・soft）、どちらでもない行は status の文字、status が空の行は「-」が出る。アプリの同じ行と同じ見え方 | CI vitest（4種の行で描画する。Pre-order の行は .comp-badge--info の要素があることを確かめる）と CI pytest（作り置きの offer_type が status_to_offer_type と同じ） |
| アプリの在庫表でも、Pre-order の行の区分が .comp-badge--info で描かれる（badge-negotiating のクラスが無い） | CI vitest（inventoryColumns の描画。審査 r10 N-r10-3） |
| 並び：既定で english_title の昇順（'' が先頭）→release_date の降順（空は末尾）→元の順。プルダウンの3択と見出しの並べ替えも、同じ english_title の中だけで効く。例外は商品名の見出しで並べるときで、english_title と japanese_title を同じ向きで並べる（inventory_offers.py:277-278。降順なら english_title も降順）。文字は Intl.Collator('en')（numeric なし） | CI vitest（固定の行で。english_title が '' の行が先頭、release_date が '' の行が同じまとまりの末尾、'item 10' と 'item 2' が文字の順、商品名の見出しの降順で english_title も降順になり、english_title が '' の行が末尾に来ることを含む。審査 r11 N-r11-7、r12 N-r12-3） |
| 本番で、アプリの /inventory と閲覧ページの並びが合う | Evaluator（比べる条件：同じタブ、24時間以内はオン、ほかの絞り込みと検索なし、既定の並び、同じ1分の中で両方を取る。作り置きは最大60秒遅れ、24時間の境目もずれるので、片方にしか無い行は比べる対象から外す（件数は残す）。両方にある行だけで、次の2つを数える（審査 r11 B-r11-1）。①題名のまとまりの順：両方にある english_title の、先頭からの並びを作り、前後が逆になった題名の組を数える。逆の組それぞれについて、本番 DB で `SELECT '<a>' < '<b>'`（読み取り専用。題名の中の ' は '' に重ねて書く。審査 r12 N-r12-2）と、ブラウザで `new Intl.Collator('en').compare('<a>','<b>') < 0` を求め、2つの答えが食い違う組だけを許す。答えが同じなのに逆になっている組が1件でもあれば不合格。②まとまりの中の順：同じ english_title の行どうしで、release_date の並び（空は末尾）が違えば不合格。比べるのはアプリの先頭50行に入る題名のまとまりすべて。生の値（両方の行・逆の組・2つの答え）を残す。プルダウンの「価格が安い順」も同じ条件で比べる。ただし②のまとまりの中の順は、release_date ではなく unit_price の昇順（空は末尾）で比べる（inventory_offers.py:127・:280。審査 r12 N-r12-1）。アプリは丸める前の価格で並べる（inventory_offers.py:127）。閲覧は作り置きの価格の文字を数にして並べるので、価格の文字が同じになる行どうしの順の違いは数えない。審査 r10 N-r10-8） |
| 閲覧ページの DataTable に stickyHeader・fitToWidth・mobileCards が付き、1ページ50件でページ送りが出る。既定の並びは release_date の降順、プルダウンは3択 | CI vitest（描画して確認する）と Evaluator（Playwright で PC と 375px） |
| コンディションのバッジの色が、アプリと同じ conditionBadgeVariant で決まる | CI vitest |

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
| 0 | 【2026-10-15 実施済み。結果は下の「計画票0の結果」】実装前の確認を事実で埋める。①本番の SMTP。②fetch_output_rows の所要時間。③本番で配信行が指す products.tenant_id の分布（人間が SELECT を実行する。NULL 以外があれば、見え方の差を PO に報告する）。④app.salesanchor.jp の前に Cloudflare などのプロキシがいるか（審査 N-20。いるなら set_real_ip_from と real_ip_header を D4 に足す）。⑤（r9 で解決済み：FRESH_WINDOW_HOURS、tcg_distribution_svc.py:212-213） | Sonnet（調査）＋PO（DB 読み取り・DNS の確認） |
| 1 | 表とトークンと分離テスト（D1）。守り手のテストを作る | Sonnet |
| 2 | 作り置きと閲覧 API（D2・D3） | Sonnet |
| 3 | 閲覧ページ（D4） | Sonnet |
| 4 | 申込、トライアル、pending の掃除、管理の操作（D5） | Sonnet |
| 各段 | コード審査（Opus。PO 決定 2026-10-15 で Fable から変更）、セキュリティ審査、マージ。secret の追加は PO の確認を取る | Opus |
| 計測用 | 本番の表示時間（受入条件の最後から2行目）を測るための閲覧者アカウントは、段4の後に登録用の専用スクリプトで1件だけ作る（email は社内で受け取れるアドレス。一覧ファイルは1行だけのものを別に作る。登録した時点の期限にかかわらず、登録の直後に extend N=1 で「記録した時刻＋1日」にする。審査 r7-N-7・r8-N-5）。作成は PO 本人の GO（上の「操作の GO の条件」）。計測が終わったら Q3 の Claude の経路で suspended にし、viewer_status_changes に残す。行は消さない（履歴を残すため）。作る前と止めた後に PO へ3行で報告する（審査 r6 N-12） | PO（GO）＋Sonnet（実行） |

Discord 案（検討中・未決。2026-10-16 PO 提案「トライアルの申込みが来る、フォームを送る、Discordに案内をする、専用サーバーでチケットを発行してもらう、チケット発行をトリガーに専用URLとパスワードを送る」。SMTP が未設定のため。調査の生出力は /tmp/CC報告ファイル/viewer_discord/）
- 【事実】本番で discord-gateway が動いている（astro-webapp-discord-gateway-1 Up、DISCORD_BOT_TOKEN は SET）。チケットはボタン（custom_id が ticket_open で始まる）を押したときだけ作られる（backend/app/discord_gateway/client.py:210-221）。作ると本人・staff ロール・ボットだけが見える部屋ができ、テナントの leads に書く（ticket_channel_creator.py）。
- 【事実】チケットができたことをほかの処理に知らせる仕組みは無い。ボットから個別メッセージ（DM）を送るコードも無い（git grep で create_dm・dm_channel の送信側 0 件。dm_writer.py は受信の記録だけ）。作るなら、チケット部屋の作成直後に閲覧者の登録とURL・パスワードの投稿を足す新規実装になる。
- 【未確認】トライアル申込者を受けるテナント（本番の設定は tenant 1・4・6 の3つ）。申込とチケットを同じ人だと結び付ける方法。
- 決まるまで、D1（メールのリンクでのログイン）は保留。
- 申込とチケットの結び付け（2026-10-16 PO 質問「フォームを入力してもらったら専用のURLを発行してそのURLから入ってきたユーザーを紐付けられる？」への調査。未決）：
  - 【事実・Discord 公式 docs.discord.com/developers/topics/oauth2】OAuth2 の identify スコープで「/users/@me」（Discord の利用者 ID）が取れる。コードの引き換えには client_secret が要る。guilds.join スコープで、ボットがその人をサーバーに入れられる（docs.discord.com/developers/resources/guild「Add Guild Member」。ボットに CREATE_INSTANT_INVITE 権限が要る）。
  - 【事実】今のボットの権限 805432406（backend/app/routers/discord_oauth.py:72）は CREATE_INSTANT_INVITE も MANAGE_GUILD も持たない（ビット計算）。既存の OAuth はボットをサーバーに招待する流れだけで（同ファイル:1-19）、利用者 ID を取る流れは無い。DISCORD_CLIENT_SECRET を読むコードも無い（git grep 0 件）。
  - 案A（推奨）：フォームの送信後に、その人専用の URL（使い切り）を出す。押すと Discord の「本人確認の許可」画面になり、許可すると Discord の利用者 ID が申込に結び付く。チケットを作った人の ID と同じなら、自動で URL とパスワードを部屋に出す。要るもの：Discord 開発者画面での client_secret の発行と戻り先 URL の登録（PO の GUI 作業）。
  - 案B：その人専用の Discord 招待リンクを作り、どのリンクで入ったかを見分ける。ボットに MANAGE_GUILD が要り、ADR-091:69 で除外している権限なので ADR の変更が要る。招待の使用回数の差で見分ける方式で、確実さは案A より低い。
  - 【PO 決定 2026-10-16「y」】案D（申込コード方式）を採る。
  - 案D（2026-10-16 Fable 相談の推奨。PO「FABLEに相談」）：フォームの送信後に、その人だけの申込コードを出す（DB には sha256 だけ、使い切り、7日）。チケットのボタンを押したとき、ボットが小窓（send_modal）でコードを聞き、合えばボタンを押した人の Discord ID（client.py:231 member = interaction.user）を閲覧者に結び付けて、部屋に URL と初期パスワードを出す。Discord 開発者画面の作業・client_secret・ボット権限の追加・入口の追加が要らない。変更点：client.py:226 の defer() を send_modal に置き換える。【未確認】専用サーバーのテナント、チケット作成でそのテナントの leads に行ができること（ticket_channel_creator.py:575）を受け入れるか、discord-gateway が public.viewer_accounts に書けるか、スマホで小窓が出るか。安全策の案：試行は Discord ID ごとに1時間5回まで、discord_user_id は一意、初期パスワードは初回ログインで変更させる（部屋は staff にも見える）。
- 【PO 決定 2026-10-16】原文「チケットは個別チャンネルにしたいので作り直しが原則しない、パスワードを忘れた場合はメールで再発行する機能にする」。ログインは専用URL＋1人1つのパスワード。チケットは1人1部屋で作り直さない（既存の ticket_channel_creator.py も作成済みなら同じ部屋を返す）。パスワードを忘れたらメールで再発行する。
  - 【事実】メールでの再発行にも SMTP が要る（計画票0 ①：本番は未設定）。
  - 【PO 決定 2026-10-16「y」】送信元メールの5項目（SMTP_HOST・SMTP_PORT・SMTP_USER・SMTP_PASSWORD・MAIL_FROM）を PO が用意して GitHub の秘密設定に入れる。値はチャット・リポジトリに出さない。入れた後のデプロイで本番の .env に入り（deploy.yml:323-327）、テストメール1通の到着で確かめる。
  - 【事実 2026-10-15T16:26Z】#4344 のデプロイ後、本番 backend の5項目は全部 SET（MAIL_FROM は22文字）。backend から mail_config.smtp_settings() を使って support@ 宛てに1通送り、RESULT=SENT refused=0（/tmp/CC報告ファイル/viewer_discord/testmail_result.txt）。受信箱に届いたかは PO の目視が残り。
- サーバー（2026-10-16）：専用サーバーを新しく作る案に PO「n,1つで管理したい」→ 説明のうえ「y」。運用サーバー「Sales Anchor」（ID 末尾 1187）1つで受ける。チケットとパスワードの送信はアプリのボット（Sales Anchor#8667、権限 805432406 で招待済み）が行い、SA Bug Intake は保守運用だけに使う。
  - 【事実 2026-10-16】新しく入った人（@everyone）に、アラートのカテゴリと子4つ・テキスト「一般」・ボイス「一般」が見えていた（/tmp/CC報告ファイル/viewer_discord/visibility.txt）。PO「y」で、役割のなかった人間2人に PO が画面で Sales Anchor Staff を付け、対象7つを「ボット・Staff・SA Bug Intake は許可 → 最後に @everyone を拒否」の順で設定した。変更後に @everyone に見えるのは中身が空のカテゴリ2つだけ（redo_visibility_after.txt）。Staff・2つのボットは7つとも見える（redo_roles_after.txt）。戻し方は restore_overwrites.py（未実行）。1回目は @everyone を先に拒否してボットが自分を締め出し、テキスト「一般」が一時的に所有者以外に見えなくなった（PO が画面で戻した。visibility_restored.txt は最初と差分なし）。教訓：上書きはボット自身の許可を先に入れる。
  - 【事実・調査】Discord 公式資料に、サーバー全体のメンバー一覧を一般の人から隠す設定は見つからなかった。公式にある対策は見せるチャンネルを絞ることだけ。全員が見る部屋で互いが一覧に出るかは公式に明記が無く【未確認】（memberlist_research.md）。
- 【PO 決定 2026-10-16】原文「全体用のカテゴリとチケットチャンネルはカテゴリを分ける、全体用としては全員が投稿できるチャンネル、障害の発生と復旧報告用のチャンネルを設置、チケットチャンネルは個別のDM用の部屋として使う」。お客さんに見せるのは「全体用」カテゴリ（全員が投稿できる部屋＋障害の発生と復旧の報告の部屋）と、その人のチケット部屋だけ。チケット部屋は本人とスタッフだけの個別の連絡部屋として使う。全体用の部屋ではお客さんどうしが見えることを前提とする。
  - 【PO 決定 2026-10-16「y」】全体用カテゴリに、チケットのボタンだけを置く「受付」部屋（お客さんは読むだけ）を作る。原文の追記「トレカ販売用に顧客用に作ったチケットと同じ仕組みを」：既存のチケットの仕組み（client.py・ticket_channel_creator.py）を使う。障害報告の部屋はスタッフとボットだけが書く（お知らせの部屋のため Opus が既定とした）。既存の仕組みを運用サーバーで使うときに合わない点は下に記録（/tmp/CC報告ファイル/viewer_ticket_recon/）。
  - 【事実 2026-10-16 Sonnet 調査・origin/main と本番 DB の読み取り（READ ONLY）。生出力 /tmp/CC報告ファイル/viewer_ticket_recon/】既存の仕組みのまま運用サーバーで使うと合わない点：
    1. 運用サーバー（末尾 1187）は public.tenant_discord_config に未登録（本番3行：tenant 1・4・6）。運用用のテナントも無い。gateway は DB の登録だけで guild を判定する（backend/app/discord_gateway/client.py:94-121）。
    2. 1 guild = 1 テナント（UNIQUE(guild_id)、migrations/20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql）。既存テナントに付け替えると元のサーバーのチケットが止まる。
    3. チケットを作ると、そのテナントの leads に必ず1行入る（backend/app/discord_gateway/ticket_channel_creator.py:570-622）。止める分岐は無い。部屋での本人の発言も meta_messages に保存され翻訳に回る（ticket_channel_writer.py:217,298）。申込コードのやり取りもそこに残る。
    4. ボタンの文面と custom_id「ticket_open」は固定（bot_texts.py:26-29,65-78）。押下は startswith("ticket_open") で受ける（client.py:216-220）ので、新しいボタンの名前は ticket_open で始めない。
    5. 設定はテナントごとに1組（カテゴリ・ボタン部屋・staff ロール）。send_modal を使うコードは無い（git grep 0件）。
  - 【PO 決定 2026-10-16「y」】トライアル申込者はアプリの見込み客（tenant の leads）に入れない。お客さんから見た動き（ボタン→自分専用の部屋）は顧客用チケットと同じにし、部屋を作る部品は使い回すが、処理はトライアル専用に分ける（ボタンの名前は ticket_open で始めない。申込者の記録は viewer_accounts などの閲覧ページ用の表だけ）。顧客用チケットの動きは変えない。
  - 【PO 質問 2026-10-16】原文「ツールの顧客管理も出来るように出来る？」。回答：管理画面（super admin の ViewerAccountsPage。下の Q3 の「管理 API と画面」）で、一覧・状態の切り替え・停止と解除・期限の延長・ログイン記録を扱う設計が既にある。Discord 案に合わせて、一覧に Discord の利用者 ID と、その人のチケット部屋への移動を足す（列の追加は D1 の書き直しで扱う）。

計画票0の結果（2026-10-15、Sonnet 調査・Opus が生出力を再確認。生出力は /tmp/CC報告ファイル/viewer_step0/）
- ① SMTP：【事実】本番 backend の SMTP_HOST・SMTP_PORT・SMTP_USER・SMTP_PASSWORD・MAIL_FROM は全部未設定（env_check.txt）。今のままではメールを送れない。deploy.yml:323-327 は GitHub の秘密設定 SMTP_HOST・SMTP_PORT・SMTP_USER・SMTP_PASSWORD・MAIL_FROM を本番の .env に書く作りだが、その5つは GitHub に登録されていない（gh secret list に SMTP・MAIL_FROM の名前が無い。2026-10-15）。段2の本番利用と段4の公開は、PO と方式を決めて送れることを確かめるまで止める。
- ② fetch_output_rows の DB 部分：【事実】本番設定（include_flag_single=false、max_age_hours=48）で組み立てた SQL を EXPLAIN ANALYZE で3回、1135.0 ms・525.5 ms・497.5 ms、返却 877 行（explain_1〜3.txt）。1分ごとの作り置きには収まる。Python 側の整形を含む全体の時間は【未確認】。
- ③ products.tenant_id：【事実】配信 877 行が指す products の tenant_id は全部 NULL、NULL 以外は 0 件（tenant_dist.txt）。PO に報告する見え方の差は無い。
- ④ プロキシ：【事実】app.salesanchor.jp は 49.212.137.46（さくら）、応答ヘッダは server: nginx のみで cf-ray・via が無い（dig.txt・curl_head.txt）。Cloudflare は前段にいないので、D4 に set_real_ip_from・real_ip_header は足さない。

---

## 外部・過去事例の参照と我々への応用

- 過去事例（社内）：GAS の在庫一覧は、Google の枠だけで 3〜7 秒かかる（recon.md §2）。応用：閲覧ページを Google の枠の外に置く。
- 過去事例（社内）：ADR-097・126・127 で、署名トークン付きの公開登録フォームを作った。応用：公開の入口は署名と回数制限で守る。
- 過去事例（社内）：GAS への配信を Celery から作る前例（tcg_extraction.py の _run_auto_distribution（origin/main 65ed8cd8b では :736 から））。応用：同じ接続条件で作り置きを作る。
- 外部事例（調査 2026-10-15。全文と出典は PR に載せず、要点だけを下に書く。数値は出典に書かれたものだけ）：
  - 成功・Yelp（2021-03、Yelp Engineering Blog）：事業者向けの再ログインを、メールのリンクに置き換えた。導入前は、パスワードの再設定で失敗したことを知らせるメールを1日に約7,500回送っていた。リンクは1回だけ使え、期限が付いている。無効なリンクのときは通常のログイン画面に戻す。応用：D1 のトークンも1回限りで期限付きにし、無効なときは「ログインの申込」の画面に戻す。
  - 成功・ドイツ連邦 DigitalService（2022-08、公式ブログ）：固定資産税の申告サービスで、メールのリンクによる登録・ログインを始め、4週間で15万人を超えた。手順はパスワードの再設定の6段から4段に減った。学び（審査 r6 N-11 で訂正）：利用者は「リンクは1回限り」「最新のリンクだけが有効」を想定しておらず、説明が要った。応用：リンクが1回限りであること、新しく頼むと前のリンクが使えなくなることを、メールの本文と画面④の i18n の文言で出す。ブラウザに縛らず email の再入力で本人を確かめる（Q2c）。
  - 失敗・Supabase の議論（2025-12）、Microsoft Defender の議論（2023-07）、Ghost のフォーラム（2020〜2023）：企業のメールの安全検査が、届いた時点でリンクを先に開いた。GET でトークンを使ったり状態を変えたりする作りだったため、リンクが無効になったり、承認が勝手に実行されたりした。件数は書かれていない。応用：D1 は、トークンを `#` の後ろに置き、ページで POST するまで使わない。受入条件の「GET で2回開いた後でも使える」がこの対策の確認になる。
  - 失敗・Auth0 の公式記事（2025-10 更新）：リンクを、申し込んだのとは別のブラウザで開くと失敗する作りのため、利用者に「リンクをコピーして元のブラウザに貼る」よう案内している。応用：email の再入力方式は、この縛りを持たない。
  - トライアル期間・Management Science の論文（2023、新規利用者 337,724人に無作為に割り当て）：購読した割合は、7日が15.35%、14日が14.97%、30日が14.67%で、差は1ポイント未満。Tunguz の約600社の調査（SaaStr）でも、7・14・21・30日のあいだに有意な差は無く、14日が最も多かった。応用：14日（Q5）は外部の実測から外れていない。ただし対象は個人向けのソフトなので、本件での転換率を予想する根拠にはしない。
  - 共有の検知・Netflix の株主向けレター（2023 Q2、SEC に提出）：世帯の外での共有を有料にした後、有料会員の純増は590万人だった（前年の同じ期はマイナス100万人）。世帯の判定には IP・端末・利用の状況を使っている（この判定方法の部分は、レターの本文を読んでおらず、検索結果の要約による【未確認】）。一方、先に始めたスペインでは、2023 Q1 に約100万人が減り、解約率が3倍になった（Kantar の推計の報道。二次情報）。誤って検知した割合を数値で公開した例は見つからなかった。応用：本設計は自動では止めず、目印を出して PO が判断する（Q6）。止めすぎによる離脱を避けられる。
  - 短い作り置き・NGINX の公式ブログ（2015-12）：WordPress で、作り置きが無いときは毎秒5.53件しか返せなかった。1秒だけ作り置きすると毎秒2,185件になった。期限が切れた瞬間にリクエストが元に集中することへの対策も要る、と書いている。Facebook の論文（NSDI 2013）では、作り直しを10秒に1回に絞ることで、DB への問い合わせのピークが毎秒17,000件から1,300件に下がった。応用：D3 は閲覧者のリクエストでは作り直さず、1分ごとのタスクが1本で作る。期限が切れたときの集中は構造上起きない。
  - 適用の限界：上の事例は、どれも本件より大きな規模か、個人向けのサービス。メールのリンクの成功率・離脱率、60秒の作り置きの効果、GAS からの移行前後の速度について、数値を出した一次の事例は見つからなかった。本件の成否は、受入条件の表と、段0〜2 の実測で判定する。

## 維持の仕組み

- 守り手: 人手で守る（段1の PR で backend/tests/test_viewer_isolation.py を作り、この行をそのファイルパスに書き換える。このテストは全ルートを自動で列挙するので、API を足すたびに検査の対象になる）
- 在庫の行の定義は、ADR-1014 の1か所のまま変えない。
- 対象：閲覧者のトークンでアプリの API に入れてしまうこと（在庫表以外が見えること）。作り置きの在庫が、配信の正本（distribution_rows_sql）とずれること。

## 継続

- 完了後の監視：作り置きタスクが続けて失敗した回数（D3 の Discord 通知）。タスクがそもそも動かない場合（worker の停止）は失敗として数えられないので、updated_at から10分以上たったら知らせる仕組みを足す（経路は段2で既存のものから選ぶ。審査 N-26）。ほかに、閲覧 API の p50、閲覧者の数（trial と active）。
- 保留の間との関係（審査 r6 N-5）：保留（再解析・抽出の途中）が10分を超えて続くと、updated_at の通知も鳴る。これは「表が10分以上止まっている」という事実の知らせとして正しいので、保留の間も止めない。通知の文に「保留中かどうか」（analysis_runs・extraction_jobs の未完了の件数）を添え、受け取った人が正常な待ちか故障かを見分けられるようにする。Q11 で「保留中も作る」に決まった場合は、この段落は要らなくなる。
- 次のフェーズ：GAS の停止（Q4）。社内ユーザーの権限の穴は別の設計で扱う（下の「別件」）。

---

## PO 決定待ち（1つずつ聞く）

- Q15.【決定 2026-10-15 PO「y」】アプリと同じ並びのまま作る（英語名が空の行は既定の並びで先頭）。以下は質問の原文。（審査 r10 B-r10-1）：英語名が空の行（33商品）は、アプリと同じく既定の並びで表の先頭にまとまる。この見え方のままでよいか。y ならアプリと同じ並びで作る。n なら空の行を末尾に回すが、アプリ（inventory_offers.py:276-280）も同じに直す設計を足す（アプリと閲覧で並びを分けない）。段3の並びの実装はこの回答の後に行う。
- ~~Q1. 閲覧ページに出す列~~ → **決定済み**：今の GAS と同じ列（PO y、2026-10-15）。その後 Q13=y で発送日を含む14列になった。D2 に反映した。
- ~~Q2a. ログインの方法~~ → **決定済み**：メールのリンクで入る。登録フォームの情報で管理し、リンクを知っているだけでは見られない形にする（PO、2026-10-15）。D1 に反映した。
- Q2b.【置き換え済み・実装しない（Q2f）】【決定 2026-10-15 PO】原文「トライアルではメール、LINE名、DISCORD IDのみ、本契約に進むときに詳しい情報を別途フォームで取得する」。申込フォームはメール・LINE 名・Discord ID の3つ（後に Q2f でメールと LINE 名の2つに変更）。本契約用の詳しい情報フォームは今回の対象外（別の便で設計する）。
- Q2d.【置き換え済み・実装しない（Q2f）】【決定 2026-10-15 PO】原文「数字のID、SAの顧客対応と同様に顧客管理で利用するため」。数字のIDで受け取る。閲覧者の行はテナントの取引先（companies）には写さない（SSOT）。本契約で取引先とつなぐ方法は、本契約フォームの便で設計する。
- Q2e.【置き換え済み・実装しない（Q2f）】【決定 2026-10-15 PO】原文「Discord ID だけ任意、ただし間違えて送られてくる可能性があるので数字以外は受け付けないようにしてくれ」。メールと LINE 名は必須、Discord の数字のIDは任意。入力があるときは、既存の検証と同じ `^\d{17,20}$`（backend/app/routers/discord_ticket_config.py:48）に合わない値を 422 で拒み、画面は i18n の案内文を出して送信させない。空欄は NULL で保存する。
- Q2f.【決定 2026-10-15 PO「Y」】Q2d・Q2e を置き換える。申込フォームはメールと LINE 名の2つだけにし、Discord ID は聞かない。Discord の数字のIDは、顧客ごとの専用URL（Discord でログイン→identify と guilds.join で ID を取得→ボットがサーバーに加える）で自動取得する。この仕組みと、ID の保存先（既存の顧客管理の列にそろえるか）は本便の対象外とし、別の仕事として設計する。調査の記録は /tmp/CC報告ファイル/viewer_discord_autoid_facts.txt（公式資料：docs.discord.com/developers/topics/oauth2、resources/guild、events/gateway-events）。
- Q2g.【決定 2026-10-15 PO】原文「在庫関連の課題も自由記述で最初のフォームに入力させる」。申込フォームはメール・LINE 名・在庫関連の課題（自由記述）の3つ。課題は任意（PO「Y」2026-10-15）。空欄でも申し込める。
- Q2c.【決定 2026-10-15 PO「Y」】リンクを押した後に、登録した email を入力し直してもらう（D1 のまま）。
- Q3.【決定 2026-10-15 PO】原文「Y,私もしくはあなたが切り替えできるようにする。私がやる場合はフロントエンドから切り替えをするがあなたに任せる場合はSSHを使用する」。切り替え（trial→active）と停止（→suspended）、停止の解除ができるのは PO と Claude だけ。
  - PO の経路：super admin 画面。API は既存の require_super_admin（backend/app/auth/dependencies.py:495（origin/main 65ed8cd8b））で守り、画面は pages/super-admin/ 配下に置く（既存例 backend/app/routers/super_admin_phase_switch.py:65・:89）。
  - Claude の経路：【事実】制限付き鍵 salesanchor-claude で実行できるのは監視の4コマンドだけで、DB の読み書きはできない（docs/adr/ADR-079-claude-code-monitoring-access.md:57、docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58-59・:220-224）。DB 書き込みには無制限鍵が要り、CLAUDE.md:29-30 により作業ごとに PO の GO が要る。そこで、SQL を手で書かず、backend コンテナ内の専用スクリプト（引数は email と変更後の状態だけ。PO の画面と同じサービス関数を呼ぶ）を無制限鍵で実行する。GO 原文は依頼文と記録に転記する。
  - GO の発行者（PO 決定 2026-10-15、原文「N,仕様に関しては壁打ちして決めているので仕様から逸脱していないGOは全てOPUSに権限委譲する」）：【2026-10-15 訂正】委任の正式記録（docs/handoff/go-record-transcription/opus-delegation.md。PR #4293 の審査で範囲を PR の GO に絞った。#4293 は 2026-10-15 に main へマージ済み＝merge commit 75fea37c1。マージ前の ADR-1003 の元の範囲も PR の GO だけなので、結論は同じ）は、無制限鍵での本番の変更を含まない。CLAUDE.md:30 により、Claude の経路（無制限鍵）の操作は、作業ごとに PO 本人の GO が要る。委任を広げるには ADR と CLAUDE.md の改訂が要る（Q12）。PO の画面からの操作は PO 本人が行うので GO は要らない。複数人の一括変更・削除・本設計に無い状態の変更など、仕様から外れる操作は Opus が止めて PO に聞く。
  - **操作の GO の条件（この1か所を正とする。審査 r6 N-9、r7-N-7）**：Claude の経路（無制限鍵）の操作は、Q12 が決まるまで、すべて PO 本人の GO で行う（CLAUDE.md:30）。依頼の前に PO へ3行で報告する（誰を・何から何へ・理由）。無制限鍵の操作を Sonnet に頼むときは、PO が `bash scripts/permit-danger.sh "<操作>"` を1回実行したチケットを証拠にする（Opus が伝えた PO の許可は、Sonnet にとって伝聞になるため。審査 r8-N-5）。Q12 で委任が認められた後に Opus が GO を出せるのは、①対象が1人、②変更が上の管理 API の4つ（activate・suspend・unsuspend・extend）のどれかで上の表のとおりの遷移、③実行の前に PO へ3行で報告、の3つをすべて満たすときだけにする予定（Q12 の案）。Q9 の22人の一括登録と、計画票の計測用アカウントの作成は、Q12 の結果にかかわらず PO 本人の GO にする（4つの操作に当たらないため）。
  - 期限の延長（PO 決定 2026-10-15、原文「トライアルが終了した人も任意で期間を決めて閲覧期限を延長させる機能もつけてほしい、延長させるのは延長を記録した日次から換算する」）：状態が trial の人（期限内・期限切れのどちらも）に、操作する人が日数 N（1以上の整数）を指定する。trial_expires_at は「延長を記録した時刻＋N日」になる。元の期限に足すのではない。状態は trial のまま。PO の画面と Claude の経路の両方から同じサービス関数で行い、変更前後の期限・N・実行者・日時を記録する。
  - どちらの経路でも、変更前後の状態・実行者（PO／Claude）・日時を記録に残す。保存先は新しい表 public.viewer_status_changes にする。【事実】既存の tenant の audit_logs は tenant_id と user_id が必須で、閲覧者には使えない（backend/app/services/audit.py:277-）。auth_events は「誰が」の列が無い（migrations/001_create_auth_events.sql:6-16）。public.audit_log（migrations/20260921_110000_pipeline_tables_public.sql:404-413）は record_id が UUID 型で、閲覧者の id（BIGSERIAL）を入れられない。また、この表は TCG の商品の編集の履歴で、書き手は商品詳細の処理（backend/tests/test_tcg_product_detail_pg.py:194 で確認される経路）なので、閲覧者の状態の履歴を混ぜない。
    - 列：id、viewer_id（viewer_accounts への FK）、action（activate・suspend・unsuspend・extend の4つ）、from_status、to_status、from_expires_at、to_expires_at、extend_days（extend のときだけ）、actor（po か claude の2値）、actor_user_id（PO の画面からのときの users.id。ADR-1008 に従い users を指す。Claude の経路では NULL）、created_at。
    - 停止の解除（unsuspend）は、その閲覧者の最後の suspend の行の from_status に戻す。viewer_accounts に「停止前の状態」の列は足さない（同じ事実を2か所に持たないため）。suspend の行が無いのに解除しようとしたら 409 にする。
    - 状態と期限の正本は viewer_accounts。この表は「いつ・誰が・何を変えたか」の履歴だけを持つ。保存期間は Q7 で決める。
  - 生の調査記録：/tmp/CC報告ファイル/viewer_ssh_recon.txt
  - 管理 API と画面（段4。審査 r6 N-8）：router は新しいファイル backend/app/routers/super_admin_viewers.py にし、前例 super_admin_phase_switch.py（:62-66 の `/super-admin/...` の形、main.py:639 の prefix "/api/v1"）にならう。すべて require_super_admin。入出力は JSON。

    | method とパス | 入力 | 出力 | エラー |
    |---|---|---|---|
    | GET /api/v1/super-admin/viewers | なし | 閲覧者の一覧（id・email・line_name・inventory_issue・状態・trial_expires_at・作成日時・目印①②） | 403 |
    | GET /api/v1/super-admin/viewers/{id}/logins | なし | ログイン記録（日時・event_type・IP・端末。新しい順） | 403・404 |
    | POST /api/v1/super-admin/viewers/{id}/activate | なし | 変更後の閲覧者 | 403・404・409（trial 以外） |
    | POST /api/v1/super-admin/viewers/{id}/suspend | なし | 同上 | 403・404・409（すでに suspended） |
    | POST /api/v1/super-admin/viewers/{id}/unsuspend | なし | 同上 | 403・404・409（suspended でない、または suspend の行が無い） |
    | POST /api/v1/super-admin/viewers/{id}/extend | {"days": N} | 同上 | 403・404・409（trial 以外）・422（N が1未満か整数でない） |

    - 4つの変更の API は、1つのサービス関数（backend/app/services/viewer_admin.py。Claude の専用スクリプトもこれを呼ぶ）を呼び、同じトランザクションで viewer_status_changes に1行書く。
    - 画面は frontend/src/pages/super-admin/ViewerAccountsPage.tsx の1ページ。部品：一覧は DataTable、状態は Badge、操作は Button、延長の日数は TextField type="number"、確認は Modal、ログイン記録は Drawer。すべて既存の金型で足りる。文言は本体の ja.json・en.json（社員の画面なので viewer の辞書ではない）。
- **PO 決定（2026-10-15、アプリと GAS の差分12項目への回答。原文の要旨。番号は Opus がチャットで示した一覧の番号）**：
  - 2 並び替えのプルダウン（4択）：「同じレイアウトと仕組みで追加」
    - 追加の決定（同日）：「新しい順」は削除する。「ヘッダーの並び替え機能で対応できるのでいらない、デフォルトで発売日の新しい順に並んでいるので不要」。プルダウンは3択（価格が安い順・在庫が多い順・投稿が新しい）。既定の並びは発売日の新しい順（アプリの今の既定 PG:133-134 と同じ）。【r9 で解決】アプリの実物（origin/main e1351e663 の InventoryPage.tsx:117-118）は表全体を release_date の降順に並べ、英語タイトルでまとめない。閲覧ページもこれと同じにする（D4）。
  - 3 検索：「GAS と同じ仕組みとレイアウトにして」
  - 4 提供者の絞り込み：「選んだ人だけ出すにする、レイアウトも同じにする」
  - 5 シリーズのタブ：「アプリを正とする」
  - 6 商品名：「アプリを正とする、ただし英語が下に出ていない、TCGシリーズ列は不要なので非表示にする」（【未確認】英語が出ていない原因。アプリのコード PG:666-670 は下段に英語を出す作りなので、データか表示の不具合として調べる）
  - 7 見出しの固定：採用。8 表を縮めて画面に収める：採用。9 スマホの縦カード：採用。10 色つきバッジ：採用。11 発送日の列：採用（Q13 は y で決定）
  - 12 件数とページ送り：「ページ送り機能をつける」
  - 1 更新ボタン：【決定 2026-10-15 PO「y」】アプリと同じく付けない（【事実】アプリの InventoryPage.tsx に手動の更新ボタンは無い）。作り置きは1分ごとに作り直し、最新はページの再読み込みで出る。画面には最終更新の時刻だけを出す。
  - Q14.【決定 2026-10-15 PO】原文「アプリの在庫表も同じ作りにする」。この決定を、アプリの在庫表と閲覧ページの両方に入れる（＝2つを同じ部品で作る）。アプリ側は便1〜3（#4317・#4327・#4330）で本番に反映済み。閲覧ページは r9 で D4 を書き直した。8・9 と 4 の複数選択は、便1・便3 で金型に登録済み（DataTable の stickyHeader・fitToWidth・mobileCards、MultiSelect）。
- Q13.（2026-10-15 の突き合わせ。/tmp/CC報告ファイル/viewer_gas_parity_check.md）Q1 の「今の GAS と同じ13列」は、2026-10-14 に GAS に発送日（Ship_JA）を足す前の手元の写し（~/tcg-viewer-1hc-release、Ship_JA 0件）を基準にしていた。【事実】本番の GAS（版16）の許可リストは14列（/tmp/CC報告ファイル/gas_pull_prod/Code.js:10-25）で、画面の11列に「発送日」がある（/tmp/CC報告ファイル/k7_prod.txt K7-1、発送日が空でない行は 891 行中 37 行）。発送日を閲覧ページにも出すか →【決定 y（PO 2026-10-15）】14列にし、表示は備考の次（アプリの列の並びと同じ）。r9 で D2・D3・D4 と受入に反映した。【r9 の注記】下の6点は、その後の Q14（アプリと同じ作り）で、アプリの実物に合わせる形に置き換えた（D4。商品名は上が日本語・下が英語、並びはアプリと同じ）。元の文：あわせて、GAS にあって本書に書いていない次の6点は、GAS と同じにする方向で書き足す（PO の方針「GAS に合わせる」の範囲）：検索の対象列、並べ替え4択の中身と既定、英語タイトルでまとめてから並べる順、見出しで並べ替えできない列、スマホの操作の配置、タイトルの上段＝英語・下段＝日本語。
- Q4. GAS の在庫一覧をいつ止めるか（移行の期間）。
- Q5.【決定 2026-10-15 PO「Y」】メールの確認が済んだ時点で自動的にトライアルを始め、14日はその時刻から数える。人の承認は挟まない。verified は今回使わない（5値は残す）。
- Q6.【決定 2026-10-15 PO「Y」】別のメールでの申込み直しは自動では止めない。気付いたら PO か Claude が停止する。判断の材料として、下のログイン記録と、申込一覧で同じ LINE 名・同じ IP の行に目印を出す。
- ログイン記録（PO 決定 2026-10-15、原文「ログインのログを取る形でいつ誰がどのIPからなどが特定できるのであれば1つのアカウントから複数人がログインしていないか、二重登録で回避していないかなど判断できる」）：
  - 【事実】既存の public.auth_events（migrations/001_create_auth_events.sql:6-16）は、いつ・IP（client_ip VARCHAR(45)）・端末（user_agent VARCHAR(500)）を持つが、「誰が」の列が無い。また AuditMiddleware が書くのは /api/v1/auth/ 配下と 401/403 だけ（backend/app/middleware/audit.py:34・:37）。保存は90日で、毎日自動で消す（backend/app/tasks/maintenance.py:30、backend/app/celery_app.py:96-99）。tenant の audit_logs は tenant_id と user_id が必須なので、閲覧者には使えない（backend/app/services/audit.py:277-）。
  - 決定：新しい表 public.viewer_login_events に記録する。列は id、viewer_id（viewer_accounts への FK）、event_type、client_ip、user_agent、created_at。client_ip と user_agent の名前と型、保存90日・毎日自動で消すことは、auth_events にそろえる（消す処理は maintenance.py の既存の型にならう）。auth_events には列を足さない（中間処理の全リクエスト記録と、閲覧者の本人の記録とを混ぜないため）。
  - event_type は4つ：login_requested（リンクを要求した）、session_created（ログインできた）、session_failed（トークンか email が合わなかった。viewer_id が分かる場合だけ）、signup（申込）。viewer_id は NOT NULL にする。閲覧者の行が無いとき（未登録の email への login、トークンが無効で誰のものか分からない session）は記録しない（審査 r6 N-7。その失敗は D1-8 の IP ごとの回数制限だけで数える）。在庫の表示（60秒ごとの取得）は記録しない（行が増えすぎるため。12時間のログインごとに1行で、共有は判断できる）。
  - IP の取り方は、本設計の回数制限と同じ1つの関数を使う（X-Real-IP）。【事実】既存の _get_client_ip は X-Forwarded-For の先頭を使っている（backend/app/auth/dependencies.py:67-72）。閲覧者ではこれを使わない。理由は D1 の回数制限と同じ（なりすまされない値を使うため）。
  - PO の画面：閲覧者ごとのログイン履歴（日時・IP・端末）を出す。目印を2つ出す。①同じ閲覧者が24時間のうちに3つ以上の別 IP からログインした。②別の閲覧者どうしで同じ IP からログインか申込がある。目印は判断の材料で、自動の停止はしない。

- Q7.【決定 2026-10-15 PO「y」】今のプライバシーポリシーと同じルールにする（lp/src/pages/privacy.astro:209「During account active period」・:219「契約終了後90日以内に削除」）。trial の期限が切れて延長が無いまま90日たった人、または本契約（active）が終わって90日たった人の閲覧者の行と関連の記録を消す。privacy.astro:206-214 の保存期間の表に閲覧者の1行を足す（段4）。消す仕組み（定期実行か専用スクリプトか）と、viewer_status_changes など関連の表の扱いは、段4のカードの前に設計して審査する。以下は質問の原文。LP のプライバシーポリシーに追記するか。**段4の公開と22人の登録の前提。決まるまで段4の公開をしない。**
- B-7.【決定 2026-10-15 PO「y」】履歴を書き直す。名字を含む作業記録を除いて1つのコミットにまとめ直した PR #4338 に置き換え、#4283 は閉じて古いブランチを消した。以下は質問の原文。（審査 r6）：コミット bf255ae8b・af1d155f7 の追加行に、個人の姓が残っている（push 済み）。merge commit でマージすると main の履歴に残る。履歴を書き直して push し直すか、このまま入れるかは PO 決定待ち。**決まるまで PR #4283 を main にマージしない。** 段1以降の実装カードは、B-7 が決まって #4283（design.md・ADR-1019）が main に入った後に出す（作業ブランチは origin/main から作るため。審査 r8-N-9）。
- SMTP（計画票 0 の①）：ログインそのものがメールのリンクなので、本番でメールを送れることが段2の本番での利用と段4の公開の前提。**確認できるまで段4の公開をしない。** 使えないときは方式を PO に相談する。
- Q12. Claude の経路（無制限鍵）での閲覧者の操作の GO を、Opus に委任するか。委任するなら、ADR-1003 の改訂か新しい ADR と CLAUDE.md:30 の改訂が要る（別の PR）。委任しないなら、操作は毎回 PO 本人の GO か、PO の画面から PO が行う。
- ~~Q11~~ → **決定済み：y**（PO「Y」、2026-10-15。保留中は前回の表のまま止める。KGI2 に「保留の間を除く」を足す）。元の問い：（審査 r6 B-1）再解析・抽出の途中（保留）の間、閲覧ページの表をどうするか。
  - 案 y：GAS と同じく前回の表のまま止める（D3 の今の案）。未確定の行を出さない（安全装置 #8 の目的）。そのかわり、保留が続くと「最終更新」が1分より古くなる。KGI2 に「保留の間を除く」を足し、受入条件に「保留でないときは updated_at が60秒以内（本番で curl）」を足す。
  - 案 n：アプリの在庫表と同じく、保留中も新しい行を出す（r5 の形）。最終更新は常に1分以内になるが、再解析の途中の行（単位が未確定のもの）が見える。GAS とは見え方がずれる。
  - 推奨は y（今の GAS の利用者の見え方を変えないため）。
- Q8.【決定 2026-10-15 PO「Y」】置き場所は app.salesanchor.jp/viewer/ にする。
- Q9.【決定 2026-10-15 PO「Y」】PO から一覧（22件、メールの重複0件・形式不正0件）を受け取った。個人情報なので、リポジトリと PR には載せず、リポジトリ外の ~/CC報告ファイル-keep/viewer-initial-accounts/initial_active_list.tsv（権限600、項目は申込日時・LINE 名・メールの3つだけ）に置く。登録は段4の公開前に、Q3 の Claude の経路（無制限鍵＋専用スクリプト。migration ではデータを入れない）で行う。登録の前に一覧を PO に見せる。 【訂正 2026-10-15 PO】原文「〇〇さんだけは本契約」（個人名のため伏せた）。active で登録するのは一覧のうち1人（2026/09/28 申込の行）だけ。残り21人（PO「Y」2026-10-15）：状態を trial にし、trial_expires_at を一覧の申込日時（JST）＋14日にして登録する。これで公開の時点では全員が期限切れになり、在庫表は見られない。PO が延長を決めた人から、延長の機能で「記録した時刻＋N日」まで見られるようになる。申込のやり直しは要らない。
  - 22人とも email_verified_at は NULL のままにする（新しい経路でメール確認をしていないため）。ログイン用リンクを送るかどうかは状態と期限だけで決め、email_verified_at は見ない（D1 の送る相手の条件と同じ）。
  - 登録用の専用スクリプトは、一覧ファイルを読んで1行ずつ登録する。登録済みの email は飛ばして、件数（登録・飛ばした・失敗）を出す。実行の前に、対象一覧を PO に見せる。
- ~~Q10~~ →【r9 で解決】4つのうち3つ（複数選択・倍率合わせ・縦カード）は PO の回答 4・8・9 で採用し、便1・便3 で金型に登録済み（MultiSelect、DataTable の fitToWidth・mobileCards）。24時間以内はアプリと同じ Button（aria-pressed）にする（InventoryPage.tsx:443-454）。新しい金型は要らない。以下は元の問い：GAS の画面のうち、金型が無い4つ（24時間以内のスイッチ、コンディション・提供者の複数選択、PC で表を枠に収める倍率合わせ、スマホで行を縦のカードにする表示）をどうするか。推奨は「スイッチと複数選択は金型（Checkbox・MultiSelect）を新しく登録して再現する。倍率合わせは作らず、DataTable の横スクロールで代える。スマホの縦カードは DataTable の金型に表示の型として足す」。金型の登録には PO の許可が要る（docs/CC_UI_GOVERNANCE.md:11-13）。PO の 10/14 の発言「原則同じ変更を入れる、ただしスプレッドシートとGASの処理を考えて全部は実装しなくても良い」に照らして、再現しない機能は PO に確認する。

## 別件（本設計の外）

- 社内ユーザーの権限の穴（会話ログの読み取り、招待トークンの発行など。security-recon.md §2）。別の設計で扱い、PO に相談する。
