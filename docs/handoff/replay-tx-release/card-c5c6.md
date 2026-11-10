# 実装カード — 試しの道具の追加の守り（C5'・C6'・K5'）

読んだ節: guards/00-common.md・guards/03-file.md・guards/04-worktree.md・guards/05-pr.md（照合: 危険パスなし・作業枝は Opus が new-worktree.sh で作成済み・PR は gh-pr-create-safe.sh・触るファイルは同一行カンマ区切り）

受領確認
  最初の応答で「受領。」と1行返してから始める。

停止時の報告
  止まったときは、画面に出たエラー出力を全文そのまま報告に貼る。報告は DONE / BLOCKED: / NEEDS_DECISION: のどれかで始める。

- 設計: docs/handoff/replay-tx-release/design.md §13・§14（§14 が正本。§13 C5・C6 と §6 K5 は §14 で置き換え済み）
- 設計の審査: Architect（opus、クラウド）第4版 APPROVE・PR #5348 の reviewer（opus）APPROVE on 75cc59f73
- PO 承認: 2026-11-10 PO「1」（作り始める。道具の追加の守りから）
- 起点: 作業枝 release/replay-tx-c5c6（origin/main から作成済み。このカードと台帳だけが入っている）。この枝に積む
- 触るファイル（これ以外は触らない）:
  - backend/app/tools/_tx_guard.py（足す）
  - backend/tests/test_tx_guard_pool.py（新規・本物の PostgreSQL の試験）
  - backend/tests/test_tools_tx_guard_required.py（新規・見張りの試験）
  - .claude-pipeline/active-work.d/release-replay-tx-c5c6.md（台帳の状態だけ）
- 触らない: migrations/・.github/・deploy.yml・scripts/・backend/app/tasks/・backend/app/services/・backend/app/database.py・backend/app/tools/ の _tx_guard.py 以外・既存の試験ファイル
- 危険なパス（migrations/・deploy.yml・本番 scripts/）は含まない

## 1. backend/app/tools/_tx_guard.py に足す（今ある関数・値・ログはそのまま残す）

import に `from sqlalchemy import event` と `from sqlalchemy.engine import Engine` を足す（今の `from sqlalchemy import text` と1行にまとめてよい）。

`set_idle_tx_limit` の上に次の2つを足す:

```python
def _on_connect_set_idle_limit(dbapi_connection, connection_record) -> None:
    """新しい DB 接続ができるたびに、開いた取引で待つ上限を置く（design §14 C5'）。

    commit まで流す。プールが接続を返すときの rollback で SET が消えないようにするため。
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SET idle_in_transaction_session_timeout = '{int(IDLE_TX_LIMIT_SECONDS)}s'")
    finally:
        cursor.close()
    dbapi_connection.commit()


def install_idle_tx_listener(engine: Engine) -> None:
    """engine に connect の受け手を1回だけ付ける。付いていれば何もしない。"""
    if not event.contains(engine, "connect", _on_connect_set_idle_limit):
        event.listen(engine, "connect", _on_connect_set_idle_limit)
```

`set_idle_tx_limit` の本文の最初（今の SET の execute の前）に次の3行を足す。残りの本文は変えない:

```python
    bind = session.get_bind()
    if isinstance(bind, Engine):
        install_idle_tx_listener(bind)
```

- 偽物の session（MagicMock）では get_bind が Engine でないので登録しない。今の試験はそのまま緑のはず。

## 2. 新規 backend/tests/test_tx_guard_pool.py（本物の PostgreSQL・CI の pytest で走る）

- DB の取り方は backend/tests/test_prompt_ab.py :19・:21 と同じにする（`from tests.test_tcg_work_matching_integration import pg as pg_fixture` と `pg = pg_fixture`）。fixture は `(conn, engine, url)` を返す。試験の中では fixture の engine を使わず、`url` から専用の engine を作る。
- 秒の期待値は `f"{IDLE_TX_LIMIT_SECONDS}s"` で作る。30 を書かない。
- 試験名は末尾を `_on_real_postgres` にする（手元では DB が無く失敗するのは想定どおり。CI で流す）。

試験A `test_limit_survives_pool_return_and_invalidate_on_real_postgres`:
1. `engine = create_engine(url, pool_size=1, max_overflow=0)`。`install_idle_tx_listener(engine)`。
2. 接続を取り、`SELECT pg_backend_pid()` と `SHOW idle_in_transaction_session_timeout` を読んで返す（with を抜ける）。
3. もう一度取り、同じ2つを読む。pid が 2 と同じ（プールの使い回し）で、値が期待値。
4. 接続を取り、`invalidate()` してから閉じる。もう一度取り、pid が 3 と違い（新しい接続）、値が期待値。
5. finally で `event.remove(engine, "connect", _tx_guard._on_connect_set_idle_limit)` と `engine.dispose()`。

試験B `test_listener_registered_once_on_real_engine_on_real_postgres`:
1. `engine = create_engine(url, pool_size=1, max_overflow=0)`。
2. `monkeypatch.setattr(_tx_guard.event, "listen", MagicMock(wraps=event.listen))` で listen の呼び出しを数える（_tx_guard が使う event の listen を差し替える。差し替え先が sqlalchemy.event 本体になる場合は試験の後で必ず元に戻る monkeypatch を使う）。
3. `with Session(engine) as s:` で `set_idle_tx_limit(s)` を2回呼ぶ。
4. `event.contains(engine, "connect", _tx_guard._on_connect_set_idle_limit)` が True。listen の呼び出しが1回。
5. finally で受け手を外し、`engine.dispose()`。

## 3. 新規 backend/tests/test_tools_tx_guard_required.py（見張り・DB を使わない）

- 根は `Path(__file__).resolve().parents[1]`（= backend）。道具の根は `<backend>/app/tools`、アプリの根は `<backend>/app`。
- 判定の関数は、見る根を引数で受け取る形にする（下の赤の実演 (5)(6) を一時フォルダで確かめるため）。
- DB を使う道具の見分け方（語の区切り付きの正規表現。どれか1つに当たれば DB を使う）:
  `\b_get_sync_session\b`・`\bSession\(`・`\bSessionLocal\(`・`\bAsyncSessionLocal\(`・`\b_engine\b`・`\bcreate_engine\(`・`\bsessionmaker\(`・`\.connect\(`・`from app\.database import`
- 見る範囲: 道具の根の下を `rglob("*.py")`。`__init__.py` と根の直下の `_tx_guard.py` は除く。表のキーは道具の根からの相対パス（`/` 区切り）。
- 例外表（キー → 理由の文）: `reextract_v6_with_v102.py` → 「書き込みを含み、投稿ごとに読み取りの後で取引を閉じる（:456）。共通の rollback を足すと書き込みを捨てうる。開いたままの握りは本番反映の前の点検が見つける」。これ以外は載せない。

関数と試験:
- `find_unguarded(tools_root, exceptions) -> list[str]`: DB を使うのに本文に `set_idle_tx_limit(` が無く、例外表にも無いファイル。
- `find_stale_exceptions(tools_root, exceptions) -> list[str]`: 例外表にあるのに、ファイルが無いか、DB を使う語が1つも無いもの。
- `find_outside_imports(app_root, tools_root) -> list[str]`: アプリの根の下で道具の根の外にあり、本文に `from app.tools`・`import app.tools`・`from app import tools` のどれかを含むファイル。
- 本物の木に対する試験3つ: 上の3つの関数がどれも空の一覧を返す。赤のときは見つかったファイル名を assert の文に出す。
- 一時フォルダの試験（ずっと残す。赤の実演 (5)(6) を兼ねる）:
  - tmp_path に `tools/sub/x.py`（中身は `_engine.connect()` の1行だけ）を作ると、`find_unguarded` が `sub/x.py` を返す。
  - tmp_path に `app/tools/a.py` と `app/tasks/t.py`（中身は `from app.tools import prompt_ab`）を作ると、`find_outside_imports` が `tasks/t.py` 相当を返す。
  - 語の区切りの確かめ: 中身が `get_engine(` だけのファイルは DB を使う扱いにならない。`SessionLocal(` だけのファイルはなる。

## 4. 赤の実演（一度だけ。手で壊して流し、赤を見たら元に戻す。生の出力を PR に貼る）

| 番号 | 壊し方 | 赤になる試験 |
|---|---|---|
| (1) | prompt_ab.py の `_tx_guard` の import と `set_idle_tx_limit(` の呼び出しを消す | 見張りの find_unguarded |
| (2) | 例外表から reextract_v6_with_v102.py を消す | 見張りの find_unguarded |
| (3) | 例外表に存在しないファイル名を足す | 見張りの find_stale_exceptions |
| (4) | prompt_ab.py の import は残し、`set_idle_tx_limit(` の呼び出しだけ消す | 見張りの find_unguarded |
| (7) | `_tx_guard.py` の `isinstance(bind, Engine)` を `False` にする | 試験B（CI でだけ流れる。PR の別の commit で入れて CI の赤を見せ、次の commit で戻す。戻した後の CI が緑であること） |

- (5)(6) は §3 の一時フォルダの試験がずっと確かめるので、手の実演は要らない。
- 試験A・B は手元に DB が無いので、(7) は CI の結果のリンクを貼る。

## 5. 完了の確かめ（流して生の出力を PR に貼る）

- `cd backend && python -m pytest tests/test_tx_guard.py tests/test_tx_guard_pool.py tests/test_tools_tx_guard_required.py tests/test_v102_replay_diff.py tests/test_prompt_ab_recompute.py tests/test_prompt_ab.py -q --no-cov`
- `cd backend && ruff check app/tools tests/test_tx_guard_pool.py tests/test_tools_tx_guard_required.py`
- `git diff origin/main --stat` が上の「触るファイル」とカード・台帳だけ
- PR の CI の「pytest (SQLite + PostgreSQL RLS)」で試験A・B が passed（skipped でない）こと。CI の記録の該当行を貼る

## 6. 想定の分かれ道

- 試験B で `event.contains` が False になる（engine に登録した受け手を engine で見つけられない）→ 直さずに止めて NEEDS_DECISION: で戻す（設計 §14 K5' の未確認の点。Opus が登録と確かめの相手をそろえる判断をする）。
- 試験A で invalidate 後の値が期待値でない、または pid が変わらない → 止めて BLOCKED: で戻す。
- 今の MagicMock の試験（test_tx_guard.py・test_v102_replay_diff.py・test_prompt_ab.py・test_prompt_ab_recompute.py）が赤になる → 試験を直さず、§1 の「Engine のときだけ」が効いているかを確かめて BLOCKED: で戻す。
- 見張りの本物の木の試験が赤（今の道具の当てはめが設計 §14 と違う）→ 例外表を足さずに止めて BLOCKED: で戻す。
- `*_on_real_postgres` が手元で DB 無しのエラーになる → 想定どおり。名前と最後の行を報告に書く。
- ruff の import の順の指摘 → 指摘どおりに直す（中身は変えない）。
- 完了の報告は DONE / BLOCKED: / NEEDS_DECISION: のどれかで始める。

## 7. PR

- commit・push・PR 作成は段を分ける。各段の後で git log と .pr-number の実在を確かめてから次へ進む。push は毎回 git push -u origin HEAD。
- gh auth status で shingo-cc を確かめる。PR は scripts/gh-pr-create-safe.sh で作り、本文は先にファイルに書いてその実在パスを渡す。Draft にしない。マージはしない（Opus が審査してマージする）。
- 標準ワークフロー確認の「触るファイル:」は1行・カンマ区切り・バッククォートなし。削除の行が出たら「削除するファイル:」に全部書く。

END OF CARD
- PR 本文は .github/pull_request_template.md に従う。`### 標準ワークフロー確認` に recon: docs/handoff/replay-tx-release/recon.md・設計: docs/handoff/replay-tx-release/design.md・対象ADR: ADR-1037 を書く。

## 8. 追記（2026-11-10・CI の結果を受けて。Opus）

- 事実: PR の CI「pytest (SQLite + PostgreSQL RLS)」で試験A・B が `sqlalchemy.exc.MissingGreenlet` で失敗した（run 42755892620、`2 failed, 8694 passed`）。共有 fixture（backend/tests/test_tcg_work_matching_integration.py の `pg`）が返す `url` は `drivername="postgresql+asyncpg"` で、同期の `create_engine` では使えない。カード §2 にこの点を書き忘れていた（Opus の書き漏れ）。
- 道具の本物の接続は psycopg2（backend/app/tasks/tcg_extraction.py :90 で asyncpg を psycopg2 に置き換えて `create_engine`）。
- 直し（backend/tests/test_tx_guard_pool.py だけ）: 試験A・B の `create_engine(url, pool_size=1, max_overflow=0)` を2か所とも `create_engine(url.set(drivername="postgresql+psycopg2"), pool_size=1, max_overflow=0)` にする。ほかは変えない。backend/app/tools/_tx_guard.py は変えない。
- 確かめ: ruff check を流す。CI で試験A・B が passed であること。§6 の分かれ道はそのまま使う。
