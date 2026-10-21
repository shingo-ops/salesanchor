# 実装カード 便1: 誤り報告の表 3 つ・報告 API・Discord 通知

> 親: [design.md](./design.md) §4-1・§4-2・§9／ADR: [ADR-1025](../../adr/ADR-1025-analysis-error-report-autofix.md)／KGI: [kgi.md](../../specs/analysis-error-report/kgi.md) G1（API 部分）・G2a
> 区分: ADR-1015 の A。`migrations/` と `.github/workflows/deploy.yml` を含むため、マージ前に ADR-136 の GO 手順が要る（GO は ADR-1003 で Opus に委任）。
> 状態: カード作成済み・PO の実装承認待ち。

## 冒頭（必読）
- 実装役は `./scripts/dev/executor-preflight.sh || exit 1` を最初に実行する。作業場所は `bash scripts/new-worktree.sh release/analysis-error-report-bin1 --claude`（origin/main 起点）。
- このカードに書いていないことはしない。迷ったら止まって Opus に `NEEDS_DECISION:` で返す。
- 本番 DB・secrets・GitHub の設定には触らない。secret の登録は PO 本人の作業。
- 前例の根拠はすべて origin/main（2026-10-17 担当 Sonnet の読み取り調査）。

## 実物点検（最初に。推測で進めない）
1. `public.analysis_results` の今の列名を、migrations の作成と後からの追加（`git grep -n "analysis_results" migrations/`）で確かめ、次の 7 項目の値の出どころを表にして報告に書く: 商品（product_id）、数量、価格、単位、状態、販売状態、メモ（note_ja）。列名がこの名前と違う場合は、実物の名前を使う。対応する列が無い項目があれば止まる。
2. `migrations/20261016_100000_create_ops_incident_tables.sql` を読み、:5・:47-59（表）、:79-84（RLS）、:98-103（POLICY）、:118-125（GRANT/REVOKE）の形を確かめる。
3. `scripts/run_all_migrations.sh` の末尾（:995 付近）に新しい行を足す場所を確かめる。
4. `backend/app/services/discord_notifier.py:40-65` の `_post_discord_webhook` の形を確かめる。
5. `.github/workflows/deploy.yml:283`（古い行を消す sed）と `:328`（.env への書き出し）、`docker-compose.yml:105`・`:234` がどのサービスの environment かを確かめる。

## 項目 1: migration（表 3 つ・連番）

### 変更
- 新規 `migrations/20261017_HHMMSS_create_analysis_error_report_tables.sql`（HHMMSS は作成時刻。`migration-guard.yml:100-117` の形式）。
- `scripts/run_all_migrations.sh` の末尾に `run_sql migrations/<そのファイル名>` を 1 行追加（`migration-guard.yml:119-140` が未登録を落とす）。deploy.yml には書かない（`deploy.yml:223`）。

### 中身（すべて `IF NOT EXISTS` で冪等）
- `CREATE SEQUENCE IF NOT EXISTS public.analysis_error_report_code_seq START 1;`
- `public.analysis_error_reports`
  - `report_code VARCHAR(16) NOT NULL UNIQUE DEFAULT 'ER-' || LPAD(nextval('public.analysis_error_report_code_seq')::TEXT, 6, '0')`（先頭列。前例 `migrations/003_add_phase1_tenant_tables.sql:26`・`:78`）
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `extraction_item_id UUID NOT NULL`、`extraction_job_id UUID NOT NULL`（FK は付けない。理由: 再解析で行が作り直されても報告を残すため。前例 item_corrections「no FK constraints by design」`20260921_110000_pipeline_tables_public.sql:324`）
  - `reported_by TEXT NOT NULL`（メール。前例 `item_corrections.py:159`）、`reported_at TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','working','resolved','unresolved','cancelled'))`
  - `discord_message_id TEXT NULL`
- `public.analysis_error_report_fields`
  - `id BIGSERIAL PRIMARY KEY`、`report_id UUID NOT NULL REFERENCES public.analysis_error_reports(id)`
  - `field_name TEXT NOT NULL CHECK (field_name IN ('product_id','quantity','price','unit','condition','status','note'))`
  - `system_value JSONB NULL`、`expected_value JSONB NULL`、`expected_missing_product BOOLEAN NOT NULL DEFAULT false`
  - `UNIQUE (report_id, field_name)`
- `public.analysis_error_report_events`（追記だけ）
  - `id BIGSERIAL PRIMARY KEY`、`report_id UUID NOT NULL REFERENCES public.analysis_error_reports(id)`、`at TIMESTAMPTZ NOT NULL DEFAULT now()`
  - `actor TEXT NOT NULL`
  - `kind TEXT NOT NULL CHECK (kind IN ('created','notified','notify_failed','session_opened','cause','action','reanalyzed','verified'))`
  - `payload JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (octet_length(payload::text) <= 8192)`（前例 ops_incident :54-58）
- 3 表とも `ENABLE` と `FORCE ROW LEVEL SECURITY`（前例 :79-84）。POLICY は `current_setting('app.is_operator', true) = 'true'` を条件に:
  - reports: SELECT・INSERT・UPDATE
  - fields: SELECT・INSERT
  - events: SELECT・INSERT だけ（UPDATE・DELETE のポリシーは作らない）
- GRANT は `DO $$ IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='salesanchor_app') ...`（前例 :118-125）
  - reports: SELECT, INSERT, UPDATE ／ fields: SELECT, INSERT ／ events: SELECT, INSERT と `REVOKE UPDATE, DELETE, TRUNCATE ... FROM salesanchor_app`
  - 連番: `GRANT USAGE, SELECT ON SEQUENCE public.analysis_error_report_code_seq, public.analysis_error_report_fields_id_seq, public.analysis_error_report_events_id_seq TO salesanchor_app`（前例 `20261016_150000_add_viewer_accounts.sql:111`）

### 触らない範囲
既存の表（item_corrections・analysis_results・extraction_*）の定義とデータ。

### 想定分岐
- 空 DB の dry-run（migration-guard）が落ちたら、落ちた理由の生出力を報告して止まる。除外表への追加は自分で決めない。

## 項目 2: 報告 API

### 変更
- 新規 `backend/app/routers/analysis_error_reports.py`。`main.py` に import と `app.include_router(analysis_error_reports.router, prefix="/api/v1", tags=["super-admin"])`（前例 `main.py:65`・`:691-693`）。
- 新規 `backend/app/schemas/analysis_error_report.py`、新規 `backend/app/services/analysis_error_report_svc.py`。

### 口
`POST /api/v1/tcg/items/{extraction_item_id}/error-reports`、`Depends(require_super_admin)`（`dependencies.py:516-544`）。
- 入力: `{"fields": [{"field_name": "...", "expected_value": ..., "expected_missing_product": false}]}`。1 件以上、field_name の重複なし。
- 値の検査（候補にない値は 422。正本はそれぞれの今の一覧だけ。値を手で書いた一覧を持たない）:
  - product_id: 商品マスタに存在する id。`expected_missing_product=true` のときは expected_value は null。
  - quantity・price: 0 以上の数。
  - unit・status: `/tcg/review/value-options` と同じ取得元（`item_corrections.py:301` が使う関数を呼ぶ）。
  - condition: `/tcg/conditions/review-options` と同じ取得元の関数を呼ぶ。
  - note: 文字列の配列。各語が `public.tcg_note_master` の `enabled = true` かつ `tenant_id IS NULL` の `label_ja` にあること（有効行を読む関数 `tcg_analyzer_svc.py:1096-1112` を使うか、同じ条件の SELECT）。
- 処理: 行が無ければ 404。`set_operator_context(db)`（`dependencies.py:482`）→ reports 1 行・fields（system_value は analysis_results の今の値＝実物点検 1 の列）・events（kind=created）を 1 トランザクションで INSERT → commit → `reset_operator_context(db)`（`:499`）。
- 応答: `201 {"report_code": "ER-000001", "notified": true|false}`。

### 触らない範囲
item_corrections・value-override の口と、配信の精度ゲート（`tcg_distribution_svc.py:557-559`）。

## 項目 3: Discord 通知

### 変更
- `backend/app/services/discord_notifier.py` に関数を 1 つ追加。送り先は新しい環境変数 `ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK`（読み方は既存 `:41` と同じ `os.getenv(...).strip()`）。投稿は webhook の URL に `?wait=true` を付け、応答の message id を受け取る。
- 本文は `誤り報告 ER-000001 項目: 数量, 価格` の形だけ（報告番号と項目名。値・文面は入れない＝design §7）。項目名は日本語の固定表（field_name → 表示名）を通知関数の中に 1 つだけ置く。
- 報告 API は commit の後に通知を呼ぶ。成功: reports.discord_message_id を更新し events に notified。失敗・未設定: events に notify_failed（理由のみ）。通知の失敗で報告は消さない（前例 `:55-65` は例外を握って False）。
- `.github/workflows/deploy.yml`: `:283` の削除行の並びと `:328` の書き出し行の並びに、`ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK` を 1 行ずつ追加（形は `ADMIN_NOTIFICATION_DISCORD_WEBHOOK` と同じ）。
- `docker-compose.yml`: backend の environment に `- ANALYSIS_ERROR_REPORT_DISCORD_WEBHOOK` を 1 行追加（実物点検 5 で backend と確かめた側だけ）。

### 触らない範囲
既存の通知関数と `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`。celery 側のサービスには足さない（通知は API の中だけ）。

### 想定分岐
- docker-compose.yml の該当行が backend でなかったら、止まって報告する。

## 項目 4: テスト
- `backend/tests/test_analysis_error_reports.py`（前例 `backend/tests/test_item_corrections.py:31-60`）: 認証なしで 401/403、super admin 以外で 403、field_name 重複で 422、候補にない unit で 422、メモに無効な語で 422、正しい入力で 201 と report_code の形 `^ER-\d{6}$`、Discord 未設定で notified=false でも 201。
- `backend/tests/test_analysis_error_report_tables_rls.py`（前例 `backend/tests/test_ops_incident_tables_rls.py`）: operator フラグなしの INSERT 拒否、フラグありの INSERT/SELECT、events の UPDATE と DELETE が salesanchor_app で拒否、report_code が 1 件目で `ER-000001` の形。

## 止まる条件
- 実物点検の結果が上の前例と違う。
- テストが通らず、原因がこのカードの範囲の外にある。
- このカードに無いファイルを触る必要が出た。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 表 3 つが RLS と追記専用の権限つきで作られる | RLS テストが緑（CI の該当ジョブのログ） |
| 正しい報告で 201 と ER-＋6 桁が返る | API テスト |
| 候補にない値は 422 | API テスト |
| Discord に番号と項目名だけが届く（G2a 60 秒以内） | 本番反映後、PO の secret 登録の後に super admin で 1 件送り、送信時刻と投稿時刻を比べる（Opus が実施） |
| 通知の失敗で報告が消えない | API テスト（未設定で 201） |

## 触るファイル（全部）
migrations/20261017_HHMMSS_create_analysis_error_report_tables.sql、scripts/run_all_migrations.sh、backend/app/routers/analysis_error_reports.py、backend/app/schemas/analysis_error_report.py、backend/app/services/analysis_error_report_svc.py、backend/app/services/discord_notifier.py、backend/app/main.py、.github/workflows/deploy.yml、docker-compose.yml、backend/tests/test_analysis_error_reports.py、backend/tests/test_analysis_error_report_tables_rls.py

## 戻し方
PR を revert する。表は新しく作るだけで既存の表を変えないので、残しても他の処理に影響しない。表を消す場合は DROP になるため PO の確認が要る。

## カードチェック（Opus・2026-10-17）
- 前例はすべて file:line 付き。正本の重複なし（候補はそれぞれの今の取得元の関数を呼ぶ）。未確認は実物点検 1・5 に置き、違えば止まる条件にした。
