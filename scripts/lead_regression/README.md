# scripts/lead_regression

リードの成約しやすさ分析のテスト用データの作り方と、本番の外の確かめ（流し方だけ。決まりは `docs/handoff/lead-regression/card-a-backend.md`・`design.md`）。
どの道具も本番の DB には繋がない。出力先（`$SCRATCH`）はリポジトリの外にする（中なら `STOP:` で終了コード 2）。

## 前提

- Python 3.12 の venv（`python3.12 -m venv <場所>`）に `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`
- K3 の突き合わせ（statsmodels 0.15.0）は、使い捨ての環境にだけ入れる（requirements には足さない）

## 1. テスト用データの SQL を書き出す

    python3 -I scripts/lead_regression/generate.py --seed 20261101 --base-date 2026-11-01 --tenant-id 1 --mode dryrun --out "$SCRATCH/lead_insert.sql"
    python3 -I scripts/lead_regression/generate.py --seed 20261101 --base-date 2026-11-01 --tenant-id 1 --mode commit --out "$SCRATCH/lead_insert_commit.sql"

dryrun は最後が `ROLLBACK;`、commit は `COMMIT;`（ほかは 1 バイトも同じ）。

## 2. 書き込み先の点検（K5①(a)）

    python3 -I scripts/lead_regression/check_sql.py "$SCRATCH/lead_insert_commit.sql"
    python3 -I scripts/lead_regression/check_sql.py docs/handoff/lead-regression/sql/delete_tenant_001.sql --read-allow public.registration_tokens

`violations=0` なら合格。pytest（`backend/tests/test_lead_regression_generate.py`）でも毎回流れる。

## 3. 本番の外の確かめ K3

    python3 -I scripts/lead_regression/k3_run.py --out-dir "$SCRATCH/k3"

種 1〜200 固定。`k3_summary.txt`（K3a〜K3c の項目ごとの数、K3d の比べる側の 15 項目の β・幅）と `k3_results.json` を出す。

## 4. 試験

    cd backend
    python -m pytest tests/test_lead_conversion_factors.py tests/test_lead_regression_generate.py tests/test_analytics.py

PostgreSQL に SQL を流す試験は、使い捨ての PostgreSQL（localhost）の接続先を環境変数 `LEAD_REGRESSION_PG_URL`（`postgresql://...`）に入れたときだけ動く（無ければ skip）。
本番やほかの外部の接続先は入れない。

## 5. 消す SQL

`docs/handoff/lead-regression/sql/delete_tenant_001.sql`。PO 本人が流す（今回は流さない）。手順0 の記録を `-- 手順0 の記録をここに貼る` の場所に貼ってから流す。
