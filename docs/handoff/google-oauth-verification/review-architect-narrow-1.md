# 設計審査 1回目: Google カレンダーの許可を狭める実装カード

審査役: architect ／ 対象: `origin/release/google-oauth-verification-plan` の `docs/handoff/google-oauth-verification/card-narrow-scope.md` と `design.md` §3-1 ／ 実物: `origin/main`（ed9a9f158）

## 判定: REVISE（直す必要）

1. カードの行番号・変更前の文は実物と全件合う。変更2（`scopes=None`）の理屈も、実物の部品で正しいと確かめた。
2. ただし変更3と試験 S3c の「実物の部品の使い方」が実物と食い違う。(a) `validate_token_parameters` は第2引数に範囲を取らず、`dict` を渡すと動かない（R1）。(b) 実際の `fetch_token` から出る `Warning` の `token["scope"]` は空白区切りの文字列ではなく**リスト**で、カードどおり読むと壊れる（R2）。
3. R1・R2 を直せば、ほかの呼び出し元（get_calendar_id・同期・webhook）や i18n・UI の決まりには触れない。作れる。

## 1. カードの行番号・変更前の文の照合（origin/main の実物）

| カードの記述 | 実物 | 結果 |
|---|---|---|
| `google_calendar.py:42` `_SCOPES = ["https://www.googleapis.com/auth/calendar"]` | `backend/app/services/google_calendar.py:42` 同文 | 合う |
| `_build_credentials` の `scopes=_SCOPES,` | `backend/app/services/google_calendar.py:227-239`、`:237` が `scopes=_SCOPES,`（設計 §3-1 の表は 227-236 と書くが、237 を含む。表の範囲の書き違いだけ。L1） | 合う |
| `exchange_code` の `await asyncio.to_thread(flow.fetch_token, code=code)` と `except Exception` | `backend/app/services/google_calendar.py:198-201` | 合う |
| 受け取り口 `routers/google_calendar.py:109-115`、`except ValueError` の前に足す | `backend/app/routers/google_calendar.py:108-115`（`:109` が `exchange_code` 呼び出し、`:110` `except ValueError`、`:113` `except RuntimeError`）。取り込み名 `cal_svc` は `:40` | 合う |
| `SchedulePageImpl.tsx:944-949` | `frontend/src/pages/schedule/SchedulePageImpl.tsx:944-949`（`:948` が `t("schedule.connectError")`。ほかに `:962` にも同じキーの別の使い道がある。触らない） | 合う |
| `ja.json`/`en.json` の `schedule` の `connectError` の次の行 | `frontend/src/locales/ja.json:3482`・`en.json:3482`（`"schedule"` は `:3389` 始まり）。`:1485` にも別の名前空間の `connectError` があり、混同しないこと（L2） | 合う |
| `TestBuildCredentials`（試験） | `backend/tests/test_google_calendar.py:569-` | 合う |
| 画面の試験ファイル | `frontend/src/pages/schedule/SchedulePageImpl.test.tsx:1357` に `?connected=true` の既存の試験がある。同じ形で足せる | 合う |

## 2. 変更2: `scopes=None` で今の全部の許可の合鍵が更新できるか

【事実】`google.oauth2._client.refresh_grant` は `scopes` が空のとき `scope` を送らない（`google/oauth2/_client.py:512-513` の `if scopes: body["scope"] = " ".join(scopes)`、google-auth 2.63.1）。実物の `Credentials.refresh` を偽の通信口で動かして、送る本文を確かめた:

```
$ $S/v312/bin/python -I $S/t2.py     # S=scratchpad、google-auth 2.63.1、Python 3.12
google-auth 2.63.1
scopes=None -> POST body keys/values: {'grant_type': ['refresh_token'], 'client_id': ['id']} | creds.token: NEW | creds.granted_scopes: None
scopes=narrow2 -> POST body keys/values: {'grant_type': ['refresh_token'], 'client_id': ['id'], 'scope': ['https://www.googleapis.com/auth/calendar.events.owned https://www.googleapis.com/auth/calendar.calendars.readonly']} | creds.token: NEW | creds.granted_scopes: ['https://www.googleapis.com/auth/calendar']
```
（`client_secret`・`refresh_token` は表示から除いた。偽の応答を返した試験で、Google 本体には接続していない。）

- `scopes=None` なら本文に `scope` が無い。`scopes=[狭い2つ]` なら `scope` が付く。カードの理屈（範囲を送らなければ前に許された範囲で更新）の「送らない」部分は実物で確かめた。
- 【未確認】「`scope` を送らないとき Google 本体が前の許可の範囲で更新する」は RFC 6749 §6 の規定どおりの動きだが、Google 本体への通信は審査では行えない。設計 §3-1 の S4（反映後 24 時間の確認）が受け皿になっており、足りる。
- 参考: `scopes=narrow2` で全部の許可が返ると、google-auth は「Not all requested scopes were granted」の警告だけを出し、失敗にはしなかった（上の出力の前に出ていた警告）。だから `scopes=None` にしない場合の危険は警告止まりと見えるが、カードは `None` なので影響しない。

## 3. 変更3: oauthlib の `Warning` と `token`

requirements の指定: `backend/requirements.txt:44` `google-auth-oauthlib>=1.2.0,<2.0.0`。`oauthlib` 自体は `requirements*.txt` に**指定が無く**（`grep` で `oauthlib` は 44 行目のみ）、`google-auth-oauthlib → requests-oauthlib → oauthlib` の推移で入る。今回の入った版: google-auth-oauthlib 1.5.0・requests-oauthlib 2.0.0・oauthlib 4.0.1（最新）。念のため 3.2.2・3.3.1 でも同じ試験を流した（本番の実際の版は未確認。L3）。

### 3-1. 関数の形（R1 の根拠）

```
$ grep -n "def validate_token_parameters" -A 25 <oauthlib 4.0.1>/oauth2/rfc6749/parameters.py
447:def validate_token_parameters(params):
...
462:    if params.scope_changed:
463:        message = 'Scope has changed from "{old}" to "{new}".'.format(
464:            old=params.old_scope, new=params.scope,
...
467:        if not os.environ.get('OAUTHLIB_RELAX_TOKEN_SCOPE', None):
468:            w = Warning(message)
469:            w.token = params
470:            w.old_scope = params.old_scopes
471:            w.new_scope = params.scopes
472:            raise w
```
引数は `params` 1つで、それは `OAuth2Token(params_dict, old_scope=...)`（`scope_changed` を持つ）。カードの「`{...}` と、求めた範囲2つを渡す」は、`dict` を渡しても `.scope_changed` が無く動かない。実際に `scope=` を付けて呼ぶと:
```
$ python -I t3.py   # 最初の試し（カードの書き方）
(params)
one only -> (<class 'TypeError'>, ...) msg= validate_token_parameters() got an unexpected keyword argume...
```

### 3-2. 実物で動かした結果（`OAuth2Token(..., old_scope=求めた2つ)` を渡した場合）

```
$ for v in oauthlib最新 oauthlib==3.2.2 oauthlib==3.3.1; do ... python -I t3b.py; done   # 3版とも同じ出力。4.0.1 を転記
oauthlib 4.0.1 requests-oauthlib 2.0.0 google-auth-oauthlib 1.5.0
DIRECT one only -> Warning Exception | msg: Scope has changed from "https://www.googleapis.com/auth/calendar.events.owned https://www.googleapis.com/auth/calendar.calendars.readonly" to "https://www.googleapis.com/auth/calendar.events.owned". | e.token.scope: https://www.googleapis.com/auth/calendar.events.owned | e.token['access_token']: x
DIRECT both -> no exception
DIRECT both reversed -> no exception
DIRECT only CR -> Warning Exception | msg: Scope has changed from "...events.owned ...calendars.readonly" to "https://www.googleapis.com/auth/calendar.calendars.readonly". | e.token.scope: https://www.googleapis.com/auth/calendar.calendars.readonly | e.token['access_token']: x
DIRECT FULL returned -> Warning Exception | msg: Scope has changed from "...events.owned ...calendars.readonly" to "https://www.googleapis.com/auth/calendar". | e.token.scope: https://www.googleapis.com/auth/calendar | e.token['access_token']: x
```
→ 片方だけなら `Warning`（`Exception` の子）で `e.token` が付く。2つ（順不同とも）なら出ない。ここまでカードの狙いどおり。

### 3-3. 実際の `Flow.fetch_token` 経由（R2 の根拠）

偽の HTTP 応答（`requests.Session.request` を差し替え）を `google_auth_oauthlib.flow.Flow.fetch_token` に通した結果:
```
E2E one only -> Warning: Scope has changed from "...events.owned ...calendars.readonly" to "https://www.googleapis.com/auth/calendar.events.owned". | token.scope: ['https://www.googleapis.com/auth/calendar.events.owned'] | refresh_token in e.token: True
E2E both -> OK; flow.credentials.refresh_token = RT
E2E both reversed -> OK; flow.credentials.refresh_token = RT
```
**`e.token.get("scope")` は `['…events.owned']`（リスト）**。直接 `validate_token_parameters` を呼んだ 3-2 では文字列だった。カードは「`scope`（空白区切り）を読み」と書いており、`.split()` するとリストで `AttributeError` になり、受け取り口が未処理の例外（500）になる。3版とも同じ。

## 4. 呼び出し元の確認（変更3〜5）

- `exchange_code` の呼び出し元は `backend/app/routers/google_calendar.py:109` の1か所のみ（`grep -rn "exchange_code" backend/app`。`meta_graph.py:264` は別物、`google_drive_oauth.py` は別モジュール）。
- `_build_credentials` の呼び出し元は `backend/app/services/google_calendar.py:269`（`_refresh_if_needed`）と `:330`（`_get_service`）の2か所のみ。後者は `expiry=None` の作り直しで、`scopes` を使うのは `Credentials` の引数だけ。`scopes=None` で壊れる箇所は無い。
- `_SCOPES` の使い道は `:139`（`get_auth_url`）・`:194`（`exchange_code`）・`:237` のみ。`google_drive_oauth.py:49` は別の `_SCOPES`（触らない）。
- `get_calendar_id`（`:335-346`）・`get_events`・`get_event`・`get_event_label_colors`（`:400` `calendars().get`）・`google_webhook.py:98` `events().watch`・`:145`/`:183` `channels().stop`・`:310` `events().list`・`calendar_service.py` の同期は、`_get_service` 経由で `_build_credentials` を使うだけ。`GoogleScopeNotGrantedError` は `exchange_code` 以外から出ない。変更3〜5で壊れない。
- 既存の試験: `TestExchangeCodeFetchTokenError`（`backend/tests/test_google_calendar.py:536-`）は `Exception("network error")` を渡す。`Warning` ではないので `RuntimeError` のまま通る。`TestRouterCallback`（`:442-`）も影響なし。
- 例外の型: `GoogleScopeNotGrantedError(Exception)` は `ValueError`/`RuntimeError` の子ではない。変更4の専用の `except` が無いと未処理になるので、カードの変更4は必須（カードに書いてあり、問題なし）。

## 5. i18n・UI の決まり

- ADR-027（`docs/adr/ADR-027-ui-internationalization.md`・`frontend/AGENTS.md:21-23`）: 新しい文は `t("schedule.connectScopeMissing")` で、`ja.json`・`en.json` の同じキー。カードどおりで反する点なし。
- ADR-144・ADR-067: 今の `banner`（`SchedulePageImpl.tsx:842` の `setBanner`、表示 `:1573`）を使い、新しい部品・色・直書きを足さない。カードどおりで反する点なし。
- 文の形（ADR-1071「起きたこと＋次にすること」）: ja「…一部だけでした。…2つとも選んで、もう一度接続してください」は合う。
- `searchParams.get("error")` は `setSearchParams({}, …)`（`:951`）より前に読むこと。カードの手順（`connected === "false"` の分岐の中で読む）で足りる。

## 6. 直す点（R。直さないと作れない・壊れる物だけ）

- **R1** `docs/handoff/google-oauth-verification/card-narrow-scope.md` の「変更3」の【実装の前に確かめる】と、試験表の S3c: 「`validate_token_parameters` に `{...}` と求めた範囲2つを渡す」を、「`OAuth2Token({"access_token": "x", "token_type": "Bearer", "scope": <返った範囲の空白区切り>}, old_scope=" ".join(_SCOPES))` を作り、`validate_token_parameters(その token)` を呼ぶ。片方だけなら `Warning`（`e.token` あり）、2つ（順不同とも）なら例外なし」に書き直す。`import` は `from oauthlib.oauth2.rfc6749.tokens import OAuth2Token`。この形は 3版（3.2.2・3.3.1・4.0.1）で動いた（上の 3-2）。今のままだと実装者が書いた通りに呼んで `TypeError`/`AttributeError` になり、カードの「違えば BLOCKED」で止まる。
- **R2** 同じカードの「変更3」2つめの箇条（`e` に付く `token` の `scope`（空白区切り）を読み…）: 「`Warning` の `e.new_scope`（リスト。oauthlib の `parameters.py:471`）を使う。無い版に備えるなら `token.get("scope")` を取り、`str` なら `.split()`、`list` ならそのまま `set()` にする」と書き直す。そのうえで `set(_SCOPES) <= 受け取った集合` で判定する。判定が `<=`（含まれていれば両方そろっている）か `==` かも一言決めて書く（Google が `openid` 等を足しても `include_granted_scopes=false`（`:151`）なので通常は足らないが、足りない側だけを見る `<=` が安全）。試験 S3a も、`e.token` の `scope` を**リスト**と**文字列**の両方で作って通す（3-3 のとおり実物はリスト）。

## 7. 軽い指摘（L。直さなくても作れる）

- **L1** 設計 §3-1 の表の「`:227-236`」は `scopes=_SCOPES` の行（`:237`）を含まない。実物は `:227-239`。表の範囲だけ直す。
- **L2** `connectError` は `ja.json`/`en.json` に2つある（`:1485` は別の名前空間、`:3482` が `schedule`）。カードに「`schedule`（`:3389` 始まり）の中の `:3482`」と行を足すと迷わない。
- **L3** `oauthlib` は `requirements*.txt` に指定が無く、ビルドの時期で版が変わる。今回は 3.2.2・3.3.1・4.0.1 で同じ結果。本番の実際の版は未確認（審査では本番に触れない）。実装役は `python -c "import oauthlib; print(oauthlib.__version__)"` を試験の確かめの出力に残すとよい。
- **L4** 【未確認】`calendar.events.owned`＋`calendar.calendars.readonly` で `events().watch`（`google_webhook.py:98`）・`channels().stop`（`:145`・`:183`）が通るか。設計 §3-1 は「全9操作○」と書くが、審査では watch/stop が含まれるか確認できなかった。S4（反映後 24 時間で同期の失敗が増えない）で見るなら、そこに「webhook の登録・更新の失敗」も数える、と1行足すとよい。`tenant_google_calendar_config.calendar_id` が非 `primary`（他人所有のカレンダー）なら `events.owned` では足りない可能性もあるが、本番の値は審査では見られない（未確認）。
- **L5** 返った範囲が求めた2つの**上位集合**（余分あり）でも oauthlib は `Warning` を出す（3-2 の `FULL returned` と同じ仕組み）。カードの「そろっていれば今と同じく `RuntimeError`」は、上位集合のとき利用者に「token 交換に失敗」と出る。`include_granted_scopes="false"` で通常は起きないが、R2 の `<=` 判定なら余分があっても両方あれば `RuntimeError`、足りなければ新しい失敗、で意味が通る。

## 8. 実行したもの（再現用）

- 作業場所: `bash scripts/new-worktree.sh release/google-calendar-narrow-scope-review1`
- 検証用の仮想環境: Python 3.12、`pip install "google-auth-oauthlib>=1.2.0,<2.0.0" "google-auth-httplib2>=0.2.0,<1.0.0" requests`（scratchpad 内。リポジトリには入れていない）
- 本番・DB・secrets・Google 本体には接続していない。偽の応答だけで確かめた。
