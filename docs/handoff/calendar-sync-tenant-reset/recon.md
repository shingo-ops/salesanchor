# recon: アプリで作った予定が Google に送られない（2026-11-05）

基準: `git fetch` 後の origin/main（c76672036）。生出力は `/tmp/CC報告ファイル/meet-not-sent/`（Mac の手元・リポジトリ外）。

## 既存 ADR の検索結果
- `docs/adr/FEATURE-INDEX.md:34` カレンダー行 → ADR-1057（送るのはつないだ本人の予定だけ）／ADR-1060（Meet）／ADR-1018（Google 接続設定の RLS）
- `docs/adr/ADR-072-tenant-schema-prefix-enforcement.md`（commit 直後に `reset_tenant_context`）
- `docs/adr/ADR-131-tenant-context-auto-reset.md`（`get_db` の finally で `app.tenant_id=''` に戻す）

## 観測事実（本番・読み取り鍵）
| # | 事実 | 根拠 |
|---|------|------|
| F1 | 会社1は 2026-11-05 03:54:35Z に user 1 が Google をつないだ（bidirectional・connected_by_user_id=1）。会社4は 2026-11-03 02:32:07Z に user 3 | `ai_ro.public__tenant_google_calendar_config`（H-config.txt） |
| F2 | 送るべきだった予定は会社1 id=2 の1件だけ（05:24:49Z・user_id=1・created_by=1）。sync_status=pending・google_event_id 空・meet_url 空 | `ai_ro.tenant_001__calendar_events`（D-db-detail.txt） |
| F3 | ほかの app 予定（会社1 id=1、会社4 id=3〜11）は、どれもつなぐ前に作られた。送らないのが ADR-1057 どおり | D-db-detail.txt・H-config.txt |
| F4 | 05:24:40〜52Z の全ログ98行で warn/error/「同期に失敗」は0件。POST /calendar/events は 201・24 バイト | B-loki-all-052440.txt |
| F5 | Google への送信が例外になると `logger.warning("Google Calendar 同期に失敗しました …")` が必ず出る（`backend/app/services/calendar_service.py:304`）。F4 で0件なので送信処理は始まっていない | E-code.txt |
| F6 | 送信を始めない道は `can_add_meet` が False のときだけ（`backend/app/services/calendar_service.py:276`）。中身は `_get_sync_target` が設定表を SELECT し、行が無ければ `('none', None)`（`calendar_service.py:59-80`） | G-engine-condition.txt |

## コード事実
| # | 事実 | 根拠 |
|---|------|------|
| C1 | `create_event` は INSERT 後 `await db.commit()` して、`reset_tenant_context` を呼ばずに設定表を読む | `backend/app/services/calendar_service.py:271`→`:276` |
| C2 | `delete_event` も同じ形。commit 後に `_get_sync_mode` で設定表を読む | `backend/app/services/calendar_service.py:486`→`:488` |
| C3 | 同じ4ファイルのほかの commit はすべて直後に reset している | `calendar_service.py:364-365,403-404,411-412,423-424`／`backend/app/services/google_calendar.py:293-294`／`backend/app/routers/calendar.py:301-302,552-553`／`backend/app/routers/google_calendar.py:146-147,230-231`（L-all-commits.txt） |
| C4 | `reset_tenant_context` の説明: commit 後は別の接続が払い出されることがある | `backend/app/auth/dependencies.py:339-358` |
| C5 | 接続の貸し出しは pool_size=20・max_overflow=10 | `backend/app/database.py:24-32` |
| C6 | `get_db` は返却前に `clear_tenant_context` で `app.tenant_id=''` にする（ADR-131） | `backend/app/database.py:46-61`／`backend/app/auth/dependencies.py:361-379` |
| C7 | 設定表は ENABLE+FORCE RLS。`tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER`。空なら全行見えない | `migrations/20261016_010000_add_google_config_rls.sql`（2026-10-16 07f1227f2） |
| C8 | 271 行目の commit は 2026-05-25（3b35ef7d0）から。10-16 までは設定表に RLS が無く、接続が変わっても読めた | F-pool-history.txt |
| C9 | 機械の見張り `scripts/lint_tenant_schema.py` は routers の口だけを見る。services は対象外なので C1・C2 を止められなかった | `scripts/lint_tenant_schema.py:251-262`・`.github/workflows/lint-tenant-schema.yml:440` |
| C10 | 実 PostgreSQL＋RLS の試験の土台がある（CI の test.yml が RLS_ADMIN/RLS_TEST_DATABASE_URL を与える） | `backend/tests/test_google_config_rls.py:14-64`・`.github/workflows/test.yml` |

## 未確認
- U1: 05:24:49Z の commit 後に本番で実際に別の接続へ切り替わったか（データベースの命令ログは保存していない）。→ 実 DB の再現試験で、仕組みとして起きることを確かめる（design.md 段A）
- U2: 予定を作るとき画面が add_meet=true で送ったか
