# 設計: 便2a 予定の種類を DB の表 1 つへ（色・共有の初期値）

- 状態: 設計審査済み（第2回 APPROVE・2026-11-25）。第2回の推奨を入れた第3版。末尾「審査」に記録する
- 親の設計: `docs/handoff/schedule-settings/design.md` §1・§6（便2 の骨組み）
- 要件: `docs/handoff/schedule-settings/requirements.md`（PO 2026-11-25「1」で承認）の G4・G6
- 関わる ADR: ADR-1081（予定の色 24 色・正本 `backend/app/services/event_colors.py`）／ADR-144（UI 金型）／ADR-067（デザイントークン）／ADR-027（i18n）／ADR-072（commit 後の reset_tenant_context）／ADR-1037（移行のロック待ち）／ADR-1052（AI 用の写しの分類）／ADR-135・136（危険 PR の GO）

## 0 便2 を 2 つに分ける（設計判断）

便2 は「種類を表へ」と「チーム共有」を一度に入れると、見え方（だれに見えるか）の変更と表の作り直しが同じ PR に混ざる。見え方の変更は漏れると他人の予定が見えてしまうため、単独で試験・審査したい。

| 便 | 中身 | だれに見えるか |
|---|---|---|
| 便2a（この文書） | 種類の表・種類の保存の直し・種類を選ぶと色と共有（自分だけ／全員）が入る・設定ページで種類を管理 | 変えない（札の見た目は変わる。§8） |
| 便2b（別の文書） | 共有「チームを選ぶ」・予定とチームの対応表・見え方の条件 | 変える |

要件 G4 の「チームを選ぶ」は便2b で満たす。便2a の共有の初期値は `self` / `all` の 2 つ。

## 1 現在地（実物・origin/main b4940fe2e。審査で 7a329ce5d と対象ファイルの差 0 を確認）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | 種類は 7 つで固定。DB の決まりと画面の表の 2 か所に書いてある | `backend/app/services/tenant.py:1579`（CHECK）・frontend/src/features/schedule/calendars.config.ts の 3〜62 行（この便で消した） |
| F2 | 予定を作る・直す受け口の入力の形に `category` が無い。画面は `category` を送るが、受け口で捨てられる | `backend/app/routers/calendar.py:122-160`・`frontend/src/pages/schedule/SchedulePageImpl.tsx:1006` |
| F3 | 本番の予定 35 件はすべて種類が `meeting` | 読むだけの鍵で数えた（2026-11-25）: 会社1 3 件・会社4 32 件 |
| F4 | 作る道は `payload.get("category", "meeting")` を入れる | `backend/app/services/calendar_service.py:423` |
| F5 | 直す道で種類を落とす所が 5 か所ある: 単発の `update_event` の `field_map`（`:502-512`）・繰り返しの変わった欄を拾う `_TEXT_FIELDS`（`:682`）・「この予定だけ」の `row_fields`（`:1055-1057`）・「これ以降」の `category=master["category"]`（`:1122`）・「単発→繰り返し」の並び（`:1224`）。読む列 `EVENT_COLUMNS`（`:152`）と写し `_row_values`（`:973`）には有る | `backend/app/services/calendar_service.py` |
| F6 | 画面で種類を選ぶと、作るときだけ「personal なら社員に見せない」に切り替わる | `frontend/src/pages/schedule/ScheduleDraftFields.tsx:284-290` |
| F7 | 画面の種類の表の使い先は 3 ファイル: `frontend/src/pages/schedule/ScheduleDraftFields.tsx:20`（`:285`・`:292`）・`frontend/src/pages/schedule/SchedulePageImpl.tsx:28`（`:94`・`:153-154`・`:222-223`・`:319`・`:344-345`・`:399-400`・`:723-736`）・`frontend/src/pages/schedule/schedule-utils.ts:62`（`:359`・`:398` も同じ型）。ほかは自分の試験 frontend/src/features/schedule/calendars.config.test.ts（この便で消した） だけ | 審査 R7 の `git grep -n "calendars.config"` |
| F8 | 色の選び方の金型 `ColorSwatchPicker` があり、予定の色で使っている。予定の色の点は `schedule-month__dot`（`frontend/src/pages/schedule/SchedulePageImpl.tsx:663`・`:731`・`schedule.css:316`） | `frontend/src/pages/schedule/ScheduleDraftFields.tsx:11`・`:327-345` |
| F9 | 本番 5 社（1・3・4・5・6）全部の `calendar_events` に CHECK `calendar_events_category_check`（7 種の一覧）がある | 読むだけの鍵で `pg_constraint` を読んだ（2026-11-25 Opus）: 5 行とも同じ名前・同じ定義 |
| F10 | 移行の手本は ADR-1081 便1。登録は `scripts/run_all_migrations.sh:1483`・`backend/tests/rls_bootstrap.py:188`・`backend/tests/test_calendar_sync_tenant_reset_pg.py:54`・`backend/tests/test_tenant_loop_migration_guard.py:51`・`:70` の 5 行 | `git grep -n 20261119_120000_add_calendar_events_color_key` |
| F11 | 管理者の判定は `is_tenant_admin(await get_user_system_keys(db, user.id))` | `backend/app/routers/calendar.py:523` |
| F12 | 画面の読み方の正本は `useApiQuery`／取り直しは `useInvalidateApi`（会社ごとの写しの名前が付く） | `frontend/src/lib/query/apiQuery.ts:1-8`・`:52`・`frontend/src/pages/schedule/ScheduleSettingsPage.tsx:54`・`:64` |
| F13 | AI 用の写しの分類表は今 1165 行。試験は `== 1165`。表の sha256 は許可一覧にある | `migrations/20261024_100300_create_ai_cloud_views.sql:3`・`backend/tests/ops/test_ai_cloud_views.py:486`・`scripts/migration-guard/reference-allowlist.tsv:7` |
| F14 | ひな形と移行後の会社の形の差は CI で 0 件を確かめる | `.github/workflows/migration-test.yml:2277`（`scripts/check_tenant_template_shape.py`） |

## 2 受入条件

| 基準 | 内容 | 検証方法 |
|---|---|---|
| A1 | 全社に種類の表があり、今の 7 種が入っている | 移行の試験（2 回流して同じ）＋反映後に Opus が読むだけの鍵で各社の `tenant_00N.calendar_categories` を数え 7 行（CI の合否ではない） |
| A2 | 予定の `category` は種類の表にある鍵だけ入る（外部キー）。種類の固定の CHECK は無い | 移行の試験（無い鍵の INSERT が失敗・`custom_1` を足した後はその鍵で INSERT が通る）＋本番で `pg_constraint` を読み、5 社とも `calendar_events_category_fkey` が有り・`category` を使う CHECK が 0 件 |
| A3 | 予定を作る・直すときに選んだ種類が保存される。直す道は単発・この予定だけ・これ以降・すべて・単発→繰り返しの 5 通り | 裏側の試験（5 通りそれぞれ） |
| A4 | 使わなくした種類・無い鍵で作ると 422 `invalid_category`。直すときに今の種類のままなら、使わなくした種類でも通る。`meeting` は使わなくできない（422 `category_not_disableable`） | 裏側の試験 |
| A5 | 管理者は種類を足す・名前を変える・色を決める・共有の初期値を決める・使わなくするができる。管理者でない人は 403 | 裏側の試験 |
| A6 | 作るときに種類を選ぶと、その種類の色（無ければ「デフォルト」）と共有の初期値が入る。直すときに種類を変えても色と共有は変わらない | 画面の試験。本番は PO が §11 の手順で目視 |
| A7 | 種類の選び方に出るのは使っている種類だけ。今の予定の種類が使わなくした種類なら、それも出る | 画面の試験 |
| A8 | 設定ページの「予定の種類」区画は管理者だけに見える | 画面の試験（管理者／staff.view だけ／管理者で staff.view なし の 3 通り） |
| A9 | だれに見えるかは変わらない（要件 G6） | `git diff origin/main...HEAD -- backend/app/services/calendar_service.py` で、見え方の条件の行（`visibility_sql` の 3 行 `:242`・`:244`・`:246` と `where += f" AND {visibility_sql}"`）が差に出ない（ほかの行は変わる）＋本番で移行の前後に `calendar_type` ごとの件数を数えて同じ（会社1 personal 1・shared 2／会社4 personal 24・shared 8） |
| A10 | 種類の一覧の正本が 1 か所 | `git grep -n "calendars.config" -- frontend/src` が 0 件／`git grep -n '"procurement"' -- frontend/src ':!frontend/src/locales'` が 0 件／`git grep -n "'procurement'" -- backend/app ':!backend/app/services/tenant.py'` が 0 件（`backend/app/services/tenant.py` の中の行数は書き方で変わるので数えない）。i18n の `schedule.calendarLabels.*` は 7 種の名前の訳として残すので数えない |
| A11 | 新しい文字はすべて `t()`、ja/en 同じキー。部品は金型だけ。色の点は既存の `schedule-month__dot` を使い、新しい CSS の色を足さない | i18n 点検・UI governance gate・Lint & Dark Mode Check |
| A12 | ひな形で作った会社と、移行を流した会社の形が同じ | CI のひな形と形の差の検査（F14）が通る |

## 3 裏側の変更

### 3-1 表（新しい会社の形 `backend/app/services/tenant.py` と移行の両方に同じ形で書く）

```sql
CREATE TABLE IF NOT EXISTS {schema}.calendar_categories (
    key character varying(50) NOT NULL,
    name character varying(50),
    color_key text,
    default_share character varying(10) DEFAULT 'all' NOT NULL,
    sort_order integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT calendar_categories_pkey PRIMARY KEY (key),
    CONSTRAINT calendar_categories_key_format_check CHECK (key ~ '^[a-z][a-z0-9_]{0,49}$'),
    CONSTRAINT calendar_categories_default_share_check CHECK (default_share IN ('self', 'all')),
    CONSTRAINT calendar_categories_color_key_check CHECK (color_key IN (<24 色・calendar_events_color_key_check と同じ並び>)),
    CONSTRAINT calendar_categories_name_check CHECK (name IS NOT NULL OR key IN ('meeting','personal','procurement','shipping','billing','release','holiday'))
);
```

- 初期の 7 行（`ON CONFLICT (key) DO NOTHING`）: `meeting` 1・`personal` 2・`procurement` 3・`shipping` 4・`billing` 5・`release` 6・`holiday` 7（数字は `sort_order`）。`name` と `color_key` は NULL。`default_share` は `personal` だけ `self`、ほかは `all`（今の F6 の動きと同じ）。
- `name` が NULL の 7 種は、画面が今の i18n の名前（`schedule.calendarLabels.<key>`）を出す。名前を付けたらその名前を出す。
- 色は NULL＝「種類の色なし（今どおりデフォルト）」。今の札の色から 24 色へ写す表は作らない（根拠の無い対応を作らないため）。
- 予定の表: `calendar_events_category_check` を外し、`calendar_events_category_fkey FOREIGN KEY (category) REFERENCES {schema}.calendar_categories(key) ON UPDATE RESTRICT ON DELETE RESTRICT` を足す。種類の行は消さない（使わなくするだけ）ので RESTRICT で足りる。
- `backend/app/services/tenant.py` では `calendar_categories` の作成と 7 行を `calendar_events` より前に置き、`calendar_events` の CHECK の行を外部キーの行に置き換える。`:1577` のコメントを「登録の移行 `20261126_100000` で外部キーが付く」に直す。
- 更新時刻: 関数 `{schema}.set_updated_at_calendar_categories()` とトリガ `trg_calendar_categories_updated_at` を、`backend/app/services/tenant.py:2139`（関数）・`:2241`（トリガ）と同じ形で、ひな形と移行の両方に書く（A12）。

### 3-2 移行（新規 `migrations/20261126_100000_create_calendar_categories.sql`）

- `^tenant_\d+$` の部屋ごとに、`calendar_events` が無い部屋は飛ばす（手本 `migrations/20261119_120000_add_calendar_events_color_key.sql`）。
- 順に:
  1. `pg_attribute` に `calendar_events.category` が無い部屋だけ `ALTER TABLE calendar_events ADD COLUMN category varchar(50) NOT NULL DEFAULT 'meeting'`（有る部屋はロックを取らない・ADR-1037。本番は全社に有る・F9）
  2. 表を作る → 7 行 → 関数とトリガ
  3. 予定の外部キーを `NOT VALID` で足す（`pg_constraint` に同じ名前が無いときだけ）→ `VALIDATE`
  4. `DROP CONSTRAINT IF EXISTS calendar_events_category_check`
  5. 確かめ: その部屋の `calendar_events` に、`contype = 'c'` で定義に `category` を含む制約が 1 件でも残れば `RAISE EXCEPTION`。全部屋を 1 つの `DO` ブロックに入れ、失敗すれば全体が戻る（手本と同じ）（名前が違う古い CHECK が残ると `custom_N` で予定が作れないため。本番 5 社は名前が同じ・F9）
- 何度流しても同じ。
- 登録は F10 の 5 行に倣う（`scripts/run_all_migrations.sh` は `:1483` の後ろ、今の末尾の `20261122_100000` の後・`mr_report_summary` の前。`backend/tests/rls_bootstrap.py` は件数 1。`backend/tests/test_calendar_sync_tenant_reset_pg.py` は True。`backend/tests/test_tenant_loop_migration_guard.py` は 2 つの一覧）。
- 保護表の一覧（`scripts/migration-guard/protected-tables.txt`）に `calendar` の表は無いので、7 行の INSERT は当たらない（審査 S8 で確認済み）。
- AI 用の写しの分類（ADR-1052・F13）:
  - `migrations/20261024_100300_create_ai_cloud_views.sql` に 3 行: `ARRAY['key','name']` を `mask`（`key` は形だけの CHECK、`name` は自由な文字）、`ARRAY['color_key']` を `allow`（理由「値の決まり calendar_categories_color_key_check で値が限られる」）、`ARRAY['default_share']` を `allow`（理由「値の決まり calendar_categories_default_share_check で値が限られる」）。整数・真偽・日時の欄は行を作らない（`backend/tests/ops/test_ai_cloud_views.py:52` の `_PASS_TYPES`）。
  - `:3` の注記を 1165 → 1169、`backend/tests/ops/test_ai_cloud_views.py:486` を 1169 に（分類表は欄ごとに 1 行。`ARRAY` は unnest で欄ごとに分かれる・`migrations/20261024_100300_create_ai_cloud_views.sql:7`）。
  - `docs/handoff/cloud-case-ai/stage1-column-class.tsv` に 4 行（6 列。`key` mask character varying・`name` mask character varying・`color_key` allow text・`default_share` allow character varying）。
  - `scripts/migration-guard/reference-allowlist.tsv:7` の sha256 を新しい値に、理由欄に「schedule-settings card-bin2a（分類3行追加: calendar_categories）」を書き足す。
  - `backend/tests/ops/test_ai_cloud_views.py` に `test_t10_calendar_color_key_is_classified_on_bootstrapped_db`（`:1017-`）と同じ形で、`calendar_categories` の 4 欄の分類を確かめる試験を 1 つ。
- 戻し方: コードの PR を戻すだけ。表と外部キーは残す（古いコードは表を読まず、7 種は表に有るので外部キーに当たらない）。消す移行は作らない。注意: 戻す前に管理者が足した `custom_N` の種類の予定は、古い画面で札が出ない（`meta &&` で守られ壊れはしない）。古い画面で開いて保存すると種類が 7 種のどれかに変わりうる。

### 3-3 正本の読み書き（新規 `backend/app/services/calendar_categories.py`）

- `list_categories(db) -> list[dict]`: `sort_order, key` の順で全行（使わなくした行も `is_active` 付きで返す）。
- `get_category(db, key) -> dict | None`
- `create_category(db, tenant_id, name, color_key, default_share) -> dict`: 鍵は `custom_` ＋ 今ある `custom_` の最大の数＋1。`sort_order` は最大＋1。「最大の数」は数に直して取る（`custom_9` の次は `custom_10`）。同時に押されて鍵がぶつかったら（`IntegrityError`）`await db.rollback()` してから 409 `category_conflict`。
- `update_category(db, tenant_id, key, fields) -> dict | None`: `name`（7 種は空の文字で NULL に戻せる。`custom_` は空にできず 422 `category_name_required`）・`color_key`（空の文字で NULL）・`default_share`・`is_active`。`meeting` を `is_active=false` にする指定は 422 `category_not_disableable`（Google からの取り込みと種類を送らない作成の既定が `meeting` のため）。
- 名前は前後の空白を落としてから 1〜50 字を見る。
- 書いたあとは `await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)`（ADR-072）。

### 3-4 受け口（`backend/app/routers/calendar.py`）

| 道 | だれ | 中身 |
|---|---|---|
| `GET /calendar/categories` | ログインした人 | 全行（`key, name, color_key, default_share, sort_order, is_active`） |
| `POST /calendar/categories` | 管理者（F11） | `{name(1〜50 字), color_key?, default_share}` → 201 で 1 行 |
| `PATCH /calendar/categories/{key}` | 管理者 | 上の欄の一部。無い鍵は 404 `not_found:calendar_category` |

- 消す道は作らない（外部キーで消せない。使わなくするで足りる）。
- 色の値の確かめは既存の `_check_color_key`（`backend/app/routers/calendar.py:115`）。共有の初期値は `self`/`all` 以外 422。
- 予定の作る・直す入力に `category: Optional[str] = None` を足す。
  - 作る: 指定が無ければ `meeting`（使わなくできないので常に通る）。表に無い・使っていない鍵は 422 `invalid_category`。
  - 直す: 指定があり、今の種類と違うときだけ同じ判定。同じなら通す（A4）。繰り返しの直しでの「今の種類」は、色の比べ方（`backend/app/services/calendar_service.py:1049-1054`）と同じく、例外の行が有ればその行、無ければ元の行の値。
- サービスで種類を通す 5 か所（F5）:
  1. `update_event` の `field_map`（`:502-512`）に `"category": "category"`
  2. `_TEXT_FIELDS`（`:682`）に `"category"`（「すべて」D1〜D3 はこれで効く）
  3. 「この予定だけ」の `row_fields` の並び（`:1056`）に `"category"`
  4. 「これ以降」（`:1122`）を `category=fields.get("category", master["category"])`
  5. 「単発→繰り返し」の並び（`:1224`）に `"category"`
- 種類を選んでも、裏側は色と共有を自動で書き換えない（初期値を入れるのは画面。送られた値をそのまま保存する）。

## 4 画面の変更

### 4-1 種類の正本を画面から消す

- frontend/src/features/schedule/calendars.config.ts（この便で消した） と frontend/src/features/schedule/calendars.config.test.ts（この便で消した） を消す。種類の型は `string` にする（F7 の 3 ファイルすべて: `frontend/src/pages/schedule/ScheduleDraftFields.tsx`・`frontend/src/pages/schedule/SchedulePageImpl.tsx`・`frontend/src/pages/schedule/schedule-utils.ts`）。
- 新規 `frontend/src/features/schedule/useCalendarCategories.ts`: `useApiQuery("/calendar/categories")`（F12）。名前を出す関数 `categoryLabel(cat, t)` = `cat.name ?? t(\`schedule.calendarLabels.${cat.key}\`)`。表に無い鍵（読み込み前など）は、7 種なら i18n 名、それ以外は鍵をそのまま出す。設定ページで書いたあとは `useInvalidateApi` で `["calendar","categories"]` を取り直す。
- 予定の詳細の札（`frontend/src/pages/schedule/SchedulePageImpl.tsx:319`・`:344-345`）: `Badge variant="neutral"` に種類の名前。種類に色があれば名前の前に既存の点 `schedule-month__dot`（背景 `eventColorVar(color_key)`）。新しい CSS の色は足さない。
- 詳細の「種類」行（`:399-400`）と一覧の名前（`:723-736`）も `categoryLabel` に置き換える。`getCalendarMeta`（`:222-223`）は消す。

### 4-2 種類を選ぶと初期値が入る（`frontend/src/pages/schedule/ScheduleDraftFields.tsx` の `DraftCategoryField`）

- 選び方の中身は、使っている種類（`is_active`）の `sort_order` 順。今の予定の種類が使わなくした種類なら、それも 1 つ足す（A7）。
- 作るとき（`mode === "create"`）に変えたら: `colorKey = cat.color_key ?? null`（デフォルト）・`visibleToStaff = cat.default_share === "all"`（今の F6 の条件の置き換え）。
- 直すときに変えたら: 種類だけ変える。色と共有は変えない（手で付けた色や Google の色を消さないため。共有は持ち主でない人が変えられないため・`frontend/src/pages/schedule/SchedulePageImpl.tsx:1068`）。
- 新しい予定の初期値（`frontend/src/pages/schedule/SchedulePageImpl.tsx:954`・`:1203`）: 種類 `meeting` と、その種類の色・共有の初期値（読み込み前は今どおり色なし・全員）。
- 送り先の本文: 作るは `:1006` で既に `category` を入れている。直すは種類が変わったときだけ `category` を入れる。

### 4-3 設定ページの「予定の種類」区画（`frontend/src/pages/schedule/ScheduleSettingsPage.tsx`）

- 管理者だけに出す（便1 の Google 区画と同じ条件 `isTenantAdmin === true`）。左の並び（金型 `SubMenu`）に 1 項目足す。
- 金型 `SectionCard` の中に、種類ごとに 1 行: 名前（金型 `TextFieldControl`）・色（金型 `ColorSwatchPicker`、先頭に「種類の色なし」）・共有の初期値（金型 `SelectControl`: 自分だけ／全員）・使う（金型 `Toggle`。`meeting` の行は切れない状態で出す）・保存（金型 `Button`）。7 種の名前の欄は空にでき、空なら i18n の名前に戻ると下に書く。
- 下に「種類を足す」（金型 `Button`）。押すと空の行が出て、名前を入れて保存で作る。
- 保存の成功・失敗は便1 と同じ帯の部品で出す。失敗の文は「起きたこと＋次にすること」（ADR-1071）。409 は「ほかの人と同時に足しました。もう一度押してください」の形。

### 4-4 新しい文字（ja/en 同じキー・`schedule` の中）

区画の見出し・説明・各欄の名前・「種類の色なし」・自分だけ／全員・使う・保存・足す・成功・失敗（422・409・その他）・空の名前の説明・`meeting` は止められない説明。実装担当が使う分だけ足し、使わないキーは足さない。

## 5 試験

- 裏側:
  - 種類の受け口（一覧・足す・直す・403・404・422・409・`meeting` を止めると 422）
  - 予定の種類: 作る（保存・既定 `meeting`・`invalid_category`）、直す 5 通り（単発・この予定だけ・これ以降・すべて・単発→繰り返し）でそれぞれ正しい行に入る、使わなくした種類のまま直すと通る
  - 移行（2 回流して同じ・7 行・外部キー・古い CHECK 0 件・無い鍵の INSERT が失敗・`custom_1` を足すとその鍵で INSERT が通る）
  - 分類表（件数 1169・新しい表の 4 欄の分類）
- 画面:
  - 作るときに種類を選ぶと色と共有が入る／直すときは色と共有が変わらない
  - 使わなくした種類が選び方に出ない／今の予定の種類なら出る
  - 設定の区画が管理者だけ（3 通り）・足す・保存の失敗の文
- 既存の試験: `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` など予定の画面を開く試験には `/calendar/categories` の応答の擬似を足す。`:1364` の札の試験は新しい札の形に直す。frontend/src/features/schedule/calendars.config.test.ts（この便で消した） は消す。

## 6 触らない

- 見え方の条件（`backend/app/services/calendar_service.py:238-250`）・`calendar_type` の値・作る／直す／消すの権限の判定。便2b で扱う。
- Google への色の送り（ADR-1081）。種類の色は予定の `color_key` に入るので、今の送り方がそのまま効く。
- Google からの取り込み（`upsert_from_google`）。種類は欄の既定値 `meeting` のまま。
- 秘書（`backend/app/routers/assistant.py`）の予定作成。種類は既定の `meeting`。
- `calendar_owner_settings` と人ごとの色。便3 で扱う。

## 7 代替案

| 案 | 採らない理由 |
|---|---|
| 画面の固定表に色と共有を足す | 種類を足す・名前を変える（要件）ができない。会社ごとに変えられない |
| 種類の表に数の id を主キーにする | 予定の `category` は今文字の鍵。鍵を主キーにすれば予定の表を書き直さずに外部キーで結べる |
| 今の札の色を 24 色へ写して初期の色にする | 写し方に根拠が無い。初期は「色なし」で今の見た目の予定の色を変えない |
| 便2 を 1 つの PR で出す | §0 のとおり見え方の変更を単独で試験・審査するため分ける |
| `meeting` も止められるようにし、種類を送らない作成を 422 にする | 秘書・Google 取り込み・古い画面が止まる。既定の種類は常に使える形にする |

## 8 危うさと手当て

| 危うさ | 手当て |
|---|---|
| 外部キーを足すときに、表に無い種類の予定があると失敗する | 今は CHECK で 7 種に限られている（F9）ので、7 行を先に入れれば必ず通る。`NOT VALID`→`VALIDATE` で長いロックを避ける（ADR-1037） |
| 古い CHECK の名前が違い、残ったまま `custom_N` が入らない | 本番 5 社は名前が同じ（F9）。移行の最後に「`category` を使う CHECK が残れば失敗」の確かめを入れる |
| 札の色が種類ごとの色から灰色＋色の点に変わる | 本番の予定は全部「会議」。PO に目視で確かめてもらう（§11） |
| 種類の保存の直しで、今まで捨てられていた値が入り始める | 直しそのものが目的（F2）。既存の予定は変わらない。種類は見え方の絞りに使わない（`personal` の種類でも「全員」にした予定は全員に見える。今も同じ） |

## 9 外部・過去事例

- Google カレンダーは「カレンダー」ごとに色と共有を持ち、予定を作るときに選んだカレンダーの色と共有が入る（support.google.com/calendar の「カレンダーを作成する」「共有する」。日付は未確認）。今回の「種類を選ぶと色と共有の初期値が入る」の形の参考。数値の根拠には使わない。

## 10 維持の仕組み

- 種類の一覧の正本は種類の表 1 つ。A10 の `git grep` を審査役の確かめに入れる。
- 外部キーで、表に無い種類は DB が止める。
- 守り手: CI（pytest・vitest・i18n 点検・UI governance gate・Lint & Dark Mode Check・移行の試験・ひな形の形の差）。設計の持ち主は Opus（設計担当）。

## 11 本番での目視（PO）

1. 予定ページで今の予定の札が「会議」の灰色の札になっている。
2. 設定ページの「予定の種類」で「出荷」に色を付けて保存する。
3. 予定ページで予定を作り、種類に「出荷」を選ぶと色が入る。「私用」を選ぶと「社員に見せる」が切れる。

## 12 審査

| 回 | 日 | 判定 | 記録 | 入れた直し |
|---|---|---|---|---|
| 1 | 2026-11-25 | REVISE（必須 7・推奨 8） | `docs/handoff/schedule-settings/review-architect-bin2a-1.md` | R1〜R7・S1〜S8 すべて（R5 は (a) の確かめと本番の制約名の読み取りの両方） |
| 2 | 2026-11-25 | APPROVE（必須 0・推奨 12） | `docs/handoff/schedule-settings/review-architect-bin2a-2.md` | N1・N2・N5〜N8・S9・S10・S12 を本文へ。S11（本番の読み方）は A1・A2 を「反映後に Opus が読むだけの鍵で `pg_constraint` と各社の表を直接数える（CI の合否ではない）」と読む。S10 の tsv と SQL の 94 行のずれは別件 |
