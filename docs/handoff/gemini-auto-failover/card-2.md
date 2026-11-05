# card-2 — 切り替え先の道の Client が使う前に閉じる不具合の直し（ADR-1062）

状態: 実装カード（Opus、2026-11-05）。設計は [design.md](design.md) §4-1・§4-2（PO 2026-11-05「1」で承認済み）。このカードは設計を変えない。設計どおりに動かなかった実装の誤りを直す。
根拠: `docs/handoff/gemini-auto-failover/recon.md`、本番での1回きりの確かめ（下の §0）。

## 0. 何が起きたか（本番の実測、2026-11-05 22:50 JST、PR #5163 反映後）

- K1（直接を先にした1回きりの呼び出し、celery-worker）: 「道を切り替えます: direct -> relay 理由=400 FAILED_PRECONDITION: User location is not supported」の warning は出た。しかし結果は `RuntimeError`。
- 中継の道だけで呼ぶと、例外は `builtins.RuntimeError: Cannot send a request, as the client has been closed.` だった。gemini-egress:18888 への TCP 接続は成功している。
- 部品 google-genai 2.8.0 の `google.genai.client.Client` には `__del__` があり、中で `self.close()` を呼ぶ（本番のコンテナで `inspect.getsource` で確認）。
- `backend/app/services/gemini_route.py:197` の `build_client(to).models.generate_content(...)` と `:220` の `await build_client(to).aio.models.generate_content(...)` は、作った Client をどこにも持たない。`.models` を取り出した時点で Client が消え、`__del__` が接続を閉じる。そのため、閉じた接続で送ることになる。
- 最初の道の呼び出しは、呼び出し側が Client を変数に持っているので起きない（`:208` の `client = build_client(route)`、解析の `client = _get_genai_client()`）。今の本番の普段の解析（最初の道 = 中継）は成功している。

## 1. 直すこと（触るファイルは2つだけ）

1. `backend/app/services/gemini_route.py`
   - `:197` を次の形にする。切り替え先の Client を、呼び出しが終わるまでローカル変数に持つ。
     ```python
     other = build_client(to)
     response = other.models.generate_content(
         model=model, contents=contents, config=config
     )
     ```
   - `:220` も同じ形にする（`other = build_client(to)` → `response = await other.aio.models.generate_content(...)`）。
   - 変えない: 切り替えの条件・回数・remember・_count_switch・warning の文・failure_reason。
   - 直した2か所の直前に、1行のコメントで理由を書く: 「Client は消えると __del__ で接続を閉じる（google-genai）。呼び出しが終わるまで変数に持つ」。
2. `backend/tests/test_gemini_route.py` に T13・T13b を足す（既存の試験は変えない）。
   - T13（同期）: 最初の道は場所の断りを出す偽物（既存の `_failing_client(_location_error())`）。`gemini_route.build_client` を `lambda route: _real_client_unreachable()` に差し替える（既存 `:134` の実物の Client、届かない中継 127.0.0.1:9）。`_call(...)` が投げる例外について、次を確かめる。
     - `gemini_route.is_route_unreachable(exc)` が True であること。
     - `"client has been closed"` が `str(exc)` に無いこと。
     直す前のコードでは RuntimeError（closed）になって落ちる、直した後は ConnectError 系になって通る、が狙い。
   - T13b（非同期）: `build_client` を `side_effect` で、`ROUTE_DIRECT` なら `_failing_client(_location_error())`、`ROUTE_RELAY` なら `_real_client_unreachable()` を返すように差し替える。`gemini_route.agenerate_content_routed(model="m", contents="c", config=None)` で、T13 と同じ2点を確かめる。
   - T13・T13b の試験名に「keeps_switched_client_alive」を含める。

## 2. 実装前点検（外れたら実装せず BLOCKED:）

- P1: `gemini_route.py:197` が `response = build_client(to).models.generate_content(` である。
- P2: `gemini_route.py:220` が `response = await build_client(to).aio.models.generate_content(` である。
- P3: `backend/tests/test_gemini_route.py:134` に `_real_client_unreachable` がある。
- P4: 直す前のコードで T13 を先に流し、`client has been closed` で落ちることを確かめる（落ちなければ NEEDS_DECISION: で、出た例外の連なりを返す）。

## 3. 確かめ

- `cd backend && python -m pytest tests/test_gemini_route.py tests/test_gemini_route_watch.py tests/test_tcg_gemini_extraction.py tests/test_api_error_auto_retry.py tests/test_message_translator.py tests/test_message_translator_usage_ledger.py -q` が全部通る。
- `ruff check backend/app/services/gemini_route.py backend/tests/test_gemini_route.py` が通る。

## 4. 想定される分岐と止まる条件

- P4 で落ちない（部品の版が違うなど）→ NEEDS_DECISION:。
- 直した後も T13 が `client has been closed` で落ちる → BLOCKED:。そのときの例外の連なりを返す（`_type_chain`）。
- 触るファイル2つ以外を変えたくなった → NEEDS_DECISION:。

## 5. 本番での確かめ（Opus がマージ後に行う）

- K1: celery-worker で GEMINI_PROXY_URL を外した1回きりの呼び出しが、「direct -> relay」の warning のあと成功する。
- K2: 届かない中継を先にした呼び出しが、「relay -> direct」の warning のあと、場所の断り（APIError 400）で終わる（今は直接が断られるため）。
- K5: backend で GEMINI_PROXY_URL を外した訳の1回きりの呼び出しが成功する。aiohttp の「Unclosed client session」の警告が出ないかも見る。

- 守り手: backend/tests/test_gemini_route.py
