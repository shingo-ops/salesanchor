# 実装カード 便④-5 — public.tenant_llm_budgets・public.tenant_settings に RLS（型C）＋運営の書込 2 か所と翻訳の見張りの書込 1 か所に文脈を足す

- 状態: 設計案（Opus 作成）。クラウド設計審査 1 回目 REVISE（指摘1〜4）を反映した 2 版。再審査の前。PO の実装承認は design.md 冒頭（2026-11-06「1」: KGI-4〜6 と 5 便の順番）。完走の指示は PO 2026-11-07 チャット「PRマージ、デプロイまで完走させてくれ」。次の 3 つの表へ進むことは PO 2026-11-07 チャット「1」。
- 根拠の版: origin/main d8db9b69d（2026-11-07 便④-4 #5233 の合流後に fetch）。行番号はすべてこの版。
- 設計: [design.md](design.md) §2 :25-26（2 表とも型C＋運営画面に運営の文脈）・§3 :88（④-5 で足すコード 3 か所）・:96-97（前提の表）・:108（前提の移行の順）・§4 :114（④-5 の試験）・§5 :123（K5-2 ④-5）・:133（会社を作る処理）・:144（コードと RLS を 1 つの戻しの PR で戻す）。手本: 便④-4 [card-4-4.md](card-4-4.md) と、合流済みの backend/tests/test_google_webhook_subscriptions_rls.py。
- 実装ブランチ: `release/s1-rls-stage4-bin5`（origin/main d8db9b69d から作った。カードはこのブランチに Opus が置く）。1 便 1 PR。PR は Draft で起票する。

## 1. 触るファイル（これ以外は触らない）

| # | ファイル | 変更 |
|---|---|---|
| 1 | `migrations/20261107_160000_add_tenant_budget_settings_rls.sql` | 新規。§2 の SQL を一字一句この内容で作る |
| 2 | `scripts/run_all_migrations.sh` | 末尾（今の最終行 :1249 `run_sql migrations/20261107_150000_add_google_webhook_subscriptions_rls.sql` の次の行）に §3 の 2 行を足す |
| 3 | `backend/app/routers/super_admin_llm_budget.py` | §6-1 のとおり（取り込み 1 行と `upsert_budget` の書込を囲む） |
| 4 | `backend/app/routers/super_admin_phase_switch.py` | §6-2 のとおり（取り込み 1 行と `switch_phase_endpoint` の書込〜commit を囲む。記録の呼び出しを savepoint に入れる） |
| 5 | `backend/app/services/translation_monitor.py` | §6-3 のとおり（`notify_translation_anomaly` の末尾の書込だけ） |
| 6 | `backend/tests/test_tenant_budget_settings_rls.py` | 新規。§5 |
| 7 | `backend/tests/test_tenant_loop_migration_guard.py` | `_REVIEWED` に 1 項目足すだけ（§5-2） |
| 8 | `docs/handoff/s1-rls-stage4/card-4-5.md` | このカード（Opus が置く。実装役は触らない） |

- `.github/workflows/migration-test.yml` は**触らない**（§4。前提の表は既に変更 SQL より先に作られる）。
- 実装の直前に `git fetch origin && git ls-tree --name-only origin/main migrations/ | tail -3` を流し、`20261107_160000` と同じ時刻か、より後の名前の移行が main に入っていたら止まって Opus に戻す（名前を自分で変えない）。
- 触らない: 上の 3〜5 以外のプログラム（backend/app 配下。§6-4 の入口はどれも既に会社の文脈がある）、`backend/tests/conftest.py`、`backend/tests/rls_bootstrap.py`、既存の試験（`backend/tests/test_translation_monitor.py` ほか）、frontend、他の表。

## 2. 移行 SQL（design §2-2 の型C を 2 表の名で埋め、1 つの取引にまとめたもの）

```sql
-- ADR-1067 段階④ 便④-5: public.tenant_llm_budgets・public.tenant_settings に会社ごとの RLS（型C）を付ける。
-- 読む: 全行（運営画面が全社を一覧するため。design.md §2）。書く: 自社の会社文脈か運営文脈だけ。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-2。
BEGIN;
ALTER TABLE public.tenant_llm_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_llm_budgets FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_llm_budgets_select ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_select ON public.tenant_llm_budgets FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_llm_budgets_insert ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_insert ON public.tenant_llm_budgets FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_llm_budgets_update ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_update ON public.tenant_llm_budgets FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_llm_budgets_delete ON public.tenant_llm_budgets;
CREATE POLICY tenant_llm_budgets_delete ON public.tenant_llm_budgets FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
ALTER TABLE public.tenant_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_settings FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_settings_select ON public.tenant_settings;
CREATE POLICY tenant_settings_select ON public.tenant_settings FOR SELECT USING (true);
DROP POLICY IF EXISTS tenant_settings_insert ON public.tenant_settings;
CREATE POLICY tenant_settings_insert ON public.tenant_settings FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_settings_update ON public.tenant_settings;
CREATE POLICY tenant_settings_update ON public.tenant_settings FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS tenant_settings_delete ON public.tenant_settings;
CREATE POLICY tenant_settings_delete ON public.tenant_settings FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
```

## 3. run_all_migrations.sh に足す 2 行

```bash
# ADR-1067 段階④ 便④-5: tenant_llm_budgets・tenant_settings に会社ごとの RLS（型C: 読取は全行・書込は自社か運営）。冪等・1 取引
run_sql migrations/20261107_160000_add_tenant_budget_settings_rls.sql
```

- 本番の順: tenant_llm_budgets を作る 062（run_all:361 `run_py scripts/migrate_inventory_sprint1.py`、その一覧 scripts/migrate_inventory_sprint1.py:51-58）、列を足す 066（:363 `run_py scripts/migrate_inventory_sprint5_to_7.py`）と 20260604_220000（:518）。tenant_settings を作る 070（:365 `run_py scripts/migrate_inventory_sprint9.py`）、080（:379）、20260604_050000（:459）。どれも本 SQL（:1251 になる）より先に流れる。
- 移行を流す役は jarvis（本番で rolsuper=t・rolbypassrls=t。便④-3 のカード §3）。後の移行が表を UPDATE しても RLS に止められない。

## 4. CI（足すものは無い）

- 変更 SQL のジョブ（`.github/workflows/migration-test.yml` migration-test-run）:
  - tenant_settings: `PUBLIC_SQL` :497-504 に定義済み（会社 1 の行も入る）。
  - tenant_llm_budgets: step「Sprint 1 マイグレーションを適用」:1042-1052 が `scripts/migrate_inventory_sprint1.py` を流し、その一覧に 062 がある（scripts/migrate_inventory_sprint1.py:51-58）。この step は「変更 SQL を 1回目実行」:1359 より前。design.md :96 のとおり。
  - 本 SQL は 2 表の ENABLE・ポリシーだけで、066・20260604_220000・080・20260604_050000 が足す列や既定値に触れない。よって前提の step は要らない。
- 全件ドライラン（migration-full-dryrun）: :1922 で Sprint 1 を流し、run_all の順（§3）で残りが先に流れる。足すものは無い。
- CI の変更 SQL のジョブが「表が無い」で落ちたら、step を自分で足さずに止まって Opus に戻す。

## 5. 試験 backend/tests/test_tenant_budget_settings_rls.py（新規）

手本: 合流済みの backend/tests/test_google_webhook_subscriptions_rls.py（便④-4）。skipif（:21-30）・`_GRANT_DDL`（:41-44）・`_with_db`・`_fresh()`（:65-112）・`_admin_exec`・`_ctx_conn`（:123-134）・`_sqlstate` を同じ形で書く。使い捨て DB の名は `tbs_rls_<hex12>`。

- 会社番号: 966（自社）・967（他社）・965（会社を作る処理の試験だけで使う）。backend/tests で未使用（`grep -rn -w -E '965|966|967' backend/tests` が 0 件。d8db9b69d で確かめた）。実装の前にもう一度流し、1 件でもあれば止まって Opus に戻す。
- `_fresh()` の中身:
  1. admin の接続で `_ensure_public_users(conn)`。続けて admin で `INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) VALUES (965, 'tenant_965', 'T965', 'T965', TRUE), (966, 'tenant_966', 'T966', 'T966', TRUE), (967, 'tenant_967', 'T967', 'T967', TRUE)`。
  2. 本物の移行を本番と同じ順で `_apply_migration(admin_engine, <名>)` で当てる（表の定義を試験に書き写さない）:
     `056_add_suppliers_type_and_promote_public.sql` → `062_create_inventory_movements_and_budget.sql` → `066_add_tenant_llm_budgets_notification_dedupe.sql` → `20260604_220000_create_translation_glossary.sql` → `070_add_spreadsheet_phase.sql` → `080_phase_b_migration.sql` → `20260604_050000_add_tenant_policy_columns.sql`。
     - 056 は 062 の外部キーの先 public.suppliers を作る（056:45。062:50・:97 が参照）。
     - 20260604_220000 は `tenant_\d+` の置き場を回す部分（:45-:135）を持つが、使い捨て DB にはその置き場が無いので 0 回まわるだけ。
     - 070 は public.tenants を外部キーで指す（070:48）。1 で用意される。
  3. admin で `_GRANT_DDL`。
  4. admin で各社 1 行ずつ: `INSERT INTO public.tenant_llm_budgets (tenant_id, monthly_budget_usd) VALUES (966, 10), (967, 20)`、`INSERT INTO public.tenant_settings (tenant_id, spreadsheet_phase) VALUES (966, 'B'), (967, 'B')`（965 には入れない）。
  5. `_apply_migration(admin_engine, "20261107_160000_add_tenant_budget_settings_rls.sql")`。
  - 1〜2 のどれかが使い捨て DB で通らないときは、通らない理由を記録して止まり、Opus に戻す（推測で定義を書き足さない）。
- 型C の試験（design §4 ①〜⑥）。2 表それぞれに行う（`@pytest.mark.parametrize` で表名を回してよい）。すべて app_engine（salesanchor_app・NOBYPASSRLS）で:
  - ① 文脈なし（新しい接続）で SELECT すると 966・967 の両方の行が見える。967 の文脈でも 966 の行が見える。同じ接続で `SET app.tenant_id = ''` の後の SELECT もエラー（22P02）にならず 2 行。
  - ② 966 の文脈で 967 の行を INSERT すると 42501（967 の行は既にあるので、主キーより先に RLS で止まることを sqlstate で確かめる）。budgets は `(tenant_id) VALUES (967)`、settings は `(tenant_id, spreadsheet_phase) VALUES (967, 'B')`。
  - ③ 966 の文脈で 967 の行への UPDATE（budgets は monthly_budget_usd、settings は spreadsheet_phase='A'）・DELETE が 0 行。後で admin で 967 の行が元のまま 1 行あることを確かめる。
  - ④ 運営の文脈（`app.is_operator='true'`・`app.tenant_id=''`）で 967 の行の UPDATE が 1 行（最後に ROLLBACK してよい）。
  - ⑤ 同じ移行をもう一度当ててもエラーにならず、`pg_policies` の本数が各表 4 のまま。
  - ⑥ 966 の文脈で自社の行の tenant_id を 967 へ付け替える UPDATE が 42501。
- 入口の試験（design §4 :114・:133。各 1 本）。session は `async_sessionmaker(app_engine, expire_on_commit=False)()` で作る:
  - ⑦ 予算の保存（運営）: session で `SET app.tenant_id = ''` と `SET app.is_operator = ''` を流して commit（get_db の後と同じ「文脈なし」）。`from app.routers.super_admin_llm_budget import LLMBudgetUpdate, upsert_budget` を直に `await upsert_budget(967, LLMBudgetUpdate(monthly_budget_usd=Decimal("25.00"), hard_stop=True, notify_admin=True), db=session)` で呼ぶ。確かめ: 例外なく返り、返り値の monthly_budget_usd が 25.00。admin で 967 の monthly_budget_usd が 25.00。続けて `await session.close()` の後、同じ app_engine（`pool_size=1, max_overflow=0` なので同じ接続が戻る）から新しい接続を取り、`SELECT current_setting('app.is_operator', true)` が `''`（運営の印が接続に残っていない。§6 冒頭）。§6-1 の直しが無いと INSERT が 42501 で落ちることを、直しの前にこの試験を流して確かめ、その生出力も残す。
  - ⑧ 段階の切替（運営）: ⑦と同じ文脈なしの session。record_audit_log は**差し替えない**（使い捨て DB には tenant_967.audit_logs が無いので本物の呼び出しが失敗し、§6-2 の savepoint の道を通る。その理由を試験の説明文に書く）。`await switch_phase_endpoint(967, PhaseSwitchRequest(phase="A"), db=session, current_user=types.SimpleNamespace(id=1))`。確かめ: 例外なく返り、返り値の phase が 'A'。admin で 967 の spreadsheet_phase が 'A'（記録の失敗で切替が消えていない）。⑦と同じく `session.close()` の後の新しい接続で `current_setting('app.is_operator', true)` が `''`。直しの前に流して 42501 で落ちることを確かめ、生出力を残す。
  - ⑨ 翻訳の見張りの通知: ⑦と同じ文脈なしの session。`app.services.translation_monitor._post_webhook` を `AsyncMock(return_value=True)` で差し替え、`await notify_translation_anomaly(session, 966, TranslationHealthSnapshot(100, 30, 40, 0.30, 0.40), tenant_code="t966")`。確かめ: 返り値 True。admin で 966 の `last_translation_monitor_notified_at` が NULL でない（試験の前は NULL であることも確かめる）。同じ session で `SELECT 1` が通る（取引が壊れていない）。⑦と同じく `session.close()` の後の新しい接続で `current_setting('app.tenant_id', true)` が `''`。直しの前に流すと時刻が NULL のままで落ちることを確かめ、生出力を残す。
  - ⑦〜⑨の「新しい接続で空」の確かめは、§6 冒頭の古い形（commit の後に外す）では `'true'`／`'966'` が残って落ちる。手元で古い形でも 1 回流して落ちることを確かめ、生出力を残す（落ちなければ試験が漏れを確かめていないので止まって Opus に戻す）。
  - ⑩ 会社を作る処理: app_engine の接続で取引を始め、`SELECT set_config('app.tenant_id', '965', true)`（backend/app/services/tenant.py:1779-1782 と同じ）の後、tenant.py:1800-1814 と同じ INSERT（`INSERT INTO public.tenant_settings (tenant_id, spreadsheet_phase, inventory_agg_filter, agg_price_threshold_jpy, agg_qty_threshold, quote_validity_days, default_currency, document_language, duty_incoterms, issue_mode) VALUES (965, 'B', 'none', 0, 0, 1, 'JPY', 'en', 'DAP', 'pdf') ON CONFLICT (tenant_id) DO NOTHING`）を流して commit。確かめ: admin で 965 の行が 1 行。
- 既にある試験への影響:
  - backend/tests/test_translation_monitor.py の `notify_translation_anomaly` の試験（:120-180）は、どれも `_post_webhook` が False を返す道で、§6-3 で変える `if sent:` の中に入らない。変えずに通ることを確かめる。
  - tenant_settings・tenant_llm_budgets を書く既存の試験（test_phase_gate.py・test_super_admin_phase_switch.py・test_rls_auth_audit.py・test_permission_resolution_pg.py）は共有の試験 DB（jarvis_test_db）を使い、本移行はそこに当たらない（本移行を当てるのは本試験の使い捨て DB だけ）。CI で通ることを確かめる。落ちたら直さずに止まって Opus に戻す。

## 5-2. 見張りの分類表への登録

- 決まり（backend/tests/test_tenant_loop_migration_guard.py:1-6）: 全テナントを回す移行を名前で参照する試験は `_REVIEWED` に分類を書く。本試験は 20260604_220000（`nspname ~ '^tenant_\d+$'` で回す。:50-51・:101-102）を名前で参照する。使い捨て DB なので分類は `own_database`。
- 直し: `_REVIEWED` の `"test_google_webhook_subscriptions_rls.py": (...)` の項目（:238-242）の直後、閉じの `}`（:243）の前に、次の 5 行を足す。ほかの行は変えない。

```python
    "test_tenant_budget_settings_rls.py": (
        "own_database",
        "",
        frozenset({"20260604_220000_create_translation_glossary.sql"}),
    ),
```

- 056・062・066・070・080・20260604_050000 は全テナントを回さない（本文に `tenant_` の置き場を選ぶ文が無い。056 の `tenant_004` は説明文だけ）ので書かない。CI でこの見張りが別の名前で落ちたら、名前を足さずに止まって Opus に戻す。

## 6. コードの直し（3 か所）

型（設計審査 指摘1 で直した）: 運営の印を外す `reset_operator_context` は **commit の前**に、同じ取引の中で流す。

- 理由（事実）: SQLAlchemy は commit の後に次の取引を自動で始める。commit の後に `SET app.is_operator = ''` を流すと、その SET は commit されない取引に入る。session を閉じるとき（get_db の finally の `clear_tenant_context` も含めて）その取引は巻き戻され、SET も消える（PostgreSQL の SET は取引の巻き戻しで元に戻る）。接続の返却時の後始末は巻き戻しだけで、設定は戻さない。結果、commit 済みの `app.is_operator='true'` が接続に残り、同じ接続を次に使う要求が運営の印を持ったまま動く。
- commit の前に外せば、外したことも commit される。途中で例外が出たら `db.rollback()` で書込と運営の印の両方が取り消される（印を張った SET も同じ取引の中のため）。
- 既にある fx_rate_admin.py:135-149 は commit の後に外す古い形で、同じ漏れがある。本便では直さない（Opus が台帳に残す）。手本にしない。

### 6-1. backend/app/routers/super_admin_llm_budget.py

- 取り込み :25 `from app.auth.dependencies import require_super_admin` を次にする:
  `from app.auth.dependencies import require_super_admin, reset_operator_context, set_operator_context`
- `upsert_budget` の :151 `await db.execute(` 〜 :171 `await db.commit()` を、次の形で囲む（中の文は 1 字も変えない。字下げだけ 4 つ深くする）:

```python
    await set_operator_context(db)
    try:
        await db.execute(
            ...（:152-170 のまま）
        )
        await reset_operator_context(db)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

- :173 以降の再取得（SELECT）は囲まない（読取は全行。運営の文脈は要らない）。

### 6-2. backend/app/routers/super_admin_phase_switch.py

- 取り込み :24 `from app.auth.dependencies import require_super_admin` を次にする:
  `from app.auth.dependencies import require_super_admin, reset_operator_context, set_operator_context`
- `switch_phase_endpoint` の :128 `# DB 更新` 〜 :153 `await db.commit()` を、次の形にする。変えるのは (a) 全体を囲む、(b) `await record_audit_log(` の呼び出しを `async with db.begin_nested():` の中に入れる、(c) commit の前に `reset_operator_context` を流す、の 3 点だけ。record_audit_log の引数・except の中身・コメントの文は 1 字も変えない（字下げだけ深くする）:

```python
    await set_operator_context(db)
    try:
        # DB 更新
        applied = await set_phase(tenant_id, new_phase, db)  # type: ignore[arg-type]

        # AC9.4: audit_log 記録（B/C 切替時の証跡用）
        try:
            async with db.begin_nested():
                await record_audit_log(
                    ...（:134-141 のまま）
                )
        except Exception as exc:  # noqa: BLE001
            ...（:144-151 のまま）

        await reset_operator_context(db)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
```

- :126 `old_phase = await get_phase(...)`（読取）は囲まない。`get_phase_endpoint`（GET）は触らない。
- `begin_nested()` を足す理由（設計審査 指摘3。事実はコードから）: record_audit_log（backend/app/services/audit.py:277-:320）は `tenant_{id:03d}.audit_logs` に INSERT する。その表のポリシーは `tenant_id = current_setting('app.tenant_id', true)::INTEGER`（NULLIF なし。backend/app/services/tenant.py:1288-1289）。運営の要求には会社の文脈が無く `app.tenant_id` は空なので、この INSERT はエラーになり PostgreSQL の取引全体が中断する。今のコードは except で握るが、続く commit は中断した取引を確定できず、段階の切替も保存されない。元のコメント（:144-147「切替自体は成功させて warning ログを残す」）の意図どおりにするため、記録だけを取引の中の小さな区切り（savepoint）に入れ、失敗してもその区切りだけを巻き戻す。本番でこの失敗が実際に起きているかは確かめていない（reader 鍵は tenant_004.audit_logs を読む権限が無く 42501。2026-11-07 09:06 JST）。
- 運営の切替で記録（audit）が書かれないこと自体は本便では直さない（会社の文脈を張るかは audit の設計の件）。Opus が台帳に残す。

### 6-3. backend/app/services/translation_monitor.py

- 取り込みは足さない（:24 で `clear_tenant_context, set_tenant_context` を取り込み済み）。
- `notify_translation_anomaly` の :204-209 を次にする（それ以外は変えない）:

変更前（:204-209）:
```python
    if sent:
        try:
            await _update_last_notified(db, tenant_id)
            await db.commit()
        except Exception as exc:
            logger.warning("[translation_monitor] デバウンス更新失敗: %s", exc)
```

変更後:
```python
    if sent:
        try:
            await set_tenant_context(db, tenant_id)
            await _update_last_notified(db, tenant_id)
            await clear_tenant_context(db)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.warning("[translation_monitor] デバウンス更新失敗: %s", exc)
```

- 文脈を外す `clear_tenant_context` は commit の前に流す（§6 冒頭と同じ理由。commit の後に外すと、その SET は session を閉じるときの巻き戻しで消える）。例外のときは `db.rollback()` が文脈を張った SET も取り消す。呼び出し元 `_run_health_check`（backend/app/tasks/translation.py）は本関数の後に会社の文脈を当てにしない（次の会社は `check_translation_health` が自分で張って外す）。

- 理由（事実）: 毎時の見張り（backend/app/tasks/translation.py:120-129 → `_run_health_check`）は 1 つの session で全社を回す。`check_translation_health` は :59 で会社の文脈を張り、:106 の finally で外す。その後に呼ばれる本関数の書込（:206 → :125-135 の INSERT … ON CONFLICT）は文脈なしになり、型C では 42501 で落ちる。`db.rollback()` を足すのは、落ちた取引を残すと同じ session の次の会社の読取が「current transaction is aborted」で止まるため。
- `_get_last_notified`（:109-122 の SELECT）は直さない（読取は全行）。

### 6-4. 触らない書込の入口（既に会社の文脈がある。根拠）

| 書込 | 場所 | 文脈 |
|---|---|---|
| tenant_llm_budgets UPDATE（月替わり）・UPDATE（費用の加算）・INSERT（行を作る） | backend/app/services/llm_budget.py:475・:527・:567 | 呼び出し元 backend/app/services/message_translator.py:462-490・:614-623。message_translator を呼ぶ入口はどれも会社の文脈を張った session: 翻訳の作業 backend/app/tasks/translation.py:128-142（`set_tenant_context`）、backend/app/routers/leads.py:1386-1445（`get_current_tenant`）、backend/app/routers/conv_logs.py:152-153（`set_tenant_context`） |
| tenant_llm_budgets UPDATE | backend/app/services/discord_notifier.py:222・:254（notify_budget_exhausted） | 呼び出し元が無い（`grep -rn notify_budget_exhausted backend/app` は定義だけ） |
| tenant_settings UPDATE | backend/app/routers/tenant_policy.py:129 | `get_current_tenant`（backend/app/auth/dependencies.py）が `app.tenant_id` を自社に張る |
| tenant_settings INSERT … ON CONFLICT DO NOTHING | backend/app/services/tenant.py:1800-1814（会社を作る処理） | :1779-1782 で新しい会社の `app.tenant_id` を張ってから書く（§5 ⑩で確かめる） |

- 読取だけの箇所（直さない）: super_admin_llm_budget.py の一覧・1 件取得（:93・:116）、backend/app/routers/tcg_analysis_dashboard.py:526、super_admin_phase_switch.py の GET、tenant_policy.py の GET。

## 7. 合格の条件（実装役が自分で確かめて生出力をファイルに残す）

| 基準 | 確かめ方 |
|---|---|
| §1 の 1〜7 以外に差分が無い（8 は Opus） | `git diff origin/main...HEAD --name-only` |
| 移行 SQL が §2 と一字一句同じ | `diff` で 0 行 |
| run_all の差分が §3 の 2 行の追加だけ | `git diff origin/main...HEAD -- scripts/run_all_migrations.sh` |
| プログラムの差分が §6-1〜6-3 だけ（中の文は字下げ以外変わらない） | `git diff origin/main...HEAD -w -- backend/app` で、足した行が取り込み 2 行・`set_operator_context`/`try:`/`reset_operator_context`/`except Exception:`/`await db.rollback()`/`raise` の各 2 組・§6-2 の `async with db.begin_nested():` 1 行・§6-3 の 3 行（`set_tenant_context`・`clear_tenant_context`・`await db.rollback()`）だけ。`reset_operator_context`・`clear_tenant_context` はどれも `await db.commit()` の直前の行 |
| §5 ⑦〜⑨が直しの前に落ち、直しの後に通る | 直しの前後で手元の PostgreSQL（または CI）で流した生出力 |
| CI の Backend Tests・migration-test・ADR index ほか必須チェックが全部緑 | `gh pr checks <PR>` |
| 新しい試験が CI で実行されて通っている（skip でない） | CI の PostgreSQL のログに `violates row-level security policy for table "tenant_llm_budgets"` と `"tenant_settings"` が両方出る |
| i18n・UI は触らない | 差分に frontend が無い |

## 8. 本番の確かめ（Opus が反映の後に行う。実装役は行わない）

基準値（2026-11-07 08:45 JST、反映前に Opus が reader 鍵の道で読んだ）: 2 表とも RLS f/f・ポリシー 0 本・持ち主 jarvis。tenant_llm_budgets は会社 4・6 の 2 行（`last_translation_monitor_notified_at` は 2 行とも NULL＝本番で見張りの通知は一度も出ていない）。tenant_settings は会社 1・3・4・5・6 の 5 行（すべて段階 B）。

- 読む道: 基準値・K4-1・K4-2 は reader 鍵の道（docs/handoff/ai-readonly-db-path/usage.md）で読む。無制限鍵で本番 DB を読むことはしない。
- K4-1: 2 表とも relrowsecurity / relforcerowsecurity が t/t、ポリシー各 4 本（計 8）。
- K4-2: 会社ごとの行数が上の基準値と同じ。
- K5-1: 反映時刻以降の backend・celery-worker・celery-beat のログで `42501`・`row-level security`・`invalid input syntax for type integer`・`デバウンス更新失敗`（translation_monitor.py）が 0 件。
- K5-2（design §5 :123 ④-5）: 運営画面で予算を同じ値で保存して 200、段階の切替の画面を開いて 200。運営（super admin）のログインが要るので PO に画面で確かめてもらう（PO の戻り後）。段階の切替は本番では押さない（会社の段階が実際に変わるため。開いて 200 まで）。マージの条件にはしない。代わりに §5 ⑦⑧で同じ関数を「文脈なし」の接続から呼んで確かめる。
- 翻訳の見張りの書込は本番で一度も起きていない（上の基準値）ため、本番では観測しない。§5 ⑨で確かめる。毎時の見張りの作業が反映後も `succeeded` で終わることを K5-1 と同じログで 1 回見る。

## 9. 戻し方（design §7 を表名で埋めたもの）

```sql
BEGIN;
DROP POLICY IF EXISTS tenant_llm_budgets_select ON public.tenant_llm_budgets;
DROP POLICY IF EXISTS tenant_llm_budgets_insert ON public.tenant_llm_budgets;
DROP POLICY IF EXISTS tenant_llm_budgets_update ON public.tenant_llm_budgets;
DROP POLICY IF EXISTS tenant_llm_budgets_delete ON public.tenant_llm_budgets;
ALTER TABLE public.tenant_llm_budgets NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_llm_budgets DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_settings_select ON public.tenant_settings;
DROP POLICY IF EXISTS tenant_settings_insert ON public.tenant_settings;
DROP POLICY IF EXISTS tenant_settings_update ON public.tenant_settings;
DROP POLICY IF EXISTS tenant_settings_delete ON public.tenant_settings;
ALTER TABLE public.tenant_settings NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tenant_settings DISABLE ROW LEVEL SECURITY;
COMMIT;
```

- 順番・道・流す人は design §7 のとおり（便④-1 card-4-1.md §8 と同じ）。design :144 のとおり、コード（§6）と RLS を 1 つの戻しの PR で戻す。コードだけを先に戻す PR は作らない（RLS が残ったまま運営画面の保存が止まる）。§6 の文脈を足すコードは RLS が無くても害が無い（運営の文脈・会社の文脈を張って外すだけ）ので、RLS だけを戻す場合はコードを残してよい。

## 10. 想定される分岐（実装役が出会ったら止まって Opus に戻す）

- §5 の 2 の移行のどれかが使い捨て DB で失敗する。
- 965・966・967 が既に使われている。
- §5 ⑦〜⑨が直しの前に落ちない（＝試験が直しを確かめていない）。
- 既にある試験（§5 の「既にある試験への影響」）が落ちる。
- 見張りの分類表の試験が、§5-2 の名前以外で落ちる。
- CI の変更 SQL のジョブが「表が無い」で落ちる（§4）。
- main に `20261107_160000` と同じ時刻か、より後の移行が先に入った。
- 上の以外でも、カードに書いていない変更が要ると分かったとき。

## 11. 危険パスと GO

- `migrations/`・`scripts/` を含む＝危険 PR（ADR-135・ADR-136）。マージの前に、審査役（reviewer・opus）の APPROVE、CI 全緑、直前のバックアップの確認を揃え、PR 本文に `### GO記録`（POの委任に基づくClaude Opus発行・委任 ADR-1003・PR 番号・HEAD・日時・相乗りの PR が無いこと）を書く。
