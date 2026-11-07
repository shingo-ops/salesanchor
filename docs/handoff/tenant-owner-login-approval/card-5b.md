# card: 便5 段2 許可一覧を埋めて、RLS の無い表が増えたら CI を落とす（K8）

状態: カード発行（Opus、2026-11-07）。PO の判断は 2026-11-07「ｃ1」（6 つの表は正直な理由を書いて許可一覧に入れ、RLS は次の段で付ける。本番は変えない）。段1 は card-5.md。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。本番・GitHub の secret には触らない。PR は作らない（Opus が作る）。
基準: このカードのコミット（枝 release/tenant-owner-bin5-public-rls-ci。origin/main a55e64ed6 を取り込み済み）。行番号はその時点のもの。ずれていたら「変更前」の文で場所を探す（同じ文が 2 か所あれば BLOCKED: で止まる）。

段1 の生出力の確かめ（Opus、2026-11-07）:
- 段1 の CI（全件ドライラン、2026-11-06 07:49Z）は 18 件。うち 8 件（discord_server_apply_runs・discord_server_snapshots・google_webhook_subscriptions・inventory_movements・tenant_discord_config・tenant_discord_ticket_config・tenant_llm_budgets・tenant_settings）は ADR-1067 段階④で RLS を付けて本番に反映済み。残りは 10 件。
- 本番を同じ問い合わせで数えると 11 件（2026-11-07 12:05 JST、読取の道）。CI の 10 件に meta_page_routing が加わる。CI の DB に無いのは、作る移行 migrations/043_create_meta_page_routing.sql が scripts/run_all_migrations.sh に登録されていないため（grep で 0 件）。本番の毎日点検（便6）も同じ一覧を読むので、11 件すべてを入れる。CI では「（参考）許可一覧にあるが見つからない: meta_page_routing」が出るだけで落ちない（scripts/check_public_tenant_rls.py の stale は表示だけ）。

設計からの小さな変更（Opus 判断・記録）:
- 試験の見本の表の作り方（CREATE TABLE の文）を backend/tests/conftest.py に移す。理由: 段1 の PR で「test-schema-dup gate」（scripts/check_test_schema_dup.py）が「テストに本番テーブル定義の新規コピーが増えています（0 -> 6）」で落ちた。この見張りの設計（docs/specs/process-hardening/design-pillar3.md §4-3）は conftest.py を「集約先」として数えない。見本の表は本番の表の写しではないが、例外の書き方はこの集約先しか無いため、決まった置き場に置く。前例: conftest.py の USER_NOTICE_DDL を backend/tests/test_user_notices.py:25 が import している。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）と照合（Opus、2026-11-07）
- 00-common.md: プレースホルダを残さない → 接続先・理由・問いは山括弧で書かず文で書いた。停止の報告経路は「4. 終わったら」に書いた。
- 03-file.md: 既存ファイルの一部の書き換えは「変更前／変更後」の逐語で示し、変更前の文は 2026-11-07 にこの枝で実測した（P2〜P6）。conftest.py は末尾に足すだけ。
- 10-executor.md: 実行役はクラウドの Sonnet（CC 系）。カードに無い確認は足さず、外れたら停止する。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin5-step2 HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝 `release/tenant-owner-bin5-public-rls-ci` を origin から取り、このカード（docs/handoff/tenant-owner-login-approval/card-5b.md）が在ること。
- P2 `grep -c "^PUBLIC_TABLES_WITHOUT_RLS: dict\[str, str\] = {}$" backend/app/ops/tenant_rls_allowlist.py` が 1。
- P3 `grep -c "python3 scripts/check_public_tenant_rls.py --db jarvis_report --report-only" .github/workflows/migration-test.yml` が 1。
- P4 `grep -c 'CREATE TABLE' backend/tests/test_check_public_tenant_rls.py` が 6。
- P5 `grep -c "^RLS_PROBE" backend/tests/conftest.py` が 0。
- P6 `grep -c "^async def create_user_notice_tables(conn):$" backend/tests/conftest.py` が 1。

## 1. 触るファイル
1. backend/app/ops/tenant_rls_allowlist.py
2. .github/workflows/migration-test.yml
3. backend/tests/conftest.py（末尾に足すだけ）
4. backend/tests/test_check_public_tenant_rls.py

触らない: scripts/check_public_tenant_rls.py・migrations・backend/app のほかのファイル・.github のほかのファイル・scripts・frontend・docs。

## 2. 変更

### 2-1 backend/app/ops/tenant_rls_allowlist.py
変更前:
```python
PUBLIC_TABLES_WITHOUT_RLS: dict[str, str] = {}
```
変更後:
```python
# 2026-11-07 時点の本番の 11 件（ADR-1063 便5 段2・ADR-1067）。
# 「会社の画面から会社の行を足せる」6 件は全社共用ではない。RLS は次の段で読み方と一緒に付ける（PO 2026-11-07「ｃ1」）。
PUBLIC_TABLES_WITHOUT_RLS: dict[str, str] = {
    "line_conditions": (
        "状態の表（別名 public.conditions）。運営の全社共用の行に加えて、会社の画面（backend/app/routers/conditions.py）から会社の行も足せる。"
        "解析が会社で絞らずに読む（backend/app/services/tcg_analyzer_svc.py）ため、RLS は次の段で読み方と一緒に付ける。"
    ),
    "line_units": (
        "単位の表（別名 public.units）。運営の全社共用の行に加えて、会社の画面（backend/app/routers/units.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "payment_fee_settings": (
        "支払い手数料の表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/payment_fee_settings.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "tcg_note_master": (
        "備考の表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/note_master.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "tcg_status_master": (
        "ステータスの表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/status_master.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "tcg_product_categories": (
        "商品区分の表。運営の全社共用の行に加えて、会社の画面（backend/app/routers/product_categories.py）から会社の行も足せる。"
        "RLS は次の段で付ける。"
    ),
    "meta_page_routing": (
        "Meta の Webhook を受けた時点では会社が決まっていないため、全社の行から page_id で会社を探す表（backend/app/routers/webhook.py）。"
        "会社の表の trigger（SECURITY DEFINER、backend/app/services/tenant.py）が書く。"
    ),
    "llm_usage_events": (
        "AI の使用量の記録。会社が決まらない呼び出しもあるため会社番号は任意（backend/app/services/llm_budget.py）。運営が全社分を集計して読む。"
    ),
    "data_deletion_logs": "運営のデータ削除の記録（backend/app/tasks/data_deletion.py が書く）。会社の画面からは読み書きしない。",
    "tenant_deletion_audit": "運営の会社削除の記録（backend/app/routers/super_admin_tenants.py が書く）。会社の画面からは読み書きしない。",
    "products_category_classification_backup": "移行で作った商品区分の控え。アプリは読み書きしない。",
}
```
（BYPASSRLS_ROLES とファイル先頭の説明は変えない。）

### 2-2 .github/workflows/migration-test.yml（1 か所・4 行）
変更前:
```
      - name: 会社の列があるのに RLS の無い public の表を数える（ADR-1063 K8・段1 は数えて出すだけ）
        # 全件ドライランを流し終えた報告用 DB（jarvis_report）を見る。許可一覧は backend/app/ops/tenant_rls_allowlist.py の1か所。
        # 段1 は --report-only（名前を出すだけ）。段2 で一覧を確かめてから --report-only を外して落とす形にする。
```
変更後:
```
      - name: 会社の列があるのに RLS の無い public の表を見つけたら落とす（ADR-1063 K8）
        # 全件ドライランを流し終えた報告用 DB（jarvis_report）を見る。許可一覧は backend/app/ops/tenant_rls_allowlist.py の1か所。
        # 許可一覧に無い表が 1 件でもあれば落ちる。RLS を付けるか、理由を書いて許可一覧に足す。
```
変更前:
```
          python3 scripts/check_public_tenant_rls.py --db jarvis_report --report-only
```
変更後:
```
          python3 scripts/check_public_tenant_rls.py --db jarvis_report
```

### 2-3 backend/tests/conftest.py（ファイルの末尾に足す。既存の行は変えない）
`async def create_user_notice_tables(conn):` の関数の後ろ（ファイルの最後）に、空行 2 つを置いてから次を足す:
```python
# ADR-1063 便5: RLS の点検（scripts/check_public_tenant_rls.py）の試験で、使い捨ての DB に作る見本の表。
# 本番の表の写しではない。backend/tests/test_check_public_tenant_rls.py が使う。
RLS_PROBE_TABLE_DDL = "CREATE TABLE public.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)"
RLS_PROBE_NO_TENANT_DDL = "CREATE TABLE public.ci_no_tenant (id int PRIMARY KEY)"
RLS_PROBE_OTHER_SCHEMA_DDL = "CREATE TABLE ci_other.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)"
```

### 2-4 backend/tests/test_check_public_tenant_rls.py
(1) import を足す。変更前:
```python
import pytest

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
```
変更後:
```python
import pytest

from tests.conftest import (
    RLS_PROBE_NO_TENANT_DDL,
    RLS_PROBE_OTHER_SCHEMA_DDL,
    RLS_PROBE_TABLE_DDL,
)

ADMIN_PG_URL = os.getenv("RLS_ADMIN_DATABASE_URL") or os.getenv("TEST_PG_URL")
```
(2) 次の文字列の置き換えをファイル全体で行う（文字列の中身ではなく、引数を定数に変える）:
- `_exec(conn, "CREATE TABLE public.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")` → `_exec(conn, RLS_PROBE_TABLE_DDL)`（4 か所: R1・R2・R3・R5）
- `_exec(conn, "CREATE TABLE public.ci_no_tenant (id int PRIMARY KEY)")` → `_exec(conn, RLS_PROBE_NO_TENANT_DDL)`（1 か所: R6）
- `_exec(conn, "CREATE TABLE ci_other.ci_rls_probe (id int PRIMARY KEY, tenant_id int NOT NULL)")` → `_exec(conn, RLS_PROBE_OTHER_SCHEMA_DDL)`（1 か所: R6）
ほかの行（ALTER TABLE・CREATE SCHEMA・assert・docstring）は変えない。

## 3. 確かめ（クラウドで実行し、生の出力を報告に貼る）
- V1 `grep -c 'CREATE TABLE' backend/tests/test_check_public_tenant_rls.py` が 0。
- V2 `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=$(git rev-parse HEAD) python3 scripts/check_test_schema_dup.py` の最後の行が「テストへの新規スキーマ複製なし(pass)」で終了コード 0。
- V3 `cd backend && python3 -c "from app.ops.tenant_rls_allowlist import PUBLIC_TABLES_WITHOUT_RLS as A; print(len(A), sorted(k for k, v in A.items() if not v.strip()))"` が `11 []`。
- V4 `grep -c "report-only" .github/workflows/migration-test.yml` が 0。`python3 -c "import yaml; yaml.safe_load(open('.github/workflows/migration-test.yml'))"` が何も出さず終わる。
- V5 `cd backend && ruff check app/ops/tenant_rls_allowlist.py tests/test_check_public_tenant_rls.py tests/conftest.py` と `ruff format --check` の同じ 3 ファイル（ruff が入っていれば。入っていなければ「未実行」と書く）。
- V6 PostgreSQL が使えるなら RLS_ADMIN_DATABASE_URL に使える接続先を入れて `cd backend && python3 -m pytest -q tests/test_check_public_tenant_rls.py`。使えなければ「未実行（PostgreSQL なし）」と書く（CI の pytest で確かめる）。
- V7 `git diff --name-only HEAD~1 HEAD`（自分のコミット）が「1. 触るファイル」の 4 件だけ。

## 4. 終わったら
- コミットは 1 つ（メッセージ: `feat(ci): fail on public tenant tables without RLS, fill allowlist (ADR-1063 bin5 step2)`）。push する。PR は作らない。
- 報告の最後の行は `DONE`、または `BLOCKED:` に続けて理由、または `NEEDS_DECISION:` に続けて問い。
- 停止するとき（実装前点検が外れた・確かめが期待と違う・カードに無い判断が要る）は、そこで作業を止め、報告の最後の行を `BLOCKED:` か `NEEDS_DECISION:` にして Opus に返す。推測で続けない。

END OF CARD
