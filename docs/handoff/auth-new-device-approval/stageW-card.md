# 段W 実装カード（いつもの機械のホーム画面のアプリへ、許可依頼の通知を出す・第3版）

- 対象: docs/handoff/auth-new-device-approval/design.md 第6.1版 §3 D13・§4 段W・§6（K2 の web push の部分・「相談係 AI の見え方」の PR-W 後 1057 行）・§7 の戻し方。ADR-1055。合格の基準は kgi.md の K2（PO 承認済 2026-11-01）。
- 中身の正本: 何をどう作るかは design.md §4 段W の文のとおり。このカードは「順番・形の細部・先に確かめること・止まる条件・受入」を足す。design.md とこのカードが食い違うときは止まって Opus へ返す（自分で選ばない。§0 の V で直したものはカードが正）。
- 根拠の写し: S=origin/main d97928fa7bd91639b3880f882c46babff22ee548（段A 前半・後半が入った後）。事実の生の出力は docs/handoff/auth-new-device-approval/stageW-recon-raw.md・stageW-recon2-raw.md（同じ S で読んだ）。
- 前提: このカードは設計書だけの PR で本線に入れてから流す。手順1 の後に origin/main に docs/handoff/auth-new-device-approval/stageW-card.md が無ければ、停止して BLOCKED: で返す。
- 読んだ節: 段A カード（docs/handoff/auth-new-device-approval/stageA-card.md）と同じ。実行役はクラウドの Sonnet。作業場所の作り方はクラウドの決まり（S scripts/agent-hooks/cloud/rules.md:15）を正とする。PR は設計担当（Opus）が手元で作る。出力には上限を付ける。待つために sleep を使わない。
- 状態: 第3版（Opus 作成）。第1版の審査 REVISE（重大1・要修正4・軽微9）と第2版の審査 REVISE（重大1・要修正1・軽微7）を全部直した。
- 受領確認: 実装役は着手の最初の報告に「段W カード 第3版 前半（または後半）を受け取った・S=d97928fa7」と書く。

## 0. 設計からの直し（V）
- V-1 2回に分けて流す。同じ枝 release/new-device-approval-stage-w-impl に積む（release/new-device-approval-stage-w は設計書の PR の枝なので使わない）。PR は後半の push の後に1つだけ作る。
  - 前半: migration・試験の表定義・ai_cloud の分類・守りの登録・docker-compose・backend 全部・pytest。
  - 後半: frontend 全部・Vitest・API の形（openapi.json）。
- V-2 依存: backend/requirements.txt は直接使う部品だけを固定する書き方（S :1-54。最後は :54 maxminddb==3.2.0）。pywebpush==2.5.0 を説明の1行と一緒に足すだけにし、pywebpush が引き込む部品（py-vapid・http-ece・aiohttp・requests・cryptography）は固定しない。入れた後に pip check が壊れを出さないことと、入った版を報告に書く（§3(j)）。
- V-3 本番は AUTH_DEVICE_APPROVAL=off のまま（段B で enforce）。off では知らない機械の依頼が作られないので、段W の本番反映の後も送信は起きない。POST の購読は「いつもの機械のログイン中だけ」なので、本番で購読できるのはいつもの機械が登録された後になる。本番の送信の確かめ（last_success_at）は段B の後の段C に回す。段W の本番の受入は §5 W7〜W10 にする。
- V-4 試験の表定義: design.md の「試験の表定義4か所」は、段W では次の3か所。backend/tests/conftest.py の2か所（:328-333 の public の名前を外す置き換え・:1363〜 の SQLite 版）と、.github/workflows/migration-test.yml の「変更 SQL の前提の移行を先に実行」の段（S :1289-1297 の段A の段と同じ形で1つ足す・#8b。新しい migration は user_trusted_devices を外部キーで指すので、前提の表が無いと CI で落ちる）。backend/tests/rls_bootstrap.py は段A と同じ理由（design.md A-1）で直さない。
- V-5 送り先の守り（設計の補い・Opus 判断）: サーバーが利用者の渡した URL へ送るので、endpoint は次だけを受ける。https であること・ホスト名が IP の数字でないこと・ホスト名が次のどれかと同じか、その下の名前であること: fcm.googleapis.com・android.googleapis.com・push.services.mozilla.com・push.apple.com・notify.windows.com。長さは endpoint 2048 文字以下・p256dh 200 文字以下・auth 100 文字以下（base64url の文字だけ）。ホスト名の照合は、小文字にした host について host == d or host.endswith("." + d)。さらに次も全部満たすこと（URL の読み方の違いで送り先をすり替えられないため）: endpoint に \・@・空白・制御文字（0x00-0x20 と 0x7f）が無い。urllib.parse.urlsplit(endpoint) の username と password が None。port が None か 443。urllib3.util.parse_url(endpoint).host を小文字にした値が urlsplit の hostname と同じ。外れたら 422 invalid_push_subscription。ホスト名の一覧の出どころは公開の実装例1件（hackutd/harp PR #153）で各社の公式文書では未確認なので、外れた要求は logger.warning にホスト名だけを書く（URL 全体と鍵は書かない）。
- V-6 1台の機械に購読は1つ: POST で同じ trusted_device_id の他の購読（revoked_at が NULL）の revoked_at に :now を入れてから upsert する。1つの依頼で同じ機械に何度も鳴らさないため。
- V-6b 他人の購読の付け替えを防ぐ: upsert は ON CONFLICT (endpoint) DO UPDATE ... WHERE user_push_subscriptions.user_id = EXCLUDED.user_id とし、RETURNING id が返らない（他人がすでに持つ endpoint）ときは、先に取り消した同じ機械の購読を戻すため await db.rollback() をしてから 409 push_subscription_conflict にする。
- V-6c 日時: SQL の中で now() を使わず、段A の devices.py と同じく Python の現在時刻を :now で渡す。
- V-6d sw.js のキャッシュ: frontend/nginx.conf:39-43 は .js に1年の不変キャッシュを付ける。sw.js だけは毎回確かめさせるため、:17-20 の location = /index.html と同じ形で location = /sw.js { add_header Cache-Control "no-cache, must-revalidate"; try_files $uri =404; } を足す（#21b。完全一致の location は正規表現の location より先に選ばれる）。W10 で本番の Cache-Control と中身を確かめる。
- V-7 送信の名乗り: VAPID の subject は https://app.salesanchor.jp/（mailto にしない。メールの宛先を外へ出さないため）。
- V-8 部品の使い方（公式の元コードで確かめた・2026-11-02）:
  - pywebpush 2.5.0 の webpush(subscription_info, data=None, vapid_private_key=None, vapid_claims=None, content_encoding="aes128gcm", curl=False, timeout=None, ttl=0, verbose=False, headers=None, requests_session=None)。返事の番号が 202 より大きいと WebPushException を出し、.response に requests の返事が入る。vapid_claims の dict に aud と exp を書き足す（呼び出し側の dict が変わる）ので、送るたびに新しい dict {"sub": subject} を渡す。
  - py_vapid の Vapid.from_string は、base64url で読んで 32 バイトなら生の秘密の数（from_raw）、それ以外は DER として読む。秘密の鍵は「32 バイトの生の数の base64url」で置く（§4b）。
  - 実物の形が違えば §3(k) で止まる。

## 1. 触るファイル（変更前→変更後）
| # | ファイル | 変更前（S） | 変更後 | 回 |
|---|---|---|---|---|
| 1 | 新 migrations/20261102_090000_add_user_push_subscriptions.sql | 無い | public.user_push_subscriptions を作る: id BIGSERIAL PRIMARY KEY / user_id BIGINT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE / trusted_device_id BIGINT NOT NULL REFERENCES public.user_trusted_devices(id) ON DELETE CASCADE / endpoint TEXT NOT NULL UNIQUE / p256dh TEXT NOT NULL / auth TEXT NOT NULL / created_at TIMESTAMPTZ NOT NULL DEFAULT now() / last_success_at TIMESTAMPTZ / failed_count SMALLINT NOT NULL DEFAULT 0 / revoked_at TIMESTAMPTZ。索引は user_id と trusted_device_id に1つずつ。全列と表に COMMENT。GRANT は migrations/20261101_130000_add_new_device_approval.sql :126-131 と同じ書き方（salesanchor_app があるときだけ）。冪等（IF NOT EXISTS）。RLS は付けない（design.md A-1 と同じ理由）。型は段A の表と同じ BIGINT（S migrations/20261101_130000_add_new_device_approval.sql:7-8） | 前半 |
| 2 | scripts/run_all_migrations.sh | :1209 が最後の登録（20261101_130000） | :1209 の後に #1 を run_sql で1行足す（同じ書き方の説明の行を1行付ける） | 前半 |
| 3 | .github/workflows/migration-guard.yml | :224 PUBLIC_TABLES の末尾が user_recovery_codes | 末尾に user_push_subscriptions | 前半 |
| 4 | migrations/20261024_100300_create_ai_cloud_views.sql | :3 が 1054 行・:285 user_recovery_codes の行 | :285 の前に ('public','user_push_subscriptions',ARRAY['auth','endpoint','p256dh'],'mask','') を1行足す・:3 を 1057 行に | 前半 |
| 5 | docs/handoff/cloud-case-ai/stage1-column-class.tsv | 1055 行（見出しは schema_pattern・table・column・class・reason・data_type の6列） | public<TAB>user_push_subscriptions<TAB><列><TAB>mask<TAB><TAB>text の形で auth・endpoint・p256dh の3行を、名前の並び順の位置に足して 1058 行 | 前半 |
| 6 | scripts/migration-guard/reference-allowlist.tsv | :7 の sha256 | #4 を直した後の sha256。4列目の末尾に「 / ADR-1055 design §4 段W（3行追加）」を足す | 前半 |
| 7 | backend/tests/ops/test_ai_cloud_views.py | :30-38 の定数・:480 の == n0 == 1054・:569-627 段A の分類の試験 | :480 を == n0 == 1057。:37 の後に _WEB_PUSH_SQL = "20261102_090000_add_user_push_subscriptions.sql" を足す。:569-627 と同じ形の試験を1つ足す。流す順は bootstrap → _AUTH_EVENTS_SQL → _SELF_AUTH_SQL → _CREATE_SQL →（3列に column_class の行があることを確かめる）→ _DEVICE_APPROVAL_SQL → _WEB_PUSH_SQL を2回（冪等）→ user_push_subscriptions の分類の漏れが0 | 前半 |
| 8 | backend/tests/conftest.py | :328-333・:1363〜 | :333 の後に public.user_push_subscriptions の置き換えを同じ形で足す。SQLite 版の段A の3表の後に、段A の SQLite の表と同じく REFERENCES を付けずに CREATE TABLE IF NOT EXISTS user_push_subscriptions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, trusted_device_id INTEGER NOT NULL, endpoint TEXT NOT NULL UNIQUE, p256dh TEXT NOT NULL, auth TEXT NOT NULL, created_at TIMESTAMP NOT NULL, last_success_at TIMESTAMP, failed_count INTEGER NOT NULL DEFAULT 0, revoked_at TIMESTAMP) を足す（列は #1 の migration と同じ10列。型は段A の SQLite の表の書き方に合わせる） | 前半 |
| 8b | .github/workflows/migration-test.yml | :1289-1297 段A の前提の段 | :1297 の後に同じ形の段を1つ足す。条件 contains(steps.detect.outputs.changed_sql, 'migrations/20261102_090000_add_user_push_subscriptions.sql')。流すのは migrations/001_create_auth_events.sql → migrations/20261013_160000_add_self_hosted_auth_tables.sql → migrations/20261101_130000_add_new_device_approval.sql の順（psql の書き方は :1289-1297 と同じ）。段A の段は 20261101_130000 が変わったときだけなので、段W の PR では両方は動かない | 前半 |
| 9 | 新 backend/app/services/web_push.py | 無い | 下の「#9 の中身」 | 前半 |
| 10 | backend/app/routers/auth.py | :336-347 _notify_new_request・:432 その呼び出し | 下の「#10 の中身」 | 前半 |
| 11 | backend/app/realtime/topics.py | :111-117 段A の行 | ("POST", "/api/v1/auth/push-subscriptions") と ("DELETE", "/api/v1/auth/push-subscriptions/{subscription_id}") を理由「通知の購読は本人の画面の応答で差し替える（ADR-1055 段W）」で足す。GET は足さない | 前半 |
| 12 | backend/requirements.txt | :54 maxminddb==3.2.0 | 説明の1行と pywebpush==2.5.0 | 前半 |
| 13 | docker-compose.yml | backend の environment :148-153（AUTH_DEVICE_* と GEOIP_DB_PATH） | :153 の後に説明の1行と WEBPUSH_VAPID_PRIVATE_KEY=${WEBPUSH_VAPID_PRIVATE_KEY:-}・WEBPUSH_VAPID_PUBLIC_KEY=${WEBPUSH_VAPID_PUBLIC_KEY:-}・WEBPUSH_VAPID_SUBJECT=${WEBPUSH_VAPID_SUBJECT:-} の3行。celery には足さない（送るのは backend だけ） | 前半 |
| 14 | 新 backend/tests/test_web_push.py | 無い | 下の「#14 の中身」 | 前半 |
| 15 | backend/tests/test_viewer_isolation.py | — | 閲覧者のトークンで GET /api/v1/auth/push-public-key が 401 になることが、既存の「認証ありの口」の試験で拾われるか確かめる。拾われなければ同じ形で1件足す（§3(e)） | 前半 |
| 16 | .github/workflows/deploy.yml | :326 -e '/^CASE_ADMIN_TOKEN=/d'・:380 CASE_ADMIN_TOKEN='${{ secrets.CASE_ADMIN_TOKEN }}' | :326 の後に -e '/^WEBPUSH_VAPID_PRIVATE_KEY=/d'・PUBLIC_KEY・SUBJECT の3行。:380 の後に WEBPUSH_VAPID_PRIVATE_KEY='${{ secrets.WEBPUSH_VAPID_PRIVATE_KEY }}' の形で3行 | 前半 |
| 17 | 新 frontend/src/lib/webPush.ts（試験は作らない。ブラウザの仕組みだけを呼ぶ薄い部品のため。動きは W11 で見る） | 無い | 下の「#17 の中身」 | 後半 |
| 18 | 新 frontend/src/pages/account-settings/PushNotifySection.tsx と PushNotifySection.test.tsx（試験は2つ: public_key が null なら何も描かない・文字列なら切り替えが1つ出る） | 無い | 下の「#18 の中身」 | 後半 |
| 19 | frontend/src/pages/account-settings/SecuritySection.tsx | :365 {isSelfAuth() && <DevicesSection />} | :365 の前に {isSelfAuth() && <PushNotifySection />} | 後半 |
| 19b | frontend/src/pages/account-settings/SecuritySection.test.tsx | :46 GET は全部 {items: []}・:97 節が4つ・:107 Firebase で1つ | 直さない。PushNotifySection は public_key が文字列でないとき（null・undefined・読み込み中・失敗）に null を返し、.account-settings-section を出さないので :97 と :107 はそのまま通る。通らなければ停止する（数を書き換えない） | 後半 |
| 20 | 新 frontend/public/sw.js | 無い | 下の「#20 の中身」 | 後半 |
| 21 | 新 frontend/public/manifest.webmanifest | 無い | {"name":"Sales Anchor","short_name":"Sales Anchor","start_url":"/","scope":"/","display":"standalone","icons":[{"src":"/apple-touch-icon.png","sizes":"180x180","type":"image/png"}]}。sizes は frontend/public/apple-touch-icon.png の実物の大きさに合わせる（§3(h)） | 後半 |
| 21b | frontend/nginx.conf | :17-20 location = /index.html の no-cache・:39-43 .js は1年の不変キャッシュ | :20 の後に location = /sw.js { add_header Cache-Control "no-cache, must-revalidate"; try_files $uri =404; } を足す（V-6d） | 後半 |
| 22 | frontend/index.html | :6 apple-touch-icon の link | :6 の後に <link rel="manifest" href="/manifest.webmanifest" /> | 後半 |
| 23 | frontend/src/locales/ja.json・en.json | accountSettings.devices（:3326-3339 付近） | accountSettings.push.title・description・toggleLabel・iosHint・unsupported・notTrusted・denied・error を両方に同じキーで足す。iosHint の ja には「ホーム画面に追加したら、最初に一度だけ許可が要ることがあります」の文を入れる | 後半 |
| 24 | frontend/api-contract/openapi.json | — | backend の口を足した後に書き出す。schema.d.ts は入れない | 後半 |

### #9 の中身（backend/app/services/web_push.py）
- 環境変数は呼び出し時に os.getenv で読む（devices.py:5 と同じ理由）。値をログに出さない。
- is_configured() -> bool: WEBPUSH_VAPID_PRIVATE_KEY・WEBPUSH_VAPID_PUBLIC_KEY・WEBPUSH_VAPID_SUBJECT の3つが空でないとき True。
- public_key() -> str | None: 設定済みなら公開鍵、未設定なら None。
- validate_subscription(endpoint, p256dh, auth) -> None: V-5 の検査。外れたら HTTPException(422, "invalid_push_subscription")。
- class PushTarget(NamedTuple): id, endpoint, p256dh, auth。
- async list_targets(db, user_id) -> list[PushTarget]: user_push_subscriptions の revoked_at IS NULL の行で、結び付いた user_trusted_devices の revoked_at IS NULL の行だけ（JOIN）。生 SQL。
- async deliver(targets, payload: dict) -> list[tuple[int, str]]: 1件ずつ asyncio.to_thread で pywebpush.webpush(subscription_info={"endpoint":..., "keys":{"p256dh":..., "auth":...}}, data=json.dumps(payload, ensure_ascii=False), vapid_private_key=秘密の鍵, vapid_claims={"sub": subject}（送るたびに新しい dict）, ttl=1800, headers={"Urgency": "high"}, timeout=10) を呼ぶ。結果は (id, "ok"|"gone"|"failed")。WebPushException で .response の status_code が 404 か 410 なら "gone"、それ以外の例外は "failed"（logger.warning に id と番号だけ）。1件の失敗で残りを止めない。
- async record_results(db, results) -> None: ok は last_success_at=:now・failed_count=0、gone は revoked_at=:now、failed は failed_count=failed_count+1（SMALLINT を超えないよう LEAST(failed_count+1, 32767)）。commit する。
- async send_login_request_push(targets, *, when, device, location) -> None: payload は {"title": "新しい機械からのログインの許可依頼 / New sign-in request", "body": f"{when} / {device} / {location}"（location が空なら最後の「 / 」と location を付けない）, "url": "/"}。番号（match_number）は入れない。deliver の後に async with AsyncSessionLocal() as db: で record_results を呼ぶ（backend/app/routers/meta.py:184 と同じ開き方）。どこで例外が起きても外へ出さない（logger.exception）。

### #10 の中身（backend/app/routers/auth.py）
- auth.py は S の時点で logging を使っていないので、import の並びに import logging を、import の後に logger = logging.getLogger(__name__) を足す。
- _notify_new_request に db: AsyncSession を足す。publish_user_change とメールは今のまま。その後の通知の部分（list_targets から add_task まで）は try/except Exception で囲み、例外は logger.exception に残して外へ出さない（:431 の commit の後なので、ここで落ちると依頼の 202 が 500 になるため）。囲みの中で、web_push.is_configured() が True なら targets = await web_push.list_targets(db, user_id) を読み、targets が空でなければ background_tasks.add_task(send_login_request_push, targets, when=devices.jst_text(), device=new.label, location=new.location) を足す。:432 の呼び出しに db を渡す。send_login_request_push は from app.services.web_push import send_login_request_push の形で読む（試験で app.routers.auth.send_login_request_push を差し替えるため）。
- 新しい口3つ（S auth.py:1618 の device_list・:1650 の device_revoke の後に置く）:
  - POST /auth/push-subscriptions: _require_app_origin(request)・session: CurrentSession = Depends(get_current_session)。体は {endpoint: str, keys: {p256dh: str, auth: str}}（pydantic のモデル。Field の説明付き）。session.trusted_device_id が None なら 403 not_trusted_device。web_push.is_configured() が False なら 409 push_not_configured。validate_subscription。V-6 のとおり同じ機械の他の購読を取り消し、INSERT ... ON CONFLICT (endpoint) DO UPDATE SET user_id, trusted_device_id, p256dh, auth, revoked_at=NULL, failed_count=0 RETURNING id。commit。返事は 200 {id}。
  - DELETE /auth/push-subscriptions/{subscription_id}（status_code=204）: _require_app_origin(request)・get_current_session。本人（session.user.id）の行だけ revoked_at に :now を入れる。すでに取り消し済みの本人の行は、revoked_at を変えずに 204。行が無い・他人の行なら 404。device_revoke（S auth.py:1650-1651）と同じ形。
  - GET /auth/push-public-key: get_current_user。返事は {public_key: str | null}。
- 段A の機械の取り消し（device_revoke）は今のまま。取り消された機械の購読は list_targets の JOIN で送らない（行は残る）。

### #14 の中身（backend/tests/test_web_push.py）
段A の試験の部品（backend/tests/test_new_device_approval.py の base_env・enforce・no_redis_and_spies などの fixture と、ログインや機械を作る手助けの関数）を import して使う。import できない形なら、同じ働きの fixture をこのファイルに書く（test_new_device_approval.py の中身は変えない）。test_web_push.py に autouse の fixture を1つ置き、各試験の前と後に DELETE FROM user_push_subscriptions を流す（段A の cleanup（test_new_device_approval.py:151-158）はこの表を消さないため。段A の cleanup を使うときは、それより先にこの表を消す順にする）。VAPID の3つは monkeypatch.setenv で試験用の値を入れる（実際の鍵は使わない。pywebpush.webpush は差し替える）。 VAPID を設定してログインの口を通す試験は、全部 app.routers.auth.send_login_request_push を差し替える（本物は AsyncSessionLocal を開き、試験の client fixture（conftest.py:1863）は get_db しか差し替えないため）。W-t3 は口を通さず、db_session を渡して deliver・record_results を直接呼ぶ。
- W-t1 依頼1件で send_login_request_push が1回呼ばれ、targets が購読の数と同じ（購読2つの機械2台）。app.routers.auth.send_login_request_push を差し替えて確かめる。
- W-t2 VAPID が未設定なら send_login_request_push は呼ばれず、依頼（202）とメールはいつもどおり。
- W-t2b VAPID を設定し web_push.list_targets を例外にしても、依頼は 202 で返り、メールは1回呼ばれる。
- W-t3 deliver で webpush を 410 の WebPushException にすると record_results の後に revoked_at が入る。404 も同じ。500 なら failed_count が1増え revoked_at は NULL。成功なら last_success_at が入り failed_count が0。
- W-t4 機械を取り消した後（DELETE /auth/devices/{id}）は、その機械の購読が list_targets に出ない。
- W-t5 送るたびに vapid_claims が新しい dict（2件送って、渡された dict が別のもの）。payload に match_number が無い。
- W-t6 POST: いつもの機械のログインで 200 と id。sid はあるが trusted_device_id の無いログインは 403 not_trusted_device。出どころ違いは 403 forbidden_origin。http の endpoint・知らないホスト・IP の数字のホスト・長すぎる値は 422。同じ endpoint を2回送ると行は1つ。同じ機械で別の endpoint を送ると古い方の revoked_at が入る。別の人がすでに持つ endpoint を送ると 409 push_subscription_conflict で、その行の user_id は変わらず、送った人の機械の既存の購読も取り消されていない。次の endpoint は全部 422: https://127.0.0.1:6379\@fcm.googleapis.com/x・https://u:p@fcm.googleapis.com/x・https://fcm.googleapis.com:8443/x・空白を含むもの。
- W-t7 DELETE: 本人の id で 204、取り消し済みの本人の id でも 204、他人の id で 404（他人の行は変わらない）、出どころ違いは 403。
- W-t8 GET push-public-key: ログイン中は設定した公開鍵、未設定は null、トークン無しは 401。

### #17 の中身（frontend/src/lib/webPush.ts）
- pushSupport(): "supported" | "ios_needs_home_screen" | "unsupported"。serviceWorker・PushManager・Notification が window にあれば supported。無くて、iPhone・iPad の Safari で、ホーム画面のアプリでない（window.matchMedia("(display-mode: standalone)").matches が false かつ navigator.standalone が true でない）なら ios_needs_home_screen。それ以外は unsupported。
- urlBase64ToUint8Array(base64url): applicationServerKey 用。
- subscribeThisDevice(publicKey) / currentSubscription() / unsubscribeThisDevice(): navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }) の後に pushManager を使う（updateViaCache "none" は MDN のとおり、本体と import に HTTP のキャッシュを使わない。frontend/nginx.conf:39-42 の .js の1年キャッシュを避けるため）。subscribe は userVisibleOnly: true と applicationServerKey。

### #18 の中身（PushNotifySection.tsx）
- GET /auth/push-public-key と GET /auth/devices（is_current を見る）を api で読む。public_key が文字列でない（null・undefined・読み込み中・失敗）なら null を返し、要素を1つも描かない（#19b）。
- 見出し・説明は SecuritySection.tsx の他の節と同じ account-settings-section・account-settings-section-title・Stack を使う。切り替えは金型 frontend/src/components/Toggle.tsx（checked・onCheckedChange・disabled・aria-labelledby）。生の input・色の直値・金型に無い部品を使わない。文字は全部 t()。
- 出し分け: pushSupport が ios_needs_home_screen なら iosHint、unsupported なら unsupported の文を出し、切り替えは出さない。今の機械が is_current のいつもの機械でなければ notTrusted の文、Notification.permission が denied なら denied の文を出し、切り替えは disabled。
- 入れる: 切り替えを押した処理の最初の await を Notification.requestPermission() にする（iPhone は本人の操作の直後でないと許可の確認を出さないため。その前に別の await を挟まない）。Notification.requestPermission() が granted のときだけ subscribeThisDevice → POST /auth/push-subscriptions（subscription.toJSON() の endpoint と keys）→ 返った id を持つ。断られたら denied を出す。失敗したら error を出して切り替えを戻す。
- 切る: DELETE /auth/push-subscriptions/{id} → unsubscribeThisDevice。DELETE が 404 でも unsubscribeThisDevice は行う。
- 開いたとき: GET /auth/devices でこの機械の is_current が真、かつ Notification.permission が granted、かつ currentSubscription() があるときだけ、POST をもう一度送り（同じ endpoint は upsert）、返った id を持って切り替えを入にする。
- Vitest: public_key が null で何も出ない・ios_needs_home_screen で iosHint と切り替え無し・いつもの機械でないと notTrusted と disabled・denied で denied・supported でいつもの機械なら切り替えが押せる、の5つ。

### #20 の中身（frontend/public/sw.js）
```js
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data ? event.data.json() : {}; } catch { data = {}; }
  event.waitUntil(self.registration.showNotification(data.title || "Sales Anchor", {
    body: data.body || "", icon: "/apple-touch-icon.png", tag: "login-request", data: { url: "/" },
  }));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
    for (const c of list) { if ("focus" in c) return c.focus(); }
    return self.clients.openWindow("/");
  }));
});
```
fetch の処理は書かない（キャッシュをしない＝今の配信の動きを変えない）。

## 2. 触らない範囲
- design.md §5 の全部（ただし frontend/nginx.conf は #21b の1か所だけ足す。design.md §5 は nginx を直さないとしていたが、S :39-43 の .js の1年の不変キャッシュが sw.js に掛かると更新が届かないため、第1版の審査を受けて Opus が補う）。
- tests/prod-check と AUTH_DEVICE_APPROVAL の値（段B）。
- backend/tests/test_new_device_approval.py の中身・backend/tests/rls_bootstrap.py・migration-test.yml の #8b 以外の所・frontend/nginx.conf の #21b 以外の所。
- 既存の migration の中身（#4 の1行の追加と :3 の数だけは例外）。
- 本番 DB・本番の .env・GitHub の秘密。クラウドでは本番に繋がない。VAPID の鍵を作らない・書かない（§4b で Opus が作る）。

## 3. 実装役が先に確かめること（想定分岐つき）
- (a) 行の合わせ直し: §1 の「変更前（S）」の行を作業場所で sed -n か grep で1つずつ読む。中身が同じで行だけ動いたものは報告に書いて進む。中身が違えば停止して BLOCKED:。段A の migration の :7-8 が id BIGSERIAL・user_id BIGINT であることを確かめる（違えば #1 の FK の型をそれに合わせて報告する）。
- (b) 名前の重なり: S の migrations と backend に user_push_subscriptions・push-subscriptions・web_push の語が無いことを grep で確かめる。有れば停止する。
- (c) 呼び出し元: _notify_new_request の呼び出しが auth.py:432 の1か所だけであること。他にあれば停止する。send_new_device_mail の :419（初めてのログイン）と :1181（パスキー）は通知の対象にしない（直さない）。
- (d) get_current_session の形: backend/app/auth/dependencies.py の CurrentSession が user・sid・trusted_device_id・family_created_at を持つこと（S :711-719）。違えば停止する。
- (e) 閲覧者の隔離: backend/tests/test_viewer_isolation.py が新しい GET の口を「閲覧者のトークンで 401」として拾うか、試験を流して確かめる。拾わない作りなら #15 で1件足す。新しい POST・DELETE が「認証なしの口」の表に要ると試験が言うなら、停止する（認証ありの口なので表に足さない）。
- (f) 話題の表の試験: backend/tests/test_realtime_topics.py が新しい POST・DELETE を NO_SIGNAL_ROUTES に求め、GET を求めないこと。違う結果なら停止する。
- (g) migration の登録検査: bash scripts/check-migration-registration-exists.sh と scripts/check-migration-value-writes.py と scripts/lint_tenant_schema.py の strict が通ること（commit の後に check-before-submit がまとめて流す）。通らなければ出力を付けて停止する。
- (h) 画像の大きさ: python3.12 -c で frontend/public/apple-touch-icon.png の幅と高さを読む（PNG の先頭 24 バイトの IHDR）。#21 の sizes をその値にする。
- (i) PostgreSQL: 段A カード §3(i) と同じ（立てられなければ SQLite の試験だけ流し「PG の試験は CI で確かめる」と書く）。
- (j) 依存: pip install -r backend/requirements.txt が通り、pip check が「No broken requirements found.」を出すこと。pywebpush・py-vapid・http-ece・aiohttp・requests・cryptography の入った版を pip show で報告に書く。入らない・壊れが出るなら停止する。
- (k) 部品の形: python3.12 -c "import inspect, pywebpush; print(inspect.signature(pywebpush.webpush))" と "import py_vapid, inspect; print(inspect.signature(py_vapid.Vapid.from_string))" の出力が V-8 と同じこと。違えば停止する。
- (l) Toggle の形: frontend/src/components/Toggle.tsx の props が checked・onCheckedChange・disabled・id・aria-label・aria-labelledby であること。違えば停止する。
- (m) deploy.yml の行: :326 と :380 の行が §1 #16 のとおりで、:385 の検査の正規表現 ^[A-Z0-9_]+='[^']*'$ に新しい3行が合うこと。違えば停止する。

## 4. 実装役の手順（1手順1命令。<W> は手順1 で作られた作業場所の絶対パス）

### 4-1. 前半
手順1. 作業場所を作る。
  cd "$(git rev-parse --show-toplevel)" && git fetch origin main
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/new-device-approval-stage-w-impl
  cd <W> && git rev-parse HEAD origin/main
  cd <W> && test -f docs/handoff/auth-new-device-approval/stageW-card.md && echo card-ok
  （2行が同じで card-ok が出ることを確かめ、sha を報告に書く。違えば停止して BLOCKED:）
手順2. design.md の段W とこのカードを読み、§3 の (a)〜(d)(k)(m) を確かめる。
  cd <W> && sed -n 160,175p docs/handoff/auth-new-device-approval/design.md
  cd <W> && grep -rn "user_push_subscriptions\|push-subscriptions\|web_push" migrations backend | head -20
  cd <W> && grep -n "_notify_new_request" backend/app/routers/auth.py
手順3. 依存を入れる（python3.12 -m venv で作った環境で）。
  cd <W>/backend && python3.12 -m venv /tmp/stW-venv
  cd <W>/backend && /tmp/stW-venv/bin/pip install -r requirements.txt > /tmp/stageW-pip.txt 2>&1
  cd <W>/backend && tail -5 /tmp/stageW-pip.txt
  cd <W>/backend && /tmp/stW-venv/bin/pip check
  cd <W>/backend && /tmp/stW-venv/bin/pip show pywebpush py-vapid http-ece aiohttp requests cryptography | grep -E "^(Name|Version)"
手順4. §1 の #1〜#8 を作る。#6 の sha256 は #4 を直した後に計算する。
  cd <W> && sha256sum migrations/20261024_100300_create_ai_cloud_views.sql
  （sha256sum が無ければ shasum -a 256。）
  cd <W> && wc -l docs/handoff/cloud-case-ai/stage1-column-class.tsv
  （1058 行でなければ停止する。）
手順5. §1 の #9〜#16 を作る。
手順6. backend の試験を流す（出力は /tmp に置く）。
  cd <W>/backend && ENVIRONMENT=test /tmp/stW-venv/bin/python -m pytest tests/test_web_push.py tests/test_new_device_approval.py tests/test_viewer_isolation.py tests/test_realtime_topics.py -q > /tmp/stageW-pytest-1.txt 2>&1
  cd <W>/backend && tail -30 /tmp/stageW-pytest-1.txt
  cd <W>/backend && ENVIRONMENT=test /tmp/stW-venv/bin/python -m pytest tests -q --ignore=tests/sandbox > /tmp/stageW-pytest-all.txt 2>&1
  cd <W>/backend && tail -30 /tmp/stageW-pytest-all.txt
  （本便と関係ない理由で落ちるものは、名前と最後の行を報告に書く。）
手順7. 変わったファイルを確かめる。
  cd <W> && git status --short | head -80
手順8. §1 の前半のファイルを名前で add して commit する。
  cd <W> && git add migrations/20261102_090000_add_user_push_subscriptions.sql migrations/20261024_100300_create_ai_cloud_views.sql scripts/run_all_migrations.sh scripts/migration-guard/reference-allowlist.tsv
  cd <W> && git add .github/workflows/migration-guard.yml .github/workflows/migration-test.yml .github/workflows/deploy.yml docs/handoff/cloud-case-ai/stage1-column-class.tsv docker-compose.yml backend/requirements.txt
  cd <W> && git add backend/app/services/web_push.py backend/app/routers/auth.py backend/app/realtime/topics.py
  cd <W> && git add backend/tests/test_web_push.py backend/tests/ops/test_ai_cloud_views.py backend/tests/conftest.py
  （#15 を足したときだけ git add backend/tests/test_viewer_isolation.py。）
  cd <W> && git status --short | head -80
  （§1 に無いファイルが入っていれば git restore --staged で外す。.claude-pipeline/active-work.d/ は add しない。）
  cd <W> && git commit -m "feat: いつもの機械へ許可依頼の通知を送る仕組み（段W前半・鍵が無ければ送らない）"
手順9. 提出前の入口を流してから push する（--no-verify は使わない）。
  cd <W> && git log -3 --oneline
  cd <W> && bash scripts/dev/check-before-submit.sh > /tmp/stageW-cbs-1.txt 2>&1
  cd <W> && tail -25 /tmp/stageW-cbs-1.txt
  cd <W> && git push -u origin release/new-device-approval-stage-w-impl
手順10. 報告を返す。PR は作らない。1つの発言は600文字以内、最後を DONE: か BLOCKED: で始める。

### 4-2. 後半（前半の push の後に、別の回で流す）
手順11. 作業場所を作り、push 済みの枝の先頭に合わせる。
  cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/new-device-approval-stage-w-impl
  cd <W> && git fetch origin release/new-device-approval-stage-w-impl
  cd <W> && git switch -C release/new-device-approval-stage-w-impl origin/release/new-device-approval-stage-w-impl
  cd <W> && git rev-parse HEAD origin/release/new-device-approval-stage-w-impl
  （2行が同じことを確かめる。reset・rebase・force・merge・pull は使わない。）
手順12. §3 の (h)(l) を確かめ、frontend の依存を入れる。
  cd <W>/frontend && npm ci > /tmp/stageW-npm.txt 2>&1
  cd <W>/frontend && tail -5 /tmp/stageW-npm.txt
手順13. §1 の #17〜#23 を作る。金型だけを使う（docs/CC_UI_GOVERNANCE.md）。文字は全部 t()。
手順14. API の形を書き出す。
  cd <W>/backend && python3.12 -m venv /tmp/stW-venv
  cd <W>/backend && /tmp/stW-venv/bin/pip install -r requirements.txt > /tmp/stageW-pip2.txt 2>&1
  cd <W>/backend && ENVIRONMENT=test /tmp/stW-venv/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json
  cd <W>/frontend && npm run generate:api-types
手順15. frontend の検査と試験を流す。
  cd <W>/frontend && npx tsc --noEmit > /tmp/stageW-tsc.txt 2>&1
  cd <W>/frontend && tail -20 /tmp/stageW-tsc.txt
  cd <W>/frontend && npm run lint > /tmp/stageW-lint.txt 2>&1
  cd <W>/frontend && tail -20 /tmp/stageW-lint.txt
  cd <W>/frontend && npm run check:i18n-missing-keys > /tmp/stageW-i18n.txt 2>&1
  cd <W>/frontend && tail -10 /tmp/stageW-i18n.txt
  cd <W>/frontend && npm run test:unit > /tmp/stageW-vitest.txt 2>&1
  cd <W>/frontend && tail -30 /tmp/stageW-vitest.txt
  cd <W>/frontend && npx vitest run src/pages/account-settings > /tmp/stageW-vitest-sec.txt 2>&1
  cd <W>/frontend && tail -20 /tmp/stageW-vitest-sec.txt
  cd <W>/frontend && npm run check:all > /tmp/stageW-checkall.txt 2>&1
  cd <W>/frontend && tail -30 /tmp/stageW-checkall.txt
手順16. 変わったファイルを確かめる。
  cd <W> && git status --short | head -80
手順17. §1 の後半のファイルを名前で add して commit する。
  cd <W> && git add frontend/src/lib/webPush.ts frontend/src/pages/account-settings/PushNotifySection.tsx frontend/src/pages/account-settings/PushNotifySection.test.tsx frontend/src/pages/account-settings/SecuritySection.tsx
  cd <W> && git add frontend/public/sw.js frontend/public/manifest.webmanifest frontend/index.html frontend/src/locales/ja.json frontend/src/locales/en.json frontend/api-contract/openapi.json frontend/nginx.conf
  （試験のファイルは実物の名前で同じく add する。）
  cd <W> && git status --short | head -80
  cd <W> && git commit -m "feat: アカウント設定に「この機械に通知を出す」を足す（段W後半）"
手順18. 提出前の入口を流してから push する。
  cd <W> && git log -3 --oneline
  cd <W> && bash scripts/dev/check-before-submit.sh > /tmp/stageW-cbs-2.txt 2>&1
  cd <W> && tail -25 /tmp/stageW-cbs-2.txt
  cd <W> && git push -u origin release/new-device-approval-stage-w-impl
手順19. 報告を返す（手順10 と同じ形）。PR は作らない。

## 4b. GO と承認・Opus の操作
- PO の承認: K2（2026-11-01）・D13 を含む設計第6版の審査 APPROVE・PO の依頼「PRマージ、デプロイまで完走させてくれ」（2026-11-01）。段W の作業指示書の作成は PO「1」（2026-11-02）。
- #1・#2・#4・#13・#16 は危険パス（migrations・本番 scripts・docker-compose・deploy.yml）→ ADR-136 の委任 GO（POの委任に基づくClaude Opus発行）。新しく起動した opus の審査役の APPROVE の後に、PR 本文へ GO記録を書いてからマージする。
- VAPID の鍵（Opus が手元で・マージの前に）: python3.12 の cryptography で P-256 の鍵を1組作り、秘密は 32 バイトの生の数の base64url（= を付けない）、公開は 65 バイトの非圧縮の点の base64url にする。py_vapid.Vapid.from_string で秘密を読めることを確かめてから、gh secret set WEBPUSH_VAPID_PRIVATE_KEY・WEBPUSH_VAPID_PUBLIC_KEY に標準入力で流す（値は画面・ファイル・記録に出さない。作った後は手元に残さない）。WEBPUSH_VAPID_SUBJECT も #16 の3行目が秘密の値から書くので、gh secret set WEBPUSH_VAPID_SUBJECT に https://app.salesanchor.jp/ を標準入力で流す（秘密ではないが置き場を1つにそろえる）。gh secret list で名前が3つあることだけを確かめる。
- PO が操作することはない（本番での通知の目視は段C で PO に頼む）。

## 5. 受入（○×）
| # | 基準 | 検証方法 |
|---|---|---|
| W1 | #14 の W-t1〜W-t8 が全部ある・緑 | CI の pytest・手順6 の tail |
| W2 | 段A の試験（test_new_device_approval.py）がそのまま緑 | CI の pytest |
| W3 | #18 の Vitest 5つが緑・i18n の検査が緑 | CI・手順15 の tail |
| W4 | CI の必須の点検が全部緑 | gh pr checks（設計担当） |
| W5 | 変わったファイルが §1 の行の範囲だけ（試験のファイルを含む） | gh pr diff --name-only（設計担当） |
| W6 | 金型の外の部品・色の直値・t() を通らない文字が無い | 審査役の確かめと check:all |
| W7 | 本番反映後、backend の入れ物に WEBPUSH の名前が3つある（値は出さない） | docker compose exec -T backend printenv | cut -d= -f1 | grep WEBPUSH（設計担当） |
| W8 | 本番反映後、public.user_push_subscriptions ができ、10 列がある | reader 鍵で to_regclass と information_schema.columns（設計担当） |
| W9 | 本番反映後、ai_cloud_meta.column_class が 1057 行・build_log の最新行が ok | reader 鍵（設計担当） |
| W10 | 本番反映後、GET https://api.salesanchor.jp/api/v1/auth/push-public-key がトークン無しで 401、https://app.salesanchor.jp/sw.js と /manifest.webmanifest が 200、sw.js の Cache-Control が no-cache, must-revalidate、取ってきた sw.js の sha256 がマージ後の frontend/public/sw.js と同じ | curl の番号だけ（設計担当） |
| W11（段C） | 段B の後、PO の機械で「通知を許可」を押してもらい、知らない機械の依頼で通知が出る・last_success_at が依頼から60秒以内 | PO の目視と reader 鍵。済むまで K2 の web push の部分は「判定待ち」 |

## 6. 戻し方
- マージの commit を git revert する PR を1つ出す。表は追加だけなので残しても害は無い。
- 急ぐときは GitHub の秘密 WEBPUSH_VAPID_PRIVATE_KEY を空にして deploy を流せば、is_configured が False になり送らない（画面の切り替えも出なくなる）。
- 登録済みの service worker は fetch を持たないので、残っても配信の動きは変わらない。

## 停止と報告
- §3 で「停止」とした時、§2 の触らない範囲を変えないと進めない時、design.md とこのカードが食い違う時、試験が直せない時は、そこで停止する。
- 停止したら、何を実行し何が返ったかの生の出力（/tmp の報告ファイルの tail）を付けて、BLOCKED: か NEEDS_DECISION: で始まる報告を返す。推測で直さない。
- 終わったら DONE: で始まる報告に、§3 の確かめた結果（動いた行の一覧を含む）、手順6（後半は手順15）の tail、push した sha を書く。

END OF CARD
