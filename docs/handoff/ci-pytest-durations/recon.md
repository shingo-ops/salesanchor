# recon: CI の pytest で「遅い試験の一覧」が出ていない件

調査日: 2026-11-26（Opus）。根拠は `git show origin/main:<path>`（origin/main f11b1dc3b 以降）とクラウドでの実測。

## 背景（PO 2026-11-26）
- CI の必須チェック「pytest (SQLite + PostgreSQL RLS)」の実体 `pytest-run-internal` は `timeout-minutes: 15`（`.github/workflows/test.yml:125`）。PO への前回報告で、時間が上限に近づいていると伝えた。
- 遅い試験を探すため、クラウドで測った（下記）。その結果が CI と同じかは分からない。PO は「1」= CI の記録に遅い試験30件を毎回出す、を選んだ。

## 既存 ADR の検索結果
- `git grep -i "durations" origin/main -- docs/adr .github backend/pyproject.toml` → 0件。遅い試験の一覧を出す決まりは無い。
- 試験の流し方の設定の正本は `backend/pyproject.toml:45-` の `[tool.pytest.ini_options]`。`backend/pyproject.toml:65` が `addopts = "-n auto --dist=loadfile --cov=app --cov-report=term-missing --cov-fail-under=60"`。

## 現在の CI（事実）
- `.github/workflows/test.yml:224` の段「Run pytest (full suite + PostgreSQL RLS)」の実行行は `.github/workflows/test.yml:259` の `pytest -q --tb=short` の1行だけ。`--durations` は無い。
- この行を参照している箇所は `git grep -n "pytest -q --tb=short" origin/main -- .github scripts docs/specs` で test.yml:259 の1件だけ。
- `.github/workflows/test.yml` の変更は、それ自体で pytest を流す（`detect-changes` の filter に `.github/workflows/test.yml` がある: `.github/workflows/test.yml:54`）。push の paths にも入っている（同 :27）。
- CI は Redis を横で動かし `REDIS_URL: redis://localhost:6379/0` を渡している（`.github/workflows/test.yml:251`）。

## クラウドでの実測（2026-11-26・Sonnet・SQLite のみ・nproc 4・HEAD 295bc608a）
- 全体 real 7m41s（coverage あり）/ 6m54s（なし）。2 failed・652 errors が出た。errors は _pg・integration 系の試験に集中（PostgreSQL が無いためかは未確認）。
- ファイル別の合計: `test_webhook_instagram` 381.3 秒（38件・合計712.4秒の約54%）、`test_line_source_names` 38.2 秒、`test_conversation_unify_bin1` 19.2 秒。
- 1件ずつは 38.1 秒・19.0 秒にそろう。どこかへの接続待ちの形。
- 生の書き写し: /tmp/CC報告ファイル/pytest-durations-cloud-20261126.md（リポジトリ外）

## 推測（確かめていない）
- 補助の仕組み Redis の既定の住所は `redis://redis:6379/0`（`backend/app/cache.py:12`）。クラウドでは REDIS_URL を渡していないので、`redis` という名前を引きに行って待った可能性がある。CI では localhost の Redis があるので、この待ちは出ない可能性がある。

## 未確認
- CI で本当に遅い試験の順位。CI の記録には試験ごとの時間が出ていない（このため本件を行う）。

## pytest の仕様（Context7: /pytest-dev/pytest）
- `--durations=N` は遅い setup/試験を N 件出す。`--durations-min` の既定は 0.005 秒（reference.rst）。
- pytest-xdist（`-n auto`）と一緒でも一覧が出ることは、上のクラウド実測（`--durations=60` を付けて上位が出た）で確認済み。
