# 実装報告 — Rule C（commit の後の会社付け直し漏れ）

設計: docs/handoff/services-tenant-reset-after-commit/design.md 3章。枝: release/services-tenant-reset-after-commit（起点 c8f5816b3 を確認、origin/main を1回だけ取り込み・衝突なし）。

## 変えたファイル（git diff --stat origin/main）
```
 .github/workflows/lint-tenant-schema.yml           |   6 +-
 backend/AGENTS.md                                  |   2 +-
 backend/app/routers/leads.py                       |   1 +
 backend/app/routers/order_commissions.py           |   4 +
 backend/app/routers/orders.py                      |   1 +
 backend/app/routers/tenant_profile.py              |   2 +
 backend/tenant/CLAUDE.md                           |   4 +-
 .../ADR-072-tenant-schema-prefix-enforcement.md    |   6 +-
 docs/adr/README.md                                 |   2 +-
 .../design-review.md                               |  37 ++++
 .../services-tenant-reset-after-commit/design.md   | 124 ++++++++++++++
 .../services-tenant-reset-after-commit/recon.md    |  97 +++++++++++
 docs/specs/rule-enforcement/rules.yml              |   2 +-
 scripts/dev/check-before-submit.sh                 |   2 +-
 scripts/lint_tenant_schema.py                      | 187 +++++++++++++++++++--
 scripts/test_lint_tenant_schema.py                 | 127 +++++++++++++-
 .../fail-commit-without-reset/case.json            |   2 +-
 .../fail-service-commit-without-reset/case.json    |  15 ++
 .../app/services/zz_fixture_service.py.fixture     |   4 +
 .../tenant-schema/pass-commit-with-reset/case.json |   2 +-
 .../pass-service-commit-with-reset/case.json       |  12 ++
 .../app/services/zz_fixture_service.py.fixture     |   5 +
 22 files changed, 618 insertions(+), 26 deletions(-)
```

> 追記（Opus・2026-11-05 マージ後）: 上は実装時点（8cc2ac66b）の生出力のまま残す。その後 c61a90c3d で ADR-072 のステータス行を短くし `docs/adr/README.md` の変更は消えた。マージされた差分（PR #5162）は README.md を含まず、代わりに `docs/handoff/services-tenant-reset-after-commit/impl-report.md` を含む22ファイル。

## K1 直す前の予定のコード（d344d12ea^1 の calendar_service.py）
```
/tmp/k1/calendar_service.py:271 [Rule C] create_event: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:276で db を使用)
/tmp/k1/calendar_service.py:486 [Rule C] delete_event: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:488で db を使用)

2 violation(s) found.

[Rule C 修正方法]
  await db.commit() の直後に必ず以下を追加してください:
    await reset_tenant_context(db, tenant_id)
  インポート: from app.auth.dependencies import reset_tenant_context
  参照: docs/adr/ADR-072-tenant-schema-prefix-enforcement.md
mode=warning: not failing CI yet (ADR-072 Phase 3 PoC)
```

## K3 直す前の main（32b39bd59）の backend/app
```
/tmp/k3/backend/app/routers/leads.py:712 [Rule C] update_lead: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:759で db を使用)
/tmp/k3/backend/app/routers/order_commissions.py:322 [Rule C] assign_commission: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:324で db を使用)
/tmp/k3/backend/app/routers/order_commissions.py:385 [Rule C] unassign_commission: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:387で db を使用)
/tmp/k3/backend/app/routers/order_commissions.py:472 [Rule C] recalculate_order_commissions: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:474で db を使用)
/tmp/k3/backend/app/routers/orders.py:440 [Rule C] create_order_items: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:441で db を使用)
/tmp/k3/backend/app/routers/tenant_profile.py:141 [Rule C] update_tenant_profile: await db.commit() の後、db を使う前に reset_tenant_context(db, tenant_id) がない (:143で db を使用)

6 violation(s) found.

[Rule C 修正方法]
  await db.commit() の直後に必ず以下を追加してください:
    await reset_tenant_context(db, tenant_id)
  インポート: from app.auth.dependencies import reset_tenant_context
  参照: docs/adr/ADR-072-tenant-schema-prefix-enforcement.md
mode=warning: not failing CI yet (ADR-072 Phase 3 PoC)
```

## K4 Rule A・B の比較
直す前の main の lint で /tmp/k3/backend/app/routers/:
```
ADR-072 lint: OK (129 file(s) scanned)
```
新しい lint で backend/app/（--mode warning）:
```
ADR-072 lint: OK (420 file(s) scanned)
```
[Rule A]・[Rule B] の行: 直す前 0件・変更後 0件（grep -c の結果が両方 0）。

## pytest scripts/test_lint_tenant_schema.py -q
```
........................                                                 [100%]
24 passed in 0.20s
```

## 新しい lint --mode strict backend/app/
```
ADR-072 lint: OK (420 file(s) scanned)
```

## check_rule_registry（実際のパスは scripts/ci/check_rule_registry.py）末尾
```
  docs/specs/branch-operations/README.md                          15    11     4     0

結果: 合格（警告 0）
rc=0
```

## 見本ランナー（commit 後に実行）tenant-schema 4件と末尾
```
OK tenant-schema/fail-commit-without-reset [ADR-072 tenant schema lint (strict mode)] 期待=fail 終了コード=1
OK tenant-schema/fail-service-commit-without-reset [ADR-072 tenant schema lint (strict mode)] 期待=fail 終了コード=1
OK tenant-schema/pass-commit-with-reset [ADR-072 tenant schema lint (strict mode)] 期待=pass 終了コード=0
OK tenant-schema/pass-service-commit-with-reset [ADR-072 tenant schema lint (strict mode)] 期待=pass 終了コード=0

違反の見本 14 件中 14 件で止まった・正しい見本 14 件中 14 件で通った・見本が一部を止めている決まり 8 件（142.1 秒）
```

## 想定と違った点
- scripts/check_rule_registry.py は存在せず、実物は scripts/ci/check_rule_registry.py（それを実行）。
- ./scripts/dev/executor-preflight.sh は gh の到達・認証が取れず FAIL（クラウド環境のため）。PR を作らず git のみの作業なので続行した。
- クラウドに pytest が無く、Python 3.12 の venv（/tmp/v312）に導入して実行。
- 見本ランナーは HEAD の写しを使うため、commit 前は新しい見本が落ちる。commit 後に全 28 件が通った。
- K3 の leads:712 は db の使用が :759（invalidate_dashboard_cache は db を使わない）。件数・行は設計と一致。
- 件数は設計どおり（K1=2・K3=6）で、止めずに進めた。

## push 後の git log --oneline -3
```
8cc2ac66b feat: commit の後の会社付け直し漏れを見張りで止める（ADR-072 v3 Rule C）
9b35cedcf Merge remote-tracking branch 'origin/main' into release/services-tenant-reset-after-commit
c8f5816b3 docs: 設計審査2回目（APPROVE）の推奨5件を反映（分岐の扱い・ADR-072前置き・tenant CLAUDE.md・表割れ・行番号）
```
