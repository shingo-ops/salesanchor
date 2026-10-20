---
mode: handoff
---
<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# Phase 3 設計 — 在庫の閲覧専用ページ（GAS 在庫一覧の置き換え）

> この文書は何か：GAS の在庫一覧の代わりに、お客さんが自社サーバーで在庫表だけを見られるページの作り方を決めた設計書。

- 親（設計仕様書）: [docs/specs/inventory-management/inventory-viewer/README.md](../../specs/inventory-management/inventory-viewer/README.md)

**対象ADR**: ADR-1019（Accepted 2026-10-16。`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md`）  
**recon**: docs/handoff/gas-viewer-fresh-fast/recon.md ／ docs/handoff/gas-viewer-fresh-fast/security-recon.md  
**審査**: r1 REVISE（Blocking 2、Non-blocking 11。/tmp/CC報告ファイル/viewer_design_review.txt）→ r2 REVISE（Blocking 1、Non-blocking 9。/tmp/CC報告ファイル/viewer_design_review_r2.txt）→ r3 REVISE（Blocking 1、Non-blocking 7。/tmp/CC報告ファイル/viewer_design_review_r3.txt）→ r4 で全件に対応し、PO 決定 Q2a（メールのリンクでログイン）を反映 → r4 REVISE（Blocking 1、Non-blocking 6。/tmp/CC報告ファイル/viewer_design_review_r4.txt）→ r5 で全件に対応 → r5 APPROVE（Blocking 0、Non-blocking 6。/tmp/CC報告ファイル/viewer_design_review_r5.txt）→ 本版で N-34〜N-39 を反映した（KPI の重複の指摘は、実物に重複が無いため対応なし）→ r5 の後に、PO 決定（Q2b〜Q9、期限の延長、ログイン記録）、外部事例、ルール点検（/tmp/CC報告ファイル/viewer_rules_check.md）への対応を足した → r6 REVISE（Blocking 7、Non-blocking 14。審査は Opus。/tmp/CC報告ファイル/viewer_design_review_r6.txt）→ 本版で B-2〜B-6 と N-1〜N-14 に対応した。B-1 は Q11、B-7 は履歴の名前の扱いとして PO 決定待ち → r7 REVISE（Blocking 1、Non-blocking 9。審査は Opus。/tmp/CC報告ファイル/viewer_design_review_r7.txt）→ 本版で B-1・N-1〜N-9 に対応し、PR #4293 で委任を PR の GO に絞ったことに合わせて操作の GO を PO 本人に直した（Q12 を追加）→ r8 APPROVE（Blocking 0、Non-blocking 9。審査は Opus。/tmp/CC報告ファイル/viewer_design_review_r8.txt）→ r8-N-1〜N-9 に対応した → r9 REVISE（Q14 で D4 をアプリと同じ部品に書き直した版。Blocking 3、Non-blocking 10。要点は review-fable.md の r9）→ 本版で B-r9-1〜3・N-r9-1〜10 に対応した → r10 REVISE（Blocking 1、Non-blocking 8。審査は Opus。/tmp/CC報告ファイル/viewer_r9/review_r10.txt）→ 本版で B-r10-1・N-r10-1〜8 に対応した → r11 REVISE（Blocking 1、Non-blocking 7。審査は Opus。/tmp/CC報告ファイル/viewer_r9/review_r11.txt）→ 本版で B-r11-1・N-r11-1〜7 に対応した → r12 APPROVE（Blocking 0、Non-blocking 3。審査は Opus。/tmp/CC報告ファイル/viewer_r9/review_r12.txt）→ N-r12-1〜3 を反映した → r13（PO 決定 2026-10-16 で D1 を email＋パスワードに、D5 を申込コードに書き直し、D6 を追加）→ r13 REVISE（Blocking 2、Non-blocking 9。審査は Opus。/tmp/CC報告ファイル/viewer_r13_review/）→ r14 で全件に対応 → r14 APPROVE（Blocking 0、Non-blocking 7。審査は Opus。/tmp/CC報告ファイル/viewer_r14_review/review_r14.txt）→ N-r14-1〜7 を反映した。→ r15（2026-10-17 PO 決定 Q16：申込の招待リンクをボットが作る。Q12=n）→ r15 APPROVE（Blocking 0、Non-blocking 2。審査は Opus。docs/handoff/gas-viewer-fresh-fast/review-opus.md の r15）。PO の承認（ADR-1019 は Proposed のまま）と §PO 決定待ち が残る  
**日付**: 2026-10-15  
**担当**: Planner（Claude Opus）  
**状態**: PO 承認済み（2026-10-16 チャット「y」：設計を承認し実装に進む）。PO 決定待ちの項目は残っている。段ごとの着手の可否は §PO 決定待ち の各項に従う（審査 r8-N-6）。

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

### D1. 閲覧専用アカウントと、アプリと交わらないトークン（審査 B-1 への対応。r13 でログインの方法を書き直した）
- 変更前：外部の人を入れるには、アプリのユーザー（public.users）にするしかない。
- r13 の書き直しの理由（PO 決定 2026-10-16）：本番の SMTP が未設定だったため、ログインを「メールのリンク」から「専用 URL＋1人1つのパスワード」に変え、申込とお客さんの結び付けは Discord の受付で申込コードを照合する形（案D）にした。パスワードを忘れたときだけメールで再発行する（PO 原文「チケットは個別チャンネルにしたいので作り直しが原則しない、パスワードを忘れた場合はメールで再発行する機能にする」）。r12 までのメールのリンクでのログイン・確認メール（verify-email）は作らない。
- 変更後：
  - 新しい表 public.viewer_accounts を作る。migration では表を作るだけで、データは入れない。
  - 列：
    - id、email（一意）、line_name（LINE の表示名）、inventory_issue（在庫関連の課題。自由記述。TEXT。1000文字まで。任意＝空欄は NULL（Q2g））。
    - 状態（pending ／ verified ／ trial ／ active ／ suspended の5値）。pending は「申込済み・申込コードの照合前」。verified は今回使わない（将来、承認を挟む形に変えるときに migration を作り直さずに済むよう、5値で作る）。コードの照合が済んだら pending から trial へ直接進む（D5）。
    - password_argon2_hash（TEXT。NULL 可。pending の間と、Q9 の登録直後は NULL。列名は ADR-1013:24-25 の public.users にそろえる）。
    - password_must_change（BOOLEAN NOT NULL DEFAULT false。ボットが初期パスワードを作ったときに true にし、本人が変えたら false に戻す）。【事実】public.users にこの列は無い（migrations と backend の grep で 0 件。/tmp/CC報告ファイル/viewer_d1_recon2/q5.txt）。閲覧者だけの列として持つ。
    - password_changed_at（TIMESTAMPTZ。NULL 可。名前と意味は public.users の同名の列にそろえる。migrations/20261013_160000_add_self_hosted_auth_tables.sql:7）。
    - discord_user_id（VARCHAR(50)。NULL 可。一意の索引（NULL は除く）。型は既存の leads.discord_user_id にそろえる。migrations/091_add_leads_discord_messaging_columns.sql:30）。1つの Discord アカウントには1人の閲覧者だけを結び付ける。
    - discord_channel_id（VARCHAR(32)。NULL 可。その人のチケット部屋。型は既存の tenant_discord_ticket_config のチャンネルの列にそろえる。migrations/20260602_120000_add_discord_ticket_config.sql:5-9）。
    - trial_expires_at、作成・更新の日時。
    - r12 までの email_verified_at は作らない（メールでの確認をしないため）。
  - テナントは持たない。
  - 本設計で作る表（viewer_accounts・viewer_login_tokens・viewer_login_events・viewer_status_changes・viewer_discord_config）の id は、すべて BIGSERIAL にする（既存の public の表と同じ。例：public.audit_log、migrations/20260921_110000_pipeline_tables_public.sql:405）。viewer_id など他の表を指す列は BIGINT ＋ FK（ON DELETE CASCADE。閲覧者の行を消したら、その人のトークン・記録・履歴も一緒に消える）。
  - 人の正本（ADR-1008）との境界：ADR-1008 の正本 public.users は「ログインして社内の業務をする人」（担当者・作成者など、人を指す列の参照先）。閲覧者は社外のお客さんで、アプリにはログインしない。このため users には入れず、viewer_accounts だけに持つ（1人1行。email の一意制約）。同じ人の email が users と viewer_accounts の両方に入らないようにする：申込（signup）の email が users.email にあるとき（大文字小文字は無視して比べる）は、行を作らない（応答は D5 の「登録済みの email」と同じ形）。登録用の専用スクリプト（Q9）でも同じ検査をし、users.email にある行は「飛ばした」に数える。社員はアプリ本体の在庫表を見る。逆向き（閲覧者の後で同じ email の社員を users に足す場合）は本便では扱わない（社員の追加はアプリ本体の操作で、閲覧者は少数のため、気付いたときに停止で対応する）。
  - email の正規化（審査 r6 N-6）：保存・比較・回数制限のキーのすべてで、前後の空白を除いて小文字にした値を使う。一意は `lower(email)` の一意索引で守る（保存の時点で小文字にしているが、DB でも守る）。正規化は1つの関数に書き、signup・login・password-reset/request・登録スクリプトのすべてがそれを呼ぶ。形式の検査は既存の validate_email_loose（backend/app/schemas/base.py:32-38。公開の問い合わせ contact.py:36 と同じ）を使う。順番は「前後の空白を除く→小文字にする→validate_email_loose」に固定する（base.py:36 は空白を含む値を拒否するため。審査 N-r13-3）。
  - DB の SSOT の原則（docs/specs/db-ssot/README.md）に従い、同じ事実を2つの表に持たない。Discord の利用者 ID は viewer_accounts だけに持ち、テナントの leads には入れない（PO 決定 2026-10-16「y」）。
  - 顧客管理（取引先 companies・担当者 contacts）には写さない。本契約のときに取引先とつなぐ方法は、本契約フォームの便で設計する。そのときは viewer_accounts から取引先を指す列（参照）で結び、email・LINE 名を取引先側に二重に持たない形を前提にする。
  - ログインの方法（PO 決定 2026-10-16）：配る URL は1つ `https://app.salesanchor.jp/viewer/`。ページで email とパスワードを入れてログインする。パスワードは1人1つ。
    - パスワードの保存と照合は、既存の hash_password・verify_password（backend/app/auth/passwords.py:20・:24。argon2-cffi 25.1.0）をそのまま使う。照合は既存の login と同じく asyncio.to_thread で呼ぶ（backend/app/routers/auth.py:258・:262 が実例。審査 N-r13-2 で行番号を直した）。email が無いとき・password_argon2_hash が NULL のときも、決まった捨てのハッシュに対して verify_password を1回呼んでから 401 を返す（応答の時間で登録済みかどうかが分からないようにする）。
    - パスワードの規則は、既存の check_password（backend/app/auth/password_policy.py:24。15〜64文字、:11-12。よくあるパスワードの一覧 common-passwords.txt）をそのまま使う。閲覧者用の規則を別に書かない。
    - ログインできるのは、状態が active か「期限内の trial」で、password_argon2_hash が NULL でない人だけ。email かパスワードが合わないとき、pending のときは、同じ 401（i18n の「メールアドレスまたはパスワードが違います」）。パスワードが合ったうえで suspended・期限切れの trial のときは 403 にし、理由（停止中・期限切れ）を i18n で出す（正しいパスワードを知っている本人にだけ理由が見える）。
    - 初回の変更（password_must_change が true の人）：ログインは通し、12時間トークンを返すが、応答に `must_change_password: true` を入れる。トークンの中身には入れず、get_current_viewer が毎回 DB の列を見る。true の間は inventory を 403（`password_change_required`）にし、ページはパスワード変更の画面だけを出す。
    - パスワードの変更（ログイン中の本人）：今のパスワードと新しいパスワードを受け取る。今のパスワードが合わなければ 401（IP ごとの失敗に数える）。新しいパスワードは check_password を通り、今のものと違うこと。通ったら password_argon2_hash を替え、password_must_change を false、password_changed_at を今にする。応答では、新しい12時間トークンを JSON の本文で返す（審査 B-r13-1 の決め事。変えた本人の端末はログインしたままにし、ほかの端末のトークンは上の iat の比べ方で切れる）。画面は受け取ったトークンで localStorage の `viewer_access_token` を置き換え、在庫表へ進む。【事実】アプリの側に、ログイン中の本人がパスワードを変える API は無い（auth.py の POST は :38・:150・:231・:308・:370・:412 の6つ。q5.txt）ので、前例は無い。
    - 再発行（メール）：D1 の下の「パスワードの再発行」。
  - パスワードの再発行（PO 決定 2026-10-16「パスワードを忘れた場合はメールで再発行する」）：既存のアプリのパスワードの再設定（auth.py:370 の request、:412 の confirm）と同じ作りにする。
    - request：email を受け取り、常に同じ 200 を返す。送るのは、viewer_accounts にあり、状態が trial（期限内・期限切れのどちらも）か active の人だけ（期限切れの trial の人も、延長された後にログインできるように）。pending・suspended・未登録には送らない。同じ email は1時間に3回まで（既存の cache.py:324 と同じ数。4回目からは送らずに同じ 200）。
    - トークンは secrets.token_urlsafe(32) で作り、DB には sha256 だけを viewer_login_tokens（purpose password_reset）に保存する。期限は30分（既存の auth.py:342 と同じ）。同じ人の未使用の再発行トークンは、新しく作るときに消す（有効なリンクは常に1本）。
    - メールの文面と送信：backend/app/services/auth_mail.py に閲覧者用の関数 send_viewer_password_reset_email を足す（既存の send_password_reset_email、auth_mail.py:49 は文面がアプリ用で固定のため、同じファイルに並べる）。送信の設定は既存の smtp_settings（mail_config.py:28）をそのまま使う。リンクは `https://app.salesanchor.jp/viewer/#reset=<トークン>`。`#` より後ろはサーバーに送られないので、nginx のアクセスログにトークンが残らない。ページの JS は読んだらすぐに history.replaceState で消し、POST でトークンを渡す。GET ではトークンを一切消費しない（メールの安全検査が先にリンクを開いてもトークンは使われない。審査 B-5）。
    - confirm：トークンと新しいパスワードを受け取る。トークンは token_sha256・purpose = password_reset・expires_at > now の3つの条件で引く（purpose を省くと、申込コードで再発行できてしまうため）。新しいパスワードは check_password を通す。通ったら password_argon2_hash を替え、password_must_change を false、password_changed_at を今にし、トークンを消す。無効なトークンは IP ごとの失敗に数える。
    - 【事実】SMTP は 2026-10-16 に PO が5項目を GitHub の秘密設定に登録し、本番からのテスト送信は SENT。受信箱での到着の目視は PO に残っている（§PO 決定待ち の SMTP）。
  - 新しい表 public.viewer_login_tokens（id、viewer_account_id、token_sha256、purpose［signup_code ／ password_reset］、expires_at、created_at）を作る。token_sha256 は BYTEA で、`CHECK (octet_length(token_sha256) = 32)` と UNIQUE を付ける。purpose は CHECK で2値に限る。salesanchor_app に必要な権限を GRANT する（前例 migrations/20261013_160000_add_self_hosted_auth_tables.sql:47-58・:95-101。審査 N-r13-5）。トークンとコードの消費は `DELETE … WHERE token_sha256 = $1 AND purpose = $2 AND expires_at > now() RETURNING …` の1文で行い、読んでから消す2段にしない（1文で消費する前例は backend/app/routers/auth.py:429-437。ただし前例の形は `UPDATE … SET used_at … RETURNING`。審査 N-r13-4・N-r14-2）。申込コード（D5）と再発行のトークンの両方をこの表に置く。ADR-1013 の表は public.users に紐づいているので流用しない。
  - （r13 で置き換え済み：「交換」は無くなった。以下は login と POST password で発行する12時間トークンに読む）発行した12時間トークンは JSON の本文で返し、URL には載せない。ブラウザでは localStorage に置く（既存の firebase-auth.ts と同じ置き場）。キー名は `viewer_access_token` にし、アプリ本体のキーと分ける。/viewer/ はアプリ本体と同じオリジンなので、アプリ本体で XSS が起きれば閲覧者のトークンにも届く（逆も同じ）。閲覧者のトークンで届く API は D2 の7本のうち3本（logout・inventory・password）だけなので、このリスクは受け入れる（審査 N-39）。
  - トークンは毎回のリクエストでアカウントの状態を確認するので、停止（suspended）にすれば次のリクエストから見られなくなる。
- トークンの分け方（ここで決める。Generator には判断させない）：
  1. iss は "salesanchor-viewer" にする（新しい定数。self_tokens.py の ISSUER とは別）。これで閲覧者のトークンは get_current_user の (c) に入らず、(d) の Firebase 検証で 401 になる（dependencies.py:187-198）。
  2. 署名鍵は、新しい環境変数 AUTH_VIEWER_JWT_SECRET にする。アプリの鍵とは分けるので、壁は iss と鍵の二重になる。secret を本番に追加するときは、PO の確認を取る（secrets の変更にあたるため）。
  3. sub は "viewer:<id>" の形にする。email のクレームは入れない。これで、回数制限（rate_limit.py:39-50）とセッション追跡（session_guard.py:45-55）がアプリのユーザーと同じ枠に混ざらない（審査 N-10）。
  4. 新しい dependency の get_current_viewer は、iss "salesanchor-viewer" と閲覧者用の鍵の両方を要求する。アプリのトークンは 401 にする。トークンの iat が password_changed_at より前なら 401 にする（パスワードを変えたり再発行したりしたら、ほかの端末のログインは切れる）。閲覧者のトークンを作る新しい関数は、iat を整数の秒で入れる（jose は小数の iat も通すため、明記する。審査 N-r14-4）。比べ方（審査 B-r13-1）：【事実】iat は秒単位の整数（backend/app/auth/self_tokens.py:87・:93）で、password_changed_at はマイクロ秒まで持つ。そのまま比べると、変えた直後に同じ秒で発行したトークンまで弾かれる。このため `iat < floor(password_changed_at の UNIX 秒)` のときだけ 401 にする（同じ秒に発行したトークンは通す）。この比べ方は get_current_viewer の中だけに置き、アプリの get_current_user には手を入れない。残るリスク（N-r14-4）：変更と同じ秒の中で、変更より前に出したトークンは切れない（幅は1秒未満）。
  5. Redis のキャッシュは `jwt:` の名前空間を使わない。cache_jwt_result と get_cached_jwt を閲覧者側から呼ばない。署名の検証結果をキャッシュするときは `viewer_jwt:` を使う。アカウントの状態・trial_expires_at・password_must_change・password_changed_at はキャッシュせず、毎回 DB を読む（審査 N-30）。
  6. ログアウトでは、既存のブラックリスト（is_token_blacklisted と blacklist_token）を使ってよい。拒否する側の仕組みなので安全。ただし blacklist_token の ttl の既定値は 3600 秒（cache.py:141）なので、トークンの exp までの残りの秒数を必ず渡す（審査 N-12）。
  7. 更新用トークン（refresh）は持たない。アクセス用トークンの寿命は 12 時間にし、切れたら再ログインしてもらう。
  8. 総当たり対策（審査 N-15・N-28。r13 でパスワードに合わせて直した）：①login・password（変更）・password-reset/confirm で、合わないパスワードか無効なトークンが来たら、既存の check_auth_rate_limit と record_auth_failure（cache.py:292、:309）で IP ごとに数え、10回で15分ロックにする（self_tokens.py:28-29 と同じ数）。②login は email ごとにも数え、同じ email に15分で10回失敗したら、その email は15分ロックにする（IP を替えた総当たりを止める。キーは `viewer_login_fail:<正規化した email の sha256>`。数は①と同じ）。③再発行のトークンは256ビットの乱数なので総当たりでは当たらない。IP は D5 と同じく X-Real-IP から取る（既存の _get_client_ip は X-Forwarded-For の先頭を使うので使わない。審査 N-27）。nginx の login ゾーン（10r/m）は、`location = /api/v1/viewer/login`・`location = /api/v1/viewer/password-reset/request`・`location = /api/v1/viewer/password-reset/confirm` の完全一致の3ブロックで当てる。前方一致にすると inventory まで 10r/m になるので使わない（前例は nginx/nginx.conf:112 の完全一致。審査 N-22）。
- 期限の判定：リクエストのたびに、DB の状態・trial_expires_at・password_must_change・password_changed_at を見る（主キーで1行を読むだけ）。pending、verified、suspended、期限切れの trial は 403 にする。

### D2. 閲覧用 API
- 新しい router `viewer` を作る。入口の allowlist は次の7本だけにする（審査 N-18、B-5。r13 でパスワード方式に合わせて直した）。
  - signup・login・password-reset/request・password-reset/confirm の4本（ログインの前に呼ぶもの）は、既存の _require_app_origin（auth.py:199-201）と同じ検査を通す。Origin が rp_origin と一致しなければ 403 にする。ほかのサイトからの申込やメールの連打を、安く防げる（審査 N-38）。
  - POST /api/v1/viewer/signup（D5。申込コードを返す）
  - POST /api/v1/viewer/login（本文の email と password を受け取り、12時間トークンと must_change_password を返す）
  - POST /api/v1/viewer/logout（get_current_viewer が要る。blacklist_token が False を返したら 503 にする。既存の auth と同じ扱い。cache.py:146。審査 N-24）
  - GET /api/v1/viewer/inventory（get_current_viewer が要る。password_must_change が true なら 403）
  - POST /api/v1/viewer/password（get_current_viewer が要る。今のパスワードと新しいパスワード。password_must_change が true でも呼べる。通ったら新しい12時間トークンを返す。D1）
  - POST /api/v1/viewer/password-reset/request（email を受け取り、再発行のリンクをメールで送るだけ。応答は常に 200）
  - POST /api/v1/viewer/password-reset/confirm（本文の token と新しいパスワードを受け取り、パスワードを替えるだけ。12時間トークンは返さない。替えた後はログインの画面に戻す）。1つの入口には1つの働きだけを持たせる。
- この7本は1か所の定数（VIEWER_ROUTE_ALLOWLIST）に書き、router とテストの両方がそれを参照する。集合を2か所に書かない（審査 N-23）。
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
- ページの状態は次の6つにする（審査 N-35、r6 B-6。r13 でパスワード方式に合わせて直した）。文言はすべて i18n にする。
  - ① ログイン（email とパスワード → POST login）。「パスワードを忘れた」と「申込」への切り替えを置く
  - ② パスワードの変更（初回の変更が要るとき → POST password。在庫画面の任意変更ボタンは 2026-10-20 に廃止）
  - ③ 在庫表と「最終更新 HH:MM」
  - ④ 案内（準備中、停止中、期限切れ）
  - ⑤ 申込（email・LINE 名・在庫関連の課題・隠し欄 → POST signup）と、その結果（申込コード・招待リンク・受付での手順）
  - ⑥ パスワードの再発行（email の入力 → POST password-reset/request。`#reset=` から来たときは新しいパスワードの入力 → POST password-reset/confirm の結果で、成功・期限切れ（使用済みを含む）のどちらかを出す）
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
  - アプリと意図して変えるのは2点：言語の切り替え（ja/en。GAS は日本語だけ、B67）と、最終更新の時刻の表示（B71）。「更新」ボタンは付けない（PO 決定待ちの節の「1 更新ボタン」の決定。2026-10-15 PO「y」）。
  - ログイン・申込・パスワードの画面（審査 r6 B-6。r13 で直した）：

    | 画面の部品 | 使う金型 |
    |---|---|
    | email の入力 | TextField type="email" |
    | パスワードの入力（ログイン・変更・再発行） | TextField type="password"（components/TextField.tsx:4。パスワード専用の金型は無いので、これを使う。新しい金型は作らない） |
    | LINE 名の入力 | TextField |
    | 在庫関連の課題 | Textarea |
    | 送信・切り替え | Button |
    | 隠し欄（ハニーポット） | 金型なし（下の ui-allow） |
    | 申込コードの表示・各画面の結果（成功・期限切れ・停止中など） | EmptyState と Button |
  - ハニーポットの欄（D5）は、画面に見せない入力欄なので金型を使わない。生の input に `ui-allow: 申込のボット対策の隠し欄 (#4338)` を付ける。
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

### D5. 申込フォームと申込コード（r13 で確認メールを申込コードに置き換えた）
- 公開の POST /api/v1/viewer/signup を作る。
  - 項目（Q2f・Q2g の決定。Q2b・Q2d・Q2e の Discord ID は置き換え済みなので作らない）：
    - email：必須。254文字まで。形式の検査は validate_email_loose（backend/app/schemas/base.py:32-38）。
    - line_name：必須。前後の空白を除いて1〜100文字。
    - inventory_issue：任意。1000文字まで。空欄は NULL。
    - 上の範囲を外れたら 422 を返し、画面は i18n の案内文を出して送信させない。
  - honeypot の欄に値が入っていたら、200 を返すが行は作らない（応答は下の「登録済みの email」と同じ形）。
  - 同じ email は 1時間に3回、同じ IP は 1時間に10回までにし、超えたら 429 を返す。
  - IP は nginx が付ける X-Real-IP から取る。X-Forwarded-For をそのまま信用しない（security-recon.md の指摘）。
- 申込で pending の行を作り、その人だけの申込コードを作って、画面に出す（PO 決定 2026-10-16 案D「y」）。メールは送らない。
  - 申込コードの形：Crockford base32 の文字（0-9 と A-Z から I・L・O・U を除いた32字）から secrets.choice で16文字（80ビット）。画面では4文字ずつハイフンで区切って出す（例 ABCD-EFGH-JKMN-PQRS）。照合のときは、大文字にし、ハイフンと空白を除いてから比べる。Discord の小窓に手で打てる長さにするため、token_urlsafe(32) は使わない。
  - DB には正規化したコードの sha256 だけを viewer_login_tokens（purpose signup_code）に保存する。期限は7日。一度使ったら消す。
  - 応答は `{"signup_code": "XXXX-XXXX-XXXX-XXXX", "expires_at": ISO8601, "invite_url": "https://discord.gg/<code>" または null}`。画面は、コードと、その人専用の招待リンク（下の「招待リンク」。2026-10-17 に PO の作る固定のリンクから置き換えた）と、「受付の部屋のボタンを押してコードを入れてください」の案内を出す。コードと招待リンクはこの画面でしか見られない（再表示の API は作らない）。
  - 招待リンク（PO 決定 2026-10-17。原文「リンクはbotが連動して自動発行するようにしてほしいのだが出来る？」「期限1週間、使用回数1回」→ 説明のうえ「y」）：申込のたびに、ボットに運用サーバーの招待リンクを1本作らせて、応答に入れる。
    - 呼び出し：`POST /channels/{reception_channel_id}/invites`、本文は `{"max_age": 604800, "max_uses": 1, "unique": true}`。【事実】Discord 公式（docs.discord.com/developers/resources/channel の Create Channel Invite、2026-10-17 に確認）：max_age は0〜604800秒（7日）、max_uses は0〜100、unique は似た招待を使い回さない指定、権限は CREATE_INSTANT_INVITE が要る。reception_channel_id は viewer_discord_config（D6）の1行から取る。送信は既存の共通ヘルパー discord_api_request（`backend/app/services/discord_rest.py`:34）と backend コンテナの DISCORD_BOT_TOKEN（`docker-compose.yml`:109）。
    - 待ち時間：【事実】discord_api_request は失敗すると最大5回まで待ってやり直す（`backend/app/services/discord_rest.py`:20-23 の _MAX_RETRIES=5・_BACKOFF_MAX_SEC=60）。申込の画面を何分も待たせないため、keyword 引数 `max_retries`（既定値は今の _MAX_RETRIES。既存の呼び出し元は変えない）を足し、申込では `max_retries=1`（やり直さない。1回の待ちは既存の _TIMEOUT_SEC=10秒まで）で呼ぶ。
    - 作れなかったとき（viewer_discord_config の行が無い・Discord が 403/429/5xx を返す・時間切れ）：申込は成功のまま、invite_url を null で返す。画面は i18n の文言「招待リンクを作れませんでした。時間をおいて、同じメールでもう一度申し込んでください」を出す（pending の再申込では新しいコードに差し替わる。下の「すでに登録されている email」）。ログには HTTP の状態と原因の種類だけを出し、email・コード・招待の文字列は出さない。
    - 登録済みの email で捨てのコードを返すときも、招待リンクは同じように作って返す（応答の形と中身から登録済みかどうかが分からないようにする。招待は1回・7日で無効になるので、余分に作っても害は小さい）。honeypot のときは作らず、null を返す（ボットに入口を渡さない）。
    - 招待リンクは DB に保存しない（正本は Discord。SSOT）。期限は申込コードと同じ7日。
    - 作り過ぎの歯止め：上の回数制限（同じ email は1時間に3回、同じ IP は1時間に10回）を通った申込でだけ作る。
    - 権限：ボットの「招待を作成」（CREATE_INSTANT_INVITE）は、ボット招待の権限の数字に含める（805432406 → 805432407、`backend/app/routers/discord_oauth.py`:72。`docs/adr/ADR-091-discord-bot-scope-definition.md` の必須の表）。PO 決定 2026-10-17（原文「再招待するので、今後のTCGのトレカ営業でも使いたい機能なので根本から設定を修正したい」→「y」）。初めは運用サーバーのロールにだけ付ける案だった。すでに入っているボットはサーバーのロールで権限が決まる（docs.discord.com/developers/topics/permissions）ので、運用サーバーは PO が新しい数字で再招待し、ボットのロールに「招待を作成」が付いたかを確かめる。
    - 実装の順：4b はこの表を使うので、4c の viewer_discord_config の migration の後に作る（公開は今までどおり 4b と 4c を一緒にする）。
  - すでに登録されている email で申し込まれたとき：行が pending なら、古い申込コードを消して新しいコードを作り、画面に出す（コードを控え損ねた人がやり直せるようにする。email ごとの回数制限の内側で）。trial・active・suspended・verified なら、DB に保存しない同じ形の捨てのコードを返す（応答の形から、登録済みかどうかが外から分からないようにする。審査 N-19）。画面には常に「すでにお申込み済みの方は、ログイン画面の『パスワードを忘れた』から再発行してください」を添える。users.email にある email でも同じ（D1）。
  - 残るリスク（r13）：email の持ち主かどうかは確かめない（メールの確認をやめたため）。他人の email で申し込まれると、その email は本人が後から申し込めない。本人はパスワードの再発行のメールでログインでき、PO は Discord の利用者 ID・ログイン記録（下）を見て停止できる（Q6 と同じく、自動では止めない）。
- 申込コードの照合とトライアルの開始は、Discord の受付で行う（D6）。照合が済んだら trial に変え、trial_expires_at を照合した時刻＋14日にする（Q5 決定 2026-10-16 PO「y」）。
- 申込コードを照合しないまま7日たった pending の行は、毎日のタスクで消す（申込コードの期限と同じ日数）。
- 本契約への切り替えと停止の操作は Q3 で決める。

### D6. Discord の受付（申込コードの照合と、本人だけの部屋）（r13 で追加。PO 決定 2026-10-16）
- 決まっていること（§PO 決定待ち の Discord 案に原文）：運用サーバー「Sales Anchor」（ID 末尾 1187）1つで受ける。お客さんに見せるのは「全体用」カテゴリ（全員が投稿できる部屋・障害の発生と復旧の報告の部屋・受付の部屋）と、その人のチケット部屋だけ。受付の部屋はボタンだけを置き、お客さんは読むだけ。チケット部屋は1人1部屋で作り直さない。部屋の作成と URL・パスワードの投稿は、アプリのボット（Sales Anchor#8667）が行う。トライアル申込者はテナントの leads に入れない。お客さんから見た動きは顧客用チケットと同じにし、部屋を作る部品は使い回すが、処理はトライアル専用に分ける。顧客用チケットの動きは変えない。
- 設定の正本：新しい表 public.viewer_discord_config を作る。列は id、guild_id（VARCHAR(32)、一意）、reception_channel_id（受付の部屋）、ticket_category_id（チケット部屋を作るカテゴリ）、staff_role_id（部屋を見られるスタッフのロール）、作成・更新の日時。ID の列の型は既存の tenant_discord_ticket_config にそろえる（VARCHAR(32)。migrations/20260602_120000_add_discord_ticket_config.sql:5-9）。テナントの tenant_discord_config・tenant_discord_ticket_config には入れない（1 guild = 1 テナントの一意制約があり、運用サーバーはテナントではないため。§PO 決定待ち の Discord 案の 1・2）。migration では表だけを作り、1行の登録は下の専用スクリプトで行う（migration でデータを入れない）。
- 専用スクリプト（Q3 の Claude の経路と同じ形。backend コンテナの中で実行し、SQL を手で書かない）に、2つの操作を持たせる。
  - set-config：guild_id・reception_channel_id・ticket_category_id・staff_role_id の4つを受け取り、viewer_discord_config の1行を作るか更新する。
  - post-button：受付の部屋にボタン（custom_id `viewer_trial_open`）を投稿する。既存の _ensure_ticket_button_step（backend/app/routers/discord_auto_setup.py:689・:729-735）と同じく、直近50件にボタンがあれば投稿しない。送信は既存の共通ヘルパー discord_api_request（backend/app/services/discord_rest.py。Bot 認証 :52）で、backend コンテナの DISCORD_BOT_TOKEN（docker-compose.yml:109）を使う。ボタンの文面は、新しいファイル backend/app/discord_gateway/viewer_bot_texts.py に置く（既存の bot_texts.py:26-29・:63-78 は顧客用チケットの固定の文面なので変えない）。 文面は日本語（PO 決定 2026-10-17、原文「SALES ANCHORのサーバーの在庫解析ツールのチケットは日本語にしてほしい」。顧客用の bot_texts.py の英語既定は変えない。部屋の名前 trial-<id> は片付けの判定 _ROOM_NAME_RE（viewer_trial.py:33）が使うので変えない）。 同日、受付の文面を「在庫集計ツールのお試しを開始する場合は、下のボタンを押してください。」、部屋の案内の名前を「在庫集計ツール」に（PO「y」）。同日、部屋の案内の1行目を「在庫集計ツールのお試しありがとうございます😊」「下記のURLにログイン情報を入力してご利用ください。」の2行に（PO 原文の「/n」は改行）。 同日、部屋の案内から「最初のログインのときに、パスワードを変えてください。」を削除（初回ログインで変更画面が自動で開くため。PO 原文「"最初のログインのときに、パスワードを変えてください。"は不要」）。
  - どちらも実行の前に PO へ3行で報告する（操作の GO の条件）。
- custom_id は `viewer_trial_open`（ボタン）と `viewer_trial_code`（小窓）。どちらも ticket_open で始めない（既存の押下は startswith("ticket_open") で受けるため。client.py:219）。
- gateway の分岐（backend/app/discord_gateway/client.py の on_interaction、:210-）：
  - 【事実】今の on_interaction は、component 以外を :216-217 で、ticket_open 以外を :219-220 で return し、:226 で defer してから :239 でテナントを引く。運用サーバーはテナントに無いので、今のままでは :241-249 で「未登録」の案内を返して終わる（/tmp/CC報告ファイル/viewer_d1_recon2/q8.txt）。
  - 変更：:218 で custom_id を取った直後、:219 の判定より前に、`viewer_trial_` で始まる custom_id を新しいファイル backend/app/discord_gateway/viewer_trial.py の処理へ渡して return する。modal の送信（type 5）は component ではなく :216 で落ちるので、その判定より前で `viewer_trial_code` だけを先に渡す。顧客用チケットの行（:219 以降）は変えない。
  - viewer_trial.py は、押された guild が viewer_discord_config の guild_id と一致するときだけ動く。一致しなければ何もしない（本人だけに見える「このサーバーでは使えません」を返す）。
- ボタンを押したとき（`viewer_trial_open`）：
  1. 押した人の Discord ID（interaction.user.id。既存の client.py:231 と同じ取り方）が、すでに viewer_accounts の discord_user_id にあるか見る（discord_user_id の一意の部分索引で1行引くだけなので、3秒の応答期限の内側で終わる。審査 N-r14-5）。あれば小窓を出さず、先に defer（ephemeral、thinking）してから、本人だけに見える返事（ephemeral）でその人の部屋（discord_channel_id）を案内する。部屋が消えていたら、下の手順 3〜4 の部屋の作成だけをやり直し、discord_channel_id を替える（作り直しは原則しないが、部屋が無いと連絡できないため）。
  2. 無ければ、小窓（send_modal）で申込コードを聞く。【事実】discord.py 2.4.0 の send_modal は最初の応答で呼ぶ必要があり、defer の後に呼ぶと InteractionResponded になる（/tmp/CC報告ファイル/viewer_d1_recon/）。このため、この分岐では defer しない。入力欄は1つ（TextInput、16〜19文字）。小窓の題と入力欄の文言は viewer_bot_texts.py に置く。
- 小窓が送られたとき（`viewer_trial_code`）：小窓の入力値は on_interaction で受けた interaction.data（components の中の value）から読む。discord.ui.Modal の on_submit は使わない（顧客用チケットと同じく、処理を on_interaction の1か所に集めるため）。【事実】（2026-10-17 Opus が discord.py 2.4.0 の原文で確認。/tmp/CC報告ファイル/viewer_stage4/recon_d6/pkg/）state.py:797 はどの種類の interaction でも dispatch('interaction') を呼ぶので、小窓の送信は on_interaction に届く。send_modal（interactions.py:1049-1050）は Modal を store_view するが、Modal.on_submit の既定は pass（ui/modal.py:140-150）で、on_error もログを出すだけなので、ライブラリは自分で返事をしない。このため小窓は discord.ui.Modal の子クラス（on_submit を書かない、timeout は900秒）で出し、返事は on_interaction 側だけで行う。
  1. 最初に defer（ephemeral）する（照合と部屋の作成が3秒を超えうるため）。
  2. 回数制限：同じ Discord ID の失敗は1時間に5回まで。Redis のキー `viewer_code_fail:<Discord ID>`（incr ＋ EXPIRE 3600）。gateway の Redis は docker-compose.yml:334 の REDIS_URL、取得は既存の get_redis（backend/app/cache.py:43）を使う。【事実】get_redis は init_redis で作った接続を返すだけで、init_redis を呼ぶのは backend/app/main.py:188 だけ。gateway（backend/app/discord_gateway/main.py）は呼んでいないので、今のままでは gateway の中で get_redis() が常に None になる（審査 B-r13-2）。このため gateway の起動時（client の setup_hook）に init_redis() を呼び、終了時（close）に close_redis() を呼ぶ変更を、この便に入れる。【事実】setup_hook（client.py:125-127）と close（:129-134）はすでにあるので、中の reaction_writer の処理と super().close() は残し、その前後に足す。run_gateway は再接続のたびに client を作り直して close を呼ぶ（:427・:439）ので、Redis の接続も毎回つなぎ直されるが、問題はない（審査 N-r14-3）。【事実】gateway の DATABASE_URL のロールは salesanchor_app（2026-10-17 本番のコンテナの環境変数で確認。値は伏せて保存：/tmp/CC報告ファイル/viewer_stage4/recon_d6/ssh_gw_dburl_masked.txt）。viewer_* への GRANT（migrations/20261016_150000_add_viewer_accounts.sql:107-113）が効く。【事実】gateway から backend/app の他のモジュールを import する前例がある（dm_writer.py:38-39、reaction_writer.py:13）。get_redis が None を返したとき（Redis が使えない）は照合をせず、「時間をおいてもう一度」を返す（回数を数えられないまま照合させない）。
  3. コードを正規化して sha256 を取り、トランザクションを始め、viewer_login_tokens から purpose = signup_code・expires_at > now の行を `DELETE … RETURNING` の1文で消して取る（D1 と同じ消費の形。審査 N-r14-1。この後の部屋の作成やコミットに失敗してロールバックすれば、行は戻る）。結び付く viewer_accounts の状態が pending でなければ、合わないものとして扱う。合わなければ失敗を1回数え、「コードが違うか、期限が切れています」を返す。
  4. 部屋を作る：既存の ticket_channel_creator.py から、部屋の作成の部品（:469-480 のカテゴリの取得、:510-534 の権限の組み立て、:535-564 のチャンネルの作成。権限は既存の _bot_permission_overwrites（:148-164）を使う。作成時の reason の文面は変えない。切り出す範囲のログ（:529-533・:544-563）は tenant=%d を出すので、新しい関数は引数 `log_context: str` を受け取り、既存の関数は今と同じ `tenant=%d` の文字列を、トライアルは `viewer_trial` を渡す。審査 N-r14-6）を、新しい関数 `create_private_text_channel(guild, category_id, member, staff_role_id, name)` として新しいファイル backend/app/discord_gateway/private_channel.py に切り出す。既存の関数（:457-625）はこれを呼ぶ形に替え、動きは変えない（既存のチケットのテストを変えずに通すことを受入にする）。leads を読む既存チェック（:486-508）と leads の INSERT（:570-622）は切り出さない（トライアルでは使わない）。部屋の名前は `trial-<viewer_accounts.id>`（個人の名前を部屋の名前に入れない）。
  5. 同じトランザクションで、viewer_accounts に discord_user_id と discord_channel_id を入れ、状態を trial、trial_expires_at を今＋14日にする。初期パスワードを secrets.token_urlsafe(18)（24文字。check_password の15〜64文字に入る）で作り、hash_password（asyncio.to_thread）で password_argon2_hash に入れ、password_must_change を true にする（申込コードの行は手順3で消してある）。viewer_status_changes に action start_trial・actor system の1行、viewer_login_events に code_matched の1行を入れる。コミットする。discord_user_id の一意の違反（同じ Discord アカウントが別の申込に結び付いている）なら、ロールバックして作った部屋を消し、「この Discord アカウントは別のお申込みに結び付いています」を返す。
  6. コミットの後で、その部屋に URL（https://app.salesanchor.jp/viewer/）・登録の email・初期パスワード・「最初のログインでパスワードを変えてください」を1通投稿する。本人には ephemeral で部屋を案内する。投稿に失敗したら "[viewer-trial]" のログを1行出す（本人はパスワードの再発行のメールでログインできる）。
  - 部屋の作成（4）が失敗したらロールバックし、「時間をおいてもう一度」を返す（失敗の回数には数えない）。コミット（5）が失敗したら、作った部屋を消す。
- 部屋での発言：【事実】on_message は、テナントに登録の無い guild のメッセージを :356-362 で捨てる。運用サーバーはテナントに無いので、チケット部屋の発言（初期パスワードの投稿を含む）は meta_messages に保存されず、翻訳にも回らない。本設計ではこの動きを変えない。
- 初期パスワードは部屋の履歴に残る（本人とスタッフが見られる）。最初のログインで必ず変えさせる（D1 の password_must_change）ので、変えた後は使えない。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 閲覧者のトークンで既存の全 APIRoute（VIEWER_ROUTE_ALLOWLIST の7本と、トークンを見ない公開ルートの固定一覧 _PUBLIC_NO_AUTH_ROUTES を除く）を全 method で叩くと、すべて 401 になる。一覧に無いルートが 401 以外を返したら失敗する（段1で、トークンを見ない公開ルート26本が見つかったため。2026-10-16 Opus 判断） | CI pytest test_viewer_isolation：app.routes を列挙する。パスの変数は 1 か固定の UUID で埋める。get_current_user は override しない。patch は _init_firebase と is_token_blacklisted→False と check_auth_rate_limit→False だけにし、get_cached_jwt は patch しない |
| get_current_viewer を一度通った後でも、同じトークンで既存の API を叩くと 401 になる（Redis 経由の抜け道がない） | 同上の別ケース |
| アプリのユーザーのトークンで GET /api/v1/viewer/inventory を叩くと 401 になる | CI pytest |
| 閲覧者のコードが cache_jwt_result と get_cached_jwt を呼んでいない | CI pytest（viewer のモジュールの中身を検査する） |
| pending・verified・suspended・期限切れの trial は 403、期限内の trial と active は 200 になる | CI pytest（時刻を固定する） |
| inventory の rows のキーの集合が、D2 の15キー（_GAS_COLUMNS の14個と offer_type）と完全に一致する。応答に fresh_window_hours があり、アプリの在庫 API の値と同じ | CI pytest（`set(keys) ==` 固定の集合。fresh_window_hours は定数 FRESH_WINDOW_HOURS（tcg_distribution_svc.py:212-213）と `==` で比べる。審査 r10 N-r10-4） |
| 作り置きの行から offer_type を除いた14キーが、同じ seed で run_distribution が GAS に渡す行（14列）と一致する | CI pytest（同じ seed。各行の offer_type を除いた辞書どうしを比べる。build_distribution_rows を両方が呼んでいることも確認する） |
| 対応表を services へ移した後も、既存のテスト test_offer_type_status_mapping_is_one_constant（test_inventory_distribution_rows.py:111-118）を変えずに通り、inventory_offers から同じ名前で読める | CI pytest（そのテストのファイルに差分が無いことを PR の diff で確かめる） |
| build_distribution_rows を切り出した後も、既存の配信のテストがすべて通る | CI pytest（既存のテストを変えずに実行） |
| analysis_runs か extraction_jobs に未完了があるとき、作り置きは前回の値と updated_at を変えず、fail_count も増えない。max_age_hours が無いときは前回の値を残し、fail_count が1増える | CI pytest |
| 申込コードの照合が成功すると、状態が trial、trial_expires_at が「照合した時刻＋14日」、discord_user_id と discord_channel_id が入り、password_must_change が true、申込コードの行が消え、viewer_status_changes（start_trial・system）と viewer_login_events（code_matched）に1行ずつ入る。leads には1行も入らない | CI pytest（viewer_trial.py の照合の関数を、Discord の部分を mock にして直接呼ぶ。時刻を固定する） |
| 切り替え（trial→active）・停止・解除・延長の API は、super admin 以外のトークンでは 403 になる | CI pytest（require_super_admin） |
| 切り替え・停止・解除・延長のたびに viewer_status_changes に1行入り、action・from/to・actor が正しい。解除は最後の suspend の from_status に戻る。suspend の行が無い解除は 409 | CI pytest |
| Claude 用の専用スクリプトは、PO の画面と同じサービス関数を呼び、actor が claude で記録される | CI pytest（スクリプトの関数を直接呼ぶ） |
| 登録用の専用スクリプトは、登録・飛ばした・失敗の件数を出し、登録済みの email を飛ばす。2回続けて実行しても行が増えない | CI pytest（架空の3行のファイルで。本物の一覧は使わない） |
| PO の画面の目印①（同じ閲覧者が24時間で3つ以上の別 IP）と目印②（別の閲覧者どうしで同じ IP）が、条件どおりの行にだけ付く。ログイン履歴に日時・IP・端末が出る | CI pytest（API の応答）と Evaluator（Playwright で画面） |
| signup・login・password-reset/request・password-reset/confirm の4本とも、Origin が違えば 403 になる | CI pytest（4本それぞれ） |
| CI の `npx vite build --manifest`（frontend-check.yml の check ジョブに足す手順）の後に dist/index.html と dist/viewer/index.html の両方ができ、manifest の viewer 入口からたどった JS に本体の辞書の目印の文字列が含まれない。viewer の中でわざと本体の i18n.ts を import すると検査が失敗する | CI（frontend-check.yml の check ジョブで check-viewer-bundle.js。失敗の確認は段3で1回、生の出力を残す）。本番と同じ設定のビルドで manifest が出ないことも段3で1回確かめる：段3のブランチで `npm run build`（vite.config.ts は本番と同じ。--manifest を付けない）を実行し、`test ! -e dist/.vite/manifest.json` の結果を生の出力で残す（審査 r8-N-2。本番 URL への curl は nginx.conf:23-25 の try_files で無くても 200 が返るので判定に使わない） |
| viewer の入口 main.tsx から import をたどった集合（import type は除き、動的な import() は含む）の t() のキー（例：金型の common.close）が viewer の辞書に無ければ検査が失敗する。viewer の ja と en のキーの集合が違えば失敗する | CI（check-i18n-missing-keys.js。わざと欠けたキーで失敗することを1回確かめる） |
| beat に refresh-viewer-inventory があり、周期が 60.0 秒である | CI pytest |
| build_distribution_rows が例外を投げたとき、また Redis への書き込み（SET）が例外を投げたとき、どちらも作り置きは前回の値を残し、fail_count が1増える | CI pytest（mock） |
| 保留でないときは、本番の閲覧 API が返す updated_at が今の時刻から60秒以内（Q11=y） | Evaluator（本番で curl。analysis_runs・extraction_jobs に未完了が無いことを同じ時刻に DB 読み取りで確かめ、生の出力を残す） |
| タスクが失敗した後、Redis の値と updated_at が変わらない。3回続けて失敗したら通知が1回だけ呼ばれ、4回目では呼ばれない。成功すると fail_count が 0 に戻る | CI pytest（mock。fail_count は Redis で数える） |
| pending の email で signup し直すと新しい申込コードが返り、古いコードは照合で合わない | CI pytest |
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
| login でパスワードを10回間違えた IP は、11回目が 429 になる。同じ email に別々の IP から15分で10回失敗すると、その email の11回目は 429 になる。同じ email への password-reset/request は4回目からメールを送らない | CI pytest |
| email が未登録・パスワードが違う・pending のときの login は、どれも同じ 401 と同じ本文になる。パスワードが合った suspended・期限切れの trial は 403 で理由が分かる | CI pytest |
| password_must_change が true の人は、login は通るが応答に must_change_password: true があり、inventory は 403（password_change_required）。POST password で変えた後は inventory が 200 | CI pytest |
| POST password：今のパスワードが違えば 401。新しいパスワードが check_password（15〜64文字・よくあるパスワード）を通らなければ 422。今のものと同じなら 422 | CI pytest |
| パスワードを変えるか再発行した後、その前に発行した12時間トークンでは inventory が 401 になる（iat が password_changed_at より前） | CI pytest（時刻を固定する） |
| iat の比べ方：password_changed_at が 10:00:00.700 のとき、iat が 10:00:00 のトークンは通り、iat が 09:59:59 のトークンは 401 になる。POST password の応答で返った新しいトークンで、すぐ inventory を叩くと 200 になる | CI pytest（時刻を固定する。審査 B-r13-1） |
| 再発行：リンク先を GET で2回開いた後でも、POST の confirm でトークンが使える（GET ではトークンを消費しない） | CI pytest |
| 再発行のトークンは30分で無効になり、一度使ったら2回目は使えない。新しい再発行のトークンを作ると、前の未使用のトークンは使えなくなる。申込コード（signup_code）では confirm できない | CI pytest（時刻を固定する） |
| 再発行のメールは、trial（期限内・期限切れ）と active の email にだけ送られる。未登録・pending・suspended の email にはメールが送られず、応答は同じ 200 | CI pytest（メール送信を mock にする） |
| 登録済み（trial・active・suspended）の email や users.email の email で signup しても、応答の形は新規のときと同じで、返るコードは DB に無い（照合で合わない） | CI pytest |
| 申込コードは7日で無効になり、一度使ったら2回目は合わない。ハイフン・空白・小文字を混ぜても同じコードとして合う | CI pytest（時刻を固定する） |
| 同じ Discord ID でコードを5回間違えると、6回目は照合せずに断る。Redis が使えないときは照合しない | CI pytest（mock） |
| gateway の起動：Redis を mock にせず（CI の Redis サービスにつなぐ）、gateway の client の setup_hook を実行した後で get_redis() が None でない。close の後は None に戻る。setup_hook の中の reaction_writer.initialize（DB を使う）だけは patch する | CI pytest（審査 B-r13-2・N-r14-3） |
| 顧客用チケットの既存テスト（ticket_channel_creator のテスト）が、テストを変えずに通る | CI pytest |
| スマホの Discord アプリで受付のボタンを押すと小窓が出て、申込コードを送れる。送った後、本人だけの部屋に URL と初期パスワードが出る | Evaluator（PO の端末か実機で1回。審査 N-r13-9） |
| すでに結び付いた Discord ID でボタンを押すと、小窓を出さずにその人の部屋を案内する。別の申込に結び付いた Discord ID でコードを入れると、結び付けずに断り、作った部屋を消す | CI pytest（mock） |
| custom_id が ticket_open のボタンの動き（部屋の作成と leads の INSERT）は変わらない。部屋の作成の部品を切り出した後も、既存のチケットのテストを変えずにすべて通る | CI pytest（既存のテストを変えずに実行） |
| viewer_discord_config の guild_id と違うサーバーで viewer_trial_open を押しても、部屋も行も作られない | CI pytest（mock） |
| 申込：メールか LINE 名が空なら 422。Discord ID の欄は無く、送られてきても保存しない | CI pytest |
| 申込：在庫関連の課題が1000文字を超えたら 422。保存した文字列は画面にそのまま文字として出し、HTML として解釈しない | CI pytest |
| 申込の招待：Discord への呼び出しを mock にすると、送り先が viewer_discord_config の reception_channel_id のチャンネルで、本文が max_age 604800・max_uses 1・unique true。応答の invite_url が `https://discord.gg/<code>` | CI pytest（mock） |
| 申込の招待：Discord が 403・429・500・時間切れのとき、または viewer_discord_config の行が無いとき、応答は 200 で invite_url が null、返った申込コードは照合で合う。呼び出しは1回だけ（やり直さない） | CI pytest（mock） |
| 申込の招待：honeypot のときは呼び出し0回で invite_url が null。登録済みの email のときは呼び出し1回で invite_url が入る | CI pytest（mock） |
| discord_api_request を max_retries なしで呼ぶ既存の呼び出しは、今までどおり5回までやり直す（既存のテストを変えずに通る） | CI pytest |
| 本番：申込の画面に出た招待リンクで運用サーバーに入れる。同じリンクを2回目に開くと無効になる。サーバー設定の招待の一覧で、そのリンクの期限が7日・使用回数の上限が1 | Evaluator（PO の端末で1回） |
| 延長：期限切れの trial に N=7 を指定すると、trial_expires_at が「記録した時刻＋7日」になり、inventory が 200 になる。N が0以下か整数でなければ 422。active・suspended・pending・verified には延長できない（409） | CI pytest（時刻を固定する） |
| ログイン記録：login の成功・失敗（閲覧者の行がある email だけ）、パスワードの変更、再発行の要求と完了、申込、コードの照合のたびに viewer_login_events に1行入り、client_ip が X-Real-IP の値になる（コードの照合は Discord 経由で IP が無いので NULL）。閲覧者の行が無い email の login では行が入らない。91日前の行は毎日の処理で消える | CI pytest |
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
  - 理由1：閲覧者が届く入口が、74 本から7本（うちログインの後に使うのは logout・inventory・password の3本）に減る。
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
| 4 | 申込と申込コード、パスワードの変更と再発行、pending の掃除、管理の操作（D5・D1 のパスワード）。Discord の受付（D6：設定の表と専用スクリプト、部屋の作成の部品の切り出し、gateway の分岐）は段4の中で別の PR に分ける（gateway の変更と、既存のチケットの部品の切り出しを、ほかと混ぜないため） | Sonnet |
| 各段 | コード審査（Opus。PO 決定 2026-10-15 で Fable から変更）、セキュリティ審査、マージ。secret の追加は PO の確認を取る | Opus |
| 計測用 | 本番の表示時間（受入条件の最後から2行目）を測るための閲覧者アカウントは、段4の後に登録用の専用スクリプトで1件だけ作る（email は社内で受け取れるアドレス。一覧ファイルは1行だけのものを別に作る。登録した時点の期限にかかわらず、登録の直後に extend N=1 で「記録した時刻＋1日」にする。審査 r7-N-7・r8-N-5）。作成は PO 本人の GO（上の「操作の GO の条件」）。計測が終わったら Q3 の Claude の経路で suspended にし、viewer_status_changes に残す。行は消さない（履歴を残すため）。作る前と止めた後に PO へ3行で報告する（審査 r6 N-12） | PO（GO）＋Sonnet（実行） |

Discord 案（r13 で決定済み。D1・D2・D5・D6 に反映。2026-10-16 PO 提案「トライアルの申込みが来る、フォームを送る、Discordに案内をする、専用サーバーでチケットを発行してもらう、チケット発行をトリガーに専用URLとパスワードを送る」。SMTP が未設定のため。調査の生出力は /tmp/CC報告ファイル/viewer_discord/）
- 【事実】本番で discord-gateway が動いている（astro-webapp-discord-gateway-1 Up、DISCORD_BOT_TOKEN は SET）。チケットはボタン（custom_id が ticket_open で始まる）を押したときだけ作られる（backend/app/discord_gateway/client.py:210-221）。作ると本人・staff ロール・ボットだけが見える部屋ができ、テナントの leads に書く（ticket_channel_creator.py）。
- 【事実】チケットができたことをほかの処理に知らせる仕組みは無い。ボットから個別メッセージ（DM）を送るコードも無い（git grep で create_dm・dm_channel の送信側 0 件。dm_writer.py は受信の記録だけ）。作るなら、チケット部屋の作成直後に閲覧者の登録とURL・パスワードの投稿を足す新規実装になる。
- （r13 で置き換え済み：テナントに入れず運用サーバー1つで受ける。D6）【未確認】トライアル申込者を受けるテナント（本番の設定は tenant 1・4・6 の3つ）。申込とチケットを同じ人だと結び付ける方法。
- 【r13 で解決】D1 は「専用 URL＋パスワード＋メールでの再発行＋申込コード」に書き直した（D1・D2・D5・D6）。
- 申込とチケットの結び付け（2026-10-16 PO 質問「フォームを入力してもらったら専用のURLを発行してそのURLから入ってきたユーザーを紐付けられる？」への調査。未決）：
  - 【事実・Discord 公式 docs.discord.com/developers/topics/oauth2】OAuth2 の identify スコープで「/users/@me」（Discord の利用者 ID）が取れる。コードの引き換えには client_secret が要る。guilds.join スコープで、ボットがその人をサーバーに入れられる（docs.discord.com/developers/resources/guild「Add Guild Member」。ボットに CREATE_INSTANT_INVITE 権限が要る）。
  - 【事実】今のボットの権限 805432406（backend/app/routers/discord_oauth.py:72）は CREATE_INSTANT_INVITE も MANAGE_GUILD も持たない（ビット計算）。既存の OAuth はボットをサーバーに招待する流れだけで（同ファイル:1-19）、利用者 ID を取る流れは無い。DISCORD_CLIENT_SECRET を読むコードも無い（git grep 0 件）。 （2026-10-17 以降の数字は 805432407＝CREATE_INSTANT_INVITE を含む。上の D5 の権限）
  - 案A（推奨）：フォームの送信後に、その人専用の URL（使い切り）を出す。押すと Discord の「本人確認の許可」画面になり、許可すると Discord の利用者 ID が申込に結び付く。チケットを作った人の ID と同じなら、自動で URL とパスワードを部屋に出す。要るもの：Discord 開発者画面での client_secret の発行と戻り先 URL の登録（PO の GUI 作業）。
  - 案B：その人専用の Discord 招待リンクを作り、どのリンクで入ったかを見分ける。ボットに MANAGE_GUILD が要り、ADR-091:86 で除外している権限なので ADR の変更が要る。招待の使用回数の差で見分ける方式で、確実さは案A より低い。
  - 【PO 決定 2026-10-16「y」】案D（申込コード方式）を採る。
  - 案D（2026-10-16 Fable 相談の推奨。PO「FABLEに相談」）：フォームの送信後に、その人だけの申込コードを出す（DB には sha256 だけ、使い切り、7日）。チケットのボタンを押したとき、ボットが小窓（send_modal）でコードを聞き、合えばボタンを押した人の Discord ID（client.py:231 member = interaction.user）を閲覧者に結び付けて、部屋に URL と初期パスワードを出す。Discord 開発者画面の作業・client_secret・ボット権限の追加・入口の追加が要らない。変更点：client.py:226 の defer() を send_modal に置き換える（r13 で置き換え済み：:226 は変えず、:218 の後で viewer_trial_ に分岐する。D6）。【未確認】（r13 で置き換え済み。残るのは D6 の【未確認】だけ）専用サーバーのテナント、チケット作成でそのテナントの leads に行ができること（ticket_channel_creator.py:575）を受け入れるか、discord-gateway が public.viewer_accounts に書けるか、スマホで小窓が出るか。安全策の案：試行は Discord ID ごとに1時間5回まで、discord_user_id は一意、初期パスワードは初回ログインで変更させる（部屋は staff にも見える）。
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
  - 【PO 決定 2026-10-16】原文「saas管理者y」。管理画面は SaaS 管理者（super admin）専用でこの内容でよい。置き場所【事実 origin/main】：SaaS 管理者メニューは frontend/src/components/DesktopShell.tsx:192-196 の saasAdminItems（今は LINE解析・買取相場・為替レートの3つ、isSuperAdmin のときだけ出る）。画面のルートは frontend/src/App.tsx:293-301 の /super-admin/* の並び（例 /super-admin/fx-rate → FxRatePage）。新しい画面は /super-admin/viewers に ViewerAccountsPage を置き、saasAdminItems の最後に「閲覧者管理」（labelKey nav.superAdminViewers、ja/en 両方）を足す。【事実 r13】スマホの殻は別の定義で、frontend/src/components/MobileShell.tsx:165-186 に isSuperAdmin のときの3項目（analysisRules・buybackPrices・supplierExtractionRules）がある。DesktopShell の3つとは同じではない（為替レートはスマホに無い。/tmp/CC報告ファイル/viewer_d1_recon2/q2.txt）。MobileShell の同じ並びの最後にも「閲覧者管理」（同じ labelKey と /super-admin/viewers）を足す。

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
- 外部事例の r13 の注記：下の Yelp・DigitalService・Supabase ほかの事例は、r12 までの「メールのリンクでのログイン」の根拠として集めたもの。r13 でログインはパスワードになったので、今も当てはまるのは「再発行のリンクを GET で消費しない・1回限り・期限付き・最新の1本だけ有効」の部分だけ（D1 の再発行）。パスワードの保存・規則・総当たり対策は、既存のアプリのログイン（ADR-1013 の hash_password・check_password・check_auth_rate_limit）と同じ部品と数をそのまま使うので、新しい外部事例は足さない（社内の既存の実装と同じ水準を、閲覧者にも当てるだけのため）。Discord のボタン→小窓→部屋の流れも、既存の顧客用チケット（ticket_channel_creator.py）と同じ部品を使う。
- 外部事例（調査 2026-10-15。全文と出典は PR に載せず、要点だけを下に書く。数値は出典に書かれたものだけ）：
  - 成功・Yelp（2021-03、Yelp Engineering Blog）：事業者向けの再ログインを、メールのリンクに置き換えた。導入前は、パスワードの再設定で失敗したことを知らせるメールを1日に約7,500回送っていた。リンクは1回だけ使え、期限が付いている。無効なリンクのときは通常のログイン画面に戻す。応用：D1 のトークンも1回限りで期限付きにし、無効なときは「ログインの申込」の画面に戻す。
  - 成功・ドイツ連邦 DigitalService（2022-08、公式ブログ）：固定資産税の申告サービスで、メールのリンクによる登録・ログインを始め、4週間で15万人を超えた。手順はパスワードの再設定の6段から4段に減った。学び（審査 r6 N-11 で訂正）：利用者は「リンクは1回限り」「最新のリンクだけが有効」を想定しておらず、説明が要った。応用：リンクが1回限りであること、新しく頼むと前のリンクが使えなくなることを、メールの本文と画面④の i18n の文言で出す（r13 で置き換え済み：メールのリンクで使うのはパスワードの再発行だけになった。画面の番号は D4 の6状態の表に読み替える）。ブラウザに縛らず email の再入力で本人を確かめる（Q2c）。
  - 失敗・Supabase の議論（2025-12）、Microsoft Defender の議論（2023-07）、Ghost のフォーラム（2020〜2023）：企業のメールの安全検査が、届いた時点でリンクを先に開いた。GET でトークンを使ったり状態を変えたりする作りだったため、リンクが無効になったり、承認が勝手に実行されたりした。件数は書かれていない。応用：D1 は、トークンを `#` の後ろに置き、ページで POST するまで使わない。受入条件の「GET で2回開いた後でも使える」がこの対策の確認になる。
  - 失敗・Auth0 の公式記事（2025-10 更新）：リンクを、申し込んだのとは別のブラウザで開くと失敗する作りのため、利用者に「リンクをコピーして元のブラウザに貼る」よう案内している。応用：email の再入力方式は、この縛りを持たない。
  - トライアル期間・Management Science の論文（2023、新規利用者 337,724人に無作為に割り当て）：購読した割合は、7日が15.35%、14日が14.97%、30日が14.67%で、差は1ポイント未満。Tunguz の約600社の調査（SaaStr）でも、7・14・21・30日のあいだに有意な差は無く、14日が最も多かった。応用：14日（Q5）は外部の実測から外れていない。ただし対象は個人向けのソフトなので、本件での転換率を予想する根拠にはしない。
  - 共有の検知・Netflix の株主向けレター（2023 Q2、SEC に提出）：世帯の外での共有を有料にした後、有料会員の純増は590万人だった（前年の同じ期はマイナス100万人）。世帯の判定には IP・端末・利用の状況を使っている（この判定方法の部分は、レターの本文を読んでおらず、検索結果の要約による【未確認】）。一方、先に始めたスペインでは、2023 Q1 に約100万人が減り、解約率が3倍になった（Kantar の推計の報道。二次情報）。誤って検知した割合を数値で公開した例は見つからなかった。応用：本設計は自動では止めず、目印を出して PO が判断する（Q6）。止めすぎによる離脱を避けられる。
  - 短い作り置き・NGINX の公式ブログ（2015-12）：WordPress で、作り置きが無いときは毎秒5.53件しか返せなかった。1秒だけ作り置きすると毎秒2,185件になった。期限が切れた瞬間にリクエストが元に集中することへの対策も要る、と書いている。Facebook の論文（NSDI 2013）では、作り直しを10秒に1回に絞ることで、DB への問い合わせのピークが毎秒17,000件から1,300件に下がった。応用：D3 は閲覧者のリクエストでは作り直さず、1分ごとのタスクが1本で作る。期限が切れたときの集中は構造上起きない。
  - 適用の限界：上の事例は、どれも本件より大きな規模か、個人向けのサービス。メールのリンクの成功率・離脱率、60秒の作り置きの効果、GAS からの移行前後の速度について、数値を出した一次の事例は見つからなかった。本件の成否は、受入条件の表と、段0〜2 の実測で判定する。

## 段2の実施の決め事（2026-10-16。Opus の判断と PO の決定）

- PO 決定（2026-10-16 チャット「y」）：段2で、本番に閲覧者専用の鍵 AUTH_VIEWER_JWT_SECRET（新しく作るランダムな文字列）を足す。経路は GitHub の秘密設定 → deploy.yml の .env 書き込み → docker-compose.yml の backend の environment。値はチャット・リポジトリ・ログに出さない。
- 段2は2つの PR に分ける。段2a：作り置き（D3）と閲覧 API の login・logout・inventory の3本（D2）と鍵の配線。段2b：作り置きが止まったことの見張り（§継続の「updated_at から10分」）。
- signup・password（変更）・password-reset/request・password-reset/confirm の4本は段4で作る（計画票の段4が申込とパスワードの変更・再発行を含むため）。
- 外側の nginx の完全一致の3ブロック（D1 の 8）は段4で入れる。閲覧者の行ができるのは段4からなので、段2では nginx の作り直しをしない。段2の間の login は、アプリの回数制限（IP ごと・email ごと）だけで守る。
- login の email ごとの回数制限は、Redis が使えないときは通す（既存の check_auth_rate_limit と同じ fail-open）。login に成功したら email ごとの数を消す。
- 作り置きの通知の文言は「[viewer-cache] 3回続けて失敗しました: 理由」。経路は既存の send_discord_notification(tenant_id=4, event_type="tcg_distribution_error")。
- 見張りの経路（段2b）：作り置きのタスクが Redis に最後に書けた時刻と最後に保留を確かめた時刻を置き、backend の /metrics が読んで Prometheus に出し、monitoring/prometheus/alert_rules.yml に規則を足す（ADR-1012 の CeleryHeartbeatStale と同じ経路）。保留中かどうかは、件数ではなく「最後に保留を確かめた時刻が2分以内か」で見分け、規則を2本（故障・保留中）に分ける。
- 段3は ①ログイン・③在庫表・④案内 の画面まで。②⑤⑥ の画面は段4で API と同じ PR に入れる（Opus 2026-10-16。理由：API が段4でできる・閲覧者の登録は段4）。

## 段4の実施の決め事（2026-10-16。Opus の判断と PO の決定）

- SMTP：【事実】PO が本番から送ったテストメールの受信箱への到着を確かめた（2026-10-16 チャット「y」）。§PO 決定待ち の SMTP の門はこれで外れた。
- 段4は4つの PR に分ける（1つの PR に1つの働き。gateway と管理の画面を混ぜない）。
  - 4a-1（パスワード）：POST password・password-reset/request・password-reset/confirm の3本（D1・D2）、画面の ②（変更）と ⑥（再発行）、外側の nginx の完全一致の3ブロック（D1 の 8）、毎日の掃除（下の Q7 の仕組みと、pending の7日・viewer_login_events の90日）、privacy.astro の保存期間の表の1行。
  - 4a-2（管理）：Q3 の管理 API（super_admin_viewers.py）・services/viewer_admin.py・Claude の経路の専用スクリプト（状態の変更・延長・Q9 の登録）・SaaS 管理の画面（/super-admin/viewers）。
  - 4b（申込）：signup（D5）と画面の ⑤。公開（申込の入口を見せること）は 4c と一緒にする（4c が無いと pending のまま進めないため）。
  - 4c（Discord の受付、D6）：最初に D6 の【未確認】2つを確かめてからカードを書く。→ 2026-10-17 に2つとも事実になった（D6 に記録）。
  - 順番（2026-10-17。招待リンクの PO 決定による）：4b の申込は viewer_discord_config を読むので、4c を先に作り、4b はその後に作る。公開は 4b と 4c を一緒にする。
- 4c の細部（2026-10-17 Opus の判断。設計の範囲内。調査は origin/main 755bdb5e1・64066e0e0 基準。カードは /tmp/CC報告ファイル/viewer_stage4/card_4c.md）：
  - viewer_discord_config は1行だけの表にする（id は 1 だけを許す CHECK）。運用サーバーは1つなので、別の guild の行が増えて正本が2つにならないようにする。set-config は id=1 の行を作るか更新する。GRANT は SELECT・INSERT・UPDATE（DELETE は付けない）。
  - 部屋の作成の部品は2つに分ける：カテゴリの取得（resolve_category）と部屋の作成（create_private_text_channel）。既存の関数では、カテゴリの取得を今と同じ位置（leads の確認より前）で呼ぶ。部屋の作成だけをひとまとめにすると、カテゴリの取得が leads の確認の後ろに移り、既存の動き（カテゴリが無いときは DB を読まずに終わる）が変わるため。作成時の reason は引数にして、既存は今の文字列のまま渡す。
  - 部屋の片付け（4a-1 で 4c に回した件）：gateway が自分で片付ける。受付のカテゴリの中の `trial-<id>` の部屋で、その id の viewer_accounts の行がもう無いものだけを消す（起動時に1回と、その後24時間ごと。1回に10件まで。DB の読み取りに失敗した回は1件も消さない）。毎日の掃除（maintenance.py の Celery タスク）から消さない理由：【事実】celery-worker には DISCORD_BOT_TOKEN が渡っていない（docker-compose.yml:212-300 に無く、backend :109 と discord-gateway :357 にだけある）。トークンを足すと、ボットの鍵を持つ入れ物が増えるため。行の有無で決めるので、照合の途中（行はあるが部屋の番号をまだ書いていない）の部屋は消さない。
  - 部屋の名前に使う id は viewer_accounts.id。照合の失敗で作った部屋は、その場で消す（消せなければ上の片付けで後から消える）。
  - 連携済みの人がボタンを押し、部屋が消えていたときの作り直しでは、新しい部屋に URL と email と「パスワードを忘れたらログイン画面から再発行」を投稿する。初期パスワードは作り直さない（すでに変えているかもしれないため）。
  - 申込コードの正規化と sha256 は backend/app/auth/viewer_signup_code.py に置き、4b の申込と 4c の照合で同じ関数を使う（コードの形の正本を1か所にする）。
  - 専用スクリプト viewer_discord_cli に、読み取りだけの list-candidates（ボットが入っているサーバー、カテゴリ、テキストの部屋、ロールの id と名前）を足す。PO が set-config の4つの ID を Discord の画面で探さずに済むようにするため。出力はファイルに置き、チャットには選んだ4つだけを出す。実行は Q12=n のとおり、毎回 PO 本人の GO を受けてから。
  - 一覧の部屋の URL は `https://discord.com/channels/<guild_id>/<discord_channel_id>`（前例 frontend/src/pages/inbox/InboxKartePanel.tsx:465）。guild_id は viewer_discord_config の1行から一覧の SQL で引き、応答には discord_channel_url だけを出す。画面は ButtonLink（frontend/src/components/ButtonLink.tsx の href 形）で別のタブに開く。
  - 4c の公開前の PO の作業（Discord の設定）：①運用サーバーのボットのロールに「チャンネルの管理」と「招待を作成」があるか確かめ、無ければ付ける ②受付の部屋に、ボットの「招待を作成」「メッセージを送信」を拒否する上書きが無いか確かめる ③list-candidates の結果から4つの ID を選ぶのを PO が確かめる ④set-config と post-button の GO。
- 4b の細部（2026-10-17 Opus の判断。設計の範囲内。調査は origin/main 78f2b9af0 基準。カードは /tmp/CC報告ファイル/viewer_stage4/card_4b.md、審査は review-opus.md r18）：
  - 回数制限は IP（1時間10回）→ email（1時間3回）の順に数える（backend/app/cache.py の count_viewer_signup。キーは viewer_signup_ip: と viewer_signup_email: に sha256）。Redis が使えないときは申込は通すが、招待は作らない（D5 の「回数制限を通った申込でだけ作る」を、数えられないときにも守るため）。
  - pending の再申込では、申込コードだけを差し替え、line_name・inventory_issue は書き換えない。
  - 招待は DB の commit の後に作る（backend/app/services/viewer_invite.py）。Discord を待つ間、トランザクションを開いたままにしない。
  - 招待リンクは Button ＋ window.open で開き、URL の文字も画面に出す。ButtonLink は react-router-dom を引き込み、viewer の JS が 338.3KB になって 300KB の上限を超えたため使わない（main 290.0KB、変更後 296.0KB）。
- 4a-2 の細部（2026-10-16 Opus の判断。設計の範囲内。調査は origin/main 9c2b9c041 基準）：
  - 一覧の Discord の部屋の URL は 4a-2 では返さない。viewer_discord_config の表が 4c まで無いため（migrations/20261016_150000_add_viewer_accounts.sql:3）。4a-2 は discord_user_id と discord_channel_id を返し、URL は 4c で足す。
  - 目印①：同じ閲覧者の login_succeeded のどれかの時点 t について、(t−24時間, t] の login_succeeded の client_ip（NULL を除く）が3種類以上。目印②：その閲覧者の login_succeeded の client_ip と同じ値が、別の閲覧者の login_succeeded にある。どちらも保存中（90日）の行だけで判定する。
  - Claude の経路の専用スクリプトは2本。backend/app/viewer_admin_cli.py は stdin の JSON {action, email, days?} を受け、PO の画面と同じ services/viewer_admin.py の関数を actor=claude・actor_user_id=NULL で呼ぶ。backend/app/viewer_register_cli.py は stdin の JSON {rows:[{applied_at, line_name, email, status}]} を受ける（前例 backend/app/line_device_admin.py）。SQL やコマンドは受け取らない。
  - 登録（Q9）：trial の人の期限は applied_at（タイムゾーン無しは JST）＋14日、active の人は NULL。登録では viewer_status_changes に行を書かない（action の許可値に登録が無く、状態の変更ではないため）。
  - 延長は「記録した時刻＋N日」（:523 のとおり）。N は 1〜365 の整数。
  - 「最後の suspend」を引く索引は足さない（閲覧者は数十人の規模）。
  - require_super_admin の定義は今は backend/app/auth/dependencies.py:516（:519 の「:495」は古い）。
  - 画面の受入（vitest）：super admin でなければ拒否の文言、状態の Badge、目印の Badge は条件の行だけ、状態ごとの操作ボタンの出し分け、確認の Modal から POST、延長 0 は送れず 7 は送れる、409 の文言、ログイン記録の Drawer に日時・IP・端末。本番では Evaluator が画面で確かめる。
- password-reset/request の回数：アプリ（auth.py:391）は4回目から 429 を返すが、閲覧者は D1 のとおり4回目からはメールを送らずに同じ 200 を返す。数えるキーは閲覧者専用の `viewer_pw_reset_req:<正規化した email の sha256>` にし、アプリの `pw_reset_req:` と同じ枠に混ぜない（D1-3 の「アプリのユーザーと同じ枠に混ざらない」と同じ理由）。
- Q7 の消す仕組み（PO 決定 Q7 の「段4のカードの前に設計して審査する」への答え）：
  - 方式：毎日の Celery タスク（backend/app/tasks/maintenance.py に足す。beat は celery_app.py の purge-auth-events（:99、毎日5:30）の後ろに、毎日5:45 で足す）。専用スクリプトにしない理由：人が実行を忘れると、ポリシーに書いた90日を守れないため。
  - 消す対象は次の2つだけ（どちらも viewer_accounts の行を DELETE する）。
    1. 状態が trial で、trial_expires_at が「今−90日」より前の行（期限が切れ、延長が無いまま90日たった人）。
    2. 状態が suspended で、viewer_status_changes の action = 'suspend' の最新の created_at が「今−90日」より前の行（停止して90日たった人。本契約の終了は停止で表すため）。suspend の記録が1件も無い suspended の行は消さない（いつ止めたか分からないものは、安全側で残す）。
  - active・pending・verified はこのタスクでは消さない（pending は下の7日の掃除で消す）。
  - 関連の記録（viewer_login_tokens・viewer_login_events・viewer_status_changes）は、FK の ON DELETE CASCADE（migrations/20261016_150000_add_viewer_accounts.sql）で一緒に消える。タスクで別に消さない。
  - 同じタスクで、①申込コードを照合しないまま7日たった pending の行（D5）、②作られて90日たった viewer_login_events の行（ログイン記録）も消す。消した件数は種類ごとにログに出す（個人の email は出さない）。
  - 4c の後は、消した人の Discord の部屋（discord_channel_id）が Discord に残る。部屋の片付けは 4c のカードで扱う（4a-1 では Discord に触らない）。→ 4c の細部（下）の「部屋の片付け」で決めた。
  - 【事実】Q9 の22人の申込日時の最も古い値は 2026/09/06。登録の後は active なので、このタスクで登録直後に消える人はいない。
- privacy.astro（英語のページだけ。日本語のページは無い：find lp/src/pages -name '*priv*' で privacy.astro の1件）の §6.3 の表（:203-216）に1行を足す：`Inventory Viewer Account` ／ `During the trial or contract period; deleted 90 days after the trial expires without extension or after suspension. Login records: 90 days`。

## 維持の仕組み

- 守り手: backend/tests/test_viewer_isolation.py（全 APIRoute を自動で列挙し、VIEWER_ROUTE_ALLOWLIST 以外が閲覧者のトークンで 401 になることを CI で確かめる。段1 で作成）。トークンを見ない公開ルートは、テストの固定一覧 _PUBLIC_NO_AUTH_ROUTES で例外にしている。一覧に無いルートが 401 以外なら失敗する
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
- ~~Q2a. ログインの方法~~ →【2026-10-16 の PO 決定（専用 URL＋パスワード、忘れたらメールで再発行）で置き換え済み。r13】元の決定：メールのリンクで入る。登録フォームの情報で管理し、リンクを知っているだけでは見られない形にする（PO、2026-10-15）。D1 に反映した。
- Q2b.【置き換え済み・実装しない（Q2f）】【決定 2026-10-15 PO】原文「トライアルではメール、LINE名、DISCORD IDのみ、本契約に進むときに詳しい情報を別途フォームで取得する」。申込フォームはメール・LINE 名・Discord ID の3つ（後に Q2f でメールと LINE 名の2つに変更）。本契約用の詳しい情報フォームは今回の対象外（別の便で設計する）。
- Q2d.【置き換え済み・実装しない（Q2f）】【決定 2026-10-15 PO】原文「数字のID、SAの顧客対応と同様に顧客管理で利用するため」。数字のIDで受け取る。閲覧者の行はテナントの取引先（companies）には写さない（SSOT）。本契約で取引先とつなぐ方法は、本契約フォームの便で設計する。
- Q2e.【置き換え済み・実装しない（Q2f）】【決定 2026-10-15 PO】原文「Discord ID だけ任意、ただし間違えて送られてくる可能性があるので数字以外は受け付けないようにしてくれ」。メールと LINE 名は必須、Discord の数字のIDは任意。入力があるときは、既存の検証と同じ `^\d{17,20}$`（backend/app/routers/discord_ticket_config.py:48）に合わない値を 422 で拒み、画面は i18n の案内文を出して送信させない。空欄は NULL で保存する。
- Q2f.【決定 2026-10-15 PO「Y」】Q2d・Q2e を置き換える。申込フォームはメールと LINE 名の2つだけにし、Discord ID は聞かない。Discord の数字のIDは、顧客ごとの専用URL（Discord でログイン→identify と guilds.join で ID を取得→ボットがサーバーに加える）で自動取得する。この仕組みと、ID の保存先（既存の顧客管理の列にそろえるか）は本便の対象外とし、別の仕事として設計する。調査の記録は /tmp/CC報告ファイル/viewer_discord_autoid_facts.txt（公式資料：docs.discord.com/developers/topics/oauth2、resources/guild、events/gateway-events）。
- Q2g.【決定 2026-10-15 PO】原文「在庫関連の課題も自由記述で最初のフォームに入力させる」。申込フォームはメール・LINE 名・在庫関連の課題（自由記述）の3つ。課題は任意（PO「Y」2026-10-15）。空欄でも申し込める。
- Q2c.【r13 で置き換え済み・実装しない（ログインのリンクを作らないため）】【決定 2026-10-15 PO「Y」】リンクを押した後に、登録した email を入力し直してもらう（D1 のまま）。
- Q3.【決定 2026-10-15 PO】原文「Y,私もしくはあなたが切り替えできるようにする。私がやる場合はフロントエンドから切り替えをするがあなたに任せる場合はSSHを使用する」。切り替え（trial→active）と停止（→suspended）、停止の解除ができるのは PO と Claude だけ。
  - PO の経路：super admin 画面。API は既存の require_super_admin（backend/app/auth/dependencies.py:495（origin/main 65ed8cd8b））で守り、画面は pages/super-admin/ 配下に置く（既存例 backend/app/routers/super_admin_phase_switch.py:65・:89）。
  - Claude の経路：【事実】制限付き鍵 salesanchor-claude で実行できるのは監視の4コマンドだけで、DB の読み書きはできない（docs/adr/ADR-079-claude-code-monitoring-access.md:57、docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58-59・:220-224）。DB 書き込みには無制限鍵が要り、CLAUDE.md:29-30 により作業ごとに PO の GO が要る。そこで、SQL を手で書かず、backend コンテナ内の専用スクリプト（引数は email と変更後の状態だけ。PO の画面と同じサービス関数を呼ぶ）を無制限鍵で実行する。GO 原文は依頼文と記録に転記する。
  - GO の発行者（PO 決定 2026-10-15、原文「N,仕様に関しては壁打ちして決めているので仕様から逸脱していないGOは全てOPUSに権限委譲する」）：【2026-10-15 訂正】委任の正式記録（docs/handoff/go-record-transcription/opus-delegation.md。PR #4293 の審査で範囲を PR の GO に絞った。#4293 は 2026-10-15 に main へマージ済み＝merge commit 75fea37c1。マージ前の ADR-1003 の元の範囲も PR の GO だけなので、結論は同じ）は、無制限鍵での本番の変更を含まない。CLAUDE.md:30 により、Claude の経路（無制限鍵）の操作は、作業ごとに PO 本人の GO が要る。委任を広げるには ADR と CLAUDE.md の改訂が要る（Q12）。PO の画面からの操作は PO 本人が行うので GO は要らない。複数人の一括変更・削除・本設計に無い状態の変更など、仕様から外れる操作は Opus が止めて PO に聞く。
  - **操作の GO の条件（この1か所を正とする。審査 r6 N-9、r7-N-7）**：Claude の経路（無制限鍵）の操作は、Q12 が決まるまで、すべて PO 本人の GO で行う（CLAUDE.md:30）。依頼の前に PO へ3行で報告する（誰を・何から何へ・理由）。無制限鍵の操作を Sonnet に頼むときは、PO が `bash scripts/permit-danger.sh "<操作>"` を1回実行したチケットを証拠にする（Opus が伝えた PO の許可は、Sonnet にとって伝聞になるため。審査 r8-N-5）。Q12 で委任が認められた後に Opus が GO を出せるのは、①対象が1人、②変更が上の管理 API の4つ（activate・suspend・unsuspend・extend）のどれかで上の表のとおりの遷移、③実行の前に PO へ3行で報告、の3つをすべて満たすときだけにする予定（Q12 の案）。Q9 の22人の一括登録と、計画票の計測用アカウントの作成は、Q12 の結果にかかわらず PO 本人の GO にする（4つの操作に当たらないため）。
  - 期限の延長（PO 決定 2026-10-15、原文「トライアルが終了した人も任意で期間を決めて閲覧期限を延長させる機能もつけてほしい、延長させるのは延長を記録した日次から換算する」）：状態が trial の人（期限内・期限切れのどちらも）に、操作する人が日数 N（1以上の整数）を指定する。trial_expires_at は「延長を記録した時刻＋N日」になる。元の期限に足すのではない。状態は trial のまま。PO の画面と Claude の経路の両方から同じサービス関数で行い、変更前後の期限・N・実行者・日時を記録する。
  - どちらの経路でも、変更前後の状態・実行者（PO／Claude）・日時を記録に残す。保存先は新しい表 public.viewer_status_changes にする。【事実】既存の tenant の audit_logs は tenant_id と user_id が必須で、閲覧者には使えない（backend/app/services/audit.py:277-）。auth_events は「誰が」の列が無い（migrations/001_create_auth_events.sql:6-16）。public.audit_log（migrations/20260921_110000_pipeline_tables_public.sql:404-413）は record_id が UUID 型で、閲覧者の id（BIGSERIAL）を入れられない。また、この表は TCG の商品の編集の履歴で、書き手は商品詳細の処理（backend/tests/test_tcg_product_detail_pg.py:194 で確認される経路）なので、閲覧者の状態の履歴を混ぜない。
    - 列：id、viewer_id（viewer_accounts への FK）、action（activate・suspend・unsuspend・extend の4つと、D6 のコードの照合で書く start_trial。r13）、from_status、to_status、from_expires_at、to_expires_at、extend_days（extend のときだけ）、actor（po・claude・system の3値。system は D6 のボットの処理。r13）、actor_user_id（PO の画面からのときの users.id。ADR-1008 に従い users を指す。Claude の経路では NULL）、created_at。
    - 停止の解除（unsuspend）は、その閲覧者の最後の suspend の行の from_status に戻す。viewer_accounts に「停止前の状態」の列は足さない（同じ事実を2か所に持たないため）。suspend の行が無いのに解除しようとしたら 409 にする。
    - 状態と期限の正本は viewer_accounts。この表は「いつ・誰が・何を変えたか」の履歴だけを持つ。保存期間は Q7 で決める。
  - 生の調査記録：/tmp/CC報告ファイル/viewer_ssh_recon.txt
  - 管理 API と画面（段4。審査 r6 N-8）：router は新しいファイル backend/app/routers/super_admin_viewers.py にし、前例 super_admin_phase_switch.py（:62-66 の `/super-admin/...` の形、main.py:639 の prefix "/api/v1"）にならう。すべて require_super_admin。入出力は JSON。

    | method とパス | 入力 | 出力 | エラー |
    |---|---|---|---|
    | GET /api/v1/super-admin/viewers | なし | 閲覧者の一覧（id・email・line_name・inventory_issue・状態・trial_expires_at・作成日時・目印①②・discord_user_id・その人の部屋への URL `https://discord.com/channels/<viewer_discord_config.guild_id>/<discord_channel_id>`（部屋が無ければ空）。r13） | 403 |
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
- Q5.【決定 2026-10-16 PO「y」（r13 で再決定。メールの確認をやめたため）。段4（D6）の PR を止める門は、この決定で外れた】決定の内容：Discord の受付で申込コードの照合が済んだ時点で自動的にトライアルを始め、14日はその時刻から数える。人の承認は挟まない。verified は今回使わない（5値は残す）。元の決定（2026-10-15 PO「Y」）：メールの確認が済んだ時点で自動的にトライアルを始め、14日はその時刻から数える。
- Q6.【決定 2026-10-15 PO「Y」】別のメールでの申込み直しは自動では止めない。気付いたら PO か Claude が停止する。判断の材料として、下のログイン記録と、申込一覧で同じ LINE 名・同じ IP の行に目印を出す。
- ログイン記録（PO 決定 2026-10-15、原文「ログインのログを取る形でいつ誰がどのIPからなどが特定できるのであれば1つのアカウントから複数人がログインしていないか、二重登録で回避していないかなど判断できる」）：
  - 【事実】既存の public.auth_events（migrations/001_create_auth_events.sql:6-16）は、いつ・IP（client_ip VARCHAR(45)）・端末（user_agent VARCHAR(500)）を持つが、「誰が」の列が無い。また AuditMiddleware が書くのは /api/v1/auth/ 配下と 401/403 だけ（backend/app/middleware/audit.py:34・:37）。保存は90日で、毎日自動で消す（backend/app/tasks/maintenance.py:30、backend/app/celery_app.py:96-99）。tenant の audit_logs は tenant_id と user_id が必須なので、閲覧者には使えない（backend/app/services/audit.py:277-）。
  - 決定：新しい表 public.viewer_login_events に記録する。列は id、viewer_id（viewer_accounts への FK）、event_type、client_ip、user_agent、created_at。client_ip と user_agent の名前と型、保存90日・毎日自動で消すことは、auth_events にそろえる（消す処理は maintenance.py の既存の型にならう）。auth_events には列を足さない（中間処理の全リクエスト記録と、閲覧者の本人の記録とを混ぜないため）。
  - event_type は7つ（r13 でパスワード方式に合わせて直した）：login_succeeded（ログインできた）、login_failed（パスワードが合わなかった）、password_changed（本人が変えた）、password_reset_requested（再発行のメールを送った）、password_reset_done（再発行で替えた）、signup（申込）、code_matched（Discord で申込コードが合った。client_ip と user_agent は NULL）。viewer_id は NOT NULL にする。閲覧者の行が無いとき（未登録の email への login、無効なトークンの confirm）は記録しない（審査 r6 N-7。その失敗は D1-8 の IP ごとの回数制限だけで数える）。在庫の表示（60秒ごとの取得）は記録しない（行が増えすぎるため。12時間のログインごとに1行で、共有は判断できる）。
  - IP の取り方は、本設計の回数制限と同じ1つの関数を使う（X-Real-IP）。【事実】既存の _get_client_ip は X-Forwarded-For の先頭を使っている（backend/app/auth/dependencies.py:67-72）。閲覧者ではこれを使わない。理由は D1 の回数制限と同じ（なりすまされない値を使うため）。
  - PO の画面：閲覧者ごとのログイン履歴（日時・IP・端末）を出す。目印を2つ出す。①同じ閲覧者が24時間のうちに3つ以上の別 IP からログインした。②別の閲覧者どうしで同じ IP からログインか申込がある。目印は判断の材料で、自動の停止はしない。

- Q7.【決定 2026-10-15 PO「y」】今のプライバシーポリシーと同じルールにする（lp/src/pages/privacy.astro:209「During account active period」・:219「契約終了後90日以内に削除」）。trial の期限が切れて延長が無いまま90日たった人、または本契約（active）が終わって90日たった人の閲覧者の行と関連の記録を消す。privacy.astro:206-214 の保存期間の表に閲覧者の1行を足す（段4）。消す仕組み（定期実行か専用スクリプトか）と、viewer_status_changes など関連の表の扱いは、段4のカードの前に設計して審査する。以下は質問の原文。LP のプライバシーポリシーに追記するか。**段4の公開と22人の登録の前提。決まるまで段4の公開をしない。**
- B-7.【決定 2026-10-15 PO「y」】履歴を書き直す。名字を含む作業記録を除いて1つのコミットにまとめ直した PR #4338 に置き換え、#4283 は閉じて古いブランチを消した。以下は質問の原文。（審査 r6）：コミット bf255ae8b・af1d155f7 の追加行に、個人の姓が残っている（push 済み）。merge commit でマージすると main の履歴に残る。履歴を書き直して push し直すか、このまま入れるかは PO 決定待ち。**決まるまで PR #4283 を main にマージしない。** 段1以降の実装カードは、B-7 が決まって #4283（design.md・ADR-1019）が main に入った後に出す（作業ブランチは origin/main から作るため。審査 r8-N-9）。
- SMTP（計画票 0 の①）：r13 でログインはパスワードになり、メールはパスワードの再発行だけに使う。2026-10-16 に5項目を登録し、本番からのテスト送信は SENT。**PO の受信箱での到着の目視が済むまで、段4の公開をしない**（再発行ができないと、パスワードを忘れた人が入れないため）。【決定 2026-10-16 PO「y」】受信箱への到着を確認した（§段4の実施の決め事）。
- Q12.【決定 2026-10-17 PO「n」】委任しない。Claude の経路の操作は、今までどおり毎回 PO 本人の GO で行うか、PO が画面から行う（「操作の GO の条件」のまま）。以下は質問の原文。Claude の経路（無制限鍵）での閲覧者の操作の GO を、Opus に委任するか。委任するなら、ADR-1003 の改訂か新しい ADR と CLAUDE.md:30 の改訂が要る（別の PR）。委任しないなら、操作は毎回 PO 本人の GO か、PO の画面から PO が行う。
- Q16.【決定 2026-10-17 PO「y」】申込の招待リンクは、PO の作る固定のリンクではなく、ボットが申込のたびに作る（期限1週間・使用1回。PO 原文「リンクはbotが連動して自動発行するようにしてほしいのだが出来る？」「期限1週間、使用回数1回」）。運用サーバーのボットのロールに「招待を作成」を PO が付ける。D5 の「招待リンク」に反映した。
- ~~Q11~~ → **決定済み：y**（PO「Y」、2026-10-15。保留中は前回の表のまま止める。KGI2 に「保留の間を除く」を足す）。元の問い：（審査 r6 B-1）再解析・抽出の途中（保留）の間、閲覧ページの表をどうするか。
  - 案 y：GAS と同じく前回の表のまま止める（D3 の今の案）。未確定の行を出さない（安全装置 #8 の目的）。そのかわり、保留が続くと「最終更新」が1分より古くなる。KGI2 に「保留の間を除く」を足し、受入条件に「保留でないときは updated_at が60秒以内（本番で curl）」を足す。
  - 案 n：アプリの在庫表と同じく、保留中も新しい行を出す（r5 の形）。最終更新は常に1分以内になるが、再解析の途中の行（単位が未確定のもの）が見える。GAS とは見え方がずれる。
  - 推奨は y（今の GAS の利用者の見え方を変えないため）。
- Q8.【決定 2026-10-15 PO「Y」】置き場所は app.salesanchor.jp/viewer/ にする。
- Q9.【決定 2026-10-15 PO「Y」】PO から一覧（22件、メールの重複0件・形式不正0件）を受け取った。個人情報なので、リポジトリと PR には載せず、リポジトリ外の ~/CC報告ファイル-keep/viewer-initial-accounts/initial_active_list.tsv（権限600、項目は申込日時・LINE 名・メールの3つだけ）に置く。登録は段4の公開前に、Q3 の Claude の経路（無制限鍵＋専用スクリプト。migration ではデータを入れない）で行う。登録の前に一覧を PO に見せる。 【訂正 2026-10-15 PO】原文「〇〇さんだけは本契約」（個人名のため伏せた）。active で登録するのは一覧のうち1人（2026/09/28 申込の行）だけ。残り21人（PO「Y」2026-10-15）：状態を trial にし、trial_expires_at を一覧の申込日時（JST）＋14日にして登録する。これで公開の時点では全員が期限切れになり、在庫表は見られない。PO が延長を決めた人から、延長の機能で「記録した時刻＋N日」まで見られるようになる。申込のやり直しは要らない。
  - 【r13 で直した】22人とも password_argon2_hash・discord_user_id・discord_channel_id は NULL で登録する。最初のパスワードは、本人がログイン画面の「パスワードを忘れた」から再発行のメールで決める（再発行は trial（期限切れを含む）と active に送るので、延長された人も、active の1人も使える）。Discord の受付は通らないので、部屋は無い。
  - 登録用の専用スクリプトは、一覧ファイルを読んで1行ずつ登録する。登録済みの email は飛ばして、件数（登録・飛ばした・失敗）を出す。実行の前に、対象一覧を PO に見せる。
- ~~Q10~~ →【r9 で解決】4つのうち3つ（複数選択・倍率合わせ・縦カード）は PO の回答 4・8・9 で採用し、便1・便3 で金型に登録済み（MultiSelect、DataTable の fitToWidth・mobileCards）。24時間以内はアプリと同じ Button（aria-pressed）にする（InventoryPage.tsx:443-454）。新しい金型は要らない。以下は元の問い：GAS の画面のうち、金型が無い4つ（24時間以内のスイッチ、コンディション・提供者の複数選択、PC で表を枠に収める倍率合わせ、スマホで行を縦のカードにする表示）をどうするか。推奨は「スイッチと複数選択は金型（Checkbox・MultiSelect）を新しく登録して再現する。倍率合わせは作らず、DataTable の横スクロールで代える。スマホの縦カードは DataTable の金型に表示の型として足す」。金型の登録には PO の許可が要る（docs/CC_UI_GOVERNANCE.md:11-13）。PO の 10/14 の発言「原則同じ変更を入れる、ただしスプレッドシートとGASの処理を考えて全部は実装しなくても良い」に照らして、再現しない機能は PO に確認する。

## 別件（本設計の外）

- 社内ユーザーの権限の穴（会話ログの読み取り、招待トークンの発行など。security-recon.md §2）。別の設計で扱い、PO に相談する。


## 段5：管理画面の追加（2026-10-19）

PO 決定 2026-10-19 原文「y,新規の申し込みがあったときの申込フォームのURLもこのページからコピペして送れるようにしたい、そしてサイドメニューを設置して、トライアル中、本契約、などステータスごとに分けて見れるページも欲しい」。招待のボタンは「申込済みでコードを失くした人に、コードと招待リンクを作り直して管理画面に表示する」形（PO「y」）。

### 目的と変化
- 新しく申し込みたい人へ、管理画面から申込フォームの URL を1回押してコピーし、そのまま送れる。URL を開くと最初から申込画面が出る（`/viewer/#signup`）。
- 管理画面の左に状態ごとのメニュー（すべて・申込中・お試し・本契約・停止中、件数つき）を置き、押した状態の人だけを表で見られる。`?status=` で URL に残る。
- 申込中の人がコードや招待リンクを失くしたとき、管理画面から作り直して、その場でコピーして渡せる。

### 決めたこと（理由）
- 招待リンクだけの発行はしない。お試しの開始には申込コードが要り、申込コードは申込でしか作られない（routers/viewer.py:470-480）。招待だけを渡しても部屋は作れない。
- 作り直しは pending の人だけ。trial 以降はすでに部屋とアカウントがあり、コードは使い終わっている（viewer_trial.py の照合で trial になる）。
- 申込コードを作る処理は services/viewer_signup.py の replace_signup_code に1つだけ置き、/signup と作り直しの両方がそれを呼ぶ（SSOT）。
- コード・招待は今まで通り DB に平文で持たない（コードは sha256、招待は保存しない＝viewer_invite.py:5）。管理画面でも閉じたら二度と出さない。
- 状態の絞り込みは画面側で行う（list_viewers は全件・LIMIT なし＝services/viewer_admin.py:39-65。閲覧者は数十人の規模）。数百人を超えたらサーバー側の絞り込みを別便で足す。
- 左メニューは共通部品 SubMenu（ADR-149）。並べ方は ManagementCenterPage と同じ hub-shell。新しい部品は作らない。
- 申込フォームの URL は `window.location.origin + "/viewer/#signup"` で作り、直書きしない。

### 選ばなかった案
- 作り直しを記録の表（viewer_login_events）に残す：種類の CHECK 制約（migrations/20261016_150000_add_viewer_accounts.sql:65）に無く、migration が要る。今回はアプリのログ（viewer_id だけ）に残す。DB に残す必要が出たら別便。
- 状態ごとに別のページ（子ルート）にする：表・操作は同じで、違うのは行の絞り込みだけなので、1ページ＋`?status=` にした。

### 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 管理画面の右上「申込フォームのURLをコピー」を押すと `https://app.salesanchor.jp/viewer/#signup` がクリップボードに入り、文言が2秒「コピーしました」になる | 画面テスト＋PO 目視（貼り付けて確認） |
| K2 その URL を開くと、ログイン画面ではなく「利用の申込」の画面が最初に出る | 画面テスト＋PO 目視 |
| K3 左メニューに すべて・申込中・お試し・本契約・停止中 と件数が出て、押すとその状態の人だけになる。`?status=trial` で開き直しても同じ | 画面テスト＋PO 目視（件数が一覧の状態の数と一致） |
| K4 申込中の人だけに「コードと招待を作り直す」が出る。押すとコード・期限・招待リンクが出る。前のコードは受付で「コードが違うか、期限が切れています。」、新しいコードで部屋ができる | API テスト＋PO の試し（申込中の人で） |
| K5 申込中以外への作り直しは 409、super admin 以外は 403 | API テスト |
| K6 migrations/・deploy.yml・本番 scripts/ の変更なし。閲覧ページの容量が 300KB 以下（design.md:509） | `git diff --name-only`＋build の記録 |

### 外部事例
- 対象外：社内の管理画面に状態の絞り込みとコピーボタンを足すだけで、既存の部品と既存の仕組み（申込コード・招待）の組み合わせ。成否を左右する外部の数値は無い。

### 戻し方
- PR を Revert。DB を変えないので、データの戻しは要らない。

### 維持の仕組み
- 文言は ja.json/en.json の同じキー（i18n の CI）。部品は SubMenu/Button/Modal（UI ガバナンスの CI）。申込コードの発行は replace_signup_code 1か所（テストが /signup と作り直しの両方を見る）。

## 段6（2026-10-19）招待をお試し中・本契約にも／延長に日付指定／停止ボタンとログイン記録を外す／使い回しの疑いを運用 Discord へ

### PO 決定（原文）
- Opus の選択肢「2. 申込中に戻さずに、お試し中の人にも招待を出せるよう画面を直す」→ PO「2」
- 「延長ボタンで日付や日数を指定して延長できるようにする」
- 「期限が終了したら見れなくしてくれれば良い、停止ボタンは不要」
- Opus の選択肢「1. 画面からログイン記録を外す。記録と使い回しの目印は残し、疑いが出たら運用の Discord に自動で知らせる仕組みを、今回の改修に入れる」→ PO「ｙ」
- 一任：「PRマージ、デプロイまで完走させてくれ。」（2026-10-19）

### 設計の要点
- A 作り直し：backend/app/services/viewer_admin.py の reissue_signup_code が pending / trial / active を受け付ける。suspended・verified は 409、Discord の部屋が既にある人は 409（viewer_already_linked）。状態と期限は変えない。
- B 受付：backend/app/discord_gateway/viewer_trial.py が pending / trial / active を通す。pending は今まで通り（trial に進め期限14日）。trial / active は状態と期限を変えず、部屋とパスワードだけ付ける（本契約がお試しに下がらない）。部屋のある人・suspended・verified は CODE_INVALID。
- C 延長：ExtendRequest は days か until_date のどちらか一つだけ（両方・無しは 422）。until_date は日本時間 23:59:59 を期限にし、今以前・今+365日より後は 422。履歴の extend_days は days のときだけ。DB の構造は変えない。
- D 画面：作り直しは pending / trial / active で部屋の無い行に出す。延長 Modal は Radio 金型で「日数で延ばす／日付まで延ばす」。停止・停止解除・ログイン記録（Drawer）と左メニューの「停止中」を外す。目印バッジは残す。
- E 通知：目印の条件は viewer_admin.py の定数だけが正（一覧と share_flag_hits が共用）。backend/app/tasks/viewer_share_flag_monitor.py を 1 時間ごとに beat で動かし、ADMIN_NOTIFICATION_DISCORD_WEBHOOK へ id だけの文面で送る。同じ知らせは Redis キー viewer_share_flag:notified:{id}:{kind}（30日）で抑える。Redis が無い・webhook 未設定なら送らない。
  - 段6b：実際は毎時15分（crontab）。理由：interval（3600.0）は再起動で計測が初めからになり、deploy が60分以内に続くと一度も動かないため。
- F 触らない：suspend・unsuspend・logins の API と CLI、viewer_login_events の書き込みと 90 日削除、migrations/・deploy.yml・本番 scripts/。

### 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 お試し中（期限切れを含む）・本契約で部屋の無い人の行に「作り直す」が出て、押すとコードと招待が出る。停止中と部屋のある人には出ないか、409 になる | API テスト＋画面テスト＋PO 目視 |
| K2 お試し中・本契約の人が受付でコードを入れると部屋ができ、状態と期限は変わらない | PG テスト |
| K3 延長で日数か日付を選べる。日付指定ならその日の日本時間 23:59:59 が期限。過去の日と366日より先は断る | API テスト＋画面テスト＋PO 目視 |
| K4 期限切れのお試しの人は、ログインも在庫も見られない（403） | 既存テスト test_viewer_api.py:308 / test_viewer_tokens.py:140 |
| K5 管理画面に「停止」「停止を解除」「ログイン記録」が無く、左メニューに「停止中」が無い。目印のバッジは残る | 画面テスト＋PO 目視 |
| K6 使い回しの疑いが新しく出たら、運用の Discord に1回だけ知らせる。email・LINE 名・IP は載せない | 単体テスト。本番では beat 登録の確認 |
| K7 目印の条件が1か所にしかない | git grep で SQL が viewer_admin.py の1か所だけ |
| K8 migrations/・deploy.yml・本番 scripts/ を変えていない。閲覧ページの容量が 300KB 以下 | git diff --name-only＋build |

### 外部事例
- 対象外：社内管理画面の部品の出し分けと、既存の定期通知（master_required_fields_monitor.py）と同じ型の通知の追加。

### 戻し方
- PR を Revert。DB を変えないので、データの戻しは要らない。Redis のキーは30日で消える。

### 維持の仕組み
- 目印の条件は定数1か所（テストが一覧の目印と通知の対象の一致を見る）。beat 登録は tests/test_celery_beat_registered.py が見る。文言は ja.json/en.json の同じキー（i18n の CI）。

## 段7（2026-10-20）閲覧者管理の一覧を5列にし、行を押すと詳細をスライドで出す

### PO 決定（原文）
- 「目印って何？フロントにはメールとDiscordIDは表示不要なので非表示にしてくれ、LINE名、状態、登録日次、期限、操作を表示、本契約にするボタンなどは1行ずつ横並びにしてくれ、行クリックしたら詳細をスライドページに表示するようにしてくれ」
- Opus の選択肢「1. 一覧から外して、スライドの詳細にだけ出す」（目印の置き場）→ PO「1」

### 要点
- A. Stack 金型に `direction?: 'column' | 'row'`（既定 column）を追加。row のとき `comp-stack--row`（flex-direction: row / nowrap / align-items: center）。Stories に Row、テストに row と既定の2系統を追加。
- B. 一覧の列は LINE名・状態・登録日時・期限・操作の5列。email・discord_user_id（部屋のリンク含む）・目印は外す。操作のボタンは `<Stack direction="row" gap="2">` で横1列。
- C. DataTable の onRowClick で `detail` を設定し、Drawer に LINE名・メール・状態・登録日時・期限・Discord ID・部屋のリンク（あれば）・目印（無ければ「なし」）を出す。ラベルと値は既存の共通 class（form-grid / form-row）。一覧を読み込み直したら detail を id で最新の行に差し替える。
- D. i18n は `superAdmin.viewers.detailTitle` と `flagsNone` を ja/en に追加。消したキーは無し。
- E. ViewerAccountsPage.test.tsx：見出しが5つだけ／行クリックで詳細が開く（メール・Discord ID・目印あり／なし）／操作ボタンで詳細は開かず確認画面が出る。メール前提だった既存テストは LINE名で行を引く形に直した。

### 受入基準
| 基準 | 検証方法 |
|---|---|
| K1 一覧の列は LINE名・状態・登録日時・期限・操作 だけ | 画面テスト＋PO 目視 |
| K2 操作のボタンが横1列に並ぶ | Stack テスト＋PO 目視 |
| K3 行を押すと右から詳細が出て、メール・Discord ID・部屋・目印が見える | 画面テスト＋PO 目視 |
| K4 ボタンを押しても詳細は開かない | 画面テスト |
| K5 生の色・px・ハードコード日本語なし。i18n・CSS 値・ページ構成の検査が合格 | 既存の検査スクリプト・eslint |
| K6 ほかの画面の Stack は見た目が変わらない（既定は column） | Stack テスト |

### 外部事例
- 対象外：既存金型（DataTable onRowClick・Drawer）の組み合わせと、Stack 金型への向き指定の追加。

### 戻し方
- PR を Revert。DB・API を変えないのでデータの戻しは要らない。

### 維持の仕組み
- 横並びは Stack 金型の direction に一本化（個別 CSS を作らない）。文言は ja.json/en.json の同じキー（i18n の CI）。

## 段8（2026-10-20）閲覧者の詳細スライドで LINE名を直せるようにする

### PO 決定（原文）
- 「全て確認した、スライドページはデータを編集できるように出来る？」
- 直す項目の選択肢に「1と状態」→ 状態の決まりの説明のあと「LINE名だけにする」
- 直せるのは LINE名だけ。メール・Discord ID・状態は直せない（状態は今あるボタンのまま）

### 変えるもの
- backend：`viewer_admin.update_line_name`（前後の空白を除き 1〜100 文字。範囲外は invalid_line_name→422、無い id は 404。行ロックして UPDATE。commit は呼び出し側）。`PATCH /api/v1/super-admin/viewers/{viewer_id}`（require_super_admin、応答は ViewerAdminItem）。
- 画面：ViewerAccountsPage の Drawer の LINE名を TextField 金型にし、footer に「保存」。下書きが元と違い 1〜100 文字のときだけ押せる。成功したらスライドと一覧を応答で差し替え「保存しました」（role="status"）、失敗は role="alert"。保存せずに閉じたら下書きは捨てる（確認画面なし）。
- 触らない：DB・migrations・deploy.yml・scripts、メール・Discord ID・状態の編集、申込（viewer.py）、金型そのもの。変更履歴の表は作らない（仕入元 PATCH と同じ前例）。
- 即時反映：NO_SIGNAL_ROUTES（topics.py:108-111 の状態変更と同じ扱い）

### 受入基準
| 基準 | 検証方法 |
|---|---|
| K1 スライドで LINE名を直して保存すると、一覧とスライドの名前が変わる | 画面テスト＋PO 目視 |
| K2 再読み込みしても直した名前のまま（DB に入っている） | backend テスト＋PO 目視 |
| K3 空と 101 文字は保存できない（画面で押せない／API は 422） | 画面テスト＋backend テスト |
| K4 super admin 以外は直せない | backend テスト |
| K5 メール・Discord ID・状態は直せないまま | 画面テスト（入力欄が LINE名の1つだけ） |
| K6 生の色・px・ハードコード日本語なし。check:*・eslint 合格 | 検査スクリプト |

### 外部事例
- 対象外：既存金型（TextField・Drawer footer・Button）と仕入元詳細スライド（SupplierDetailDrawer）の前例の組み合わせ。

### 戻し方
- PR を Revert。DB を変えないのでデータの戻しは要らない（直した名前は元に戻らないが、画面からもう一度直せる）。

### 維持の仕組み
- LINE名の置き場所は public.viewer_accounts.line_name の1か所だけ。検証の範囲（1〜100）は申込と同じ。文言は ja.json/en.json の同じキー（i18n の CI）。


## 段9（2026-10-20）計測用の閲覧者1件の削除／歓迎メッセージの初期パスワードをコードで囲む

### 9-1 計測用の閲覧者1件（id=23）の削除
- PO 決定（2026-10-20「一度データを消して再度登録できるようにしたい」）で、計測用の閲覧者1件（id=23）を削除した。
- design.md:418 付近の「計測用は suspend して行を残す」とは異なる扱い。PO 決定で上書きした例外である。
- バックアップは PO 手元のみ。リポジトリには載せない。名簿の中身（メール等）はここに書かない。

### 9-2 歓迎メッセージの初期パスワードをインラインコードで囲む
- 変更: backend/app/discord_gateway/viewer_bot_texts.py:33 の `初期パスワード: {password}` を `` 初期パスワード: `{password}` `` にする。
- 理由: スマホの Discord で長押しコピーしやすくするため（PO 依頼 2026-10-20「パスワードはマークダウンで囲ってスマホでもコピーできるようにしてほしい」）。
- 安全性: パスワードは secrets.token_urlsafe(18)（backend/app/discord_gateway/viewer_trial.py:286）で、A-Za-z0-9-_ のみ。バッククォートを含まないので囲みが崩れない。
- 触らない範囲: URL 行・メールアドレス行・ROOM_RECREATED。

### 9-3 残り
- 失敗理由の記録（出し先は PO 回答待ち）。
- LINE 内ブラウザ対策（PO の試行待ち）。

### 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 歓迎文のパスワード行がバッククォートで囲まれる | 単体テスト（backend/tests/test_viewer_discord_trial.py、PG 不要） |
| K2 メール・URL 行は変わらない | 単体テスト |
| K3 本番で新しく部屋ができたときの文面をスマホで長押しコピーできる | PO 目視 |

### 外部事例
- 対象外：Discord 標準のインラインコード記法の利用のみ。

### 戻し方
- PR を Revert。

## 段10（2026-10-20）流れごとの文面のひな形と、部屋への自動のお知らせ

### 10-0 PO の依頼と決定（原文）
- 「フローごとにメッセージ用のテンプレートを用意できる？申し込みがあり、フォームの入力をお願いするテンプレートから順番に」
- 置き場所：「1,3のハイブリッド」（管理画面のコピー＋システムが Discord で自動送信）
- 「discordの招待URLもLINEのブラウザではなく外部ブラウザで開くように出来る？」
- ③：「2日前に面談の日程調整を依頼する文面にしたい」→「前日という意味」
- 面談の日程の決め方：「進める」（Opus の提示したおすすめ＝専用の部屋に都合のよい日時を書いてもらう、と解釈。違えば PO が訂正）

### 10-1 現状（調べた事実。生の引用 /tmp/CC報告ファイル/viewer_templates/recon_raw.md・recon_impl.md・recon_impl2.md、origin/main c7bac6249）
- 文面の正本は backend/app/discord_gateway/viewer_bot_texts.py（全60行・SSOT と明記 :1-7）。部屋へ送る文は ROOM_WELCOME :28-34 と ROOM_RECREATED :35-40 だけ。①〜④の文面は無い。
- 申込 URL のコピーは frontend/src/pages/super-admin/ViewerAccountsPage.tsx:345-353（`${window.location.origin}/viewer/#signup`、:349）。コード作り直しの結果は :503-537（コード・期限・招待の素データだけ。API は ViewerReissueResponse super_admin_viewers.py:96-101）。
- 状態の変更は viewer_admin.change_status（backend/app/services/viewer_admin.py:181-291、commit しない）。commit は Web が super_admin_viewers.py:_change :130-152（:148）、CLI が viewer_admin_cli.py:run :16-28（:28）。Discord には何もしない。管理画面に停止ボタンは無い（段6、ViewerAccountsPage.test.tsx:129）。停止は CLI だけ。
- 停止しても部屋の権限は変わらない（private_channel.py:60-76 の本人・staff・bot のみ可のまま）。→ 停止の連絡は部屋に送れば本人に届く。
- 部屋の ID は viewer_accounts.discord_channel_id（migrations/20261016_150000_add_viewer_accounts.sql:16）。期限は trial_expires_at TIMESTAMPTZ（:17、UTC で比較 viewer.py:195-197、延長の日付指定は JST 23:59:59 viewer_admin.py:213-216）。お試しは開始から14日（viewer_trial.py:29）。
- bot の鍵 DISCORD_BOT_TOKEN は backend（docker-compose.yml:110）と discord-gateway（:362）だけ。celery には無く、それは意図的（本書 :498「鍵を持つ入れ物を増やさない」）。
- backend から部屋へ送る共通関数 discord_api_request（backend/app/services/discord_rest.py:34-42、429/5xx 再試行）。閲覧者の前例 viewer_invite.py:23-57（commit 後に呼ぶ・失敗は None・ログは種類と HTTP 状態だけ）。
- gateway は REDIS_URL（docker-compose.yml:358）と DATABASE_URL（:365）を持ち、setup_hook で init_redis（client.py:132）。定期ループの前例 _viewer_room_sweep_loop（client.py:161-175、on_ready で create_task :157-159、close で cancel :136-139）。
- 重複送信を防ぐ前例は Redis の存在キー（backend/app/tasks/viewer_share_flag_monitor.py:21,40-41,80-85、送れたら TTL 30日・失敗ならキーを作らない・Redis が無ければ送らない）。
- 閲覧ページは hash の完全一致で申込画面を開き、クエリは無視・保持する（frontend/src/pages/viewer/ViewerApp.tsx:27,54,61）。nginx は location = /viewer/（frontend/nginx.conf:32-35）。
- LINE の公式説明（https://developers.line.biz/en/docs/line-login/using-line-url-scheme/ 2026-10-20 確認、Context7 は月の上限で使えず直接確認）：URL に openExternalBrowser=1 を付けると「LINE アプリから開いたすべての URL」が外部ブラウザで開く（LIFF を除く）。

### 10-2 文面（PO に提示した案。正本は viewer_bot_texts.py に置く）
- ① SIGNUP_REQUEST（手で送る・管理画面でコピー）
  在庫集計ツールのお試しのご案内です😊 / 下記のページから、メールアドレスと LINE の表示名を入力してお申し込みください。/ 申込ページ：{signup_url} / お申し込みのあと画面に出る「申込コード」と「Discord に参加する」ボタンで、Discord の受付にお進みください。
  - signup_url = `https://app.salesanchor.jp/viewer/?openExternalBrowser=1#signup`（定数 SIGNUP_URL。クエリは # の前）
- ② REISSUE_NOTICE（手で送る・作り直し結果でコピー）
  {line_name}さん、申込コードを作り直しました。/ 申込コード：{code}（{expires}まで有効）/ Discord への招待：{invite_url} / Discord の受付の部屋で「申込コードを入れる」ボタンを押し、このコードを入れてください。
  - invite_url には `?openExternalBrowser=1` を付ける（既にクエリがあれば `&`）。招待が作れなかった（None）ときは招待の行を出さない REISSUE_NOTICE_NO_INVITE。
  - {expires} は JST の「M月D日 HH:MM」。
- ③ INTERVIEW_REQUEST（自動・期限の前日）
  お試し期間は {expires_date} で終わります。/ ご利用の感想やこれからのご利用についてお話しするため、短い面談をお願いできますでしょうか😊 / ご都合のよい日時を、この部屋に3つほどお送りください。
  - {expires_date} は JST の「M月D日」。
- ④ NOTICE_EXTENDED / NOTICE_ACTIVATED / NOTICE_SUSPENDED（自動・操作の直後）
  - 延長：お試し期間を {until_date} まで延長しました😊
  - 本登録：本登録が完了しました。引き続きご利用ください😊
  - 停止：ご利用を停止しました。ご不明な点は、この部屋でお知らせください。
  - 停止の解除（unsuspend）は文面なし（PO の依頼に無い）。

### 10-3 作り方（選んだ案と理由）
- 文面は全部 viewer_bot_texts.py に置く（1か所）。→ 段11 便2 で DB（viewer_message_templates）へ移す（本書「段11」参照）。管理画面は API が返す出来上がりの文を表示・コピーするだけで、フロントに文面を持たない（二重管理を作らない）。前例：顧客用 welcome_template を API が返す（backend/app/routers/discord_ticket_config.py:60）。画面のボタン名だけ i18n（ja/en 同一キー、ADR-027）。
- 日付の書式は1つの関数（viewer_bot_texts.format_jst_date / format_jst_datetime）にまとめる。招待へ目印を付けるのも1つの関数（external_browser_url）。
- ④は backend の commit の後に送る（Web は _change、CLI は run の commit の後）。送る処理は新しい backend/app/services/viewer_room_notice.py の `send_room_notice(channel_id, text) -> bool`：discord_api_request で POST /channels/{id}/messages、本文 {"content": text, "allowed_mentions": {"parse": []}}、max_retries=1、例外は外へ出さず False、ログは種類と HTTP 状態だけ（本文・メールは出さない）。部屋が無い人（discord_channel_id が NULL）には送らない。送れなくても操作は成功のまま（前例 viewer_invite.py）。
  - Web の応答に room_notice（"sent" | "failed" | "no_room"）と room_notice_text を足し、送れなかったときだけ管理画面に「部屋に送れませんでした。下の文をコピーして送ってください」とコピーボタンを出す。
- ③は gateway の中に1時間ごとのループを足す（sweep と同じ型）。理由：gateway は既に鍵・DB・Redis を持ち、celery に鍵を足さずに済む（本書 :498 の方針を守る）。
  - 送る条件：status='trial' かつ discord_channel_id あり かつ trial_expires_at あり、かつ「期限の JST の日付の前日」が今日（JST）、かつ今が JST 10:00 以降。
  - 重複防止：Redis キー `viewer_interview_notice:{id}:{trial_expires_at の UTC ISO}`。送れたら TTL 30日で置く。失敗ならキーを作らない（次の1時間で再試行）。Redis が無ければ送らない。延長で期限が変わればキーが変わり、新しい期限の前日にまた送る。
  - 前日に gateway が1日中止まっていた場合は送らない（期限当日には送らない）。
- 却下した案：celery に鍵を足す（:498 の方針に反する）／送信済みを DB 列に持つ（migration が要り、毎回全部流し直す仕組みで事故が出たばかり #4562。Redis の前例で足りる）／フロントの i18n に文面を置く（自動送信の文と二重になる）。

### 10-4 便
- 便1：①②（viewer_bot_texts.py に定数と関数、ViewerReissueResponse に message、GET 申込のお願いの文を返す口、管理画面に「申込のお願いをコピー」と作り直し結果の「案内文をコピー」）
- 便2：④（viewer_room_notice.py、_change と CLI run の commit 後に送信、応答の room_notice、管理画面の送れなかったとき表示）
- 便3：③（gateway の1時間ループと送信関数）
- migration・deploy.yml・本番 scripts は どの便も触らない。

### 10-5 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| K1 ①のコピーで、目印付き申込 URL（`?openExternalBrowser=1#signup`）入りの文がコピーされる | vitest（コピー内容）＋ pytest（文を返す口） |
| K2 ②の作り直しで、その人の LINE名・コード・JST の期限・目印付き招待が入った文が返る。招待が無いときは招待の行が無い | pytest |
| K3 延長・本登録・停止の後に、その人の部屋へ1回だけ送る。部屋が無い人には送らない。送れなくても操作は成功し room_notice=failed | pytest（discord_api_request をモック、前例 backend/tests/test_viewer_signup.py:142-146） |
| K4 ③は期限の JST 前日の 10:00 以降に1回だけ送る。前日以外・trial 以外・部屋なしには送らない。延長後は新しい期限で再び送る。Redis が無ければ送らない | pytest（前例 backend/tests/test_viewer_share_flag_monitor.py） |
| K5 本番：①をコピーして LINE に貼り、スマホで開くと外部ブラウザで申込画面が開く | PO 目視 |
| K6 本番：②の目印付き招待を LINE から開くと Discord の招待画面まで進める | PO 目視（だめなら招待の目印を外す） |
| K7 本番：③が初めて送られた日に、その部屋に1通だけ届く | gateway ログの送信件数（本文なし）＋ PO 目視 |

### 10-6 リスクと対処
- 誤った部屋へ送る：送り先は本人の discord_channel_id だけ。メンションは無効（allowed_mentions）。
- 二重送信：③は Redis キー、④は操作1回につき1回。
- Discord の招待に目印を付けると開けない可能性（K6 未確認）：だめなら external_browser_url を招待に使わない1行の変更で戻す。
- 送信失敗で管理操作が止まる：commit 後に送り、例外は外へ出さない。

### 10-7 外部事例
- LINE 公式の openExternalBrowser 仕様のみ使う（上記 10-1）。成功事例の数値は使わない（該当事例は不要：既存の仕組みの組み合わせで、新しい技術選択が無いため）。

### 10-8 維持
- 文面の直しは viewer_bot_texts.py の1か所。テストが差し込み項目と目印を確かめる。

### 10-9 戻し方
- 便ごとに PR を Revert。DB は変えない。Redis キーは TTL で消える。

### 10-10 設計審査（2026-10-20、architect・Opus。同一 AI による審査）と決定
- 判定：APPROVE（10-1 の file:line はすべて実物一致、SSOT・ADR-027・ADR-144/067・ADR-1019・本書 :498 と矛盾なし）。
- 審査で出た未決を次のとおり決める：
  - a. 4つの入口（activate/suspend/unsuspend/extend、super_admin_viewers.py:176-212）の response_model は今 ViewerAdminItem で、room_notice が落ちる。→ ViewerAdminItem を継承し `room_notice: Literal["sent","failed","no_room"] | None` と `room_notice_text: str | None` を足した ViewerStatusChangeResponse に替える。一覧と PATCH は ViewerAdminItem のまま。K3 は入口経由で確かめる。
  - b. unsuspend は送らず room_notice=None。「部屋に送れませんでした…」の案内は画面の文言なので ja/en 同一キー（ADR-027）。i18n にしないのは「お客様に送る文」だけ。
  - c. CLI run の結果 JSON（viewer_admin_cli.py:29-35）にも room_notice を足す。既存 CLI テスト（backend/tests/test_super_admin_viewers.py:458-471）は discord_api_request をモックする。
  - d. ③の重複防止キーは「期限の JST の日付」：`viewer_interview_notice:{id}:{YYYY-MM-DD}`。同じ日付への延長で二重に送らない。
  - e. ③も便2の send_room_notice（REST）で送る。discord.py の channel.send と二重の送信経路にしない（gateway は DISCORD_BOT_TOKEN を持つ docker-compose.yml:362）。
  - f. ①の文を返す口：`GET /api/super-admin/viewers/signup-request`（require_super_admin、応答 {text}）。ルーター冒頭の API 一覧（super_admin_viewers.py:5-13）に追記。②の LINE名は commit 後に _get_item で取る。正確なパス接頭辞は実物の router prefix に合わせる。
  - g. SIGNUP_URL は本番 URL を固定で書く（開発環境でも本番 URL がコピーされることを受け入れる。前例 ROOM_WELCOME の URL 直書き viewer_bot_texts.py:31）。
- ③の送る時刻「前日の JST 10:00 以降」は Opus の既定。PO に伝え、変えたいときは定数1つ（INTERVIEW_NOTICE_HOUR_JST）を直す。

### 10-11 便2 実装メモ（2026-10-20）
- 実物と設計の差：CLI の実体は backend/app/viewer_admin_cli.py（services 配下ではない）。管理画面に停止ボタンは無い（段6）ので、画面で「部屋に送れませんでした」の案内が出るのは activate・extend の応答のとき。suspend・unsuspend は API と CLI だけ。
- 送る処理は viewer_room_notice.py の send_room_notice のほか、文面選びと結果の決定を `notify_status_change(action, item)`（戻り (room_notice, text)）にまとめ、Web（_change）と CLI（run）の両方が同じ関数を commit 後に呼ぶ。unsuspend は (None, None)。
- DISCORD_BOT_TOKEN が無い環境では Discord を呼ばず False（= failed）。
- 延長の {until_date} は change_status が返す item の trial_expires_at（延長後）を format_jst_date で書く。取り直しは不要だった。
- テスト：送信は viewer_room_notice.send_room_notice をモック（PG の入口試験・CLI 試験）。送信関数そのものは discord_api_request をモックして JSON の形を確かめる。openapi.json は ViewerStatusChangeResponse と4口の応答だけを反映（手元の pydantic 2.13.0 は CI の 2.10.6 と出力が違うため、他の差分は取り込まない）。

### 10-12 便3 実装メモ（2026-10-20）
- 置き場所は sweep と同じ backend/app/discord_gateway/viewer_interview_notice.py。DB は sweep と同じく `self._db_factory()`（AsyncSessionLocal）で public.viewer_accounts を直読み（テナント文脈・RLS なし）。
- send_room_notice は async なので to_thread は使わず直接 await。Redis は gateway が init_redis 済みの非同期クライアント（app.cache.get_redis()）を使う（share_flag_monitor は同期 redis だが gateway では非同期が前例）。
- `run_once(db_factory, redis_client, now_utc)`：テストでモックを差せるよう引数で受ける。client.py の `_viewer_interview_loop` が1時間ごとに呼ぶ。Redis が None なら 0 件。
- 重複防止キーは 10-10 d のとおり `viewer_interview_notice:{id}:{期限の JST 日付}`、TTL 30日、送れたときだけ置く。

## 段11（2026-10-20）閲覧者向け文面のテンプレートページ（一覧・確認・コピー・編集）

### 11-0 PO の依頼と決定（原文）
- 「ヘッダーにテンプレートボタンを設置してテンプレートページが開くように出来る？テンプレートページにテンプレート一覧がテーブルで表示されて行をクリックするとスライドページが開き内容が確認できてコピーや編集も出来る」
- 置き場所：Opus が「①閲覧者管理の画面の上に置く【おすすめ】②受信箱の今のテンプレートボタンの先 ③両方」を示し、PO「1」。
- 守ること（PO 原文の要旨）：配線と DB の SSOT を守りデータを分散させない／デザイントークンとデザインシステムを守り金型にない直書きをしない／推測で進めない。

### 11-1 現状（調べた事実。生の引用 /tmp/CC報告ファイル/viewer_templates/tpl_page/recon.md・recon2.md、origin/main 386727908 以降）
- 文面の正本は今 backend/app/discord_gateway/viewer_bot_texts.py の定数（段10 10-3「文面は全部 viewer_bot_texts.py に置く」design.md:838）。画面で編集する手段は無い。
- 「テンプレート」ボタンは受信箱にある（frontend/src/pages/inbox/InboxPage.tsx:81-91、`navigate("/templates")`）。先の /templates は仮ページ（App.tsx:281-289 ComingSoonPage、ja.json templates.description「メール・メッセージテンプレート管理」）で全社員向け。→ PO「1」により使わない（お客様とのやり取り用に空けておく）。
- 閲覧者管理：ViewerAccountsPage.tsx。PageLayout の headerAction（:371-384、Button secondary sm が2つ）、super admin ガード（:90、:272-284）、DataTable onRowClick→Drawer（:410-416、:421-511、footer に保存 :425-438）、保存の結果はインライン表示（:453-462）、コピー（:187-195）。
- 金型：PageLayout（headerAction :8・navKey は nav.* :27）、DataTable（:38-68、onRowClick :100）、Drawer（:22-32、default 480px / wide）、Textarea（:62-71、rows・maxLength を素通し、文字数表示なし）、Button。新しい金型は作らない（docs/CC_UI_GOVERNANCE.md:9-15）。
- API の前例：super_admin_viewers.py（prefix なし・main.py:650 で /api/v1、require_super_admin dependencies.py:516-518、User.id INTEGER models.py:25）。更新者の列の前例 `updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL`（migrations/20260608_080000_add_carrier_credentials.sql:21）。updated_at の trigger 前例 migrations/20261018_100000_create_product_packagings.sql:52-60。
- migration：形式 migrations/YYYYMMDD_HHMMSS_*.sql、scripts/run_all_migrations.sh 末尾に登録、public の全体共通表の手本 add_viewer_accounts.sql（RLS なし :2、GRANT salesanchor_app :107-113）。ai_ro のビューは自動で作り直し（run_all_migrations.sh:99-127）。
- 初期データ：migration は構造だけ（ADR-1007:31-36、ADR-155:25-32）。前例は「表は migration、1行は専用 CLI」（design.md:277-281 D6、backend/app/viewer_discord_cli.py：stdin の JSON だけを受ける・`python -m app.viewer_discord_cli`）。
- 文面を使う箇所（recon2 §7）：gateway の viewer_trial.py:206（ROOM_RECREATED）・:381（ROOM_WELCOME）、viewer_interview_notice.py:80、viewer_discord_cli.py:114（RECEPTION_MESSAGE）、backend の super_admin_viewers.py:142-143（申込のお願い）・:258（作り直し）、services/viewer_room_notice.py:44-57（④）。今は sync 関数（DB 無し）から返している。
- Discord の1通の上限 2000 文字に対する定数は viewer 側に無い。前例 discord_notifier.py:37 `_MAX_MESSAGE_CHARS = 1800`。

### 11-2 対象にする文面（9件）と対象外
| 鍵 | 画面の名前 | 送り方 | いつ | 差し込み項目 |
|---|---|---|---|---|
| signup_request | 申込のお願い | 手で送る | 申込の前 | {signup_url}（固定値・自動で入る） |
| reissue_notice | 申込コードの作り直し | 手で送る | 作り直したとき | {line_name} {code} {expires} {invite_url} |
| reissue_notice_no_invite | 申込コードの作り直し（招待なし） | 手で送る | 招待が作れなかったとき | {line_name} {code} {expires} |
| room_welcome | 部屋のはじめの案内 | 自動 | 申込コードを入れて部屋ができたとき | {email} {password} |
| room_recreated | 部屋の作り直しの案内 | 自動 | 部屋を作り直したとき | {email} |
| notice_extended | 延長のお知らせ | 自動 | 延長したとき | {until_date} |
| notice_activated | 本登録のお知らせ | 自動 | 本登録にしたとき | なし |
| notice_suspended | 停止のお知らせ | 自動 | 停止したとき | なし |
| interview_request | 面談のお願い | 自動 | 期限の前日 10:00 以降 | {expires_date} |
- 対象外（今のまま viewer_bot_texts.py）：受付のボタン付きメッセージ RECEPTION_MESSAGE（直しても貼ってある投稿は変わらず、貼り直しが要るため）、ボタン名・小窓の題・エラーの返事（WRONG_SERVER など）・YOUR_ROOM・ROOM_TOPIC（システムの部品で、お客様に送る案内文ではないため）。
- 9件の名前・送り方・いつ・差し込み項目の意味は画面の言葉なので i18n（ja/en 同一キー）。文面の本文は i18n に入れない。

### 11-3 作り方（選んだ案と理由）
- **正本を DB の1か所へ移す**：新しい表 `public.viewer_message_templates`（key TEXT PRIMARY KEY、body TEXT NOT NULL、updated_at TIMESTAMPTZ NOT NULL DEFAULT now()、updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL、CHECK (char_length(body) BETWEEN 1 AND 1800)）。RLS なし・GRANT は add_viewer_accounts.sql と同じ。全体共通（テナント別ではない。閲覧者は全体で1つの仕組みのため）。
- **コードに残すのは「台帳」だけ**：新しい backend/app/services/viewer_message_templates.py に9件の鍵と、それぞれの差し込み項目の集合（文面は持たない）。読み出し `async get_body(session, key) -> str | None`、差し込み `render(key, body, **values)`、検査 `validate(key, body)`。
- **編集の検査**（保存の前に API で必ず行う）：①差し込み項目の集合が台帳と完全に同じ（足りない・余計・書式指定や `!r` 付きは 422）②空は 422 ③1800 文字を超えたら 422（前例 discord_notifier.py:37。差し込み後に 2000 を超えないための余裕）④`{` `}` の対応が崩れていたら 422（string.Formatter で解析できない）⑤画面で開いた時の updated_at と違えば 409（2人が同時に直したときの上書き防止）。
- **送る側**：9件を使う全箇所を「DB から読んで差し込む」に替える。行が無い・読めないときは送らず（自動は警告ログ、コピーの API は 503 で「テンプレートが見つかりません」）。コードの文面へ戻る道は作らない（正本を2か所にしないため）。
- **初期値の入れ方**：migration は表だけ。専用 CLI `python -m app.viewer_template_cli`（stdin の JSON {action:"seed"} だけを受ける。前例 viewer_discord_cli.py）が、viewer_bot_texts.py の今の9つの定数を読み、無い行だけ INSERT する（ある行は触らない）。本番で1回だけ Opus が実行（PO 委任・GO 記録）。便2 で定数と seed を消す。
- **画面**：
  - 閲覧者管理の headerAction（ViewerAccountsPage.tsx:371-384）に Button secondary sm「テンプレート」を足し、`/super-admin/viewer-templates` へ。サイドバーには足さない（前例：非掲載ページ recon2 §3）。
  - 新しいページ frontend/src/pages/super-admin/ViewerTemplatesPage.tsx：PageLayout（navKey nav.superAdminViewerTemplates、headerAction に「閲覧者管理へ戻る」）、super admin ガードは ViewerAccountsPage と同じ形、DataTable 4列（名前・送り方・いつ・最終更新）。
  - 行クリックで Drawer（default 幅）：名前・送り方・いつ・差し込み項目の説明（i18n）・本文（便1 は読むだけ、便2 で Textarea 編集）・「コピー」（copy_text を写す）・便2 で footer に保存。保存の結果は ViewerAccountsPage と同じインライン表示。
  - copy_text：固定値の差し込み（{signup_url} だけ）を API が入れた文。人ごとの項目（{line_name} など）は {…} のまま写る（人ごとの完成文は今までどおり閲覧者管理の各ボタンで写す）。
  - 色・寸法の直書きなし。新しい部品なし。
- **却下した案**：コードの定数を残して DB を上書き用にする（正本が2か所になる）／migration で初期値を入れる（ADR-1007 に反する）／受信箱の /templates に作る（PO「1」）／履歴表を作る（今回の依頼に無い。updated_at と更新者だけ残す）。

### 11-4 便
- 便1：表（migration）・台帳・seed CLI・一覧 GET（`GET /api/v1/super-admin/viewer-templates`、body・copy_text・updated_at・更新者の表示名）・ページ（表＋スライド＋コピー、読むだけ）・ヘッダーのボタン。送る側は今のまま（定数）。→ 本番で seed を実行し、9行が今の定数と一字一句同じことを確かめる。
- 便2：編集（`PUT /api/v1/super-admin/viewer-templates/{key}`、11-3 の検査）・スライドの編集と保存・送る側9件を DB 読みに替える・viewer_bot_texts.py から9つの文面定数と seed を消す。
- 便1 と便2 の間だけ、DB の9行は定数の写しになる（画面は読むだけで、送る側は定数を使う）。便2 で定数を消して1か所に戻す。この間に画面から文面を変える手段は無いので、食い違いは起きない。

### 11-5 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| T1 閲覧者管理の上に「テンプレート」があり、押すと9行の表が開く。super admin 以外は開けない（API 403） | vitest・pytest、PO 目視（再読み込みしてから） |
| T2 行を押すとスライドが開き、本文・送り方・いつ・差し込み項目の説明が出て、「コピー」で copy_text が写る（申込のお願いは目印付き URL 入り） | vitest・pytest |
| T3 本番の seed 後、9行の本文が今の定数と一字一句同じ | CLI の結果（鍵ごとの一致○×、本文は出さない） |
| T4 編集：保存すると DB の本文が変わり更新者・時刻が残る。差し込み項目の不足/余計・空・1801文字・括弧の崩れは 422、古い画面からの保存は 409 | pytest |
| T5 編集した文が、そのまま自動のお知らせ・コピーに使われる | pytest（送る側全9件が DB の本文を使う） |
| T6 行が無いときは送らない（自動は警告ログ、コピーは 503） | pytest |
| T7 便2 の後、viewer_bot_texts.py に9つの文面定数が無い | `git grep` 0件 |
| T8 本番：PO が1件を直し、閲覧者管理のコピーに直した文が出る | PO 目視 |

### 11-6 リスクと対処
- 部屋のはじめの案内（ログイン情報）が送れなくなる：便2 の deploy 前に T3 を必ず○にする。便2 のテストで9件全部の読み出しを確かめる。
- 編集で差し込み項目を消して、ログイン情報が届かない：T4 の検査で保存させない。
- 誤ってお客様に崩れた文が届く：括弧の検査と 1800 文字の上限。
- 同時編集の上書き：409。

### 11-7 外部事例
- 該当事例は不要（既存の部品・前例の組み合わせで、新しい技術選択が無いため）。

### 11-8 維持
- 文面の直しは画面（正本は DB の1か所）。鍵と差し込み項目を増やすときだけコード（台帳）を直す。台帳と表の9行が揃っているかは T3/T5 のテストで見る。

### 11-9 戻し方
- 便2 を Revert すると送る側は定数に戻る（その時点で画面の直しは送る側に効かなくなる。表は残す）。便1 を Revert しても表は残る（migration は構造だけで、表の削除はしない）。

### 11-10 審査 REVISE（review_design.md、基準 origin/main 38613d7d7）への対応（11-1〜11-9 より優先）
基準は 38613d7d7 に更新（386727908 からの差は #4576 のみで 11-1 に反映済み）。

**B-1 本番の初期値の入れ方（11-3「初期値の入れ方」を置き換え）**
- CLI `python -m app.viewer_template_cli` は stdin の JSON `{"action":"seed","dry_run":true|false}` と `{"action":"verify"}` だけを受ける。seed は viewer_bot_texts.py の今の9定数を読み、`INSERT ... ON CONFLICT (key) DO NOTHING`。dry_run=true は入れる予定の鍵だけ返し書かない。verify は鍵ごとに「行がある／本文が定数と一字一句同じ」を○×で返す（本文は出さない）。
- 本番の実行者は Opus（Sonnet には無制限鍵を使わせない）。根拠は本セッションの PO 原文「GO記録やSSHへの無制限鍵へのアクセス等、必要な権限は全て必要な場合は使用して良い許可を与える。PRマージ、デプロイまで完走させてくれ。」（Q12=n の「毎回 PO 本人の GO」に対し、PO が本セッションで明示した個別の許可）。手順は dry_run → seed → verify。GO 原文・時刻・結果（鍵ごとの○×）を docs/handoff/gas-viewer-fresh-fast/ の段11 記録に残す。
- 便2 で seed は消す（定数が無くなるため）。空の環境は B-4 の画面から入れる。テストはテスト内で行を入れる。

**B-2 「送らない」の判定は後戻りできない処理の前（11-3「送る側」に追記）**
review_design.md B-2 の文案をそのまま採用：部屋のはじめの案内は申込コードの照合より前に読み、無ければ TRY_LATER（申込コードは使用済みにせず部屋も作らない）／部屋の作り直しは部屋を作る前に読み、無ければ TRY_LATER／申込コードの作り直しは reissue_signup_code の前に読み、無ければ 503 で何も変えない／延長・本登録・停止は状態の変更と同じトランザクションで commit 前に読んで文を作り、無くても状態は変え、お知らせは送らない（commit 後に DB を読まない）／面談のお願いは run_once の最初に1回読み、無ければ警告ログ1回・0件・Redis キーを作らない／申込のお願いは db を受け、無ければ 503。

**B-3 作り直し案内の書き出し**
- reissue_notice・reissue_notice_no_invite は、本文が `{line_name}さん、` で始まらなければ 422（画面に理由を出す i18n キー superAdmin.viewerTemplates.errorLineNamePrefix）。差し込み後、名前が空なら今と同じく頭の「さん、」を外す。理由：今の動きを変えず、名前が空の人にも崩れた文を出さないため。代わりの言葉を持つ案は、台帳に文面を持つことになり正本が2か所になるので採らない。

**B-4 行が無い環境（11-3 PUT・11-4 便2 に追記）**
- 一覧 GET は台帳の9件を必ず返し、行が無い鍵は body=null・「未登録」。PUT は `expected_updated_at: null` かつ行が無いとき INSERT（ある時は 409）。行がある時は `UPDATE ... SET body, updated_by_user_id, updated_at=now() WHERE key=:k AND updated_at=:expected` で更新件数0なら 409（比べるのは SQL、N-2）。updated_at は SQL の now() で入れ、trigger は付けない（N-1）。

**B-5 お知らせが送れなかったことを画面に出す**
- 延長・本登録・停止でテンプレートが無い・検査に通らないときは `room_notice: "no_template"`、`room_notice_text: null`（ViewerStatusChangeResponse の Literal に追加、openapi.json 再生成）。閲覧者管理は新キー superAdmin.viewers.roomNoticeNoTemplate「テンプレートが見つからないため、部屋に送れませんでした。テンプレートの画面で文を確かめてください」（ja/en）を出す。

**Non-blocking の採用**
- N-1：`REFERENCES public.users(id) ON DELETE SET NULL`、`GRANT SELECT, INSERT, UPDATE ON public.viewer_message_templates TO salesanchor_app;`（SEQUENCE の GRANT なし）。PG テストの準備に新 migration を足す。
- N-3：自動で送る直前に差し込み後の長さを数え、2000 を超えたら送らず警告ログ（no_template と同じ扱い）。コピーの API は文をそのまま返す（LINE で使うため）。画面は Textarea の helperText に「n / 1800」（Array.from で数える、ViewerAccountsPage.tsx:147-151 の前例）。
- N-4：検査は field_name を `.` `[` で切らず文字列のまま台帳の集合と比べる／`list(Formatter().parse(body))` を try の中で回し切る／format_spec・conversion が空でなければ 422／`{{` `}}` は文字として許す／送るときも同じ検査を通し、失敗は「行が無い」と同じ扱いで例外を外へ出さない。
- N-5：触るテスト（review_design.md ③の4ファイルの行と db_factory の順番）、openapi.json の再生成、新ページの vitest、i18n の追加キー（nav.superAdminViewerTemplates、superAdmin.viewerTemplates.*、errorLineNamePrefix、roomNoticeNoTemplate）をカードに列挙する。
- N-6：更新者の表示は users.full_name、空なら username。
- N-7：段11 を docs/handoff/gas-viewer-fresh-fast/design.md に追記してコミット（recon も同フォルダへ）。10-3（:838）に「段11 便2 で DB へ移した」と注記。便2 で viewer_bot_texts.py の冒頭説明を直し、残すもの（SIGNUP_URL、format_jst_date、format_jst_datetime、external_browser_url、RECEPTION_MESSAGE ほか 11-2 の対象外）を明記。
- N-8：T7 の検索式 `git grep -n -E "^(SIGNUP_REQUEST|REISSUE_NOTICE|REISSUE_NOTICE_NO_INVITE|ROOM_WELCOME|ROOM_RECREATED|NOTICE_EXTENDED|NOTICE_ACTIVATED|NOTICE_SUSPENDED|INTERVIEW_REQUEST) =" origin/main -- backend/app` が0件。T9 新設：行が無いとき ①申込コードを入れても使用済みにならず部屋も作られない ②作り直しで申込コードが変わらない ③延長の応答が room_notice="no_template" で状態は変わる（pytest）。T8 は手で送る「申込のお願い」1件だけを直し、確かめた後に元の文へ戻す。
- 未確認4（gateway の起動し直し）：便2 の本番確認で discord-gateway コンテナの起動時刻が deploy 後であることを観測項目 T10 にする（便1 は gateway のコードを変えないので不要）。
