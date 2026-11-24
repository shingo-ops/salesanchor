# 実装カード: Google カレンダーの許可を狭い2つに変える

- 設計: `docs/handoff/google-oauth-verification/design.md` §3-1（PO 2026-11-25「1」= 狭める。同日「1」= 実装・マージ・本番反映まで進める）
- 枝: `origin/main` から `release/google-calendar-narrow-scope`（`bash scripts/new-worktree.sh release/google-calendar-narrow-scope --claude` で場所を作る）
- 触るファイル（これ以外は触らない）:
  1. `backend/app/services/google_calendar.py`
  2. `backend/app/routers/google_calendar.py`
  3. `backend/tests/test_google_calendar.py`
  4. `frontend/src/pages/schedule/SchedulePageImpl.tsx`
  5. `frontend/src/locales/ja.json`
  6. `frontend/src/locales/en.json`
  7. 画面の試験を足すなら `frontend/src/pages/schedule/` の既存の試験ファイル1つ

## 変更1 許可の範囲（`backend/app/services/google_calendar.py:42`）

変更前:
```python
_SCOPES = ["https://www.googleapis.com/auth/calendar"]
```
変更後:
```python
# 狭い2つ（design §3-1）。予定は本人が持つものだけ読み書きし、カレンダーの設定（色ラベル）は読むだけ。
_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events.owned",
    "https://www.googleapis.com/auth/calendar.calendars.readonly",
]
```

## 変更2 合鍵の更新で範囲を送らない（同ファイル `_build_credentials`）

`Credentials(...)` の `scopes=_SCOPES,` を `scopes=None,` に変える。直前に1行の注記: 「範囲を送らないと、Google は前に許された範囲で合鍵を更新する。今つないでいる人（全部の許可）をつなぎ直させないため（design §3-1）」。

## 変更3 片方だけ許可されたときの失敗（同ファイル `exchange_code`）

- 同ファイルにクラスを足す: `class GoogleScopeNotGrantedError(Exception): """利用者が Google の同意の画面で、求めた許可の一部を外した。"""`
- `await asyncio.to_thread(flow.fetch_token, code=code)` の `try` で、今の `except Exception` の前に `except Warning as e:` を足す。`e` に付く `token` の `scope`（空白区切り）を読み、`_SCOPES` の2つが両方そろっていなければ `GoogleScopeNotGrantedError` を出す。そろっていれば今と同じく `RuntimeError` にする。
- 【実装の前に確かめる】今入る版の `oauthlib` で、範囲が変わったとき `fetch_token` から `Warning` が出て `token` が付くこと。`oauthlib.oauth2.rfc6749.parameters.validate_token_parameters` に `{"access_token":"x","token_type":"Bearer","scope":"https://www.googleapis.com/auth/calendar.events.owned"}` と、求めた範囲2つを渡す試験で確かめる。型か `token` の付き方が違えば、**実装をやめて BLOCKED: で返す**（推測で書き換えない）。
- 2つとも許されたときに `Warning` が出ないこと（並び順が違っても）も同じ試験で確かめる。出るなら BLOCKED: で返す。

## 変更4 受け取り口（`backend/app/routers/google_calendar.py:109-115`）

`except ValueError` の前に足す:
```python
    except cal_svc.GoogleScopeNotGrantedError as e:
        logger.warning("Google Calendar callback: 許可の一部が外された %s", e)
        return RedirectResponse(f"{frontend_schedule}?connected=false&error=scope_missing")
```
（`cal_svc` の取り込み名は今のファイルに合わせる。）

## 変更5 画面（`frontend/src/pages/schedule/SchedulePageImpl.tsx:944-949`）

`connected === "false"` のとき、`searchParams.get("error") === "scope_missing"` なら `t("schedule.connectScopeMissing")`、それ以外は今と同じ `t("schedule.connectError")`。新しい部品・色・直書きの文は足さない（今の知らせの帯をそのまま使う。ADR-144・ADR-067）。

## 変更6 文（`ja.json` と `en.json` の `schedule` の `connectError` の次の行。同じキーを両方に）

- ja: `"connectScopeMissing": "Google カレンダーの許可が一部だけでした。Google の画面で2つとも選んで、もう一度接続してください"`
- en: `"connectScopeMissing": "Only some Google Calendar permissions were granted. Select both on the Google screen and connect again."`

## 試験（`backend/tests/test_google_calendar.py`）

| 基準 | 試験 |
|---|---|
| S1 | `get_auth_url` の URL の `scope` を分解し、狭い2つだけで、`auth/calendar` 単体が無い |
| S2 | `_build_credentials` が `Credentials` を `scopes=None` で呼ぶ（今の `TestBuildCredentials` に足す） |
| S3a | `fetch_token` が `token` 付きの `Warning`（片方だけ）を出すと `GoogleScopeNotGrantedError` |
| S3b | 受け取り口が `GoogleScopeNotGrantedError` で `error=scope_missing` に送る |
| S3c | 実物の `oauthlib` の検査の関数で、片方だけなら `Warning`・2つとも（順不同）なら出ない |

既存の試験の `exchange_code` の成功の形（`creds.refresh_token` が無いと失敗、など）は変えない。

## 確かめ

- `cd backend && python -m pytest tests/test_google_calendar.py -q` の生の出力をファイルに残す。
- `frontend` の i18n の検査（`frontend/CLAUDE.md` の grep 自己点検）。
- 提出前: `bash scripts/dev/check-before-submit.sh`。
- PR は `--base main`、`shingo-cc` 名義、本文はひな形どおり。`migrations/`・`deploy.yml` は触らない。

## 止まる条件

- 上の【実装の前に確かめる】が設計と違う。
- 触るファイル以外を変える必要が出た。
- 既存の試験が、この変更と関係なく落ちる。
