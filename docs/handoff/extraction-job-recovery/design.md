# design：抽出ジョブの停滞回収

- 作成：2026-09-30（設計：Opus 設計担当 ／ 実装：Claude Sonnet 5 実装担当）
- 関連 ADR：ADR-1003（GO委任）
- recon: `docs/handoff/extraction-job-recovery/recon.md`

## §A 事実

recon.md 参照。要点のみ再掲する。

- `backend/app/celery_app.py:52-55`：`worker_prefetch_multiplier=1`、`task_acks_late=True`、`task_reject_on_worker_lost=True`。`broker_transport_options` はない。
- `backend/app/tasks/tcg_extraction.py` の `tcg.extract_source_message`：`max_retries=2`、`time_limit=330`、`soft_time_limit=300`。`_run_extraction` は `status='pending'` のジョブだけを拾う（224-249行目）。
- `docker-compose.yml:197-262` の celery-worker には、`stop_grace_period` と `stop_signal` がない。`--concurrency=2`。
- `.github/workflows/deploy.yml:332-335`：`docker ps -a --filter name=astro-webapp-${_svc} | xargs -r docker rm -f` で強制削除してから `docker compose up -d`。キューが空になるのを待つ処理はない。
- 停滞ジョブを自動で直す beat タスクはない。`backend/app/services/tcg_diagnostics_svc.py:91-100` の `extraction-running-stale` は、読み取りの診断だけ。
- 本番（2026-09-30）：直近7日の attempt 所要時間は p50 2.4 秒、p90 5.3 秒、最大 31.9 秒（1,142 件）。deploy.yml は 09-24 09:02 から 09-30 03:24 までに 51 回。9/30 03:29 のデプロイで、pending 5 件と running 1 件が取り残された。

## §B 変更

1. **停滞ジョブの回収タスク（新規）**：`backend/app/tasks/tcg_extraction_recovery.py`
   - Celery タスク `tcg.recover_stale_extraction_jobs` を作り、beat で10分ごとに動かす。
   - 回収の条件は定数でまとめる：`STALE_RUNNING_MINUTES=15`、`STALE_PENDING_MINUTES=15`、`MAX_RECOVER_PER_RUN=50`。
     - 根拠は §A（最大 32 秒、time_limit 330 秒）。実行中の attempt が15分を超えることは、time_limit 上ありえない。
   - (a) running のジョブで、最新の attempt の `started_at` から15分以上たったもの（attempt がなければ `created_at` から15分以上）を pending に戻す。
     - `UPDATE public.extraction_jobs SET status='pending' WHERE id = ANY(:ids) AND status='running'`
   - (b) pending のジョブで、`created_at` から15分以上たち、最新の attempt が無いか、あっても15分以上前に始まったものを見つけたら、**停滞している pending の ID だけを**、`retry_extraction`（`backend/app/services/tcg_diagnostics_svc.py`）の手順4（`extract_source_message_task.apply_async(args=(source_message_id,), countdown=i*_COUNTDOWN_STEP)`）と同じ方法で投入する。
     - `retry_extraction` 自体（`_ELIGIBLE_STATUSES={"error"}` と `scope="pending"` の経路）は変えない・呼ばない。`scope="pending"` は status='pending' の**全件**を対象にしてしまい、正常にキューで待っている新しいジョブまで巻き込んで二重投入する恐れがあるため（設計担当レビュー指摘）。
     - 対象ジョブの `source_message_id` は `WHERE id = ANY(:ids) AND status = 'pending'` で再取得する（判定後に状態が変わった行を除外するため）。
     - ステータスは変えない（対象は既に pending のまま）。
     - `retry_extraction` と同様、`AsyncSession` を要求する処理なので、`backend/app/tasks/tcg_extraction.py:610-642`（`auto_distribute_after_analysis_task`）と同じパターン（ワンショット `create_async_engine`/`async_sessionmaker` ＋ `asyncio.run()`）で呼ぶ。
     - 最大 `MAX_RECOVER_PER_RUN` 件。古いものから（`retry_extraction` 内部の `_MAX_JOBS=50` と一致させる）。
   - 回収した件数と ID を `logger.warning` で出す。
   - DB の表や列は増やさない。
   - 見分けに使うのは、既存の `extraction_jobs` の `status` と `extraction_attempts` だけ。

2. **beat への登録**：`backend/app/celery_app.py` の `beat_schedule` に `recover-stale-extraction-jobs` を足す。10分ごと（`schedule=600.0`、既存の `refresh-dashboard-kpis` と同じ書式）。

3. **止め方をていねいにする**：
   - `docker-compose.yml` の celery-worker に、`stop_signal: SIGTERM` と `stop_grace_period: 60s` を足す。
   - `.github/workflows/deploy.yml:332-335` のループは、今 celery-worker も含めて一律 `docker rm -f` している。
   - これを「celery-worker だけは、先に `docker compose stop -t 60 celery-worker` で止めて（warm shutdown で実行中のタスクを終えさせる）、そのあと rm する」に変える。
   - ループの対象からは celery-worker を外し、`frontend celery-beat discord-gateway` の3つだけを従来どおり force-rm する。celery-worker は事前に `stop -t 60` してから、同じループの外で rm する。
   - ほかのサービス（frontend / celery-beat / discord-gateway）の扱いは変えない。変更は最小にする。

## §C 検証（基準と方法）

| # | 基準 | 方法 |
|---|---|---|
| T1 | 15分未満の running と pending は触らない | 単体テスト |
| T2 | 15分以上の running は pending に戻り、そのあと再投入される | 単体テストまたは pg テスト |
| T3 | 1回に回収するのは最大50件 | 単体テスト |
| T4 | beat に10分ごとで登録されている | テスト |
| V1 | 本番に反映したあと、beat が登録されている | celery inspect／beat のログ |
| V2 | 反映したあと30分以内に、pending・running が15分以上残っていない | 本番 DB の読み取り |

## §D リスク・戻し方

- 実行中のジョブを誤って二重に動かすリスクについて：time_limit が 330 秒なので、15分以上実行中のものは実在しない。
- pending の二重投入リスクについて：`retry_extraction(scope="pending")` を呼ばず、停滞している job_ids だけに限定して `extract_source_message_task.apply_async` を呼ぶため、正常にキューで待っている新しい pending ジョブを巻き込まない（設計担当レビューで指摘・修正）。
- 戻し方：この PR を revert する。

## 維持の仕組み

- 守り手: Opus 設計担当（しきい値の見直し）／PO（運用の判断）
- しきい値（`STALE_RUNNING_MINUTES`・`STALE_PENDING_MINUTES`・`MAX_RECOVER_PER_RUN`）は定数としてモジュール冒頭にまとめ、根拠のコメントを§Aへのリンクとして残す。将来 `time_limit` を変更する場合は、このファイルのコメントが変更点を示す。
- beat 登録のテスト（T4）があるため、`beat_schedule` からの削除・書式崩れは CI で検知される。
- 回収件数と ID を `logger.warning` で出すため、本番ログ（Loki/Promtail 経由）で回収の発生を事後に確認できる（V1/V2 の裏付け）。

## 外部・過去事例

- 該当なし。社内の既存パターン（`backend/app/tasks/tcg_import_discard.py` の期限切れ回収タスク、`backend/app/tasks/tcg_extraction.py:610-642` の Celery→非同期サービス呼び出しパターン）を根拠にした。Celery の stale task 回収は Celery 公式ドキュメントの `task_acks_late`/`worker_prefetch_multiplier` の推奨設定（本リポジトリは既に採用済み、recon.md 参照）に沿う一般的な対処であり、外部の失敗事例調査は本件の変更規模（既存パターンの組み合わせ）に対して不要と判断した。

## 追記（2026-10-17）解析失敗のやり直し
同じ10分ごとの回収に、解析段で失敗した v102 job（status='done' かつ error_message='ANALYSIS_FAILED'）を1回だけ再解析に積む段を足した。新しい表・列は増やしていない。詳細: docs/handoff/analysis-failed-record/design.md

## 追記（2026-11-13）試験が時々落ちる件の直し（区分 B-3: 試験と正本でない文書だけ）
事実は recon.md「追記（2026-11-13）」。審査の記録は review-opus.md。

### KGI（ADR-1015 B 区分のため PO 承認は不要。AI が書いて残す）
- K1: `test_tcg_extraction_recovery_pg.py` の7件が、試験全体の長さに関係なく、時刻の境目で落ちない。判定: 下の T1〜T3。
- K2: 試験ファイルの読み込みのときに「今」を読む書き方（一番外・クラスの本体・その中の if/try/with/for・デコレータの引数・関数と lambda の既定値）が、試験全体（backend/tests 配下）で 0 か所。新しく書かれたら CI の Backend Tests が赤になる。判定: T4・T5。
- K3: マージ後14日（〜2026-11-27）、Backend Tests の失敗のうち `test_tcg_extraction_recovery_pg.py` が原因のものが 0 回。判定: T6。

### 直し方（選んだ案）
1. `test_tcg_extraction_recovery_pg.py` は、試験本体の始めに **DB の時計**（`SELECT clock_timestamp()`）を読み、それを基準に行を作る。判定側も DB の `NOW()` を使うので、同じ時計どうしで比べることになる。基準を読んでから判定までは、行を入れて1回 SELECT するだけ（ミリ秒の単位）。
2. `test_viewer_api.py` の `NOW` も、使う所で毎回作る形にする（実害は無いが、K2 の見張りを例外なしにするため）。
（審査1 REVISE の指摘で、3 と 4 の見張りの範囲を広げた。記録は review-opus.md）
3. `test_line_import_devices.py` のデコレータの引数の `svc.now()` 2か所も、時刻を読まない形にする（実害は無いが、K2 の見張りを例外なしにするため）。「過去の時刻」の意味は固定の過去日 `_PAST` で保ち、「1秒前に切れた」の意味は試験本体で時刻を読む新しい試験1件で保つ。
4. 見張りの試験 `backend/tests/test_no_import_time_clock.py` を新しく足す。backend/tests 配下の全 .py を `ast` で読み、読み込みのときに評価される所（一番外とクラスの本体の文・その中の if/try/with/for の中・デコレータの引数・関数と lambda の既定値）で時計を読む呼び出しがあれば、ファイル名と行番号を並べて落とす。時計を読む呼び出しは `.now()`・`.utcnow()`・`.today()`、`time.` の `time`・`time_ns`・`monotonic`・`monotonic_ns`・`perf_counter`・`perf_counter_ns`、`from time import …` で取り込んだ同じ名前（別名を含む）。関数と lambda の本体は数えない（呼ばれたときに動くため）。

### 採らなかった案
- しきい値の15分を試験で小さくする／大きくする: 試験全体の長さは増え続けるので、いつかまた超える。根本の「時刻が古くなる」は直らない。
- 時刻を止める道具（freezegun 等）を入れる: 判定は DB の `NOW()` で、Python の時計を止めても効かない。依存も増える。
- Python の `datetime.now()` を試験本体で読む: 経過の問題は消えるが、CI の DB と Python の時計の差が残る。DB の時計なら差が無い。

### 変更前後（実装役はこのとおりに書く）
`backend/tests/test_tcg_extraction_recovery_pg.py`
- 11行目 `from datetime import datetime, timedelta, timezone` → `from datetime import timedelta`
- 20行目 `_NOW = datetime.now(timezone.utc)` を消し、次の関数に置き換える:
```python
def _db_now(connection):
    """DB の時計で「今」を読む。判定側（NOW()）と同じ時計にするため、試験本体の始めで毎回読む。"""
    with connection.cursor() as cur:
        cur.execute("SELECT clock_timestamp()")
        return cur.fetchone()[0]
```
- 7つの試験すべてで、`connection, _, _ = pg` の次の行に `now = _db_now(connection)` を足し、その試験の中の `_NOW` を `now` に置き換える（対象行: 61・62・76・77・94・110・124・138・139・155）。ほかの行は変えない。

`backend/tests/test_viewer_api.py`
- 34行目 `NOW = datetime.now(timezone.utc)` を消す。
- 311・313・347行目の `NOW` を `datetime.now(timezone.utc)` に置き換える。ほかは変えない。

`backend/tests/test_line_import_devices.py`
- 1行目 `from datetime import timedelta` → `from datetime import datetime, timedelta, timezone`
- 14行目 `TOKEN = ...` の次の行に足す: `_PAST = datetime(2000, 1, 1, tzinfo=timezone.utc)  # 固定の過去日。読み込みのときに時計を読まないため`
- 25行目 `('revoked_at', svc.now())` → `('revoked_at', _PAST)`
- 26行目 `('expires_at', svc.now()-timedelta(seconds=1))` → `('expires_at', _PAST)`
- `test_invalid_grants_denied` の次に、この試験を足す:
```python
def test_just_expired_grant_denied():
    # 1秒前に切れた鍵も拒否する（時刻は試験本体で読む）。
    assert not svc.valid(row(expires_at=svc.now() - timedelta(seconds=1)))
```
- ほかの行は変えない。

`backend/tests/test_no_import_time_clock.py`（新規）
```python
"""試験ファイルの読み込みのときに「今」を読む書き方を止める。

読み込みのときに決めた時刻は、試験全体が長くなるほど古くなる。時刻の境目を確かめる試験が時々落ちる
（2026-11-11〜13 に3回。docs/handoff/extraction-job-recovery/recon.md「追記（2026-11-13）」）。
読み込みのときに動くのは、一番外とクラスの本体（if/try/with/for の中も）・デコレータの引数・
関数と lambda の既定値。関数と lambda の本体は呼ばれたときに動くので見ない。
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent
_CLOCK_ATTRS = {"now", "utcnow", "today"}
_TIME_FUNCS = {
    "time", "time_ns", "monotonic", "monotonic_ns", "perf_counter", "perf_counter_ns",
}


def _time_names(tree: ast.Module) -> set[str]:
    """from time import time などで取り込んだ名前（別名を含む）。"""
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "time":
            for alias in node.names:
                if alias.name in _TIME_FUNCS:
                    names.add(alias.asname or alias.name)
    return names


def _is_clock_call(node: ast.AST, time_names: set[str]) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in _CLOCK_ATTRS:
            return True
        if func.attr in _TIME_FUNCS and isinstance(func.value, ast.Name) and func.value.id == "time":
            return True
    if isinstance(func, ast.Name) and func.id in time_names:
        return True
    return False


def _import_time_nodes(node: ast.AST):
    """読み込みのときに評価される式の木を返す。関数と lambda は本体を飛ばし、既定値とデコレータだけ見る。"""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        yield from node.decorator_list
        yield from node.args.defaults
        yield from (d for d in node.args.kw_defaults if d is not None)
        return
    if isinstance(node, ast.Lambda):
        yield from node.args.defaults
        yield from (d for d in node.args.kw_defaults if d is not None)
        return
    yield node


def _clock_lines(tree: ast.Module) -> list[int]:
    time_names = _time_names(tree)
    lines = []
    stack: list[ast.AST] = list(tree.body)
    while stack:
        cur = stack.pop()
        for part in _import_time_nodes(cur):
            if part is not cur:
                stack.append(part)
                continue
            if _is_clock_call(cur, time_names):
                lines.append(cur.lineno)
            stack.extend(ast.iter_child_nodes(cur))
    return sorted(set(lines))


def _findings() -> list[str]:
    found = []
    for path in sorted(TESTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line in _clock_lines(tree):
            found.append(f"{path.relative_to(TESTS)}:{line}")
    return found


_SELF_CHECKS = [
    ("_NOW = datetime.now(timezone.utc)", True),
    ("T = time.time()", True),
    ("D = date.today() - timedelta(days=1)", True),
    ("from time import time as t\nX = t()", True),
    ("X: float = time.monotonic()", True),
    ("if True:\n    N = datetime.now()", True),
    ("try:\n    N = datetime.now()\nexcept Exception:\n    pass", True),
    ("@pytest.mark.parametrize('v', [svc.now()])\ndef test_a(v):\n    pass", True),
    ("def f(t=datetime.now()):\n    pass", True),
    ("class C:\n    N = datetime.utcnow()", True),
    ("f = lambda t=datetime.now(): t", True),
    ("f = lambda: datetime.now()", False),
    ("def test_a():\n    n = datetime.now()", False),
    ("X = timedelta(minutes=5)", False),
    ("class C:\n    def m(self):\n        return time.time()", False),
]


def test_detector_catches_the_pattern():
    for source, expected in _SELF_CHECKS:
        assert bool(_clock_lines(ast.parse(source))) is expected, source


def test_no_clock_read_at_import_time():
    found = _findings()
    assert found == [], (
        "試験ファイルの読み込みのときに時刻を読んでいます。試験本体の中で読んでください"
        "（読み込み時の時刻は試験全体が長いほど古くなり、時刻の境目の試験が時々落ちます）: "
        + ", ".join(found)
    )
```

### 検証（基準と方法）
| # | 基準 | 方法 |
|---|---|---|
| T1 | 回収の試験7件が合格し、飛ばされていない | CI は `pytest -q` で試験ごとの行が出ない（recon 追記）。そのため PR の Backend Tests の最後の合計の1行を、PR の土台（merge-base）の main の push run の合計の1行と比べる（Opus）。判定: `failed` が無い、`skipped` が同じ数、`passed` がちょうど +3（見張り2件と「1秒前に切れた」1件）。土台と PR の間に main へ試験が足されていたら、その数を `git diff --stat` で数えて差に足し、計算を記録に残す |
| T2 | `_NOW` がファイルに残っていない | `grep -n "_NOW" backend/tests/test_tcg_extraction_recovery_pg.py` が 0 件 |
| T3 | 試験の中身（行の古さ・期待）は変えていない | diff で、変わった行が上の「変更前後」の対象行と import と関数・試験1件の足しだけであること（reviewer） |
| T4 | 見張りが今の試験全体で 0 件 | `pytest backend/tests/test_no_import_time_clock.py backend/tests/test_line_import_devices.py backend/tests/test_viewer_api.py -p no:cacheprovider -o addopts=""` 合格（実装役の手元。生出力を報告に）と CI |
| T5 | 見張りが本当に止める | `test_detector_catches_the_pattern`（15例: 拾うべき11・拾わない4）合格。加えて実装役が一時的に `test_tcg_extraction_recovery_pg.py` の一番外へ `_NOW = datetime.now(timezone.utc)` を足して `test_no_clock_read_at_import_time` が赤になり行番号が出ることを確かめ、戻す（報告に生出力。戻したことは `git diff` で示す） |
| T6 | 14日間落ちない | 2026-11-27 に Opus が数える: `gh run list --workflow test.yml --status failure --created 2026-11-13..2026-11-27 --limit 500 --json databaseId,createdAt` で全件を取り、件数が 500 未満であることを確かめる。各 run を `gh run view <id> --log-failed` で読み、`test_tcg_extraction_recovery_pg.py` を含む run の数を数える（このPRのマージより前の run は除く）。生出力は `/tmp/CC報告ファイル/flaky/` に残す。0 なら合格 |

### リスクと戻し方
- `clock_timestamp()` が返す時刻は psycopg2 で時差つきの datetime になる。`timedelta` を引いて INSERT する使い方は今と同じ。
- 見張りが関係ない書き方を拾うおそれ: 設計担当が上の見張りの中身をそのまま c296af3bb の backend/tests 全470ファイル（`git archive` で取り出したもの）に当てた結果は `['test_line_import_devices.py:25', 'test_line_import_devices.py:26', 'test_tcg_extraction_recovery_pg.py:20', 'test_viewer_api.py:34']` の4件だけで、どれも上で直す所。読めないファイルは0件。自己点検の15例もすべて期待どおりだった（生出力 `/tmp/CC報告ファイル/flaky/detector-v2-probe.txt`）。拾ったら行番号が出るので、その場で直せる。
- 見張らない形（わざと対象外）: `time.time` を別の名前の変数に入れてから呼ぶ形、`datetime` 以外のライブラリの時計（`pendulum` 等。今の試験では使っていない）、`exec`・`eval` の中。拾える形を増やすほど誤検知の危険が増えるので、実際に起きた形と、その近い仲間だけを見る。
- 実装の土台が main の新しい版になったとき、新しく足された試験に同じ書き方があれば見張りが赤にする。その場合、実装役は止めて Opus に報告する（勝手に直す範囲を広げない）。
- 戻し方: この PR を revert する。本番のコードは触らない。

### 維持の仕組み
- 守り手: `backend/tests/test_no_import_time_clock.py`（CI の Backend Tests の一部。必須チェック）
- 対象: 試験ファイルの読み込みのときに時刻を決める書き方
- 14日後の数え直し（T6）は Opus が台帳に予定として残す。

### 外部・過去事例
- 該当なし（理由: 試験の作り方の小さな直しで、社内の実際の失敗3回の記録が直接の根拠になる。外の事例で判断が変わる所が無い）。
