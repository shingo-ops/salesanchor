# impl-report-3: 権限の一覧に無いキーの見張り（便2）

- 枝: release/permission-keys-watch-code（new-worktree.sh で origin/main から作成）
- git rev-parse origin/main: db715ffced42d93fab101c20b2370f03cce7b096

## §0 点検（grep -n 生出力）
```
646:def require_permission(*permission_keys: str):
655:    required: set[str] = set(permission_keys)
672:    checker.required_permission_keys = frozenset(required)  # type: ignore[attr-defined]
81:async def _update_viewer_inventory_gauges() -> None:
115:    async def metrics_middleware(request: Request, call_next):
134:    async def metrics() -> Response:
152:        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
36:AsyncSessionLocal = sessionmaker(
55:  - name: application_alerts
6:rule_files:
7-  - ../alert_rules.yml
347:## OpsMailPollStale
71:      - name: Prometheus ルール構文と単体試験（promtool）
75:          docker run --rm -v "$PWD/monitoring/prometheus:/r:ro" --entrypoint promtool prom/prometheus:v3.11.3 check rules /r/alert_rules.yml
76:          docker run --rm -v "$PWD/monitoring/prometheus:/r:ro" --entrypoint promtool prom/prometheus:v3.11.3 test rules /r/tests/alert_rules_test.yml
```
想定どおり。

## venv に入れたコマンド
```
python3.12 -m venv /tmp/venv312
/tmp/venv312/bin/pip install -q -r backend/requirements.txt pytest pytest-asyncio httpx aiosqlite pytest-xdist pytest-cov
```

## git diff --stat origin/main（コード commit a1a1449a5 時点）
```
 backend/app/auth/dependencies.py                 |   6 ++
 backend/app/auth/permission_catalog.py           |  24 +++++
 backend/app/metrics.py                           |  39 ++++++++
 backend/tests/test_permission_catalog.py         | 111 +++++++++++++++++++++++
 docs/runbooks/alerts.md                          |  18 ++++
 monitoring/prometheus/alert_rules.yml            |  24 +++++
 monitoring/prometheus/tests/alert_rules_test.yml |  56 +++++++++++-
 7 files changed, 277 insertions(+), 1 deletion(-)
```

## §3 出力（pytest は coverage 表が長いので末尾 4 行だけ。coverage 閾値の FAIL 行は一部実行のため失敗に数えない）
### 順 1: test_permission_catalog.py → test_conditions_permission_keys.py
```
----------------------------------------------------------------------------------
TOTAL                                                45971  32446    29%
FAIL Required test coverage of 60% not reached. Total coverage: 29.42%
11 passed, 2 warnings in 23.83s
```
### 順 2: 逆順
```
----------------------------------------------------------------------------------
TOTAL                                                45971  32446    29%
FAIL Required test coverage of 60% not reached. Total coverage: 29.42%
11 passed, 2 warnings in 22.79s
```
### check_alert_rules.py（rc=0）
```
OK: Prometheus 36 rules, Loki 6 rules, runbook 42 sections
```
promtool: クラウドに無いので流していない（GitHub の監視スタック整合性チェックが流す）。
### check-before-submit.sh（rc=0・末尾 25 行）
```
  ○ check-dangling-routes                               1.0 秒
  ○ test-dangling-routes                                0.2 秒
  ○ check-lessons-section                               0.0 秒
  ○ check-migration-registration-exists                 0.0 秒
  ○ test-migration-registration-exists                  0.1 秒
  ○ migration-value-writes diff --check 7               0.0 秒
  ○ migration-value-writes diff --check 8               0.0 秒
  ○ migration-value-writes repo                         0.1 秒
  ○ test_migration_value_writes                         5.7 秒
  - check-migration-column-churn                     流していない: 関連パスの変更なし（CI と同じ条件で対象外）
  - check-migration-duplicate-registration           流していない: 関連パスの変更なし（CI と同じ条件で対象外）
  ○ check-doc-heading-duplicates                        0.0 秒
  ○ test_check_rule_registry                            1.0 秒
  ○ 見本の選別（case.json）                      0.0 秒
  - test-guard-evaluations (node --test)             流していない: CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    流していない: CI で確かめる（約 375 秒。--full で流せます）

== 版の違い（手元と CI）==
  手元: Python 3.11.18 / node v22.23.4
  CI  : Python 3.12 / node 22（guard-authoring だけ 24）
  版が違うので、最後の判定は CI です（この入口は提出前の補助）

合計 10.2 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.lRl1AN（消さずに残します）
結果: ○ 流した検査は全部通りました（終了コード 0）
流した印を書きました: /home/user/salesanchor/.git/worktrees/release-permission-keys-watch-code/check-before-submit.ok
```

## 最終 HEAD
- コード commit: a1a1449a5ba32bd74fe7a14f58660c5f256699f6（この報告は次の commit で足す。push 後の HEAD は git rev-parse origin/release/permission-keys-watch-code で確認）

DONE
