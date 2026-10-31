# 実装カード 便6 の直し 2 — 書き込みの口の一覧への登録漏れ

対象: PR #4944（branch `release/passkey-login-enroll-design`、HEAD `475012d07567a405f5e3cf497641195961c1253e`）。
元のカード: `docs/handoff/auth-self-hosted-passkey/card-b6-login-enroll.md`（§4〜§6 の決まりはそのまま有効）。

## 0. 何が起きたか（事実）

CI の pytest（run 41193653605、job 124515476076）で 1 件だけ落ちた:

```
FAILED tests/test_realtime_topics.py::test_every_write_route_is_in_exactly_one_table - AssertionError: どちらの表にも無い書き込みルート: [('POST', '/api/v1/auth/passkey/prompt/skip')]
1 failed, 7494 passed, 69 skipped, 1 xfailed, 633 warnings in 529.33s (0:08:49)
```

書き込みの口は、画面に知らせる表 `WRITE_ROUTE_TOPICS` か、知らせない表 `NO_SIGNAL_ROUTES` のどちらか 1 つに必ず載せる決まり（ADR-1016、`backend/tests/test_realtime_topics.py:34-39`）。便6 で足した `POST /api/v1/auth/passkey/prompt/skip` がどちらにも無い。元のカードと設計がこの決まりを書き漏らしたのが原因。

前例: 便5 で足したパスキーの口は、すべて `NO_SIGNAL_ROUTES` に `_PENDING` で載っている（`backend/app/realtime/topics.py:125-129`、コミット 102b93574）。スキップの記録は本人の案内を出すかどうかにしか使わず、ほかの画面の表示を変えない。

## 1. 触るファイル（これ以外は触らない）

- `backend/app/realtime/topics.py`

## 2. 直すこと

`backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES` の中、次の行のすぐ後に 1 行足す。

変更前:

```python
    ("POST", "/api/v1/auth/passkey/register/verify"): _PENDING,
```

変更後:

```python
    ("POST", "/api/v1/auth/passkey/register/verify"): _PENDING,
    ("POST", "/api/v1/auth/passkey/prompt/skip"): "ログイン直後の案内 ADR-1013: 本人の案内を出すかどうかの記録だけで画面更新の通知対象外",
```

`GET /api/v1/auth/passkey/prompt` は読み取りなので足さない（表は書き込みの口だけ）。

## 3. 確かめ方（生の最終行を報告に貼る）

- `cd backend && python -m pytest tests/test_realtime_topics.py --no-cov -q`（python は 3.12 の venv）
- `cd backend && python -m pytest tests/test_passkey_login_enroll.py --no-cov -q`
- `cd backend && ruff check app/realtime/topics.py`
- `git diff --stat origin/release/passkey-login-enroll-design` で触ったファイルが §1 の 1 つだけ

## 4. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| `test_every_write_route_is_in_exactly_one_table` が合格 | 担当の報告の生の最終行・CI の pytest（SQLite + PostgreSQL RLS）が緑 |
| 触ったファイルが 1 つだけ・足した行が 1 行だけ | `git diff --stat`・Opus が差分を読む |

## 5. 同じ種類の漏れを止める仕組み

この漏れは CI の既存の試験（`test_realtime_topics.py`）がお客さんに届く前に止めた。見張りは働いている。
漏れた理由は、元のカードの「確かめ方」が便6 の 2 ファイルの試験しか流さなかったこと。新しい書き込みの口を足すカードでは、`tests/test_realtime_topics.py` も確かめ方に入れる。
