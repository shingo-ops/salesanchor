# 設計の審査（architect 第1回）: schedule-settings 便3a

- 審査した物: `origin/release/schedule-settings-bin3` の `docs/handoff/schedule-settings/design-bin3a.md`（以下「設計」）
- 照らした実物: `origin/main` 314eeef1e（行番号は全部この版）
- 範囲: 読むだけ。製品のコード・DB・本番・secrets には触っていない。試験は流していない（実行して確かめたことは無い。下の事実は全部ファイルを読んで確かめた物）

## 判定: REVISE

1. 設計の中身（列の削除・API・画面）は実物と合っていて、作れる形になっている。ただし **CI が落ちる登録の漏れが 4 件**ある（openapi.json・AI 用分類の sha256 一覧・AI 用分類の行数の試験・移行の見張りの分類）。設計は F10 に「登録の場所」を書いたが、これらは入っていない。
2. 受け入れ条件 A5 の検査命令は、書いたとおりに流すと**何も拾わず常に 0 件**になる（`-E` に `\|`）。A4/A9 の「古い形から流す」試験の作り方も書かれていない。
3. 軽い指摘（行番号の誤り・ひな形と移行の書き方をそろえる・既存試験の形）は L に書いた。直せば合格にできる。REJECT の理由は無い。

## R（直さないと作れない・壊れる物）

### R1 `frontend/api-contract/openapi.json` を作り直す（設計 §3-2・§10 に足す）

- 事実: `/home/user/salesanchor/.github/workflows/api-contract-check.yml:38-58` は API の形を書き出して `frontend/api-contract/` に差分があれば失敗にする。
- 事実: 該当の形は `frontend/api-contract/openapi.json:25683-25747`（`OwnerRosterItem`）と `:25788-25824`（`OwnerSettingsBody`）。`is_visible`・`share_mode`・`color` がここにある。便3a の API 変更でずれる。
- 直し: §3-2 に「`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流して openapi.json をコミットする」を足す。§10 の CI の欄にも `api-contract-check` を足す。
- 補足: `frontend/src/api/generated/` は追跡されていない（`git ls-tree` で `frontend/src/api` は `closeReasons.ts`・`funnel.ts` だけ）ので、型ファイルの更新は要らない。

### R2 `scripts/migration-guard/reference-allowlist.tsv` の sha256 を直す（設計 §3-4・F10 に足す）

- 事実: `scripts/migration-guard/reference-allowlist.tsv:7` は `migrations/20261024_100300_create_ai_cloud_views.sql` の sha256（現在の中身と一致を確かめた: `ef4dddd9…4dde`）を持つ。規則（同 :5）は「一覧にあっても sha256 が違えば失敗」、`scripts/check-migration-value-writes.py` の repo モードは一致を確かめる。
- 事実: 便2b の `7b60986c7` は同じ SQL を 1 行足したとき、この一覧の sha256 も直している（`git show 7b60986c7 -- scripts/migration-guard/reference-allowlist.tsv`）。
- 設計は §3-4 でこの SQL の 3 行を変えるが、この一覧に触れていない。このまま作ると migration-guard が落ちる。
- 直し: §3-4 に「SQL を直した後で `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の値に `reference-allowlist.tsv:7` を書き換える。理由欄の末尾に `/ schedule-settings 便3a（分類の入れ替え）` を足す」を入れる。

### R3 `backend/tests/ops/test_ai_cloud_views.py:486` の行数を直す（設計 §3-4・§5 に足す）

- 事実: `backend/tests/ops/test_ai_cloud_views.py:486` は `column_class` の件数を `== 1170` で固定している（便2b の `7b60986c7` で 1169→1170 に直した前例）。
- 設計の変更は「`color`（1 列）と `share_mode`（1 列）を外して `color_key`（1 列）を足す」なので、件数は 1170 → **1169**。直さないと落ちる。
- 直し: §3-4 に「`test_ai_cloud_views.py:486` を 1169 にする」を足す。
- 軽い付記: `migrations/20261024_100300_create_ai_cloud_views.sql:3` のコメントの「1169 行」は今も古い（1170 のはず）。直すならこの変更の中で 1169 に合わせる。

### R4 移行の見張りの分類と、登録の場所（F10）の正しい行（設計 F10・§5 を直す）

- 事実: `backend/tests/test_tenant_loop_migration_guard.py:1-8` は「全テナントを回す移行を流す試験は `_REVIEWED` に分類を書く。書くまでこの試験は落ちる」と決めている。
- 設計 §5 は新しい試験ファイル（移行の試験・A6 の試験）を作ると書くが、それを `_REVIEWED` に入れる記述が無い。新しい試験が新しい移行を流す（または文字として読む）なら、その試験ファイルの項（`scoped` か `own_database` か `text_only`）を足す。
- 設計 F10 の `:53`・`:74`・`:83` の行は次のとおり。実物で確かめた:
  - `:53` = `rls_bootstrap.py` の項、`:74` = `test_calendar_sync_tenant_reset_pg.py` の項（どちらも新しい移行を流すなら足す）
  - `:83` = **`test_calendar_team_share.py` の項**。便3a の移行はこの試験が流す物ではないので、足さない（足すと、試験が実際に流す移行と一覧がずれる恐れ）。
- 直し: F10 の `:83` を外し、代わりに「新しい試験ファイルごとに `_REVIEWED` へ 1 項」を書く。`rls_bootstrap.py:190` の対応表（件数 1）・`test_calendar_sync_tenant_reset_pg.py:56` の流す順の末尾に新しい移行を足す点は設計のとおりで正しい。
- 事実: 移行の登録行は `scripts/run_all_migrations.sh:1494-1495`（便2b の最後）。設計の「:1495」は便2b の行なので、新しい行は **その次（`mr_report_summary` の前）** に足す。書き方を「:1495 の次」にする。

### R5 A5 の検査命令が空振りする（設計 §2 A5 を直す）

- 事実: 設計は `git grep -n -E 'is_visible\|share_mode\|_DEFAULT_OWNER_COLOR' -- backend/app frontend/src` と書く。`-E`（拡張正規表現）では `\|` は文字の `|` そのもの。つまり「`is_visible|share_mode|…` という並びの文字」を探し、**今の実物でも 0 件**になる。変更が漏れていても通ってしまう。
- 直し: `git grep -n -E 'is_visible|share_mode|_DEFAULT_OWNER_COLOR' -- backend/app frontend/src` にする。
- この形で、今は拾う場所（実物）: `backend/app/routers/calendar.py` の 53・83-84・94-95・404-405・410・429-431・462-470・502・529-530・537・552-554、`backend/app/services/tenant.py:1652-1656`、`frontend/src/pages/schedule/schedule-owner.ts:1・10-11・30・34・45-46` と 4 つの試験の fixture。`backend/app`・`frontend/src` にほかの `is_visible` は無い（`git grep` で確かめた）。設計が直す場所と一致するので、直した後は 0 件になる。
- 付記: `schedule-owner.ts:34` のコメントに `_DEFAULT_OWNER_COLOR` が出る。設計 §4-1 の「コメントを書き換える」で消えるが、**A5 が拾うのでコメントから名前を完全に消す**ことを §4-1 に明記する。

### R6 移行の試験で「古い形」を作る方法を書く（設計 §5・A4・A9）

- 事実: 試験の土台 `backend/tests/rls_bootstrap.py` の `bootstrap_tenant_schema` はひな形（`backend/app/services/tenant.py`）で会社の部屋を作る。便3a 後のひな形は新しい形（`color_key` あり・古い 3 列なし）。続けて流す `20260621_020000_add_schedule_calendar_category_and_owner_settings.sql` の表づくりは `CREATE TABLE IF NOT EXISTS`（同 :53-65）なので、表がある部屋では何もしない。
- つまり、土台から作った部屋は最初から新しい形で、「`color` の hex を鍵へ写す」「合わない値が NULL になる」「古い 3 列が消える」「2 回流しても同じ」を確かめる**入口の形が作れない**。
- 試験の中で表を作る `CREATE TABLE` は禁止（設計 §5 の test-schema-dup の門）。
- 直し: §5 に作り方を 1 つ決めて書く。例: 試験が部屋の表に `ALTER TABLE … ADD COLUMN color/is_visible/share_mode` と `color_key` の外し（`DROP COLUMN`）で古い形に戻し、hex の行を入れてから移行を流す（`ALTER` は門の対象外かを、実装役が `scripts/` の門の定義で先に確かめる。外なら `own_database`＋古い形の SQL を移行ファイル側（20260621）で作る）。どちらでも、`_REVIEWED` の分類（R4）と合わせて書く。

## L（軽い指摘）

- **L1 行番号の誤り**: 設計 §3-2 の「`backend/app/services/event_colors.py:252`」は存在しない（ファイルは 27 行）。`EVENT_COLOR_KEYS` は `event_colors.py:18`、`calendar.py:43` で取り込み済み、既存の検証の書き方は `calendar.py:119`（`value in EVENT_COLOR_KEYS`）。さらに、設計の 422 `invalid_color_key` は pydantic の検証（形が違う）ではなく、**受け口の中で `HTTPException(422, detail="invalid_color_key")` を上げる**と書く（便の `no_fields_to_update` と同じ形）。`""`（空文字）は鍵ではないので 422 になる点も 1 行足す（予定の `calendar.py:119` は空文字を許すが、ここは許さない）。
- **L2 ひな形と移行を同じ書き方にそろえる**: `scripts/check_tenant_template_shape.py`（`.github/workflows/migration-test.yml:2222-2295` の `tenant-template-shape`）は列の型・NOT NULL・既定値と、CHECK の定義文を比べる。設計は移行の列を `character varying(32) NULL`、CHECK を `color_key IS NULL OR color_key IN (…)` と書くが、ひな形側（§3-1「3 列を `color_key`＋CHECK に変える」）の型・CHECK の形が書かれていない。既存の `color_key` は `text`・CHECK は `IS NULL OR` なし（`tenant.py:1555`・`:1599`・`:1607`）で、形が 2 通りになる。設計に「ひな形も `color_key character varying(32)`・名前 `calendar_owner_settings_color_key_check`・同じ定義文」と 1 行で決める。この比べは移行が名前の同じ CHECK を飛ばすため、書き方が違っても CI は気づかない（本番とひな形が静かにずれる）。
- **L3 24 色の対応の写し間違い**: 設計 §3-1 の手順 3 は「（24 行）」と略してあり、`event_colors.py:8-17` と一字一句合うかは設計の段では確かめられない。写し間違いを防ぐ試験を 1 本足す（移行の `WHEN '#…' THEN '…'` の行を読み、`EVENT_COLORS` と同じ 24 組・CHECK の鍵の並びが `tenant.py:1607` と同じであることを照らす。`backend/tests/test_event_colors_tokens.py` が前例）。本番は 0 行（F2）で被害は小さいが、試験環境の値で出る。
- **L4 既存の試験の形**: `backend/tests/test_calendar_owner_api.py:95`・`:113` は本体を `SimpleNamespace(...)` で呼ぶ。新しい本体は `model_fields_set`（pydantic 2.10.6、`backend/requirements.txt:8`）で未送と null を分けるので、`SimpleNamespace` では `AttributeError`。試験は `OwnerSettingsBody(**{"color_key": None})` や `OwnerSettingsBody()` の本物で呼ぶ、と §5 に書く。`db.execute` の `side_effect` の順（今は staff→staff→INSERT→再読込）は列を減らしても変わらない。
- **L5 チームの絞り込みの周辺（問題なし・記録）**: 設計 §3-3 の 2 か所（`calendar_service.py:226-232`・`:381-383`）は実物と合う。ほかに `calendar_event_teams` を読む所は `calendar_service.py:210`（もともと有効なチームだけ）と、書き手 `:243`・`:238` だけ（`git grep` で確かめた）。
  - `:993`（「この予定だけ」で送られた `team_ids` と元の行の対応の比べ）: 画面は有効なチームだけを送るので、絞り込み後は比べる側も有効なチームだけになり、むしろ合う（前は無効なチームの id が画面に出ず 422 になる恐れがあった）。
  - `:1273-1275`（元の行の対応を新しい元の行へ写す）: 写されるのは有効なチームだけになる。無効なチームだけの予定は `team` 種別で対応が空の行になる（`validate_team_ids` は通らない）。もとから見えない（`visibility_sql` が無効なチームを見ない）ので表示は変わらないが、設計 §8 に 1 行「写し先からは外れる・チームを再び使い始めると、書き直していない予定には前の対応が戻る」と書くと誤解が無い。
  - Google 同期・秘書: `team_ids` を読む `backend/app` の場所はこの 2 つの関数と `calendar.py` の本体の受け渡し（`:136`・`:158`・`:578`・`:668-693`）だけで、壊れる道は見つからなかった。
- **L6 A6 の試験は実 PostgreSQL**: `JOIN teams t ON t.id = cet.team_id AND t.is_active` は `visibility_sql`（`calendar_service.py:210-211`）と同じ形で、`teams.is_active` は実在する。試験は予定を 1 件作り、チームを `is_active = false` にして一覧と `event_team_ids` の両方を見る、と書けば足りる。
- **L7 画面の周辺（問題なし・記録）**:
  - `CalendarOwner.color` を読む全部（設計 F5 の行番号は実物と合う: `SchedulePageImpl.tsx:262`・`:612`・`:618`・`:641`・`:647`・`:705`・`:776`・`:1323`・`:1334`・`:1445`、`ScheduleSettingsPage.tsx:79`）は、色の文字をそのまま `style` か CSS 変数に入れるだけ。`CalendarView.tsx:49` は `--comp-calendar-owner-color` に文字をそのまま置き、`CalendarView.css:147-148` が `var()` で受けるので `var(--event-color-…)` でも動く。`dataColor`（`SchedulePageImpl.tsx:618`・`:647`）も文字を受ける。`CheckboxControl.test.tsx:83-102` の `dataColor` の登録（ファイルごとの出現数）は、この便で出現数が変わらないので影響しない。
  - `ColorSwatchPicker`（`frontend/src/components/ColorSwatchPicker.tsx:15-31`）は `value: string | null` の選択肢を受けるので、`{ value: null, label, color }` の「標準の色」は金型のままで作れる。
  - `settingsConnectedAt` を使うのは `ScheduleSettingsPage.tsx:476` だけ（`git grep` で確かめた。ほかは `locales/ja.json:3641`・`en.json:3640`）。`shareTeam` は `ScheduleDraftFields.tsx:435`・`ScheduleSettingsPage.tsx:371` で使われ続けるので残す、で合っている。
  - `i18n.ts:38` は `escapeValue: false` なので、`{{names}}` にチーム名の `&` などを渡しても二重に変わらない。
- **L8 既存の試験の直し**: `SchedulePageImpl.test.tsx:1939` は `` `${i18n.t("schedule.shareTeam")}: Team One, Team Two` `` と書いてあり、新しい文面（ja は `チーム: A、B`・en は `Team: A, B`）に直すこと。`en.json` の `nameListSeparator` は値が `", "`（末尾に空白）なので、JSON の値を trim する整形・検査が無いかを実装役が確かめる（未確認）。`ScheduleSettingsPage.test.tsx:348`（`{ color: "rgb(17, 34, 51)" }`）も `color_key` に直す。
- **L9 A8 は列の削除では動かない**: 予定の件数は列の削除で変わらないので A8 は形だけの確認になる。要るなら「A6 の絞り込みは `team_ids` を変えるだけで件数を変えない」ことの確認、と趣旨を書き直す。

## 設計どおりで実物と合う点（確かめた物）

- F1 `tenant.py:1649-1660`・F2・F3（`calendar.py` の 83-84・94-95・404-405・430-431・462-470・502・529-530・553-554、`schedule-owner.ts:10-11・45-46`）・F4（`ScheduleSettingsPage.tsx:426` の `type="color"`、`calendar.py:53`、`schedule-owner.ts:35`）・F6（`calendar_service.py:226-232`・`:381-383`）・F8（`20261024_100300_create_ai_cloud_views.sql:381-382`）・F9（`run_all_migrations.sh:412`・`:416`）は行番号も変更前の形も合う。`type="color"` は `frontend/src` の全体でここ 1 か所だけ（A1 の検査は成り立つ）。
- 列の削除が引っかかる物は見つからなかった: `calendar_owner_settings` を名前に持つのは `20260621_020000_…sql`（表づくり・`CREATE TABLE IF NOT EXISTS`）、`20261013_110000_repoint_person_columns_to_users.sql:21`（`staff_id` の外部キーの付け替え・3 列に触れない）、`20261024_100300_create_ai_cloud_views.sql:381-382`、`tenant.py`、`calendar.py`、試験だけ（`git grep` で確かめた）。ビュー・関数・方針・トリガは無い（ひな形は RLS を切ったまま。`tenant.py` のコメント）。`share_mode` の CHECK は列とともに消える。AI 用の写しは毎回 `TRUNCATE` して作り直す（`20261024_100300_…sql:11`）ので、残る古い分類の行も無い。`CASCADE` を使わない方針は正しい。
- 何度流しても同じ: 手順 1（`IF NOT EXISTS`）・手順 2（名前で確かめる）・手順 3（`color` が有るときだけ・`color_key IS NULL` だけ）・手順 4（`IF EXISTS`）は、2 回目に何も起きない形。`information_schema` の確かめは `table_schema`・`table_name` の両方で絞ること（`20261109_200000_drop_staff_firebase_uid.sql` の前例どおり）。
- `calendar_owner_settings` は保護対象の表（`scripts/migration-guard/protected-tables.txt`）に無く、移行の中の `UPDATE` は migration-guard の確認 7 に当たらない。
- `backend/app/realtime/topics.py:204` の PATCH の登録は経路だけで本体の形に依らない。API を読む `frontend` 以外の場所は無い（`git grep` で `calendar/owners`・`OwnerRosterItem` を全体で探した）。

## 受け入れ条件の検証できるか

| 条件 | 判定 | 根拠 |
|---|---|---|
| A1 | 検証できる | `type="color"` は `ScheduleSettingsPage.tsx:426` の 1 か所だけ |
| A2 | 検証できる | 画面の試験・受け口の試験とも作れる（L4 の形で） |
| A3 | 検証できる | L1 の形（受け口の中の 422） |
| A4 | R6 を直せば検証できる | 古い形の入口が要る |
| A5 | R5 を直せば検証できる | 今の命令は空振り |
| A6 | 検証できる | L6 |
| A7 | 検証できる | 2 本の `git grep -F` は実物の文字と合う（`SchedulePageImpl.tsx:346`・`ScheduleSettingsPage.tsx:476`） |
| A8 | 形だけ | L9 |
| A9 | R6 を直せば検証できる | 同上 |

## 付記（事実と未確認）

- 試験・検査（pytest・npm・CI の検査）は一つも流していない。上の「落ちる」は、検査の定義と固定値をファイルで読んで導いた物で、実行はしていない。R1〜R4 は、定義が明文（`api-contract-check.yml` の差分検査・`reference-allowlist.tsv:5` の規則・`test_ai_cloud_views.py:486` の固定値・`test_tenant_loop_migration_guard.py:1-8` の決まり）なので確度が高い。
- 本番の列の形（`calendar_owner_settings` の実際の型・CHECK 名）は、読む窓口を使っていないので未確認。設計 F2 の 0 行は設計の記載のまま（私は再確認していない）。
