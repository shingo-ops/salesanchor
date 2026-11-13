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
- K2: 試験ファイルの一番外で「今」を1回だけ決める書き方が、試験全体（backend/tests 配下）で 0 か所。新しく書かれたら CI の Backend Tests が赤になる。判定: T4・T5。
- K3: マージ後14日（〜2026-11-27）、Backend Tests の失敗のうち `test_tcg_extraction_recovery_pg.py` が原因のものが 0 回。判定: T6。

### 直し方（選んだ案）
1. `test_tcg_extraction_recovery_pg.py` は、試験本体の始めに **DB の時計**（`SELECT clock_timestamp()`）を読み、それを基準に行を作る。判定側も DB の `NOW()` を使うので、同じ時計どうしで比べることになる。基準を読んでから判定までは、行を入れて1回 SELECT するだけ（ミリ秒の単位）。
2. `test_viewer_api.py` の `NOW` も、使う所で毎回作る形にする（実害は無いが、K2 の見張りを例外なしにするため）。
3. 見張りの試験 `backend/tests/test_no_import_time_clock.py` を新しく足す。backend/tests 配下の全 .py を `ast` で読み、モジュールの一番外とクラスの本体（読み込みのときに実行される所）にある代入の右辺が `.now()`・`.utcnow()`・`.today()`・`time.time()` を呼んでいたら、ファイル名と行番号を並べて落とす。`lambda` と `def` の中は数えない（呼ばれたときに動くため）。

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

`backend/tests/test_no_import_time_clock.py`（新規）
```python
"""試験ファイルの読み込みのときに「今」を1回だけ決める書き方を止める。

読み込みのときに決めた時刻は、試験全体が長くなるほど古くなる。時刻の境目を確かめる試験が時々落ちる
（2026-11-11〜13 に3回。docs/handoff/extraction-job-recovery/recon.md「追記（2026-11-13）」）。
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent
_CLOCK_METHODS = {"now", "utcnow", "today"}


def _calls_clock(node: ast.AST) -> bool:
    """node の中で時計を読む呼び出しがあれば True。lambda と関数の中は呼ばれたときに動くので数えない。"""
    stack = [node]
    while stack:
        cur = stack.pop()
        if isinstance(cur, (ast.Lambda, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(cur, ast.Call) and isinstance(cur.func, ast.Attribute):
            if cur.func.attr in _CLOCK_METHODS:
                return True
            if cur.func.attr == "time" and isinstance(cur.func.value, ast.Name) and cur.func.value.id == "time":
                return True
        stack.extend(ast.iter_child_nodes(cur))
    return False


def _import_time_assignments(body: list[ast.stmt]):
    """読み込みのときに実行される代入（モジュールの一番外とクラスの本体）を返す。"""
    for stmt in body:
        if isinstance(stmt, ast.ClassDef):
            yield from _import_time_assignments(stmt.body)
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)) and stmt.value is not None:
            yield stmt


def _findings() -> list[str]:
    found = []
    for path in sorted(TESTS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for stmt in _import_time_assignments(tree.body):
            if _calls_clock(stmt.value):
                found.append(f"{path.relative_to(TESTS)}:{stmt.lineno}")
    return found


def test_detector_catches_the_pattern():
    assert _calls_clock(ast.parse("_NOW = datetime.now(timezone.utc)").body[0].value)
    assert _calls_clock(ast.parse("T = time.time()").body[0].value)
    assert _calls_clock(ast.parse("D = date.today() - timedelta(days=1)").body[0].value)
    assert not _calls_clock(ast.parse("f = lambda: datetime.now()").body[0].value)
    assert not _calls_clock(ast.parse("X = timedelta(minutes=5)").body[0].value)


def test_no_clock_read_at_import_time():
    found = _findings()
    assert found == [], (
        "試験ファイルの読み込みのときに時刻を決めています。試験の中で毎回読んでください"
        "（DB と比べるなら SELECT clock_timestamp()）: " + ", ".join(found)
    )
```

### 検証（基準と方法）
| # | 基準 | 方法 |
|---|---|---|
| T1 | 回収の試験7件が合格する | CI の Backend Tests（pg 試験は CI でだけ動く）。PR の run のログで7件の PASSED を数える |
| T2 | `_NOW` がファイルに残っていない | `grep -n "_NOW" backend/tests/test_tcg_extraction_recovery_pg.py` が 0 件 |
| T3 | 試験の中身（行の古さ・期待）は変えていない | diff で、変わった行が上の対象行と import と関数の足しだけであること（reviewer） |
| T4 | 見張りが今の試験全体で 0 件 | `pytest backend/tests/test_no_import_time_clock.py` 合格（実装役の手元とCI） |
| T5 | 見張りが本当に止める | `test_detector_catches_the_pattern` 合格。加えて実装役が一時的に `_NOW = datetime.now(timezone.utc)` を足して赤になることを確かめ、戻す（報告に生出力） |
| T6 | 14日間落ちない | 2026-11-27 に `gh run list --status failure` の Backend Tests を走査し、このファイルの FAILED を数える（Opus） |

### リスクと戻し方
- `clock_timestamp()` が返す時刻は psycopg2 で時差つきの datetime になる。`timedelta` を引いて INSERT する使い方は今と同じ。
- 見張りが関係ない書き方を拾うおそれ: 設計担当が上の見張りの中身をそのまま c296af3bb の backend/tests 全478ファイルに当てた結果は `['test_tcg_extraction_recovery_pg.py:20', 'test_viewer_api.py:34']` の2件だけで、読めないファイルは0件。自己点検の5件も期待どおりだった。拾ったら行番号が出るので、その場で直せる。
- 戻し方: この PR を revert する。本番のコードは触らない。

### 維持の仕組み
- 守り手: `backend/tests/test_no_import_time_clock.py`（CI の Backend Tests の一部。必須チェック）
- 対象: 試験ファイルの読み込みのときに時刻を決める書き方
- 14日後の数え直し（T6）は Opus が台帳に予定として残す。

### 外部・過去事例
- 該当なし（理由: 試験の作り方の小さな直しで、社内の実際の失敗3回の記録が直接の根拠になる。外の事例で判断が変わる所が無い）。
