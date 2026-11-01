# 試験の表の写し 13 件を 0 に戻す 実装カード（第1版）

> この文書は何か（専門用語なしの1行）:
> 相談係AIの第2段階と自社ログインの直しで、試験のファイルに本番の表の作り方が13か所書き写された。それを決まりどおりの置き場所へ移し、見張りの確かめを緑に戻す作業の指示書。

- 根拠の写し: S=origin/main dc99a062e2c409aeb1a851a01b8bd0fa09ac3b64（Merge #4957）。行番号はすべてこの sha。実装の前に最新の origin/main で行を合わせ直す（§6 の分岐1）。
- 対象の決まり: docs/specs/process-hardening/design-pillar3.md（ADR-121）§1・§4-3・§4-5。docs/specs/transaction-flow/lead-merge/design.md:80（試験の表は手で書かず rls_bootstrap で作る）。
- 状態: 第1版。設計審査 APPROVE（2026-11-01・審査役 opus・4 回目で合格）。PO の実装承認はまだ。実装は承認の後。
- 設計: docs/handoff/test-schema-dup-ops-case/design.md。下調べ: docs/handoff/test-schema-dup-ops-case/recon.md。

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・sleep しない・報告に無い出力を成功と扱わない | ○（§7・§13） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4・§13） |
| guards/04-worktree.md | 作業場所は scripts/new-worktree.sh で作り、作った後に枝の名前と先頭を確かめる | ○（§7 手順1） |
| guards/05-pr.md | commit・push の各段で実在を確かめる。PR はクラウドでは作らない（コード変更を含む枝のため） | ○（§12） |
| scripts/agent-hooks/cloud/rules.md | クラウドは push まで・PR は手元で shingo-cc 名義・`.claude-pipeline/active-work.d/` は commit しない・reset/rebase/force/merge/pull を使わない | ○（§7・§12・§13） |

あなたは Sales Anchor の実装役（Sonnet）です。このカードだけを実行し、push までします。PR は作りません。最初に `scripts/agent-hooks/cloud/rules.md` を読み、従ってください。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 試験の表の写し13件を0に戻す（第1版）の実行結果である」と書くこと。
- 種類: 試験のコードだけ（backend/tests 配下）。本番のコード・migration・CI・deploy には触れない。

## 1. 目的と、PO から見える変化
- 今: 本線のすべての PR で「test-schema-dup gate」の照合の段が赤い（必須の確かめではないので合流は止まらない）。赤が常に出ていると、本当に新しい写しが増えたときに気づけない。
- 後: 照合の段が緑に戻る。数は記録表と同じ 29 ファイル・71 件になる。
- 原因: 段2 の実装（#4945）で 2 つの試験ファイルに 12 件、自社ログインの監査の直し（#4942）で 1 件、本番の表の作り方を書き写した。設計担当（Opus）が #4945 の合流のときにこの赤を見落とした。

## 2. 現在地（実測。S で測った）
- 照合の実測: `python3 scripts/check_test_schema_dup.py --check-inventory docs/specs/process-hardening/pillar3-inventory.md dc99a062e…` → exit 1、`MEASURED files=32 tables=84` / `RECORDED files=29 tables=71`、増えた 13 件（生出力 /tmp/CC報告ファイル/schema-dup/check-main.txt）。
- 増えた 13 件の場所:
  - backend/tests/ops/test_ops_case_db.py:153（public.plain_demo）・:155（public.text_pk）・:157（public.has_secret）・:159（public.two_pk）・:162（tenant_001.leads・id uuid/customer_name/email）・:169（tenant_001.viewer_accounts）
  - backend/tests/test_ops_case_router.py:141（public.plain_demo）・:142（public.small_pk）・:143（public.has_secret）・:144（public.two_pk）・:146（tenant_001.leads・id uuid/customer_name の 2 列）・:147（tenant_001.viewer_accounts）
  - backend/tests/test_rls_auth_audit.py:58-70（tenant_991.audit_logs・:60 が BIGSERIAL）と :71-81（RLS・方針・GRANT 3 行）
- 見張りの除外の決まり: scripts/check_test_schema_dup.py:23-25 の EXCLUDE_FILES に backend/tests/conftest.py（集約先）。設計 design-pillar3.md:24・:48（§4-3）も同じ。
- 集約先に作り物の表を置いた手本: backend/tests/conftest.py:192-202（INBOX_BADGE_GENERIC_SINGLE_COLUMN_DDL・INBOX_BADGE_MINIMAL_LEADS_DDL）。使う側の手本: backend/tests/test_inbox_new_assignment_badge.py:45-50（`from .conftest import (…)`）。tests/ops には __init__.py が無いので、ops の試験は `from tests.…` の書き方にする（手本: backend/tests/test_permission_resolution_pg.py:25 `from tests.rls_bootstrap import (…)`。backend/tests/__init__.py はある）。
- 本物の定義でテナントを作る手本: backend/tests/rls_bootstrap.py:340（bootstrap_tenant_schema）。使う側の手本: backend/tests/test_permission_resolution_pg.py:25-29（import）・:56-64（試験のテナントの行だけ消す）・:96（tenant_schema_lock）・:126（bootstrap_tenant_schema）。backend/tests 配下で bootstrap_tenant_schema を使うファイルは 8（定義元の rls_bootstrap.py を除く）。
- 本物の監査の表: backend/app/services/tenant.py:482-492（{schema}.audit_logs・id SERIAL）・:1186（RLS を有効）・:1247-1249（tenant_isolation_audit_logs・`tenant_id = current_setting('app.tenant_id', true)::INTEGER`。今の試験 :74-75 の式と同じ）。列の名前と順は試験 :59-68 と同じ（違いは id が SERIAL、action と table_name に長さの上限、tenant_id に DEFAULT）。
- viewer_accounts の本物は public（migrations/20261016_150000_add_viewer_accounts.sql:6）。ops の試験は名前で拒否されるかだけを見ている（deny_tables は名前で突き合わせる）。

## 3. 直し方（選んだ案と理由）

### 3-A ops の 2 ファイル（12 件）→ 作り物の表の作り方を集約先 conftest.py に移す
- この 12 件の表は、本番の表の写しではなく「形の違う表」を作る作り物（主キーが文字・2 列・smallint、秘密の列あり、拒否表の名前）。持ち主は superuser でない aic_owner で、使い捨ての DB の中に作る（test_ops_case_db.py:146-152）。
- 作り方の文字列を backend/tests/conftest.py の定数にし、2 つのファイルはその定数を import して execute する。中身の文字列は 1 文字も変えない（試験の意味を変えないため）。
- 同じ文字列は 1 つの定数にまとめる（plain_demo・has_secret・two_pk・viewer_accounts は 2 ファイルで同じ）。leads は 2 ファイルで列が違うので 2 つの定数にする。
- 採らなかった案: bootstrap_tenant_schema で本物のテナントを作る。理由: 本物のテナントは管理の役で作られ public の共有の表も作る。ops の試験は「superuser でない持ち主の表に、持ち主が読めない拒否表がある」形を作って確かめている（test_ops_case_db.py:509-518・:686-699）。持ち主が変わると試験の意味が変わる。
- 採らなかった案: 記録表（pillar3-inventory.md）を作り直して 84 件を正にする。理由: 設計 §1「コピーはこれ以上増やさない」に反する。

### 3-B test_rls_auth_audit.py（1 件）→ 本物の定義でテナントを作る
- この表は本番の audit_logs の写しで、試験の目的も「本番と同じ式」での動きの確かめ（:72 のコメント）。本物の定義（tenant.py）から作るのが正しい。lead-merge 設計 :80 の決まりにも合う。
- setup_schema の中の DROP/CREATE SCHEMA・CREATE TABLE・ENABLE RLS・CREATE POLICY を、test_permission_resolution_pg.py と同じ流れに置き換える: tenant_schema_lock の中で、前回の残りを消す → bootstrap_tenant_schema(admin_engine, 991)。
- GRANT の 3 行（:77-81）は、bootstrap の後にそのまま残す。理由: 本物の作り方の権限付与は 1 つの DO ブロックで、失敗すると全部まとめて付かない（tenant.py:1691-1709）。残しても同じ権限を付け直すだけで害が無く、CREATE TABLE ではないので見張りに当たらない。
- 片付けは、テナント 991 の schema と public.tenants・public.tenant_settings の 991 の行だけ消す（手本 :56-64 と同じ。ほかのテナントの行には触れない）。

## 4. 変更前後（実装の担当はこの形どおりに書く）

### 4-1 backend/tests/conftest.py（S の末尾 :1876 の後に足す。既存の行は触らない）
```python
# 相談係AIの第2段階の試験（backend/tests/ops/test_ops_case_db.py・backend/tests/test_ops_case_router.py）用:
# 本番の表の写しではなく、主キーの形・秘密の列・拒否表の名前を試すための作り物の表。
# 持ち主を superuser でない役にして使い捨ての DB に作るため、bootstrap_tenant_schema は使わない。
OPS_CASE_PLAIN_DEMO_DDL = "CREATE TABLE public.plain_demo (id integer PRIMARY KEY, memo text, email text)"
OPS_CASE_TEXT_PK_DDL = "CREATE TABLE public.text_pk (code text PRIMARY KEY, memo text)"
OPS_CASE_SMALL_PK_DDL = "CREATE TABLE public.small_pk (id smallint PRIMARY KEY, memo text)"
OPS_CASE_HAS_SECRET_DDL = "CREATE TABLE public.has_secret (id integer PRIMARY KEY, memo text, api_token text)"
OPS_CASE_TWO_PK_DDL = "CREATE TABLE public.two_pk (a integer, b integer, memo text, PRIMARY KEY (a, b))"
OPS_CASE_TENANT_LEADS_DDL = "CREATE TABLE tenant_001.leads (id uuid PRIMARY KEY, customer_name text, email text)"
OPS_CASE_TENANT_LEADS_NO_EMAIL_DDL = "CREATE TABLE tenant_001.leads (id uuid PRIMARY KEY, customer_name text)"
OPS_CASE_TENANT_VIEWER_ACCOUNTS_DDL = "CREATE TABLE tenant_001.viewer_accounts (id integer PRIMARY KEY, note text)"
```

### 4-2 backend/tests/ops/test_ops_case_db.py
- 前（:153）: `c.execute("CREATE TABLE public.plain_demo (id integer PRIMARY KEY, memo text, email text)")`
- 後: `c.execute(OPS_CASE_PLAIN_DEMO_DDL)`
- 同じく :155→OPS_CASE_TEXT_PK_DDL・:157→OPS_CASE_HAS_SECRET_DDL・:159→OPS_CASE_TWO_PK_DDL・:162→OPS_CASE_TENANT_LEADS_DDL・:169→OPS_CASE_TENANT_VIEWER_ACCOUNTS_DDL。
- import は、ファイルの今の import の並び（:26 の `import pytest` の後）に `from tests.conftest import (…)` で 6 つ足す。
- INSERT の行・コメント・他の行は触らない。

### 4-3 backend/tests/test_ops_case_router.py
- :141→OPS_CASE_PLAIN_DEMO_DDL・:142→OPS_CASE_SMALL_PK_DDL・:143→OPS_CASE_HAS_SECRET_DDL・:144→OPS_CASE_TWO_PK_DDL・:146→OPS_CASE_TENANT_LEADS_NO_EMAIL_DDL・:147→OPS_CASE_TENANT_VIEWER_ACCOUNTS_DDL（いずれも `a.execute(定数)`）。
- import は :18-20 の並びの後に `from tests.conftest import (…)` で 6 つ足す。

### 4-4 backend/tests/test_rls_auth_audit.py
- 前（:53-84 の setup_schema）: DROP/CREATE SCHEMA・CREATE TABLE audit_logs・ENABLE RLS・CREATE POLICY・GRANT 3 行・後片付けの DROP SCHEMA。
- 後:
```python
@pytest_asyncio.fixture(scope="module", loop_scope="module", autouse=True)
async def setup_schema(admin_engine):
    # 本物の定義（backend/app/services/tenant.py）でテナント 991 を作る。本番の表の作り方を試験に書き写さない
    async with tenant_schema_lock(admin_engine, _TENANT_ID):
        async with admin_engine.begin() as conn:
            await _remove_test_tenant_rows(conn)
        await bootstrap_tenant_schema(admin_engine, _TENANT_ID)
        async with admin_engine.begin() as conn:
            # 今の :77-81 の GRANT 3 行をそのまま移す（本物の作り方の権限付与は失敗すると全部付かないため・tenant.py:1691-1709）
            await conn.execute(text(f"GRANT USAGE ON SCHEMA {_SCHEMA} TO salesanchor_app"))
            await conn.execute(text(f"GRANT SELECT, INSERT ON {_SCHEMA}.audit_logs TO salesanchor_app"))
            await conn.execute(text(
                f"GRANT USAGE, SELECT ON SEQUENCE {_SCHEMA}.audit_logs_id_seq TO salesanchor_app"
            ))
        yield
        async with admin_engine.begin() as conn:
            await _remove_test_tenant_rows(conn)
```
- `_remove_test_tenant_rows` は test_permission_resolution_pg.py:56-64 と同じ中身をこのファイルに置く（テナント番号は _TENANT_ID）。
- 冒頭の説明文 :3 の「本番の tenant_NNN.audit_logs の行の制限（NULLIF なし）と同じ式を持つ表を作り、」を「本番と同じ作り方（rls_bootstrap.bootstrap_tenant_schema）でテナント 991 を作り、」に直す。:3 のほかの文字と :1-2・:4-7 は触らない。
- import: `from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock`。
- _count・試験 3 本（:87-151）は触らない。

## 5. 触らない範囲
- scripts/check_test_schema_dup.py・.github/workflows/test-schema-dup-gate.yml・docs/specs/process-hardening/pillar3-inventory.md（記録表は作り直さない）。
- backend/app 配下・migrations 配下・本番の設定。
- 3 つの試験ファイルの、表を作る行と import と setup_schema と §4-4 の説明文 :3 以外の行。

## 6. 想定の分岐（実物を見て違えば止める）
- 分岐1: 最新の origin/main で §2 の行が動いていたら、文字列の一致で場所を合わせ直す。文字列そのものが変わっていたら止めて Opus へ。
- 分岐2: 照合の実測で 13 件以外の増減があったら止めて Opus へ（ほかの PR で増えた分をこのカードで直さない）。
- 分岐3: 本物の作り方で audit_logs_id_seq という名前の連番ができない（GRANT の 3 行目が失敗する）ときは、止めて Opus へ。
- 分岐4: 本物の audit_logs は id SERIAL（tenant.py:483）、今の試験は BIGSERIAL（:60）。列の名前は同じ。試験 a（:97-112）は「invalid input syntax for type integer」の文言を確かめている。本物の方針の式は同じだが、同じ失敗になるかはまだ確かめていない（CI で確かめる）。_count と試験 3 本がこの違いで落ちたら、直さず止めて Opus へ。
- 分岐5: bootstrap_tenant_schema が CI の試験 DB で失敗したら（権限・時間）、止めて Opus へ。3-B を 3-A の形（conftest の定数）に切り替えるかは Opus が決める。
- 分岐6: tests/ops から `from tests.…` は解ける（手本: backend/tests/ops/test_ai_cloud_views.py:531 が `from tests.rls_bootstrap import`。CI は .github/workflows/test.yml:208 の working-directory: backend で pytest を起動）。それでも import のエラーが出たら、止めて Opus へ。
- 分岐7: 手順2・4 の試験の数え上げが、依存パッケージが無いなどで数えられないときは、止めずに「未測定」と報告に書いて手順を続ける（試験の確かめは CI の test.yml に任せる）。

## 7. 手順（実行役）
手順1 作業場所を new-worktree.sh で作り、直す前の数を測る（new-worktree.sh の出力はパイプに通さない。照合の出力だけ tail で 40 行までに絞る）
    cd "$(git rev-parse --show-toplevel)" && git fetch origin main
    cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/test-schema-dup-ops-case 2>&1
    cd "$(git rev-parse --show-toplevel)" && ls -1d "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git worktree list
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git branch --show-current && git log --oneline -1 && git rev-parse origin/main
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && python3 scripts/check_test_schema_dup.py --check-inventory docs/specs/process-hardening/pillar3-inventory.md "$(git rev-parse HEAD)" 2>&1 | tail -n 40
    期待する出力: ls -1d と git worktree list の両方にその道が出る。道が salesanchor 以外のフォルダ名の下にできたら、以後の cd をその道に読み替えず BLOCKED: で止まる。枝は release/test-schema-dup-ops-case。先頭は origin/main と同じ sha。照合は MEASURED files=32 tables=84・増えた 13 件（§2 と同じ）。違えば分岐2。作業場所が作れなければ BLOCKED: で止まる
手順2 直す前の試験の数を取る（基準値。PG が無くても数えられる）
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case/backend" && python -m pytest -o addopts="" --collect-only -q tests/ops/test_ops_case_db.py tests/test_ops_case_router.py tests/test_rls_auth_audit.py 2>&1 | tail -n 5
    期待する出力: 最後の行の「N tests collected」の N を記録する。数えられなければ分岐7
手順3 §4 のとおりに 4 つのファイルを Edit ツールで直す（ほかのファイルは作らない・直さない）
手順4 commit してから、直した後の数と試験の数を測る（見張りは git に入った中身を読むので、commit の前に測ると必ず 84 になる）
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git add backend/tests/conftest.py backend/tests/ops/test_ops_case_db.py backend/tests/test_ops_case_router.py backend/tests/test_rls_auth_audit.py
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git commit -m "test: move ops case table DDL to conftest and use real tenant bootstrap for auth audit test" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>" 2>&1 | tail -n 20
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git log -1 --oneline
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && python3 scripts/check_test_schema_dup.py --check-inventory docs/specs/process-hardening/pillar3-inventory.md "$(git rev-parse HEAD)" 2>&1 | tail -n 40
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && BASE_SHA="$(git rev-parse origin/main)" HEAD_SHA="$(git rev-parse HEAD)" python3 scripts/check_test_schema_dup.py 2>&1 | tail -n 40
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case/backend" && python -m pytest -o addopts="" --collect-only -q tests/ops/test_ops_case_db.py tests/test_ops_case_router.py tests/test_rls_auth_audit.py 2>&1 | tail -n 5
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git diff --name-only origin/main...HEAD
    期待する出力: 照合は MEASURED files=29 tables=71 で、増えた・減ったの行が無く、「一覧と実測が一致(pass)」が出る。BASE_SHA・HEAD_SHA を付けた起動は、db の試験と router の試験が BASE=6 HEAD=0、監査の試験が BASE=1 HEAD=0、最後に「テストへの新規スキーマ複製なし(pass)」。collected の数は手順2 と同じ。変わったファイルは conftest.py と 3 つの試験の 4 つだけ。違えば停止して Opus へ
手順5 push して、push した先頭を確かめる（PR は作らない）
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git push -u origin release/test-schema-dup-ops-case 2>&1 | tail -n 30
    cd "$HOME/worktrees/salesanchor/release-test-schema-dup-ops-case" && git fetch origin release/test-schema-dup-ops-case && git rev-parse HEAD && git rev-parse origin/release/test-schema-dup-ops-case
    期待する出力: 2 つの sha が同じ。push が断られたら（提出前の入口の × を含む）、直さず BLOCKED: で止まり、出力を報告する

## 8. 受入基準

| 基準 | 検証方法 |
|---|---|
| 写しが記録表と同じ数に戻る | PR の HEAD で `--check-inventory` が exit 0、`MEASURED files=29 tables=71` |
| 3 つの試験ファイルに表の作り方が残らない | 手順4 の BASE_SHA・HEAD_SHA を付けた起動が「テストへの新規スキーマ複製なし(pass)」を出し、3 ファイルとも HEAD=0（exit 0 は PR の CI と Opus の手元で確かめる） |
| CI の確かめが緑 | PR の「test-schema-dup gate」が success（照合の段を含む） |
| 試験の数が直す前と同じ | 手順2 と手順4 の collected の数が同じ |
| 試験が実際の PG で通る | PR の「test.yml」の backend の試験（RLS_TEST_DATABASE_URL 付き・.github/workflows/test.yml:223）が success |
| 作り物の表の中身が変わらない | conftest.py の 8 つの定数の文字列が、S の 12 行の文字列と 1 文字ずつ一致（diff で確かめ、報告に並べる） |
| 触る範囲が守られる | `git diff --name-only origin/main...HEAD` が conftest.py と 3 つの試験の 4 つだけ |

## 9. 弊害・戻し方・維持
- 弊害: test_rls_auth_audit.py は本物のテナントを作るので遅くなる（ほかの 8 ファイルと同じ重さ）。conftest.py に作り物の表の定数が 8 つ増える（集約先の決まりどおり）。
- 戻し方: この PR を revert する。本番には触れないので本番の戻しは無い。
- 測り方: §8 の表。
- 維持: 見張り .github/workflows/test-schema-dup-gate.yml の照合の段が、次に写しが増えたときに赤を出す。赤を見落とした件の再発防止として、設計担当は合流の前に必須でない確かめの赤も全部読み、理由を PR に書く（設計担当の作法。このカードの範囲外の仕組みは作らない）。

## 10. 外部事例
- 不要。理由: 本リポジトリの決まり（design-pillar3.md）と手本（conftest.py:192-202・test_permission_resolution_pg.py）がそのまま当てはまり、新しい技術の選択が無いため。

## 11. 接触面
- 人: 無し（PO の画面は変わらない）。
- 機械: CI の試験だけ。
- データ・本番・外部: 非接触。

## 12. commit・push・PR
- commit は手順4、push は手順5 で行う。push の後に手順5 の 2 つの sha が同じことで実在を確かめる。
- 実行役は PR を作らない（コード変更を含む枝はクラウドでは push まで・scripts/agent-hooks/cloud/rules.md）。PR は Opus が手元で shingo-cc 名義・scripts/gh-pr-create-safe.sh で作る。
- `.claude-pipeline/active-work.d/` の登録ファイルは commit しない（new-worktree.sh が自分で登録する）。
- reset・rebase・force・merge・pull・`--no-verify` は使わない。

## 13. 報告と委任の定型
- 完了報告の本文に: 冒頭の受領文／手順1・2・4 の出力／§8 の各行の結果／8 つの定数と S の 12 行の文字列の対照／push した枝の名前と、push 後に確かめた先頭の sha／判断を要した点（事実のみ）。
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文。
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか。
- sleep しない（CI の待ちは Opus が行う）。
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- このカードに書いていないファイル・行は触らない。

END OF CARD
