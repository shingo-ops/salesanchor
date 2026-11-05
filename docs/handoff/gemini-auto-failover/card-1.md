# 実装カード 1 — gemini-auto-failover（道の自動切り替え・止まりの見張り・理由の記録）

親: docs/handoff/gemini-auto-failover/design.md（決定: docs/adr/ADR-1062-gemini-auto-route-failover.md）
この文書は何か: Sonnet が迷わず作れるよう、触る場所・中身・試験・触らない範囲を決めたカード。

状態: カード発行（Opus、2026-11-05）。根拠: design.md 第1版（PO 2026-11-05「1」）、recon.md。
担当: Sonnet（クラウド）。触ってよいのは下の「触るファイル」だけ。本番 DB・VPS・GitHub secret には触らない。DB の変更なし。.github/workflows・migrations・scripts は触らない。
読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md・guards/03-file.md・guards/05-pr.md（照合: 新規ファイルは丸ごと書く／commit と push の後は git log で確かめる／PR はクラウドで作らない／出力には上限を付ける）。

## 受領確認
着手前に、作業場所のブランチが release/gemini-auto-failover で、HEAD に docs/handoff/gemini-auto-failover/card-1.md があることを報告の1行目に書く。

## 実装前点検（結果を報告に書く。外れたら実装せず BLOCKED: で停止する）
- P1 `backend/app/services/gemini_extraction_svc.py` の _get_genai_client が :248 付近にあり、GEMINI_PROXY_URL を読んで HttpOptions の client_args と async_client_args に proxy を渡していること。
- P2 同じファイルの :429 付近と :517 付近に client.models.generate_content があり、:439 付近に recorder.record_error_detail があること。
- P3 `backend/app/services/gemini_raw_copy_v8.py` の :218〜:229 付近で _gem._get_genai_client() → client.models.generate_content → 失敗は RuntimeError（from exc）であること。
- P4 `backend/app/services/line_analysis_v102_svc.py` の :518 付近に recorder.record_error_detail({"raw": ..., "category": ...}) があること。
- P5 `backend/app/services/message_translator.py` の :358 付近の _call_gemini が google.generativeai（genai.configure・GenerativeModel・generate_content_async）を使っていること。
- P6 `backend/app/tasks/tcg_extraction_recovery.py` に _get_sync_engine（:50）と _get_redis（:457）があり、`backend/app/celery_app.py` の include に "app.tasks.tcg_extraction_recovery"（:38）、beat_schedule に recover-stale-extraction-jobs（:203）があること。
- P7 作業場所の Python で google.genai.errors.APIError と httpx.ConnectError・httpx.ConnectTimeout・httpx.ProxyError が import できること（python -c で確かめ、版を報告に書く）。

## 触るファイル

1. backend/app/services/gemini_route.py（新規）
2. `backend/app/services/gemini_extraction_svc.py`（_get_genai_client の中身、呼び出し2か所、記録1か所）
3. `backend/app/services/gemini_raw_copy_v8.py`（呼び出し1か所）
4. `backend/app/services/line_analysis_v102_svc.py`（記録1か所）
5. `backend/app/services/message_translator.py`（_call_gemini と古い部品の読み込み、sdk 名3か所、説明文の型名）
6. backend/app/tasks/gemini_route_watch.py（新規）
7. `backend/app/celery_app.py`（include に1行、beat_schedule に1件）
8. backend/tests/test_gemini_route.py（新規）
9. backend/tests/test_gemini_route_watch.py（新規）
10. `backend/tests/test_message_translator.py` と `backend/tests/test_message_translator_usage_ledger.py`（偽物の差し込み方だけを新しい部品に合わせる）
11. `backend/tests/test_tcg_gemini_extraction.py` と `backend/tests/test_api_error_auto_retry.py`（理由の記録の試験 T11・T12 を1つずつ足すだけ）

## 触らない範囲

- `backend/app/tasks/tcg_extraction_recovery.py` のすべて（送り直しの SQL は raw の末尾で引いている。raw の文を変えない）。
- `backend/app/services/gemini_extraction_svc.py` の _safe_error_message と _classify_error。
- `backend/app/services/tcg_work_comparison_svc.py` のすべて（対象外: design.md §3）。
- `backend/app/services/line_analysis_v102_svc.py` のその場の送り直し（:463〜:516）。
- backend/requirements.txt（google-generativeai の行は残す）。
- docker-compose.yml・.env・scripts・.github。
- 上の10番・11番以外の既存の試験ファイル。

## 1. gemini_route.py（新規・丸ごと書く）

モジュールの説明文: 「Gemini への道（直接 / prod2 の中継）を選ぶ正本。ADR-1062。道の選び方はここ1か所だけ。」

定数:
- ROUTE_DIRECT = "direct"、ROUTE_RELAY = "relay"
- DEFAULT_RELAY_URL = "http://gemini-egress:18888"（コメント: docker-compose.yml の gemini-egress。GEMINI_PROXY_URL が空のときの中継の先）
- STICKY_SECONDS = 600
- SWITCH_COUNT_PREFIX = "gemini_route:switch:"（後ろに "direct_to_relay" か "relay_to_direct"）
- SWITCH_COUNT_TTL_SECONDS = 24 * 60 * 60
- REASON_MAX_CHARS = 300
- _CHAIN_MAX_DEPTH = 5
- _LOCATION_REFUSAL_TEXT = "location is not supported"

状態: `_sticky: dict = {"route": None, "until": 0.0}`（プロセスの中だけ）。

関数（この名前と形で作る）:
- relay_url() -> str: GEMINI_PROXY_URL を strip した値、空なら DEFAULT_RELAY_URL。
- preferred_route() -> str: GEMINI_PROXY_URL を strip した値が空でなければ ROUTE_RELAY、空なら ROUTE_DIRECT。
- first_route() -> str: _sticky["route"] があり time.monotonic() が _sticky["until"] より前ならそれ、そうでなければ preferred_route()。
- other_route(route) -> str: 反対の道。
- remember(route) -> None: _sticky を route と time.monotonic() + STICKY_SECONDS にする。
- reset_state() -> None: _sticky を初期値に戻す（試験用。説明文にそう書く）。
- build_client(route): 今の `backend/app/services/gemini_extraction_svc.py:248-276` の中身をここへ移す。import の失敗と GEMINI_API_KEY 空の RuntimeError の文は一字一句そのまま。route が ROUTE_RELAY なら HttpOptions(client_args={"proxy": relay_url()}, async_client_args={"proxy": relay_url()}) を付け、ROUTE_DIRECT なら genai.Client(api_key=api_key) だけで作る（今の試験 `backend/tests/test_tcg_gemini_extraction.py:797-835` が assert_called_once_with(api_key=...) で見ている）。
- _exception_chain(exc) -> list: exc から始めて、`__cause__` があればそれ、無ければ `__context__` をたどる。_CHAIN_MAX_DEPTH 個まで。同じものが2回出たら止める。
- is_location_refusal(exc) -> bool: 連なりのどれかが google.genai.errors.APIError で、getattr(e, "code", None) == 400 で、str(getattr(e, "message", "") or e).lower() に _LOCATION_REFUSAL_TEXT を含む。
- is_route_unreachable(exc) -> bool: 連なりのどれかが httpx.ConnectError・httpx.ConnectTimeout・httpx.ProxyError、または aiohttp.ClientConnectorError（子の ClientProxyConnectionError を含む）のどれか。aiohttp はファイルの先頭で `try: import aiohttp` とし、読み込めなければ httpx の3つだけで判定する（google-genai は aiohttp が入っていると非同期の呼び出しに aiohttp を使う: google/genai/_api_client.py の _use_aiohttp。本番には discord.py 経由で入っている）。httpx.ReadTimeout・aiohttp.ServerTimeoutError など他は False。
- should_switch(exc) -> bool: 上の2つのどちらか。
- failure_reason(exc) -> str: 連なりの中で最初の APIError なら f"{e.code} {e.status}: {e.message}"。無ければ最初の httpx.TransportError で f"{type(e).__name__}: {e}"。それも無ければ f"{type(exc).__name__}: {exc}"。最後に、`key=` の後ろの空白・&・引用符・山括弧までを「key=(省略)」に、AIza で始まる英数字と - と _ の並び（10字以上）を「(APIキー省略)」に置き換え、REASON_MAX_CHARS 字で切る。
- _get_redis(): `backend/app/tasks/tcg_extraction_recovery.py:457-467` と同じ形を、このファイルに作る（import で使い回さない）。redis.from_url に socket_connect_timeout=1 と socket_timeout=1 を足す。
- _count_switch(from_route, to_route) -> None: Redis が None なら何もしない。キー SWITCH_COUNT_PREFIX + f"{from_route}_to_{to_route}" を incr し、expire を SWITCH_COUNT_TTL_SECONDS にする。全体を try/except Exception で包み、例外は logger.warning（型名だけ）。
- generate_content_routed(client, *, model, contents, config): 同期。route = first_route()。client.models.generate_content(model=model, contents=contents, config=config) を返す。例外のとき should_switch が False ならそのまま投げ直す。True なら to = other_route(route)、logger.warning("[gemini_route] 道を切り替えます: %s -> %s 理由=%s", route, to, failure_reason(exc)) を出し、build_client(to) で作った client で同じ呼び出しを1回だけする。成功したら remember(to) と _count_switch(route, to) をして返す。2回目の失敗はそのまま投げる（except の中で呼ぶので最初の例外は `__context__` に残る）。
- agenerate_content_routed(*, model, contents, config): 非同期。client = build_client(first_route()) を作り、await client.aio.models.generate_content(...) にする。切り替えの決まりは同期と同じ。_count_switch は await asyncio.to_thread(_count_switch, route, to) で呼ぶ。

import してよいもの: 標準ライブラリ、httpx、google.genai（関数の中で import してよい）、redis（_get_redis の中だけ）。app.services.gemini_extraction_svc は import しない（輪になるため）。

## 2. gemini_extraction_svc.py

- :248 の _get_genai_client の中身を `return gemini_route.build_client(gemini_route.first_route())` だけにする。説明文は「道は gemini_route が決める（ADR-1062）」に直す。関数の名前と引数なしの形は残す（多くの試験がこの名前を差し替えている）。
- :429 の `response = client.models.generate_content(model=..., contents=..., config=...)` を `response = gemini_route.generate_content_routed(client, model=..., contents=..., config=...)` にする。引数の中身は変えない。:420 の client の行は残す。
- :517 も同じ置き換え。:508 の client の行は残す。
- :439 を `recorder.record_error_detail({"raw": detail, "category": _classify_error(exc), "reason": gemini_route.failure_reason(exc)})` にする。
- import は `from app.services import gemini_route` を1行。

## 3. gemini_raw_copy_v8.py

- `from app.services import gemini_route` を1行足し、:221 の `client.models.generate_content(...)` を `gemini_route.generate_content_routed(client, model=..., contents=..., config=...)` にする（引数の中身は変えない）。:218 の client の行と :229 の RuntimeError は変えない。

## 4. line_analysis_v102_svc.py

- :518 を `recorder.record_error_detail({"raw": _safe_error_message(exc), "category": _classify_error(exc), "reason": gemini_route.failure_reason(exc)})` にする。import を1行足す。ほかは変えない。

## 5. message_translator.py

- _call_gemini（:358）の中身を次の形にする:
  - api_key = _ensure_api_key() は残す（鍵が無いときの LLMConfigError を変えないため。値は使わなくてよい。使わないなら `_ensure_api_key()` とだけ書く）。
  - `from google.genai import types as genai_types` を関数の中で import。
  - try の中で `response = await gemini_route.agenerate_content_routed(model=model_name, contents=prompt, config=genai_types.GenerateContentConfig(temperature=0.1))`。
  - except の中身（logger.exception と LLMParseError の文）は今のまま。
  - それより後（text_payload 以降）は今のまま。
- _GENAI_CACHE（:101）と _get_genai_module（:104-113）を消す。ほかに使う所が無いことを grep で確かめ、結果を報告に書く。
- :495・:517・:649 の sdk="google-generativeai" を sdk="google-genai" にする。
- :10-12 の説明文の既定の型名を、:49-50 の実際の既定（gemini-3.5-flash-lite）に合わせる。

## 6. gemini_route_watch.py（新規・丸ごと書く）

型は `backend/app/tasks/tcg_extraction_recovery.py` と同じ: _get_sync_engine（同じ形をこのファイルに作る）、sessionmaker、最後に engine.dispose、celery_app.task を try で包んで登録。

定数:
- STALL_WINDOW_MINUTES = 30
- STALL_REDIS_KEY = "gemini_route_watch:stalled"
- STALL_REDIS_TTL_SECONDS = 7 * 24 * 60 * 60
- SWITCH_NOTIFIED_PREFIX = "gemini_route_watch:switch_notified:"
- SWITCH_NOTIFIED_TTL_SECONDS = 24 * 60 * 60
- schema は `from app.services.tcg_extraction_record_svc import TCG_SCHEMA` を使う。

関数:
- find_stall(session, at=None) -> dict: at が None なら datetime.now(timezone.utc)。SQL（読むだけ）:
  - 直前30分（finished_at が at から STALL_WINDOW_MINUTES 分前より後、かつ at 以前）の extraction_attempts で、phase='completed' の数（completed）と phase='failed' の数（failed）。分は make_interval(mins => :window) で渡す。数字の直書きは禁止。
  - 同じ範囲の phase='failed' で finished_at が一番新しい1行の COALESCE(validation_result->>'reason', validation_result->>'raw', error_code)（last_reason）。
  - 返す: {"completed": n, "failed": n, "last_reason": 文字 か None, "stalled": completed == 0 and failed >= 1, "at": at}
- build_stall_message(info) -> str: 1行目「⚠️ 解析が30分成功していません（ADR-1062）」、「直前30分の失敗: N 回」、「最後の失敗の理由: 」＋last_reason（無ければ「不明」）、「判定の時刻: 」＋at を日本時間 YYYY-MM-DD HH:MM。
- build_recovered_message(info) -> str: 「✅ 解析が戻りました（ADR-1062）直前30分の成功: N 回」。
- build_switch_message(direction, count) -> str: direction が direct_to_relay なら「🔀 Gemini への道を自動で切り替えました: 直接 → prod2 の中継（24時間で N 回・ADR-1062）」、relay_to_direct なら「🔀 Gemini への道を自動で切り替えました: prod2 の中継 → 直接（24時間で N 回・ADR-1062）」。
- run_watch(session, redis_client, url) -> dict: 
  - info = find_stall(session)。
  - stalled で STALL_REDIS_KEY が無い → 止まりの文を送り、送れたら STALL_REDIS_KEY を TTL 付きで置く。
  - completed が1以上で STALL_REDIS_KEY がある → 戻りの文を送り、送れたら STALL_REDIS_KEY を消す（redis の delete）。
  - 2つの向き（direct_to_relay・relay_to_direct）ごとに、gemini_route.SWITCH_COUNT_PREFIX ＋向き の数を読み、1以上で SWITCH_NOTIFIED_PREFIX ＋向き が無ければ切り替えの文を送り、送れたら知らせ済みの印を TTL 付きで置く。
  - 送信は `backend/app/services/discord_notifier.py:45` の _post_discord_webhook を asyncio.run で呼ぶ。
  - 返す: {"stalled": bool, "stall_notified": bool, "recovered_notified": bool, "switch_notified": 送った向きの list}
- _run() -> dict: url は `backend/app/services/discord_notifier.py:40` の _get_webhook_url。空なら warning を1行出して {"skipped": "no_webhook"}。Redis は gemini_route._get_redis()。None なら warning を1行出して {"skipped": "no_redis"}。あれば engine と session を作り run_watch を呼ぶ。全体を try/except Exception で包み、例外は logger.exception にして {"error": 型名} を返す（定期作業を落とさない）。
- タスク: name="app.tasks.gemini_route_watch.watch_gemini_route"、time_limit=120、soft_time_limit=100。中身は return _run()。

## 7. celery_app.py

- include の `"app.tasks.tcg_extraction_recovery",` の行の後に `"app.tasks.gemini_route_watch",  # ADR-1062: 解析が30分成功しないときと道の切り替えの知らせ` を足す。
- beat_schedule の recover-stale-extraction-jobs の後に "watch-gemini-route": {"task": "app.tasks.gemini_route_watch.watch_gemini_route", "schedule": 300.0} を足す。コメントは「# ADR-1062: 解析の止まりと Gemini への道の切り替えを5分ごとに見て管理者用 Discord へ」。

## 8. 試験

backend/tests/test_gemini_route.py（新規）。各試験の前後で gemini_route.reset_state() を呼ぶ autouse の fixture を置く（他の試験に道の記憶を持ち越さないため）。APIError は google.genai.errors.APIError(400, {"error": {"code": 400, "status": "FAILED_PRECONDITION", "message": "User location is not supported for the API use."}}) のように実物の型で作る（作り方が合わなければ部品の中身を読んで合わせ、報告に書く）。
- T1: 直接が先（GEMINI_PROXY_URL なし）で、最初の client が場所の断りを投げる → build_client が ROUTE_RELAY で呼ばれ、2回目の結果が返る。その後 first_route() が ROUTE_RELAY。_count_switch が ("direct", "relay") で1回呼ばれる。
- T2: 中継が先（GEMINI_PROXY_URL あり）で、最初の client が httpx.ConnectError を投げる → build_client が ROUTE_DIRECT で呼ばれる。httpx.ProxyError と httpx.ConnectTimeout でも同じ（parametrize）。
- T3: agenerate_content_routed で T1 と同じ（client.aio.models.generate_content を AsyncMock にする）。
- T4: 切り替えない場合: APIError 400 で文が別（"API key not valid"）、APIError 429、APIError 503、httpx.ReadTimeout、ValueError → build_client が呼ばれず、同じ例外がそのまま出る。
- T5: failure_reason: 場所の断りを RuntimeError で包んだ（from exc）もので「400 FAILED_PRECONDITION: User location is not supported for the API use.」を返す。文に key=abc と AIza で始まる20字を入れた例外で、どちらも伏せられる。400字の文は300字に切れる。
- T6: 実物の google.genai.Client を、proxy に http://127.0.0.1:9 を渡して作り、generate_content を1回呼ぶ（鍵は "dummy"）。出た例外で is_route_unreachable が True になる。出た例外の型の連なりを報告に書く。もし False なら、実装を推測で直さずに停止して NEEDS_DECISION: で型の連なりを返す。
- T6b: T6 と同じ Client で、非同期の client.aio.models.generate_content を1回呼ぶ（pytest の非同期試験）。出た例外で is_route_unreachable が True になる。型の連なりと、aiohttp が読み込めたかを報告に書く。もし False、または 127.0.0.1:9 に行かずに外へ出ようとした跡（例外の文に generativelanguage.googleapis.com への接続の失敗だけが出る等）があれば、推測で直さずに停止して NEEDS_DECISION: で返す。
- T7: 切り替え先も失敗したら2回目の例外が出て、`__context__` が1回目の例外。build_client は1回だけ。first_route() は変わらない。
- T8: 道の記憶: remember 後、time.monotonic を STICKY_SECONDS 先に進めると preferred_route() に戻る。
- T10: 対象のファイル（gemini_extraction_svc.py・gemini_raw_copy_v8.py・message_translator.py）の本文に「client.models.generate_content(」と「generate_content_async」が無いことを、ファイルを読んで確かめる（道の選び方を1か所に保つ見張り）。

backend/tests/test_gemini_route_watch.py（新規）。session と redis は偽物、送信は差し替える。
- T9a: find_stall の SQL が make_interval と :window を持ち、params の window が 30。completed 0・failed 3 で stalled が True。completed 1・failed 3 で False。completed 0・failed 0 で False。
- T9b: run_watch: stalled で印なし → 1回送り印を置く。印あり → 送らない。送信が False → 印を置かない。
- T9c: run_watch: completed 1 で印あり → 戻りの文を1回送り印を消す。印なし → 送らない。
- T9d: 切り替えの数が direct_to_relay 2 で知らせ済みなし → 1回送り印を置く。知らせ済みあり → 送らない。
- T9e: _run が webhook 空・Redis None で送らずに skipped を返す。find_stall が例外でも例外を外に出さない。
- T9f: celery_app.conf.beat_schedule["watch-gemini-route"] の task 名と 300.0。
- T9g: build_stall_message が last_reason None で「不明」を出し、時刻が日本時間になる。

理由の記録の試験（既存の試験ファイルに1つずつ足す。既存の検査は変えない）:
- T11: `backend/tests/test_tcg_gemini_extraction.py` に、:695 と同じ形（_get_genai_client を差し替え・recorder は MagicMock）で、client.models.generate_content が場所の断りの APIError を投げ、切り替え先の client も同じ APIError を投げる試験を足す（gemini_route.build_client も差し替える）。RecordError が出て、record_error_detail に渡った dict の reason が「400 FAILED_PRECONDITION: User location is not supported for the API use.」、raw と category が今と同じ値であること。
- T12: `backend/tests/test_api_error_auto_retry.py` に、_Env で call_gemini_raw_copy_v8 が場所の断りの APIError を `backend/app/services/gemini_raw_copy_v8.py:229` と同じ形で包んだもの（`RuntimeError(f"Gemini v8 API 呼び出し失敗: {gemini_extraction_svc._safe_error_message(api_err)}")` を `from api_err` で投げる）を投げる試験を足す。record_error_detail の dict の reason が T11 と同じ文、raw が「(HTTP 400)」で終わること。

`backend/tests/test_message_translator.py` と `backend/tests/test_message_translator_usage_ledger.py`:
- 古い部品の偽物（_install_fake_genai・_GENAI_CACHE）を、`app.services.gemini_route.agenerate_content_routed` を AsyncMock にする形に置き換える。応答の偽物（response.text と usage_metadata）は今のまま使う。
- GenerativeModel が MODEL_SEND で呼ばれたことを見ていた所（test_message_translator.py:565-566）は、agenerate_content_routed が model=MODEL_SEND で呼ばれたことを見る形にする。
- sdk == "google-generativeai" の所は "google-genai" にする。
- それ以外の検査の中身は変えない。変えないと通らない所があれば、直さずに停止して NEEDS_DECISION: で返す。

## 9. 確かめ方

- 手元では関係する試験だけを流す: pytest backend/tests/test_gemini_route.py backend/tests/test_gemini_route_watch.py backend/tests/test_tcg_gemini_extraction.py backend/tests/test_gemini_raw_copy_v8.py backend/tests/test_message_translator.py backend/tests/test_message_translator_usage_ledger.py backend/tests/test_celery_beat_registered.py backend/tests/test_api_error_auto_retry.py backend/tests/test_api_error_retry_governance.py backend/tests/test_gemini_error_redact.py。全件は CI に任せる。
- DB が要る試験が手元で飛ばされる（skip）なら、その数を報告に書く。
- ruff は変更したファイルだけ。
- 生出力は作業場所の外の一時フォルダに保存し、パスを報告に書く。出力は head や tail で上限を付けて読む。
- `git diff origin/main...HEAD --name-only` が「触るファイル」と docs/・.claude-pipeline/ の文書だけであること。

## 想定される分岐と止まる条件

- T6 または T6b で is_route_unreachable が False → 停止。NEEDS_DECISION: で型の連なりを返す。
- APIError の作り方が部品の版で違う → 部品の中身（errors.py）を読んで合わせる。合わせ方を報告に書く。
- 既存の試験（上の10番・11番以外）が落ちる → 直さずに停止し、BLOCKED: で生出力のパスを返す。
- カードに無いファイルを触る必要が出た → 停止し、NEEDS_DECISION: で返す。
- 迷ったら停止して NEEDS_DECISION: で Opus に戻す。
- 終わったら commit（shingo-cc 名義、最後の行は Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>）→ git log -1 で確かめる → git push origin release/gemini-auto-failover → git log origin/release/gemini-auto-failover -1 で確かめる。PR は作らない（手元の Opus が作る）。

END OF CARD
