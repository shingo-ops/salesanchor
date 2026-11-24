# 設計審査 2回目: Google カレンダーの許可を狭める実装カード

審査役: architect ／ 対象: `origin/release/google-oauth-verification-plan`（3d03d2330）の `docs/handoff/google-oauth-verification/card-narrow-scope.md` と `design.md` §3-1 ／ 実物: `origin/main`（ed9a9f158）／ 1回目: `review-architect-narrow-1.md`

## 判定: APPROVE（設計合格）

1. 1回目の R1・R2 は直っている。特に R2 の読み方（`e.new_scope` → 無ければ `token["scope"]` を str なら split・list ならそのまま → set、判定は `set(_SCOPES) <= 集合`）を、実物の `Flow.fetch_token` 経由の `Warning` で動かし、片方だけ・順不同・余分あり・別の範囲だけの全ケースで正しく判定できた（§2）。L1〜L5 も反映済み（§1）。
2. 直しで新しく書いた行番号（`:198-201`・`:151`・`:951`・`:962`・`:3389`・`:3482`・`:1485`・`SchedulePageImpl.test.tsx:1357`）は origin/main の実物と全件合う。新しい食い違いは無い（§3）。
3. 実装者が迷う箇所・直さないと壊れる箇所は見つからなかった。R は無し。軽い指摘 L1〜L3 のみ（§5）。

## 1. 1回目の指摘が直っているか（`git log -p -1 origin/release/google-oauth-verification-plan` の差分と照合）

| 指摘 | 直し（カード／設計の実物） | 結果 |
|---|---|---|
| R1 `validate_token_parameters` の呼び方 | カード「変更3」の【実装の前に確かめる】が `OAuth2Token({...}, old_scope=" ".join(_SCOPES))` を作って `validate_token_parameters(tok)` に渡す形（`card-narrow-scope.md:45-52`）。試験 S3c も同じ形（`:85`） | 直っている。§2 の「DIRECT」で同じ形が動いた |
| R2 受け取った範囲の読み方 | `card-narrow-scope.md:38-44`。`e.new_scope`（リスト）→ 無ければ `token["scope"]` を `str`→`split`／`list・tuple`→そのまま／他→空 → `set`。判定は `set(_SCOPES) <= granted_set`。S3a は list・str・`new_scope` 有無の4通りを通す（`:82`） | 直っている。§2 で実物が合う |
| L1 設計の行範囲 | `design.md` の表が `:227-239`（`scopes` は `:237`）。実物 `google_calendar.py:227` `def _build_credentials`・`:237` `scopes=_SCOPES,`・`:239` `)` | 直っている |
| L2 `connectError` の2か所 | カード変更6 が `schedule`（`:3389` 始まり）の `:3482` と、`:1485` の別物を明記（`:71`）。実物 `ja.json:3389`・`:3482`・`:1485`、`en.json` も同じ行で `"connectError"` | 直っている |
| L3 oauthlib の版 | カード `:53` が `oauthlib.__version__` を確かめの出力に残すと書く | 直っている |
| L4 webhook | 設計 S4 に「変更の通知の登録（webhook）の失敗」を数える（`design.md` 受け入れの基準 S4）。あわせて公開の API 定義で `events` の watch と `channels.stop` が `calendar.events.owned` を受け付けるという事実と、本番の `calendar_id` が2社とも `primary` という事実が足されている（読むだけの鍵での確認。審査では再確認していない＝**未確認（審査では本番に触れない）**） | 直っている |
| L5 余分な範囲 | カード `:44`（含まれていれば `RuntimeError`）。§2 の「superset」で意味が通ると確かめた | 直っている |

## 2. R2 の実物での確かめ（本番・DB・Google 本体に触れない。偽の HTTP 応答だけ）

環境: Python 3.12 の仮想環境（scratchpad 内）に `pip install "google-auth-oauthlib>=1.2.0,<2.0.0" requests`（`backend/requirements.txt:44` の指定どおり）。入った版は google-auth 2.63.1・google-auth-oauthlib 1.5.0・requests-oauthlib 2.0.0・oauthlib 4.0.1。偽の応答は `requests.Session.request` を差し替えて返し、`google_auth_oauthlib.flow.Flow.from_client_config(...).fetch_token(code="c")` を実物のまま通した。判定の関数 `classify` はカード変更3の1〜3の文面をそのまま写したもの。

```
$ /tmp/claude-0/-home-user-salesanchor/2088a117-6843-5787-b106-0214c7f7a512/scratchpad/v/bin/python -I t_r2.py 2>&1 | cut -c1-460
oauthlib 4.0.1
EV only -> Warning: Warning | e.new_scope: ['https://www.googleapis.com/auth/calendar.events.owned'] | e.token['scope'] type: list | classify: ('NOT_GRANTED', 'new_scope', ['https://www.googleapis.com/auth/calendar.events.owned'])
CR only -> Warning: Warning | e.new_scope: ['https://www.googleapis.com/auth/calendar.calendars.readonly'] | e.token['scope'] type: list | classify: ('NOT_GRANTED', 'new_scope', ['https://www.googleapis.com/auth/calendar.calendars.readonly'])
both -> no Warning; refresh_token: RT
both reversed -> no Warning; refresh_token: RT
superset(+openid) -> Warning: Warning | e.new_scope: ['https://www.googleapis.com/auth/calendar.calendars.readonly', 'https://www.googleapis.com/auth/calendar.events.owned', 'openid'] | e.token['scope'] type: list | classify: ('OK-both', 'new_scope', ['https://www.googleapis.com/auth/calendar.calendars.readonly', 'https://www.googleapis.com/auth/calendar.events.owned', 'openid'])
full calendar only -> Warning: Warning | e.new_scope: ['https://www.googleapis.com/auth/calendar'] | e.token['scope'] type: list | classify: ('NOT_GRANTED', 'new_scope', ['https://www.googleapis.com/auth/calendar'])
no scope field -> no Warning; refresh_token: RT
DIRECT one -> Warning; token.scope type: str new_scope: ['https://www.googleapis.com/auth/calendar.events.owned'] ('NOT_GRANTED', 'new_scope', ['https://www.googleapis.com/auth/calendar.events.owned'])
DIRECT both -> no exception
```

読み取れること（すべて上の出力が根拠）:
- 実物の `Flow.fetch_token` 経由では `e.token["scope"]` は `list`、直接の `validate_token_parameters` では `str`。どちらでも `e.new_scope`（リスト）が先に取れるので、カードの順序（`new_scope` 優先 → `token["scope"]` の str/list 両対応）で `AttributeError` にならない。
- 片方だけ（2通り）・別の範囲だけ（`auth/calendar` のみ）は `NOT_GRANTED`。2つそろい（順不同とも）は `Warning` 自体が出ない。余分あり（`openid` 付き）は `Warning` が出るが `<=` で `OK-both` となり、カードどおり `RuntimeError` 側に回る。
- `Warning` は `Exception` の子なので、`except Warning` を `except Exception` の前に置く順序の指定（`card-narrow-scope.md:37`）は必須で、カードに書いてある。
- 範囲の欄が無い応答は `Warning` が出ず通る。Google は範囲を返すので通常は起きないが、この場合は両方許可の確認ができない（実装の前提の注意。L1）。
- 【未確認】`e.new_scope` が無い版で `token["scope"]` 側に落ちる経路は、本審査の oauthlib 4.0.1 では通らなかった（常に `new_scope` が取れた）。経路は単純な `str`/`list` 分岐で、S3a がその両方を試験で通すと決めているので足りる。

## 3. 直しで新しく書いた行番号・文の照合（origin/main）

| カードの記述 | 実物 | 結果 |
|---|---|---|
| `google_calendar.py:198-201` の `try`〜`except Exception` | `backend/app/services/google_calendar.py:198` `try:`・`:199` `await asyncio.to_thread(flow.fetch_token, code=code)`・`:200` `except Exception as e:`・`:201` `raise RuntimeError(f"Google token 交換に失敗: {e}") from e` | 合う |
| `:151` `include_granted_scopes="false"` | `backend/app/services/google_calendar.py:151` 同文 | 合う |
| `SchedulePageImpl.tsx:944-949` と `:951`（`setSearchParams({}, …)` の前に `error` を読む） | `frontend/src/pages/schedule/SchedulePageImpl.tsx:944` `const connected = …`・`:947-949`・`:951` `setSearchParams({}, { replace: true });`（`if (connected)` の中）。`error` は `useEffect` の最初の `searchParams` を読む位置で足せる | 合う |
| `:962` の `connectError` は触らない | `SchedulePageImpl.tsx:962`（`handleGoogleConnect` の `catch` の中の `setBanner`） | 合う |
| `ja.json`/`en.json` の `schedule`（`:3389`）・`connectError`（`:3482`）・`:1485` の別物 | `ja.json:3389 "schedule": {`・`:3482 "connectError": "接続に失敗しました",`（次の行 `:3483` `disconnectConfirm` が続くので、その間に足せば末尾のカンマの問題なし）・`:1485 "connectError": "接続を開始できませんでした",`。`en.json` も同じ行 | 合う |
| `SchedulePageImpl.test.tsx:1357` の `?connected=true` の試験 | `frontend/src/pages/schedule/SchedulePageImpl.test.tsx:1357` `render(<MemoryRouter initialEntries={["/schedule?connected=true"]}>…`（G28 の試験。`i18n.t(...)` で文を引く形）。同じ形で `?connected=false&error=scope_missing` を足せる | 合う |
| 受け取り口 `routers/google_calendar.py:109-115` | `backend/app/routers/google_calendar.py:109` `exchange_code` 呼び出し・`:110` `except ValueError`・`:113` `except RuntimeError`・`:115` 戻り先。取り込み名 `cal_svc` は `:40` | 合う |
| 既存の試験が壊れないか | `TestRouterCallback`（`backend/tests/test_google_calendar.py:442`）は `app.routers.google_calendar.cal_svc.exchange_code` だけを差し替える（モジュール全体は差し替えない）ので、新しい `except cal_svc.GoogleScopeNotGrantedError` の属性参照は壊れない。`TestExchangeCodeFetchTokenError`（`:536`）は `Exception("network error")` で `RuntimeError` のまま通る。`TestBuildCredentials`（`:569`）は `MockCreds.assert_called_once()` のみで `scopes=None` への変更と矛盾しない | 問題なし |
| `_SCOPES` の使い道 | `google_calendar.py:42`（定義）・`:139`（`get_auth_url`）・`:194`（`exchange_code`）・`:237`（`_build_credentials`）。試験側に `_SCOPES`・`auth/calendar` の参照は無い（`git grep` で0件） | 変更1〜3が試験を壊さない |

## 4. 実装者が迷わず作れるか

- 触るファイル7つ・変更1〜6・試験 S1〜S5 は1対1で対応しており、「止まる条件」も明記されている。作れる。
- 設計の「受け入れの基準 S3」（片方だけなら保存せず次にすることを伝える）とカードの変更3〜6・S3a〜S3c が対応している。
- 【事実】`design.md` §3-1 の「触らない範囲」にある `google_drive_oauth.py`（別の `_SCOPES`）は今回の変更に入らない。

## 5. 軽い指摘（L。直さなくても作れる）

- **L1** 範囲の欄が無い応答（`no scope field`）は `Warning` が出ずに通る（§2）。Google の実際の応答は範囲を返すので問題は無いが、実装者が `Warning` の外側（`fetch_token` の後）でも範囲を検査するなら別途考える。カードは `Warning` 経路だけで足りるとしている。直さなくてよい。
- **L2** カード `:63` の「`cal_svc` の取り込み名は今のファイルに合わせる」は、`backend/app/routers/google_calendar.py:40` で `cal_svc` と確定している。その1行を足すと迷いが減る。
- **L3** `oauthlib` は `backend/requirements*.txt` に直接の指定が無く（1回目 L3 と同じ）、試験 S3c が直接 import する。推移で入る前提のまま。`backend/requirements.txt` は触るファイルの7つに入っていないので触らない判断は妥当。実装役はカード `:53` のとおり版を出力に残す。

## 6. 実行したもの（再現用）

- 作業場所: `bash scripts/new-worktree.sh release/google-calendar-narrow-scope-review2`
- 検証: `python3.12 -m venv` の scratchpad の環境で `/tmp/claude-0/-home-user-salesanchor/2088a117-6843-5787-b106-0214c7f7a512/scratchpad/t_r2.py`（偽の応答の `Flow.fetch_token` と `OAuth2Token` の直接呼び）。リポジトリには入れていない。
- 本番・DB・secrets・Google 本体には接続していない。
