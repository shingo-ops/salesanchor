# impl-report-1: 便1-コード（状態マスタ CSV 取り込みを 3 権限で守る）

- origin/main の先頭: `996af2f0ebf1f7b66a1974c38cee85c8d562be4d`
- 作業ブランチ: `release/permission-keys-conditions-code`

## 逸脱・注意
- `executor-preflight.sh` は FAIL（クラウドに gh が無く api.github.com に届かない）。gh は PR 作成用で、本作業は PR を作らないため続行した。
- §0 の想定との差: 取り込み 2 経路の文字列は `"/import/preview"` ではなく `"/conditions/import/preview"` / `"/conditions/import/commit"`（router の prefix は main.py で `/api/v1`）。中身（`conditions.view` 1 つ）は想定どおり。
- `ConditionsPage.tsx` の `hasPermission("conditions.view") ?` の枝の中の取り込みボタンは条件なしで出ていた（想定どおり）。
- backend 依存: `python3.12 -m venv /tmp/venv312` → `/tmp/venv312/bin/pip install -r requirements.txt -r requirements-dev.txt`。
- 追加で `cd frontend && npm ci` と `npm run generate:api-types`（生成物 `src/api/generated/schema.d.ts` は未追跡・commit していない）。生成前の tsc は schema 欠落の 4 誤り（本変更と無関係）、生成後は 0。
- pytest の `Coverage failure: fail-under=60` は 2 ファイルだけ流したための全体カバレッジ閾値。試験自体は 9 passed。

## §0 grep の生出力
```
130:    dependencies=[Depends(require_permission("conditions.view"))],
163:    dependencies=[Depends(require_permission("work_items.view"))],
186:    dependencies=[Depends(require_permission("conditions.view"))],
210:    dependencies=[Depends(require_permission("conditions.create"))],
273:    dependencies=[Depends(require_permission("conditions.update"))],
327:    dependencies=[Depends(require_permission("conditions.delete"))],
371:    dependencies=[Depends(require_permission("conditions.view"))],
414:    dependencies=[Depends(require_permission("conditions.view"))],
452:    dependencies=[Depends(require_permission("conditions.view"))],
522:    dependencies=[Depends(require_permission("conditions.view"))],
551:    dependencies=[Depends(require_permission("conditions.update"))],
595:    dependencies=[Depends(require_permission("conditions.delete"))],
646:def require_permission(*permission_keys: str):
655:    required: set[str] = set(permission_keys)
672:    return checker
130:  const canImport = hasPermission("conditions.view");
106:      anchor.download = "conditions-export.csv";
369:        hasPermission("conditions.view") ? (
371:            <HeaderButton loading={exporting} variant="secondary" disabled={exporting} data-testid="conditions-export" onClick={() => void downloadExport()}>
374:            <HeaderButton variant="primary" data-testid="conditions-import" onClick={() => navigate("/management-center/conditions/import")}>
421:        with patch("app.auth.dependencies.load_user_permissions", _no_perms):
432:        with patch("app.auth.dependencies.load_user_permissions", _no_perms):
446:        with patch("app.auth.dependencies.load_user_permissions", _no_perms):
```

## git diff --stat origin/main（試験・実装の commit 3e1fa12d8、本報告の追加前）
```
 backend/app/auth/dependencies.py                   |  1 +
 backend/app/routers/conditions.py                  | 14 ++++-
 backend/tests/test_conditions_import_permission.py | 57 +++++++++++++++++++
 backend/tests/test_conditions_permission_keys.py   | 65 ++++++++++++++++++++++
 .../pages/conditions/ConditionImportPage.test.tsx  | 41 ++++++++++++++
 .../src/pages/conditions/ConditionImportPage.tsx   |  3 +-
 frontend/src/pages/conditions/ConditionsPage.tsx   |  8 ++-
 7 files changed, 182 insertions(+), 7 deletions(-)
```

## pytest（tail）
```
bringing up nodes...
bringing up nodes...

.........
ERROR: Coverage failure: total of 30 is less than fail-under=60
                                                                         [100%]
=============================== warnings summary ===============================
  /root/worktrees/salesanchor/release-permission-keys-conditions-code/backend/app/main.py:27: StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.
    from app.routers import (

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.12.3-final-0 ________________

Name                                                 Stmts   Miss  Cover   Missing
FAIL Required test coverage of 60% not reached. Total coverage: 29.66%
9 passed, 4 warnings in 20.98s
```

## vitest（tail）
```

 RUN  v4.1.7 /root/worktrees/salesanchor/release-permission-keys-conditions-code/frontend


 Test Files  1 passed (1)
      Tests  2 passed (2)
   Start at  00:59:35
   Duration  1.64s (transform 401ms, setup 44ms, import 613ms, tests 135ms, environment 653ms)

```

## tsc（schema 生成後・出力なし＝誤り 0）
```
(exit 0)
```

## eslint（出力なし、exit 0）
```
(exit 0)
```

## check-before-submit（tail）
```
  ○ 見本の選別（case.json）                      0.0 秒
  - test-guard-evaluations (node --test)             流していない: CI で確かめる（約 120 秒。--full で流せます）
  - run_rule_fixtures（全件）                    流していない: CI で確かめる（約 375 秒。--full で流せます）

== 版の違い（手元と CI）==
  手元: Python 3.12.3 / node v22.23.4
  CI  : Python 3.12 / node 22（guard-authoring だけ 24）
  版が違うので、最後の判定は CI です（この入口は提出前の補助）

合計 10.6 秒 / 必須 16 件を表示 / 流した検査 18 件 / 落ちた検査 0 件 / ログ /tmp/check-before-submit.MDYLq8（消さずに残します）
結果: ○ 流した検査は全部通りました（終了コード 0）
流した印を書きました: /home/user/salesanchor/.git/worktrees/release-permission-keys-conditions-code/check-before-submit.ok
```

## 最終 HEAD
実装の commit: `3e1fa12d8`（この報告を足す commit はその次。push 後の HEAD は `git rev-parse origin/release/permission-keys-conditions-code`）

DONE
