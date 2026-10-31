# recon — 試験の表の写し 13 件を 0 に戻す

- 測った時点: S=origin/main dc99a062e2c409aeb1a851a01b8bd0fa09ac3b64（2026-11-01T01:53:57+09:00・Merge #4957）
- 生出力: /tmp/CC報告ファイル/schema-dup/（check-main.txt ほか。手元の記録で、リポジトリには入れない）
- 既存 ADR の検索: `git grep -i -l "schema-dup\|test_schema_dup\|CREATE TABLE" docs/adr/` と docs/adr/FEATURE-INDEX.md。当たるのは ADR-121（工程の固め・柱3）。新しい ADR は要らない（決まりは既にあり、今回はそれに戻すだけ）。

## file:line 引用表

| 場所 | 中身 |
|---|---|
| scripts/check_test_schema_dup.py:23-25 | EXCLUDE_FILES に backend/tests/conftest.py（集約先）ほか 2 つ |
| docs/specs/process-hardening/design-pillar3.md:11・24・48 | :11（§1）「コピーはこれ以上増やさない」。:24・:48 集約先は conftest.py（見張りの対象外） |
| docs/specs/process-hardening/pillar3-inventory.md | 記録は 29 ファイル・71 件 |
| /tmp/CC報告ファイル/schema-dup/check-main.txt | S で `--check-inventory` が exit 1・MEASURED files=32 tables=84 |
| backend/tests/ops/test_ops_case_db.py:153・155・157・159・162・169 | 作り物の表 6 つ（#4945 で入った） |
| backend/tests/ops/test_ops_case_db.py:144-152 | fixture pg。使い捨ての DB を作り、持ち主を superuser でない aic_owner にしてから表を作る |
| backend/tests/ops/test_ops_case_db.py:509-518・686-699 | 拒否表と持ち主の権限を確かめる試験（持ち主が aic_owner であることが前提） |
| backend/tests/test_ops_case_router.py:141-147 | 作り物の表 6 つ（db の試験と比べ text_pk→small_pk、leads に email 無し） |
| backend/tests/test_rls_auth_audit.py:53-84 | setup_schema。:58-70 で audit_logs を手書き（:60 BIGSERIAL）、:71-76 で RLS と方針、:77-81 で GRANT 3 行（#4942 で入った） |
| backend/app/services/tenant.py:482-492 | 本物の {schema}.audit_logs（id SERIAL・tenant_id DEFAULT・列の名前は試験と同じ） |
| backend/app/services/tenant.py:1186・1247-1249 | 本物の RLS と方針 tenant_isolation_audit_logs（式は試験 :74-75 と同じ） |
| backend/tests/rls_bootstrap.py:304・340 | tenant_schema_lock・bootstrap_tenant_schema（public の共有の表も自分で用意する） |
| backend/tests/test_permission_resolution_pg.py:25・56-64・96・126 | bootstrap を使う手本と、試験のテナントの行だけ消す手本 |
| backend/tests/conftest.py:192-202 | 作り物の表を集約先の定数に置いた手本（INBOX_BADGE_…） |
| backend/tests/test_inbox_new_assignment_badge.py:45-50 | その定数を import する手本 |
| backend/tests/__init__.py | ある（tests は package）。backend/tests/ops には __init__.py が無い |
| docs/specs/transaction-flow/lead-merge/design.md:80 | 試験の表は手で書かず rls_bootstrap で作る |
| migrations/20261016_150000_add_viewer_accounts.sql:6 | viewer_accounts の本物は public（ops の試験は名前だけ使う） |
| .github/workflows/test.yml:223 | CI の試験は RLS_TEST_DATABASE_URL 付きの PG で走る |
| .github/workflows/test-schema-dup-gate.yml | 照合の段（必須の確かめではない） |

## 不明点リスト

- [?] bootstrap_tenant_schema が salesanchor_app に audit_logs の権限を付けるか。→ 確かめずに済む形にした（GRANT 3 行を残す。本物の付与は 1 つの DO ブロックで、失敗すると全部付かない・tenant.py:1691-1709）。
- [?] 試験 a（test_rls_auth_audit.py:97-112）の失敗の文言が、本物の表でも同じになるか。式は同じ。CI で確かめる（カード §6 分岐4）。
- [解決] tests/ops から `from tests.…` は解ける。根拠: backend/tests/ops/test_ai_cloud_views.py:531（`from tests.rls_bootstrap import`）・.github/workflows/test.yml:208（working-directory: backend）・backend/tests/__init__.py がある。

## 補足

- 増えた 13 件は、段2 の実装（#4945）の 12 件と自社ログインの監査の直し（#4942）の 1 件。設計担当が #4945 の合流のときに照合の段の赤を見落とした。
