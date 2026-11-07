# 実装カード: 古い会社ごとの名簿 tenant_NNN.channel_masters を消す（PR-C）

- 設計: docs/handoff/channel-master-shared/design.md §6 の4（PO 承認 2026-11-06）・recon.md
- PO の実施依頼: 2026-11-07「1,2を順番に」（2＝この PR-C）
- 区分: **危険**。DROP TABLE を含む migration。ADR-1003 の例外なので、マージ前に **PO 本人の「GO #PR番号」** が要る（Opus の委任 GO では出さない）。`scripts/check-process-artifacts.js` も機械で止める
- マージの条件（設計 §6 の4）: ①PR-B 反映後に「検索 K1」0件 ②PR-B 反映（2026-11-07 02:06 UTC）から7日間エラー0（最短 2026-11-14）③PO 本人の GO。**この3つが揃うまで Draft のまま待つ**
- 実装役は Draft PR を作るところまで。マージ・GO 記録は実装役の仕事ではない
- 対象 ADR: **ADR-1069**（`docs/adr/ADR-1069-drop-tenant-channel-masters.md`・Proposed・Opus がこのブランチに起案済み）。`backend/AGENTS.md:26-28` の「テーブル削除は PO 確認のうえ ADR を起案」に当たる。PR 本文には最初の作成時から `ADR-1069` と `ADR-1007` を書く（`.github/workflows/migration-guard.yml:343-391` のチェック6 は、追加行に DROP TABLE があると PR 本文の `ADR-[0-9]+` を探し、無ければ赤）
- 改訂: 2026-11-07 クラウド設計審査 REVISE（`docs/handoff/channel-master-shared/review-pr-c-card.md`）の必須 M1〜M3・推奨 R1〜R5 を反映

## 1. 実物（origin/main 2969725e9 で確認）

- 本番: tenant_001・003・004・005・006 の5つに `channel_masters` と `channel_masters_id_seq` がある。中身はどれも public と同じ6行（messenger・instagram・discord・phone・in_person・whatsapp、全部有効）。会社独自の行は無い（2026-11-07 読み取り専用の鍵で確認）
- 本番でこの表に依存するのは `ai_ro.tenant_00X__channel_masters` と `ai_cloud.tenant_00X__channel_masters` のビューだけ。外部キーは public.channel_masters だけを指す
- `scripts/run_all_migrations.sh:220`・`:224` が毎回の反映の最初に ai_cloud・ai_ro のビューを外し、`:236-273` の EXIT trap が最後に作り直す。作り直しは実在の表を `pg_class` から拾う（`migrations/20261017_130100_create_ai_ro_views.sql:25-33`・`migrations/20261024_100000_create_ai_cloud_meta.sql:80-90`）。だから表を消しても作り直しは失敗しない
- `scripts/run_all_migrations.sh:569-570` が毎回 `migrations/20260611_100000_create_channel_masters.sql`（`CREATE TABLE IF NOT EXISTS %I.channel_masters`）を流す。外さないと次の反映で会社ごとの表が作り直される
- 検索 K1（設計 §7）: `git grep -nE 'tenant_table_ref\(db, tenant_id, "channel_masters"\)|\{schema(_name)?\}\.channel_masters' origin/main -- backend/app` は 0件（rc=1）。`backend/app/services/tenant.py` に channel_masters の文字は無い
- 試験の足場が古い migration を使う所:
  - `backend/tests/rls_bootstrap.py:38`（`_TENANT_BOOTSTRAP_MIGRATIONS` の1つ目）・`:188`（`_scope_tenant_migration` の selectors の1行）
  - `backend/tests/test_tenant_loop_migration_guard.py:42`（rls_bootstrap.py の scoped 一覧）・`:137`（test_value_migrations_neutralized.py の text_only 一覧）
  - `backend/tests/test_value_migrations_neutralized.py:26`（無効化18本の一覧）・`:84-88`（`test_channel_masters_selector_line_is_kept_byte_identical`。理由のコメントが「rls_bootstrap.py の正本のセレクタ」）
- ai_cloud の分類: `migrations/20261024_100300_create_ai_cloud_views.sql:357-359` に `'tenant_*','channel_masters'` の3行。控えの `docs/handoff/cloud-case-ai/stage1-column-class.tsv:574-576` にも同じ3行がある（控えは全体ではすでに SQL とずれている: データ行 1057・SQL 1084。どの試験も TSV を読まない）。件数は `:3` のコメント「1084 行」と `backend/tests/ops/test_ai_cloud_views.py:484` の `== 1084`
- `backend/tests/ops/test_ai_cloud_views.py` の T10（`_classification_gaps`）は、試験 DB の実在の列に分類の行があるかを見る。rls_bootstrap が古い表を作ったまま分類3行だけ消すと T10 が落ちる。だから足場と分類は同じ PR で直す
- ai_cloud_views.sql を変えると sha256 が変わる。`scripts/migration-guard/reference-allowlist.tsv:7` の sha と理由の欄を更新する（今までの PR-A と同じやり方）

## 2. 変更

### 2-1 新しい migration `migrations/20261107_180000_drop_tenant_channel_masters.sql`（新規）

```sql
-- channel-master-shared PR-C（design §6 の4）: 古い会社ごとの名簿 tenant_NNN.channel_masters を消す。
-- 名簿は public.channel_masters（全社1つ）に移った（PR-A/PR-B）。会社ごとの表は 2026-11-07 時点で全社 public と同じ6行だけ。
-- 何度流しても安全（IF EXISTS）。CASCADE は付けない（ビューは run_all_migrations.sh の先頭で外れている。
-- 想定外の依存があれば止まって反映が失敗する側に倒す）。連番 channel_masters_id_seq は表と一緒に消える（OWNED BY）。
-- 戻し方: この PR を revert して反映すると 20260611 が流れ空の表ができる。中身は反映前の控え（reader の道で取った6行×5社）から戻す。ADR-1069。
DO $$
DECLARE
  r record;
BEGIN
  FOR r IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' ORDER BY nspname LOOP
    EXECUTE format('DROP TABLE IF EXISTS %I.channel_masters', r.nspname);
  END LOOP;
END $$;
```

- 先に `git ls-tree --name-only origin/main migrations/ | grep 20261107_180000` が空であることを確かめる。埋まっていたら、空いている一番近い後ろの時刻にずらし、PR 本文に書く
- 「連番は表と一緒に消える」は 2-11 の試験（CI の使い捨て PostgreSQL）で確かめる。試験が落ちたら出力を貼って BLOCKED: で返す

### 2-2 `scripts/run_all_migrations.sh`

- `:569-570`（SA-02 Stage 1 のコメントと run_sql の2行）を消し、代わりに次の1行コメントを置く:
  `# SA-02 Stage 1 の channel_masters（会社ごと）は channel-master-shared PR-C で廃止。名簿は public.channel_masters（20261106_190000）`
- ファイルの最後（今の `:1251` の後ろ）に、他の行と同じ形で2行足す:
  ```
  # channel-master-shared PR-C: 古い会社ごとの名簿 tenant_NNN.channel_masters を消す（冪等・IF EXISTS）
  run_sql migrations/20261107_180000_drop_tenant_channel_masters.sql
  ```
- `migrations/20260611_100000_create_channel_masters.sql` のファイル自体は消さない（過去の記録。試験 `test_value_migrations_neutralized.py` が文字として読む）

### 2-3 `migrations/20261024_100300_create_ai_cloud_views.sql`

- `:357-359` の3行を消す
- `:3` の「1084 行」を「1081 行」にする

### 2-4 `scripts/migration-guard/reference-allowlist.tsv:7`

- 2列目の sha256 を、2-3 を当てた後のファイルの sha256 に置き換える（`sha256sum migrations/20261024_100300_create_ai_cloud_views.sql`）
- 4列目の最後に ` / channel-master-shared card-pr-c（分類3行削除）` を足す

### 2-5 `docs/handoff/cloud-case-ai/stage1-column-class.tsv`

- `:574-576` の `tenant_*	channel_masters` の3行を消す

### 2-6 `backend/tests/ops/test_ai_cloud_views.py:484`

- `== 1084` を `== 1081` にする

### 2-7 `backend/tests/rls_bootstrap.py`

- `:38` の `"20260611_100000_create_channel_masters.sql",` を消す（`_TENANT_BOOTSTRAP_MIGRATIONS` は sales_form の1本になる）
- `:188` の selectors の1行を消す
- ほかは触らない

### 2-8 `backend/tests/test_tenant_loop_migration_guard.py`

- `:42`（rls_bootstrap.py の scoped 一覧）から `"20260611_100000_create_channel_masters.sql",` を消す
- `:137`（test_value_migrations_neutralized.py の text_only）は、2-9 の後も test_value_migrations_neutralized.py が文字として読むので残す。この試験を流して落ちたら、出力どおりに直し、何を直したかを返す
- `_REVIEWED` に2-11 の新しい試験を `own_database` として足す（この見張りの決まり `:3-5`・`:317-320`）:
  ```python
      "test_drop_tenant_channel_masters_pg.py": (
          "own_database",
          "",
          frozenset(
              {
                  "20260611_100000_create_channel_masters.sql",
                  "20261107_180000_drop_tenant_channel_masters.sql",
              }
          ),
      ),
  ```
  置く場所は既存の `"test_leads_assignment_opened_at_pg.py"` の項目（`:157` から）の直後

### 2-9 `backend/tests/test_value_migrations_neutralized.py`

- `:84-88` の `test_channel_masters_selector_line_is_kept_byte_identical` を消す（守っていた相手の rls_bootstrap.py の行が 2-7 で無くなる）
- `:26` の一覧の行は残す（無効化した18本の静的な確かめは今も意味がある）

### 2-10 台帳とカード

- `.claude-pipeline/active-work.d/release-channel-master-pr-c.md`（Opus が作成済み）の PR# を埋める

### 2-11 新しい試験 `backend/tests/test_drop_tenant_channel_masters_pg.py`（新規・CI の使い捨て PostgreSQL 専用）

- 型は `backend/tests/test_leads_assignment_opened_at_pg.py:36-46` と同じ: `from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture` を使い、`pytestmark = pytest.mark.skipif(os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required")`。ファイルの中に `CREATE DATABASE` の文字が無ければ見張り（`test_tenant_loop_migration_guard.py:318-320`）の条件は `test_tcg_work_matching_integration import` の文字で満たす
- migration の中身は本体のファイルを読んで流す（書き写さない。`test_leads_assignment_opened_at_pg.py:73-76` と同じ）
- 試験の中身（1つの関数でよい）:
  0. 冒頭で `connection, _, _ = pg`（`pg` は3つ組を返す。手本 `test_leads_assignment_opened_at_pg.py:104`）。`pg` は試験ごとに専用 DB を作り、終わりに DB ごと消す（`test_tcg_work_matching_integration.py:398`・`:434`）ので、試験の中に片付けの文は書かない
  1. `tenant_9101`・`tenant_9102` のスキーマを作る（既存の会社番号とぶつけない）
  2. `migrations/20260611_100000_create_channel_masters.sql` を流す → 2つのスキーマに `channel_masters` があることを確かめる
  3. `migrations/20261107_180000_drop_tenant_channel_masters.sql` を2回流す（2回目もエラーにならない）
  4. `SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname IN ('channel_masters','channel_masters_id_seq') AND n.nspname ~ '^tenant_\d+$'` が 0（Python では `r"..."` の文字列に書く。`\d` の警告を避ける。全 tenant_ スキーマで数える。部品が作る tenant_006・tenant_902・tenant_901 もループの範囲に入るので、範囲も一緒に確かめる）
  5. 手順2の直後に同じ文で数えて 4（2スキーマ × 表と連番）以上であることも assert する（消す前に在ったことの確かめ。この assert が試験の中の証拠になる）
  - public の名簿（`20261106_190000_create_public_channel_masters.sql`）はこの試験の DB では作らない（`pg` 部品が流さない・`public.tenants` を要る）。public が残ることは本番の §3 の h で確かめる
  - 試験ファイルに書く migration の名前はこの2本（20260611・20261107_180000）だけにする。他の全社ループの migration の名前を書くと `_REVIEWED` の登録が要る
- 20260611 が他の前提（関数・型）を要求して2で落ちたら、出力を貼って BLOCKED:（足場を勝手に作らない）
- この試験は手元では skip になる。確かめは CI（§3 の c）

触らない範囲: `backend/app/` のすべて。`migrations/20260611_100000_create_channel_masters.sql`。`deploy.yml`。`docs/adr/`（ADR-1069 は Opus が書いた。触らない）。上に書いていないファイルすべて。

## 3. 確かめ方

| 基準 | 検証方法 |
|---|---|
| a. 古い表を作る道が無い | `grep -n "20260611_100000_create_channel_masters" scripts/run_all_migrations.sh backend/tests/rls_bootstrap.py` が0件 |
| b. 新しい migration が登録されている | `grep -n "20261107_180000_drop_tenant_channel_masters" scripts/run_all_migrations.sh` が1件で、ファイルの最後の run_sql |
| c. migration が冪等で、表と連番が消える | CI の `pytest-run`（PR の画面では `pytest-run-internal` と、必須のまとめ `pytest`）が緑。理由: CI は `GITHUB_ACTIONS=true` なので 2-11 の skipif は偽。`pg` 部品は環境が無いと assert で落ちる（`test_tcg_work_matching_integration.py:386-391`）ので CI では黙って skip にならない。CI は `pytest -q`（`.github/workflows/test.yml:253`）でファイル名の行を出さないので、PR コメントにはログ末尾の `N passed` の行を貼る。psql で直に流して確かめない（クラウドの決まり: SQL は pytest の中だけ） |
| d. 分類の件数 | `grep -c "^  ('" migrations/20261024_100300_create_ai_cloud_views.sql` の前後差が -3。`grep -n "'tenant_\*','channel_masters'" migrations/20261024_100300_create_ai_cloud_views.sql` が0件 |
| e. 検索 K1 | §1 の検索が0件のまま |
| f. 試験 | `backend/tests/test_tenant_loop_migration_guard.py`・`backend/tests/test_value_migrations_neutralized.py`・`backend/tests/test_rls_bootstrap_ordering.py`・`scripts/tests/test_migration_value_writes.py` を手元で流して全部通る。PG が要る試験（T10・2-11 など）は CI で確かめる |
| g. CI | 必須チェックが緑。ただし process-artifacts gate は「DROP TABLE に PO の GO 記録が無い」で赤のままになるのが正しい（GO は PO 本人がマージ前に出す）。migration-guard のチェック6 は PR 本文の `ADR-1069` で通る。それ以外の赤は直す |
| h. 本番（マージ後・Opus が行う） | 読み取り専用の鍵で `SELECT n.nspname, c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relname IN ('channel_masters','channel_masters_id_seq') ORDER BY 1,2` を流し、public の2行だけ。反映を2回またいで変わらない（設計 K1）。`information_schema.tables` は reader の権限で絞られて表が残っていても 0 と出るので使わない。反映前の実測（2026-11-07 15:01 JST）: public と tenant_001・003・004・005・006 の各2行、計12行（reader で pg_catalog が読めることも確認済み） |

## 4. 想定分岐

- §1 の行番号の中身が1字でも違う → BLOCKED:（本線が先に進んだ。Opus が照合し直す）
- `migration-guard` のチェック6（DROP）は PR 本文に `ADR-1069` があれば通る。本文に書いたのに止まる、または他の理由（全テナントを回す migration など）で止まる → 出力を貼って BLOCKED:。迂回しない
- PR 本文の欄（`scripts/check-process-artifacts.js:1560-1615`・`:1773`・`:1813`）: 「### 標準ワークフロー確認」「対象ADR: ADR-1069, ADR-1007」「recon: docs/handoff/channel-master-shared/recon.md」「設計doc: docs/handoff/channel-master-shared/design.md」「触るファイル:」「削除するファイル:」を最初から書く。「削除するファイル:」には1行でも消した行があるファイルを全部並べる（run_all_migrations.sh・create_ai_cloud_views.sql・reference-allowlist.tsv・stage1-column-class.tsv・test_ai_cloud_views.py・rls_bootstrap.py・test_tenant_loop_migration_guard.py・test_value_migrations_neutralized.py）
- T10 が他の理由で落ちる（今回と関係ない表の分類漏れ）→ 直さずに出力を貼って返す
- check-before-submit（push 前の自動確認）が止める → 出力を読み、このカードの範囲で直せるものだけ直す。範囲外なら BLOCKED:
- process-artifacts gate の赤は直さない（§3 の g）

## 5. 本番に出す前と後（Opus と PO が行う。実装役はしない）

1. 条件の確認: 2026-11-14 02:06 UTC 以降に、PR-B 反映後のエラーが0（設計 §6 の4 の②）。数える所は Opus が条件の確認の前に決めて PR に書く（候補: 本番 backend のログで channel_masters・conv_logs・lang_judge を含む ERROR 行の件数／Deploy 以降の監視の通知）。PR-B の本番反映の成功時刻も Deploy to VPS の記録で確かめて書く
2. 控え（AGENTS.md の決まりどおり reader 鍵の道・SELECT だけ）: 反映を始める前に（デプロイ中は ai_ro が約70秒外れる・usage.md §4）、読み取り専用の鍵で5社それぞれ `SELECT * FROM ai_ro.tenant_00X__channel_masters ORDER BY id` を1文ずつ流す（ベース表は reader では 42501。tenant のビュー5本（public を入れて6本）の実在は 2026-11-07 15:01 JST に確認済み）。出力と sha256 を `docs/handoff/channel-master-shared/pr-c-backup/` に置く。usage.md §2 の保存先（「出力は /tmp/CC報告ファイル/ に置く」）の例外。この例外は Opus の判断なので PR 本文にも書き、PO が止めれば /tmp に移す: 中身は連絡手段の名前など6行×5社で秘密の列は無く、戻すときの正本として repo に残す必要があるため（PO の決めた範囲の外に出すものではない）。加えて Deploy to VPS のログの `✅ Backup:` 行（`.github/workflows/deploy.yml:214`・`:221`、全体の控え）のファイル名を PR に記録する。pg_dump が要るときは PO が `!` で流す
3. PO 本人の「GO #PR番号」→ PR 本文の GO記録に原文を転記 → マージ → Deploy to VPS の成功を確かめる
4. §3 の h を反映直後と次の反映の後の2回数える

## 6. 戻し方

- この PR を revert して反映すると、`run_all_migrations.sh` に 20260611 の行が戻り、会社ごとの表が**空で**作り直される（seed は無効化済み）。中身は §5 の2の控えから戻す。revert の PR も migrations を含むので、PO の GO が要る
- PR-B 以降、アプリは古い表を読まない（検索 K1 0件）ので、表が無い間も画面と解析は動く

## 受領確認

実装役は最初に「card-pr-c.md を受領: 古い会社ごとの名簿を消す migration を足し、作り直す行と試験の足場・分類3行を外す。Draft PR まで」と返す。
