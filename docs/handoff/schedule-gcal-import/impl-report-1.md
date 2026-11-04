# impl-report-1: celery-worker に Google 取り込みの設定4つを渡す

指示書: `docs/handoff/schedule-gcal-import/fix-worker-env.md`（§3・§3-1 のみ実施）

## 作業場所と起点

- 枝: `release/gcal-worker-env`
- `git rev-parse HEAD`（作業開始時の先頭）: `c17beebc8b3700878735e13d75c6a9799d6b3a1c`（`origin/release/gcal-worker-env` と一致・指定どおり c17beebc8）
- 変更の commit: `b6989f5f083203dbb99e570a99bf9d7e186216e6`（最終 HEAD はこの報告を足した commit。push 後に `git rev-parse HEAD` で得られる）

## 変更

- `docker-compose.yml`: celery-worker の environment の `MAIL_FROM` の次（288 行の次）に、注釈4行と設定4行を指示書どおり追加
- `backend/tests/test_compose_worker_env.py`: 新規。REQUIRED 4つの存在確認と、`google_calendar.py` の `os.getenv("NAME"` を全部拾って worker に渡っているかの確認の2試験
- celery-beat・deploy.yml・scripts・google_calendar_sync.py は触っていない

## PyYAML か素朴な読み方か

PyYAML（`yaml.safe_load`）を使った。`backend/requirements*.txt` に直接の記載は無いが、requirements-dev.txt の bandit が引き込み、既存の `backend/tests/test_secretary_agent_compose.py` も `import yaml` している。素朴な読み方は不要と判断。

## 確かめ

入れたコマンド（python3.12 の venv をスクラッチパッドに作成。py312-guard のため）:

```
python3.12 -m venv <scratchpad>/venv
<venv>/bin/pip install pytest pyyaml
<venv>/bin/pip install pytest-xdist pytest-cov
<venv>/bin/pip install -r requirements.txt -r requirements-dev.txt
```

試験の流し方: `python -m pytest tests/test_compose_worker_env.py -v -p no:cacheprovider --no-cov -n0`（backend ディレクトリ）

### (1) 通ること（tail）

```
tests/test_compose_worker_env.py::test_worker_has_required_google_calendar_env PASSED [ 50%]
tests/test_compose_worker_env.py::test_worker_has_every_env_read_by_google_calendar_service PASSED [100%]

============================== 2 passed in 0.14s ===============================
```

### (2) GOOGLE_CALENDAR_CLIENT_SECRET の1行だけ消す → 落ちる（tail）

```
E       AssertionError: google_calendar.py が読むのに worker に渡っていない: ['GOOGLE_CALENDAR_CLIENT_SECRET']
E       assert not {'GOOGLE_CALENDAR_CLIENT_SECRET'}

tests/test_compose_worker_env.py:48: AssertionError
=========================== short test summary info ============================
FAILED tests/test_compose_worker_env.py::test_worker_has_required_google_calendar_env
FAILED tests/test_compose_worker_env.py::test_worker_has_every_env_read_by_google_calendar_service
============================== 2 failed in 0.17s ===============================
```

Edit で元に戻し（`git checkout` は不使用）、再実行（tail）:

```
tests/test_compose_worker_env.py::test_worker_has_required_google_calendar_env PASSED [ 50%]
tests/test_compose_worker_env.py::test_worker_has_every_env_read_by_google_calendar_service PASSED [100%]

============================== 2 passed in 0.12s ===============================
```

### (3) yaml として読める（tail）

```
yaml OK 37
```

（`yaml.safe_load` で読み、celery-worker の environment が 37 項目）

## git diff --stat origin/main（コード commit b6989f5f0 時点）

```
 backend/tests/test_compose_worker_env.py           | 48 ++++++++++++
 docker-compose.yml                                 |  8 ++
 .../handoff/schedule-gcal-import/fix-worker-env.md | 90 ++++++++++++++++++++++
 3 files changed, 146 insertions(+)
```

fix-worker-env.md は起点 c17beebc8 にすでにある指示書（この便の変更ではない）。

## 注意

- ローカル全体の試験・pre-push の結果は push 時の出力に従う。
- 本番反映後の G1〜G5 は未確認（この便の範囲外）。

DONE
