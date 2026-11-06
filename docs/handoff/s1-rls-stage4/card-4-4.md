# 実装カード 便④-4 — public.google_webhook_subscriptions に RLS（型C）

- 状態: 草案（クラウド設計審査の前）。PO の実装承認は design.md 冒頭（2026-11-06「1」: KGI-4〜6 と 5 便の順番）。完走の指示は PO 2026-11-07 チャット「PRマージ、デプロイまで完走させてくれ」。次の 3 つの表へ進むことは PO 2026-11-07 チャット「1」（便④-2 の報告の選択肢 1）。
- 根拠の版: origin/main 9ffbc1997（2026-11-07 07:15 JST に fetch。便④-3 #5227 の合流後）。行番号はすべてこの版。
- 設計: [design.md](design.md) §2（表ごとの型: 型C）・§2-2（型C のポリシー）・§3（④-4 行と「前提の表」:98・:107）・§4（試験 型C ①〜⑥）・§5（K4-1・K4-2・K5-1・K5-2）・§7（戻し方）。現状: [recon.md](recon.md) R§4-5。手本: 便④-3 [card-4-3.md](card-4-3.md) と、合流済みの backend/tests/test_discord_config_rls.py。CI の前提の step の手本: 便④-2 [card-4-2.md](card-4-2.md) と `.github/workflows/migration-test.yml:1339-1347`。
- 実装ブランチ: `release/s1-rls-stage4-bin4`（origin/main 9ffbc1997 から作った。カードはこのブランチに Opus が置く）。1 便 1 PR。PR は Draft で起票する。

## 1. 触るファイル（これ以外は触らない）

| # | ファイル | 変更 |
|---|---|---|
| 1 | `migrations/20261107_150000_add_google_webhook_subscriptions_rls.sql` | 新規。§2 の SQL を一字一句この内容で作る |
| 2 | `scripts/run_all_migrations.sh` | 末尾（今の最終行 :1247 `run_sql migrations/20261107_140000_add_discord_config_rls.sql` の次の行）に §3 の 2 行を足す |
| 3 | `.github/workflows/migration-test.yml` | §4 の step を 1 つ足す（:1339-1347 の「Discord サーバーの記録の表」の step の直後、:1349 の「変更 SQL を 1回目実行」の前） |
| 4 | `backend/tests/test_google_webhook_subscriptions_rls.py` | 新規。§5 |
| 5 | `backend/tests/test_tenant_loop_migration_guard.py` | `_REVIEWED` に 1 項目足すだけ（§5-2） |
| 6 | `docs/handoff/s1-rls-stage4/card-4-4.md` | このカード（Opus が置く。実装役は触らない） |
| 7 | `.claude-pipeline/active-work.d/release-s1-rls-stage4-bin4.md` | 台帳（Opus が本店の写しに置く。実装役は触らない） |

- 実装の直前に `git fetch origin && git ls-tree --name-only origin/main migrations/ | tail -3` を流し、`20261107_150000` と同じ時刻か、より後の名前の移行が main に入っていたら止まって Opus に戻す（名前を自分で変えない）。
- 触らない: プログラム（backend/app 配下すべて。書込の入口はどれも会社の文脈がある。§6）、`backend/tests/conftest.py`、`backend/tests/rls_bootstrap.py`、frontend、他の表、`.github/workflows/migration-test.yml` の §4 以外の行。

## 2. 移行 SQL（design §2-2 の型C を表の名で埋め、1 つの取引にまとめたもの）

```sql
-- ADR-1067 段階④ 便④-4: public.google_webhook_subscriptions に会社ごとの RLS（型C）を付ける。
-- 読む: 全行（Google の通知の受け口が会社を決める前に channel_id から会社を引くため。design.md §2）。書く: 自社の会社文脈か運営文脈だけ。
-- 冪等（DROP POLICY IF EXISTS）・1 取引（ENABLE とポリシーの間に全拒否の間を作らない）。design.md §2-2。
BEGIN;
ALTER TABLE public.google_webhook_subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.google_webhook_subscriptions FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS google_webhook_subscriptions_select ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_select ON public.google_webhook_subscriptions FOR SELECT USING (true);
DROP POLICY IF EXISTS google_webhook_subscriptions_insert ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_insert ON public.google_webhook_subscriptions FOR INSERT
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS google_webhook_subscriptions_update ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_update ON public.google_webhook_subscriptions FOR UPDATE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true')
  WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
              OR current_setting('app.is_operator', true) = 'true');
DROP POLICY IF EXISTS google_webhook_subscriptions_delete ON public.google_webhook_subscriptions;
CREATE POLICY google_webhook_subscriptions_delete ON public.google_webhook_subscriptions FOR DELETE
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
         OR current_setting('app.is_operator', true) = 'true');
COMMIT;
```

## 3. run_all_migrations.sh に足す 2 行

```bash
# ADR-1067 段階④ 便④-4: google_webhook_subscriptions に会社ごとの RLS（型C: 読取は全行・書込は自社か運営）。冪等・1 取引
run_sql migrations/20261107_150000_add_google_webhook_subscriptions_rls.sql
```

- 本番の順: 表を作る 077（:376）と列を足す 20261103_200000（:1217）は、本 SQL（:1249 になる）より先に流れる。
- 移行を流す役は jarvis（本番で rolsuper=t・rolbypassrls=t。便④-3 のカード §3 で 2026-11-07 04:21 JST に読んだ）。後の移行が表を UPDATE しても RLS に止められない。

## 4. CI の前提の step（1 つ足す）

- 事実: 変更 SQL のジョブの `PUBLIC_SQL` は tenant_google_calendar_config を :957 に定義しているが、google_webhook_subscriptions は定義していない（`git grep -n google_webhook_subscriptions origin/main -- .github/workflows/migration-test.yml` が 0 件）。このままだと本 SQL の 1 行目の ALTER が「表が無い」で落ちる。
- design.md :98・:107 のとおり、077 → 20261103_200000 の順で先に流す step を足す。077 が ALTER する tenant_google_calendar_config は :957 に定義済み。077 の外部キーの tenants も定義済み（design.md :98）。
- 足す step（:1339-1347 の手本と同じ形。インデントも合わせる）:

```yaml
      - name: 変更 SQL の前提の移行を先に実行（Google カレンダーの通知の登録の表）
        if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261107_150000_add_google_webhook_subscriptions_rls.sql')
        run: |
          # 20261107_150000 は google_webhook_subscriptions（077）と、その列を足す 20261103_200000 が先にある前提（本番と同じ順）
          for sqlfile in migrations/077_calendar_sync_mode_and_webhook_subscriptions.sql migrations/20261103_200000_add_google_calendar_import_sync.sql; do
            echo "▶ $sqlfile を前提として実行中..."
            psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
            echo "✅ $sqlfile 成功"
          done

```

- 全件ドライラン: run_all の順で表が先に作られる（§3）。足すものは無い。

## 5. 試験 backend/tests/test_google_webhook_subscriptions_rls.py（新規）

手本: 合流済みの backend/tests/test_discord_config_rls.py（便④-3）。skipif・`_GRANT_DDL`・`_fresh()`・`_admin_exec`・`_ctx_conn`・`_sqlstate` を同じ形で書く。

- 会社番号: 968（自社）・969（他社）。backend/tests で未使用（`git grep -n -w 968 origin/main -- backend/tests` と `git grep -n -w 969 origin/main -- backend/tests` がどちらも 0 件。9ffbc1997 で確かめた）。実装の前にもう一度流し、1 件でもあれば止まって Opus に戻す。
- `_fresh()` の中身（使い捨て DB `gws_rls_<hex12>`、app_engine は `pool_size=1, max_overflow=0`）:
  1. admin の接続で `_ensure_public_users(conn)`（rls_bootstrap.py）。続けて admin で `INSERT INTO public.tenants (id, tenant_code, tenant_name, company_name, is_active) VALUES (968, 'tenant_968', 'T968', 'T968', TRUE), (969, 'tenant_969', 'T969', 'T969', TRUE)`。
  2. 本物の移行を本番と同じ順で `_apply_migration(admin_engine, <名>)` で当てる（表の定義を試験に書き写さない）: `076_add_google_calendar_config.sql` → `077_calendar_sync_mode_and_webhook_subscriptions.sql` → `20261103_200000_add_google_calendar_import_sync.sql`。
     - 076 は public.users を外部キーで指す（:108）。1 の `_ensure_public_users` で用意される。
     - 20261103_200000 は `tenant_\d+` の置き場を回す部分を持つが、使い捨て DB にはその置き場が無いので 0 回まわるだけ。
  3. admin で `_GRANT_DDL`（便④-3 の試験と同じ）。
  4. admin で各社 1 行ずつ INSERT: `(tenant_id, channel_id, expiration)` = `(968, 'ch968', now() + interval '3 days')`・`(969, 'ch969', now() + interval '3 days')`。
  5. `_apply_migration(admin_engine, "20261107_150000_add_google_webhook_subscriptions_rls.sql")`。
  - 1〜2 のどれかが使い捨て DB で通らないときは、通らない理由を記録して止まり、Opus に戻す（推測で定義を書き足さない）。
- 試験（design §4 型C ①〜⑥）。すべて app_engine（アプリの接続役 salesanchor_app・NOBYPASSRLS）で行う:
  - ① 文脈なし（新しい接続）で SELECT すると 968・969 の両方の行が見える（2 行）。969 の文脈でも 968 の行が見える。同じ接続で `SET app.tenant_id = ''` の後の SELECT もエラー（22P02）にならず 2 行。加えて、文脈なしで `SELECT tenant_id, channel_token_hash FROM google_webhook_subscriptions WHERE channel_id = 'ch969'`（backend/app/services/google_webhook.py:212 の受け口と同じ文）が 1 行返る。
  - ② 968 の文脈で tenant_id=969 の INSERT が 42501（channel_id は 'x969'。tenant_id の UNIQUE と channel_id の UNIQUE より先に RLS で止まることを sqlstate で確かめる）。
  - ③ 968 の文脈で 969 の行への UPDATE（sync_token だけ変える）・DELETE が 0 行。後で admin で 969 の行が元のまま 1 行あることを確かめる。
  - ④ 運営の文脈（`app.is_operator='true'`・`app.tenant_id=''`）で 969 の行の UPDATE が 1 行（取引は最後に ROLLBACK してよい）。
  - ⑤ 同じ移行をもう一度当ててもエラーにならず、`pg_policies` の本数が 4 のまま。
  - ⑥ 968 の文脈で自社の行の tenant_id を 969 へ付け替える UPDATE が 42501。
  - ⑦ 書込の入口と同じ文脈の張り方で、自社の行の書込が通る: app_engine の接続で `SET app.tenant_id = '968'` と `SET app.is_operator = ''`（backend/app/auth/dependencies.py:297-298 の set_tenant_context と同じ 2 文。set_config でなく SET）を流し、次の 3 文がエラー無く通り、admin で値が変わったことを確かめる。最後に同じ接続で `SET app.tenant_id = ''` に戻す。
    - google_webhook.py:117-129 と同じ `INSERT INTO google_webhook_subscriptions (tenant_id, channel_id, resource_id, calendar_id, expiration, channel_token_hash) VALUES (968, 'ch968x', 'r968', 'primary', now() + interval '7 days', 'h968') ON CONFLICT (tenant_id) DO UPDATE SET channel_id = EXCLUDED.channel_id, resource_id = EXCLUDED.resource_id, expiration = EXCLUDED.expiration, channel_token_hash = EXCLUDED.channel_token_hash, created_at = NOW()`（既にある 968 の行に当たり UPDATE 側を通る）。確かめ: channel_id が 'ch968x'。
    - google_webhook.py:353-358 と同じ `UPDATE google_webhook_subscriptions SET sync_token = 's968' WHERE tenant_id = 968` が 1 行。確かめ: sync_token が 's968'。
    - google_webhook.py:190-192 と同じ `DELETE FROM google_webhook_subscriptions WHERE tenant_id = 968` が 1 行。確かめ: 968 の行が 0 行、969 の行は 1 行のまま。
- 既にある試験への影響: `git grep -l google_webhook_subscriptions origin/main -- backend/tests` が 0 件（9ffbc1997）。影響なし。

## 5-2. 見張りの分類表への登録

- 決まり（backend/tests/test_tenant_loop_migration_guard.py:1-6）: 全テナントを回す移行を名前で参照する試験は `_REVIEWED` に分類を書く。本試験は 20261103_200000（`nspname ~ '^tenant_\d+$'` で回す）を名前で参照する。`_fresh()` で `CREATE DATABASE` する使い捨て DB なので分類は `own_database`。
- 直し: `_REVIEWED` の `"test_discord_config_rls.py": (...)` の項目（:233-237）の直後、閉じの `}`（:238）の前に、次の 5 行を足す。ほかの行は変えない。

```python
    "test_google_webhook_subscriptions_rls.py": (
        "own_database",
        "",
        frozenset({"20261103_200000_add_google_calendar_import_sync.sql"}),
    ),
```

- 076・077 は全テナントを回さない（本文に `tenant_` の置き場を選ぶ文が無い）ので書かない。CI でこの見張りが別の名前で落ちたら、名前を足さずに止まって Opus に戻す。

## 6. 書込の入口（触らないが、文脈があることの根拠。origin/main 9ffbc1997）

| 書込 | 場所 | 文脈 |
|---|---|---|
| INSERT … ON CONFLICT DO UPDATE | backend/app/services/google_webhook.py:117-129 `register_webhook` | 呼び出し元 3 つすべてで会社の文脈: backend/app/routers/calendar.py:559（画面。:553 `reset_tenant_context`）、backend/app/tasks/google_calendar_sync.py:62（:44 `set_tenant_context`）、google_webhook.py:405（:404 `set_tenant_context`）。途中の `_get_service` が commit しても backend/app/services/google_calendar.py:293-294 で `reset_tenant_context` し直す |
| DELETE | google_webhook.py:190-192 `stop_webhook` | 呼び出し元 calendar.py:566（画面。:553 で文脈を張り直し済み） |
| UPDATE sync_token | google_webhook.py:353-358 `sync_tenant_from_google` | :255・:278 `set_tenant_context` |

- `git grep -n google_webhook_subscriptions origin/main -- backend/app scripts` の 10 行で、INSERT・UPDATE・DELETE は上の 3 か所だけ（残りは SELECT と説明文）。
- 文脈なしで読む箇所（型C で読取を全行にした理由）: google_webhook.py:210-216 `verify_channel`（Google の通知の受け口 backend/app/routers/google_calendar.py:423 から。会社が決まる前）、:393-398 `renew_expiring_webhooks`（全社の期限の点検）。

## 7. 合格の条件（実装役が自分で確かめて生出力をファイルに残す）

| 基準 | 確かめ方 |
|---|---|
| §1 の 1〜5 以外に差分が無い（6・7 は Opus） | `git diff origin/main...HEAD --name-only` |
| 移行 SQL が §2 と一字一句同じ | `diff` で 0 行 |
| run_all の差分が §3 の 2 行の追加だけ | `git diff origin/main...HEAD -- scripts/run_all_migrations.sh` |
| migration-test.yml の差分が §4 の step の追加だけ | `git diff origin/main...HEAD -- .github/workflows/migration-test.yml` |
| CI の Backend Tests・migration-test・ADR index ほか必須チェックが全部緑 | `gh pr checks <PR>` |
| 新しい試験が CI で実行されて通っている（skip でない） | CI の PostgreSQL のログに `violates row-level security policy for table "google_webhook_subscriptions"` が出る（便④-1〜④-3 で使った確かめ方） |
| i18n・UI は触らない | 差分に frontend が無い |

## 8. 本番の確かめ（Opus が反映の後に行う。実装役は行わない）

基準値（2026-11-07 07:17 JST、反映前に Opus が reader 鍵の道で読んだ）: RLS f/f・ポリシー 0 本・持ち主 jarvis。行は会社 1 が 1（期限 2026-11-12 13:11 JST）・会社 4 が 1（期限 2026-11-11 11:34 JST）の計 2。

- 読む道: 基準値・K4-1・K4-2 は design §5 のとおり reader 鍵の道（docs/handoff/ai-readonly-db-path/usage.md）で読む。無制限鍵で本番 DB を読むことはしない。
- K4-1: relrowsecurity / relforcerowsecurity が t/t、ポリシー 4 本。
- K4-2: 会社ごとの行数が上の基準値と同じ（会社 1・4 が各 1）。
- K5-1: 反映時刻以降の backend・celery-worker・celery-beat のログで `42501`・`row-level security`・`invalid input syntax for type integer` が 0 件。加えて celery-worker のログで `Google 取り込み失敗`（google_calendar_sync.py:66）と `Webhook 更新失敗`（google_webhook.py:409）が 0 件。
- K5-2（design §5 ④-4 を、本番で観測できる形に置き換えたもの。理由は下）:
  1. 反映後に 15 分おきの取り込み（celery_app.py:216-219 `sync_google_calendar_all`）が 1 回以上 `succeeded` になる。この作業は会社ごとに文脈を張って google_webhook_subscriptions を読み、sync_token を UPDATE する（§6 の 3 行目の書込の入口を本番で通る）。
  2. 期限の点検を反映後に 1 回手で起こす: `docker exec astro-webapp-celery-worker-1 celery -A app.celery_app call app.tasks.google_calendar_sync.renew_google_calendar_webhooks`（無制限鍵の SSH。DB は直接触らない。アプリの通常の作業を 1 回起こすだけ）。そのログが `succeeded` でエラー 0。基準値の期限はどちらも 2 日より先なので、更新は 0 件のはず（文脈なしの全社の読取だけを通る）。
  - 置き換えの理由（事実）: design §5 は「Google の通知の受け口が反映後に 1 回以上 200 を返す」としていたが、2026-11-07 07:20 JST に nginx の直近 24 時間のログで `google-calendar/webhook` が 0 件、backend の直近 72 時間でも 0 件だった。通知はいつ来るか分からず、待っても観測できない恐れがある。受け口の読取（文脈なしの SELECT）は CI の試験①の追加の 1 文（google_webhook.py:212 と同じ文）で確かめる。
- 画面での確かめ: 無し（書込の入口は裏の作業と設定画面の切替だけで、上の K5-2 の 1 で本番の書込を通る）。

## 9. 戻し方（design §7 を表名で埋めたもの）

```sql
BEGIN;
DROP POLICY IF EXISTS google_webhook_subscriptions_select ON public.google_webhook_subscriptions;
DROP POLICY IF EXISTS google_webhook_subscriptions_insert ON public.google_webhook_subscriptions;
DROP POLICY IF EXISTS google_webhook_subscriptions_update ON public.google_webhook_subscriptions;
DROP POLICY IF EXISTS google_webhook_subscriptions_delete ON public.google_webhook_subscriptions;
ALTER TABLE public.google_webhook_subscriptions NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.google_webhook_subscriptions DISABLE ROW LEVEL SECURITY;
COMMIT;
```
- 順番・道・流す人は design §7 のとおり（便④-1 card-4-1.md §8 と同じ）。戻しの PR では移行ファイル・run_all の 2 行・CI の step を消す。

## 10. 想定される分岐（実装役が出会ったら止まって Opus に戻す）

- §5 の 2 の移行のどれかが使い捨て DB で失敗する。
- 968・969 が既に使われている。
- CI の前提の step で 077 または 20261103_200000 が失敗する（変更 SQL のジョブの DB に tenant_ の置き場があり、calendar_events の google_event_id に重複がある等）。
- 見張りの分類表の試験が、§5-2 の名前以外で落ちる。
- main に `20261107_150000` と同じ時刻か、より後の移行が先に入った。
- 上の以外でも、カードに書いていない変更が要ると分かったとき。

## 11. 危険パスと GO

- `migrations/`・`scripts/` を含む＝危険 PR（ADR-135・ADR-136）。マージの前に、審査役（reviewer・opus）の APPROVE、CI 全緑、直前のバックアップの確認を揃え、PR 本文に `### GO記録`（POの委任に基づくClaude Opus発行・委任 ADR-1003・PR 番号・HEAD・日時・相乗りの PR が無いこと）を書く。
