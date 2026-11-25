# 審査報告 便2a 設計（第1回）

本報告は design-bin2a.md（c07380e3e）の設計審査である。

- 審査役: クラウドの Architect（コードは直さない）。審査日 2026-11-25
- 対象: `docs/handoff/schedule-settings/design-bin2a.md`（枝 `release/schedule-settings-bin2a`、HEAD `c07380e3e`。作業場所で `git log -1 --oneline` が `c07380e3e` を確認済み）
- 読んだもの: 親の `design.md`・`requirements.md`、手本 `docs/handoff/event-color/card-bin1.md` §4
- 実物の基準: 設計が基準にした `b4940fe2e` と、いまの `origin/main`（`7a329ce5d`）の間で、設計が触るファイル群（`calendar_service.py`・`routers/calendar.py`・`tenant.py`・`frontend/src/pages/schedule`・`frontend/src/features/schedule`・`migrations`・`run_all_migrations.sh`）の差は 0（`git diff --stat b4940fe2e origin/main -- <それらのファイル>` が空）。行番号は両方で同じ
- 本番の値（F3・F9）は、この審査では本番を読んでいないため「未確認」と書く

## 1 事実 F1〜F11 の照合

| # | ○× | 実物（file:行） |
|---|---|---|
| F1 | ○ | `backend/app/services/tenant.py:1579` に `calendar_events_category_check CHECK (category IN ('meeting','personal','procurement','shipping','billing','release','holiday'))`。`frontend/src/features/schedule/calendars.config.ts:3-62` に 7 種の表（`CalendarId` が `:3-10`、`CALENDARS` が `:19-62`） |
| F2 | ○ | `backend/app/routers/calendar.py:122`（`CreateEventBody`）・`:140`（`UpdateEventBody`）・`:160`（次の `SyncModeBody`）。両方に `category` の欄なし（`color_key` はある）。画面は `SchedulePageImpl.tsx:1006` で `category: draft.category` を送る |
| F3 | 未確認 | 本番の値（35 件・すべて `meeting`）。この審査では読んでいない。ただし移行の外部キーの前提（表に無い種類が無いこと）は、種類が今は CHECK で 7 種に限られるので、本番の件数に関係なく成り立つ（`tenant.py:1579`） |
| F4 | ○ | `backend/app/services/calendar_service.py:423` `"category": payload.get("category", "meeting")` |
| F5 | ○（補足あり） | `_TEXT_FIELDS`（`:682`）に `category` なし。`EVENT_COLUMNS`（`:148-152`）に `category` あり。`_row_values`（`:969-973`）に `"category": master["category"]` あり。`:742` が `_TEXT_FIELDS` を使う。**ただし F5 は `update_event` の `field_map`（`:490` 付近）を挙げていない。下の R1 を参照** |
| F6 | ○ | `frontend/src/pages/schedule/ScheduleDraftFields.tsx:284-290`（`changeCategory`。`:288` が `visibleToStaff: category !== "personal"`、作るときだけ） |
| F7 | ○（数え漏れあり） | `SchedulePageImpl.tsx:319`（`getCalendarMeta(draft.category)`）・`:344-345`（`Badge variant={meta.badgeVariant}`＋`t(meta.labelKey)`）・`:723-736`（一覧の名前）。**ほかに `:94`・`:153-154`・`:222-223`・`:399-400` と `schedule-utils.ts:62` にも表を使う所がある。下の R7 を参照** |
| F8 | ○ | `ScheduleDraftFields.tsx:11`（`ColorSwatchPicker` の取り込み）・`:327-345`（`DraftColorField`） |
| F9 | 未確認 | 本番の値。ただし `tenant.py:1577` のコメントに「本番 5 社全部にある（`category` 列）」とある（これも本番を読んだ値ではなく、コメントの記述） |
| F10 | ○ | `docs/handoff/event-color/card-bin1.md` §4-2（移行・登録 4 か所）・§4-3（AI 用の写しの分類表）。**ただし手本の §4-3 は 4 か所で、実物にはもう 1 か所ある。下の R4 を参照** |
| F11 | ○ | `backend/app/routers/calendar.py:523` `not is_tenant_admin(await get_user_system_keys(db, user.id))`（`:623-624` にも同じ形） |

F1〜F11 のうち、実物と食い違う記述は無かった。ただし F5・F7・F10 は「書いてあることは正しいが、数えが足りない」。

## 2 判定の要約

| 重さ | 件数 |
|---|---|
| 必須 | 7（R1〜R7） |
| 推奨 | 8（S1〜S8） |

## 3 必須の指摘

### R1 単発の予定を直す道（`update_event`）が種類を保存しない（A3 が単発で成り立たない）

- 設計 §3-4 は「サービスの `_TEXT_FIELDS`（F5）に `category` を足し」としか書いていない。
- 繰り返しでない予定の更新は `cal_svc.update_event`（`calendar_service.py:480-`）で、ここは `_TEXT_FIELDS` を使わず **専用の `field_map`**（`:490-499` 付近。`title`・`description`・`location`・`start_datetime`・`end_datetime`・`is_all_day`・`calendar_type`・`user_id`・`color_key` の 9 つ）で SET 句を作る。ここに `category` が無いと、受け口で `payload` に入れても UPDATE されず、F2 と同じ「受け口で捨てる」が形を変えて残る。
- 直し方: §3-4 に「`update_event` の `field_map` に `"category": "category"` を足す」と書く。§5 の試験に「繰り返しでない予定を直して `billing` が保存される」を明記する。

### R2 繰り返しの直す道の 3 か所で種類が落ちる（設計は 1 か所を「そのまま」と書いている）

- 設計 §3-4 は「繰り返しの 3 択（`_row_values`・`_merged`・`_update_single_to_recurring`）でも元の行の種類を引き継ぐ（今は `master["category"]` を使っている所はそのまま）」と書く。実物では次のとおり。
  - 「これ以降」（`calendar_service.py:1122`）: `values = _row_values(source, ..., category=master["category"], ...)` と **種類を明示で元の行に固定**している。`_TEXT_FIELDS` に足しても `fields["category"]` は使われず、「これ以降」で種類を変えても新しい行は元の種類のまま。**設計の「そのまま」は誤り**。`category=fields.get("category", master["category"])` に変える必要がある。
  - 「この予定だけ」（`:1031-1033`）: `row_fields` を `("title", "description", "location", "color_key")` の固定の並びで作る。`category` が無いので、例外の行へ種類が入らない。
  - 「単発→繰り返し」（`_update_single_to_recurring`、`:1218-1228`）: `("title", "description", "location", "calendar_type", "user_id", "is_all_day", "color_key")` の固定の並び。`category` が無い。
  - 「すべて」D1〜D3 は `fields`（= `_TEXT_FIELDS` の絞り）を使うので、`_TEXT_FIELDS` に足せば効く。
  - `_merged`（`:1021-1024`）は辞書を重ねるだけで、直す所は無い（設計が名指しする必要は無い）。
- 直し方: §3-4 を「`_TEXT_FIELDS`（`:682`）・`:1122` の `category=` ・`:1031-1033` の並び・`:1220` の並び・`update_event.field_map`（R1）の 5 か所に `category` を足す」と書き換える。§5 の試験に 3 択ごと（この予定だけ・これ以降・すべて・単発→繰り返し）で種類が正しい行に入る試験を足す（手本 card-bin1 §4-9 の「3 択それぞれで色が正しい行に入る」と同じ形）。

### R3 「使わなくする」で `meeting` を止められると、種類を指定しない作成がすべて 422 になる

- 設計 §3-4 は「作る: 指定が無ければ `meeting`。表に無い・使っていない鍵は 422 `invalid_category`」。`meeting` を `is_active=false` にできる（§3-3 の `update_category` は `is_active` を受ける・禁止の規則なし）ので、そうすると、種類を送らない作成（古い画面の写し・API の直叩き・秘書など。`backend/app/services/calendar_service.py:423` の既定）が 422 になる。逆に既定のまま検査をしない書き方にすると、使っていない種類の予定が作れてしまう。どちらか決まっていない。
- 加えて、Google からの取り込み（`upsert_from_google`、設計 §6 で「欄の既定値 `meeting` のまま」）は DB の既定 `meeting` で入るため、`meeting` の行が外部キーの相手として常に必要（行は消さないので OK）。
- 直し方（どちらかを §3-3・§3-4 に明記）:
  - 案1（推奨）: `meeting` は `is_active=false` にできない（422 `category_not_disableable`）。「使っている種類が 0 件」の状態も作らない。
  - 案2: 既定の `meeting` は「使っていなくても通す」と明記し、A4 の試験に入れる。

### R4 AI 用の写しの分類表: 「全部 allow」は規則に合わない・件数と許可一覧の手順が足りない

設計 §3-2 は「分類は、秘密の欄が無いので全部 `allow`」「件数の注記と試験の数」としか書かない。実物では次のとおり。

1. **allow にできるのは「値の決まりで値が限られる列」だけ**。根拠: `migrations/20261024_100300_create_ai_cloud_views.sql:373` で、文字の形だけの CHECK の `recurrence_rule` は `mask`（理由「値の決まりが値の一覧でなく文字の形だけのため伏せる」）。`docs/handoff/cloud-case-ai/design.md:315` も「値の決まりは値の一覧の形だけを根拠にする」「根拠の無い自由入力の列は mask」。新しい表では次になる。
   - `key`（CHECK は正規表現 `^[a-z][a-z0-9_]{0,49}$` で一覧ではない）→ `mask`
   - `name`（利用者が書く自由な文字）→ `mask`
   - `color_key`（24 色の CHECK）→ `allow`
   - `default_share`（`self`/`all` の CHECK）→ `allow`
   - `sort_order`・`is_active`・`created_at`・`updated_at` は「そのまま」の型（`tsv` の `calendar_events` に整数・日時の行が無いのと同じ。`backend/tests/ops/test_ai_cloud_views.py:52` の `_PASS_TYPES`）で、分類の行は不要
2. **件数**: 今の正本の注記は「1165 行」（`create_ai_cloud_views.sql:3`）、試験は `backend/tests/ops/test_ai_cloud_views.py:486` で `== 1165`（手本カードの 1163 は古い）。上の 4 行を足すと 1169。設計に数が書いていないので、実装者が「欄を全部＝8 行」と取ると 1173 になって試験が落ちる。数を書く。
3. **許可一覧の sha256**: `scripts/migration-guard/reference-allowlist.tsv:7` に `create_ai_cloud_views.sql` の sha256（今の実物と一致を確認: `e36ff150…b4810`）がある。このファイルを変えると、`scripts/check-migration-value-writes.py repo`（規則 2・3）が落ちる。手本カード §4-3 の 4 か所には無いが、実物の前回の PR は同じ行の理由欄（`event-color card-bin1（分類1行追加: calendar_events.color_key）`）を書き足している。設計の登録の手順に「`reference-allowlist.tsv` の sha256 と理由欄の更新」を足す。
4. `docs/handoff/cloud-case-ai/stage1-column-class.tsv` と、新しい表の分類を確かめる試験（手本 `test_t10_calendar_color_key_is_classified_on_bootstrapped_db`、`test_ai_cloud_views.py:1017-`）を、`calendar_categories` 用に書く（`bootstrap_tenant_schema` で新しい表が実在すること）。
- 直し方: §3-2 を上の 1〜4 に書き換える。

### R5 移行の古い CHECK を名前で外す: 本番の名前は未確認（外れなければ `custom_N` が入らない）

- 設計 §3-2 は「古い CHECK を外す」（名前 `calendar_events_category_check` が前提、§3-1）。実物では、`tenant.py:1577` のコメントが「作る SQL `migrations/20260621_020000_…` は登録に無い」と書く。`scripts/run_all_migrations.sh` に当該ファイルは無い（`git grep 20260621_020000 scripts/run_all_migrations.sh` は `migrate_20260621_020000_backfill_lead_country.py` の別物だけ）。つまり本番の `category` 列と CHECK は登録の外の経路で入った。本番の CHECK の名前が `calendar_events_category_check` である証拠が、設計・実物のどこにも無い（A2 の「本番で制約の一覧を読む」は反映後の確認で、移行を書く前の確認ではない）。
- 名前が違えば古い CHECK が残り、**管理者が足した `custom_N` の種類で予定を作ると CHECK 違反になる**（外部キーは通るのに保存できない）。
- 直し方（どちらか）: (a) 移行を、`pg_constraint` から「`calendar_events` の CHECK で定義が `category` だけを使うもの」を名前で引いて外す形にする（`DROP CONSTRAINT IF EXISTS` を名前で決め打ちしない）。(b) 反映前に、読むだけの鍵で本番 5 社の制約名を確かめ、設計に事実として書く。(a) を推奨（(b) だけだと将来の会社で崩れる）。あわせて、列 `category` が無い会社が無いことの確かめ（`ADD COLUMN IF NOT EXISTS category varchar(50) NOT NULL DEFAULT 'meeting'` を外部キーの前に置く）も書く。

### R6 画面の種類の書き換えで、設定ページの保存が選び方へ反映される道が書いていない（読み込みの鍵）

- 設計 §4-1 は「react-query で `GET /calendar/categories`（鍵 `["calendar", "categories"]`）」。この画面の正本は `useApiQuery`（`frontend/src/lib/query/apiQuery.ts:1-8` 「取り方は useApiQuery だけ」・`:50` 写しの名前は `["api", uid, …]`）。生の `useQuery` に `["calendar","categories"]` を渡すと、ユーザーごとの名前（`uid`）が付かず、別の会社の人が同じブラウザでログインし直したときに前の会社の種類が出る。読み方・書いた後の取り直し（`useInvalidateApi(["calendar","categories"])`。既存は `invalidate(["calendar","events"])`、`SchedulePageImpl.tsx:1060` 付近）を `useApiQuery` で書くと明記する。
- 直し方: §4-1 を「`useApiQuery("/calendar/categories")`。保存・足す・使わなくするのあとは `useInvalidateApi` で `["calendar","categories"]` を取り直す」に直す。
- 重さの注記: 設計の「鍵」が `useInvalidateApi` の語の並びを指しているだけの可能性もある（その場合は表現の曖昧さ）。文面を 1 つに決めれば足りる。

### R7 `calendars.config` の使い先の数え漏れ（§4-1 は 2 か所しか書かない）

`git grep -n "calendars.config" -- . ':!docs'` の結果（全数）:

| # | 場所 | 中身 |
|---|---|---|
| 1 | `frontend/src/pages/schedule/ScheduleDraftFields.tsx:20` | `import { CALENDARS, type CalendarId }`。`:285` の型・`:292` の選び方の元 |
| 2 | `frontend/src/pages/schedule/SchedulePageImpl.tsx:28` | `import { CALENDAR_MAP, type CalendarId }`。使い先は `:94`（`category: CalendarId`）・`:222-223`（`getCalendarMeta`）・`:319`・`:344-345`・`:399-400`・`:723-736` |
| 3 | `frontend/src/pages/schedule/schedule-utils.ts:62` | `category: import("../../features/schedule/calendars.config").CalendarId \| null`（型だけの取り込み。`:359` の `as ScheduleItem["category"]` と `:398` の `category: "personal"` も同じ型に依る） |
| 4 | `frontend/src/features/schedule/calendars.config.test.ts:4` | 自分自身の試験（消す対象） |
| 5 | `.claude-pipeline/active-work.md:316` | 2026-07-12 の古い作業メモ（実装には関係ない） |

- `frontend/src` の取り込み 4 か所（上の 1〜4）が全数で、うち**実装の変更が要る場所は 3 か所（1〜3）**。設計は 1・2 の入り口しか書かず、**3（`schedule-utils.ts:62`）と、2 の中の `:399-400`（詳細の「種類」行）・`:94`・`:222-223`・`:153-154` を書いていない**。`calendars.config.ts` を消すと型が通らなくなって実装者が気付くが、設計の「全数」として足りない。
- 設計 §5 の「既存の試験で `calendars.config` を使うものは、表の取り込みの擬似の値に置き換える」は、使う既存の試験が無い（上の 4 が自分自身の試験だけ）ので、文の意味が無い。実際に壊れるのは `SchedulePageImpl.test.tsx:1364`（`schedule.calendarLabels.meeting` の文を期待する札の試験）と、`/calendar/categories` の取得が未定義になる画面の試験全般（`useCalendarCategories` を足すと、その画面を開く試験すべてがこの API の応答を要る）。
- 直し方: §4-1 に上の 3 か所と `:399-400` を書く。§5 の最後の行を「`SchedulePageImpl.test.tsx` など、予定の画面を開く試験は `/calendar/categories` の応答の擬似を足す。`calendars.config.test.ts` は消す」に書き換える。

## 4 推奨の指摘

### S1 種類を変えると、直すときも色が上書きされる（A6・§4-2）

- §4-2 は「変えたとき: `colorKey = cat.color_key`（NULL ならデフォルト）」。共有の自動切り替えは「作るとき（`mode === "create"`）」に限るのに、色は作る・直すの両方で書き換える。画面は保存のたびに `color_key: draft.colorKey ?? ""` を送る（`SchedulePageImpl.tsx:1009`）ので、既存の予定の種類を変えただけで、手で付けた色（や Google から取り込んだ色）がデフォルトに戻る。
- 直し方: 色の初期値は作るときだけ入れる（共有と同じ条件）。直すときも入れたいなら、色を触っていないときだけ入れる、と書く。A6 の試験に「直すと色が変わらない」を足す。

### S2 `create_category` の鍵の採番が競合に弱い（§3-3）

- 「`custom_` ＋ 今ある `custom_` の最大の数＋1」を 2 人が同時に押すと、同じ鍵になり PK 違反が 500 になる。名前の前後の空白・空白だけの名前の扱いも決まっていない（1〜50 字だけ）。
- 直し方: `IntegrityError` を 409 にして画面で「もう一度押してください」を出す（または `pg_advisory_xact_lock` で直列化）。名前は前後の空白を落としてから 1〜50 字を見る。

### S3 A10 の `git grep` が今すでに通っていて、守りになっていない

- A10 の `git grep -n "'procurement'" -- backend/app frontend/src` を、いまの実物で流した結果は `backend/app/services/tenant.py:1579` の 1 行だけ（`calendars.config.ts` は二重引用符の `"procurement"` なので当たらない）。つまり変更前から「`tenant.py` だけ」で、**この検査は変更を測れない**。さらに、変更後の `tenant.py` は初期の 7 行と `calendar_categories_name_check` の鍵の並びで `'procurement'` が 2 回出る（設計の想定は「初期の 7 行だけ」）。
- 直し方: A10 を `git grep -n "calendars.config" -- frontend/src` が 0 件、かつ `git grep -n '"procurement"' -- frontend/src ':!frontend/src/locales'` が 0 件、かつ `git grep -n "'procurement'" -- backend/app` が `tenant.py` だけ（件数は 7 行の INSERT と `name_check` の分で決めて書く）に直す。`schedule.calendarLabels.*`（`locales/ja.json:3642` ほか）は i18n の名前として残るので、検査から外す理由を一言書く。

### S4 受入条件 A1〜A11 の測り方（○×で測れるか）

| 基準 | ○×で測れるか | 指摘 |
|---|---|---|
| A1 | ○ | 試験は測れる。本番の「5 社 × 7 行」は、分類表に新しい表が載り（R4）、AI 用ビューが作り直されたあとに読める。読む手順（どのビューを読むか）を 1 行書く |
| A2 | 条件つき | 試験は○。本番の「制約の一覧を読む」は、読むだけの鍵で制約を読める手段が設計に無い（AI 用ビューは制約を出さない）。反映後に読む手段を決める（または A2 の本番の確認を「無い鍵の INSERT が失敗する」を試験のみにする） |
| A3 | ○ | 試験は R1・R2 を直せば測れる。本番の目視は「一覧の種類の名前で目視」とあるが、一覧に出るのは `SchedulePageImpl.tsx:736`（`schedule-list__category`）で、設計の新しい札でも出る（OK） |
| A4 | ○ | R3 を決めれば測れる |
| A5 | ○ | 403・404・422・201 の試験で測れる |
| A6 | 条件つき | 「画面の試験」は○。「本番で PO 目視」は、本番は全予定が `meeting`・色 NULL（F3）なので、目視する対象が無い。PO に、種類を足して色と共有を付ける手順を書く（または試験のみ） |
| A7 | ○ | 画面の試験で測れる |
| A8 | ○ | 管理者のみ見える・staff.view だけは見えない・管理者で staff.view なし、の 3 通りで測る（便1 の K1 と同じ形） |
| A9 | 弱い | 「`calendar_type` ごとの件数が同じ」は、移行が `calendar_type` に触らない（§3-2）ので、書いた通りなら自明に成り立つ。**測りたいのは「だれに見えるか」**で、`calendar_service.py:240-246` の見え方の条件（`calendar_type = 'shared' OR user_id = :me`）を 1 文字も変えていないこと。差分の確認に `git diff` で `:238-250` に変更が無いことを足す |
| A10 | × | S3 のとおり、いまの書き方は変更を測れない |
| A11 | ○ | 既存の点検（i18n・UI governance・Lint）で測れる。「部品は金型だけ」は、設計が新しい色の点を `schedule.css` に足す余地を残している（§4-1）ので、`schedule-month__dot`（`SchedulePageImpl.tsx:731` が使っている既存の点）を使い回す、と決めて書く |

### S5 トリガの関数・形の差の検査（§3-1・§3-2）

- §3-1 は「更新時刻の自動更新は、`calendar_events` と同じ形のトリガを足す（`tenant.py:2241` の手本）」。手本は関数 `set_updated_at_calendar_events()`（`tenant.py:2139`）を先に作る。新しい表用の関数 `set_updated_at_calendar_categories()` を、**ひな形と移行の両方**に書くと明記する。
- 設計の受入条件に、「会社のひな形と移行後の形の差が 0」を足す: `scripts/check_tenant_template_shape.py`（`:1-14` の流れ。ひな形で作った会社と、登録の移行を全部流した後の形を比べる）。表・制約（外部キー）・トリガ・関数が両方で同じ形になることが必要。

### S6 戻し方の一文が足りない（§3-2「戻し方」）

- 「コードの PR を戻すだけ」は正しい（外部キーと表は残る）が、戻すまでの間に管理者が足した `custom_N` の種類を持つ予定ができていると、古い画面は `CALENDAR_MAP[category]` が `undefined` になり（`SchedulePageImpl.tsx:223`・`:344`・`:736` は `meta &&` で守られている）札が出ないだけで壊れはしない。ただし、古い画面で開いて保存すると、選び方が空の `select` から 7 種の 1 つに変わりうる。戻すときの注意として 1 行書く。

### S7 §8 と §0 の「見え方は変えない」の言葉（観点 5）

- 「だれに見えるか」は変わらない: `calendar_type` の値は 2 つのまま（`tenant.py:1582`）、見え方の SQL（`calendar_service.py:240-246`）に触らない、作るときの共有の初期値は `personal` が `self`（＝今の `visibleToStaff: category !== "personal"`、`ScheduleDraftFields.tsx:288`）で同じ、直すときは共有を自動で変えない。これは設計どおりに作れば成り立つ。
- ただし「見た目」は変わる: 札が `Badge variant={meta.badgeVariant}`（青など。`SchedulePageImpl.tsx:344`）から `neutral` ＋色の点に変わる（§8 に書いてある）。§0 の表の「見え方: 変えない」は「だれに見えるか」の意味だと分かるように、「（見えるかどうかは変えない。札の見た目は §8）」と書き添える。PO の目視の確認項目に、札の見た目を明記する（§8 はすでに書いている）。
- 一点、実際に変わる動き: 設計どおりなら、いままで受け口に捨てられていた `category` が保存され始める（F2）。`personal` の種類で作った予定は、作るときの共有が `self` で入るため、画面の初期状態では「社員に見せない」が付く（今も同じ）。ただし、人が共有をあとから変えて「全員に見せる」にした予定の `category=personal` が、今後は DB に残る。見え方には効かない（種類は絞りに使われない）が、「分類 personal ＝ 見えない」と誤解されないよう、設計に 1 行書く。

### S8 その他の軽い点

- 受け口の道の名前: `GET/POST /calendar/categories`・`PATCH /calendar/categories/{key}` は既存の道（`/calendar/events`・`/calendar/owners`・`/calendar/holidays`・`/calendar/sync-mode`、`calendar.py:169-663`）と衝突しない。○。
- 移行の `calendar_categories` への 7 行の INSERT は、`scripts/migration-guard/protected-tables.txt`（保護対象は商品マスタ系 42 表で、`calendar` を含む行は無い。`grep -n calendar` が 0 件）に当たらない。ADR-155 は商品マスタ限定なので、チェック 7 は通る。○（確認済み。設計に一言書くと実装者が迷わない）。
- 登録 4 か所（手本 `20261119_120000` が書かれている所）は実物で次のとおり: `scripts/run_all_migrations.sh:1483`・`backend/tests/rls_bootstrap.py:188`（`_TENANT_LOOP_MIGRATIONS` の件数 1）・`backend/tests/test_calendar_sync_tenant_reset_pg.py:54`（True）・`backend/tests/test_tenant_loop_migration_guard.py:51`・`:70`（**2 つの一覧**）。設計は「登録 4 か所」と書くが、`test_tenant_loop_migration_guard.py` は 2 か所あるので合計 5 行。実装者への注記として「`git grep -n 20261119_120000_add_calendar_events_color_key -- backend/tests scripts` の全部（5 行）に倣う」と書く。新しい移行の置き場所は `run_all_migrations.sh:1483` の後（`20261121_100000`・`20261122_100000` はその後ろにあり、日付順は `20261126_100000` が最後）。
- 新しい移行のファイル名 `20261126_100000_create_calendar_categories.sql` は、いまの最新（`20261122_100000_add_tenants_meta_review_switch.sql`）より後で順序の矛盾は無い。○。
- ひな形側の `calendar_events` の `category` 列のコメント（`tenant.py:1577` 「作る SQL は登録に無い」）は、外部キーに替えるときに「登録の移行で外部キーが付く」へ直す（読み手が迷わない）。

## 5 観点ごとの結論

| 観点 | 結論 |
|---|---|
| (1) 事実 F1〜F11 | 食い違い 0。F3・F9 は本番の値で未確認。F5・F7・F10 は数え漏れ（R1・R2・R4・R7） |
| (2) 移行・外部キー・`tenant.py`・登録・AI 用ビュー分類表 | 抜けあり: 古い CHECK の名前（R5）、分類表の allow/mask・件数・sha256（R4）、トリガ関数（S5）、登録の行数（S8） |
| (3) 受け口・繰り返し・画面の種類選び・設定区画 | 設計どおり作ると壊れる所: 単発の直し（R1）・繰り返し 3 か所（R2）・`meeting` の無効化（R3）。`calendars.config` の使い先の全数は上の R7（`frontend/src` の取り込み 4 か所・実装の変更は 3 か所、別に古いメモ 1 行） |
| (4) 受入条件 A1〜A11 | A10 は測れない（×）、A2・A6・A9 は条件つき・弱い。ほかは○ |
| (5) 便2a で見え方が変わらないか | 「だれに見えるか」は変わらない（S7 の根拠）。札の見た目は変わる（設計 §8 に記載済み） |

## 6 次にすること

1. 設計担当（Opus）が R1〜R7 を design-bin2a.md に入れる（S1〜S8 は同時に入れてよい）。
2. 直したあとの再審査（第2回）では、R1〜R7 が §3-2・§3-4・§4-1・§5・A10 に入ったことを実物の行で照合する。
3. 実装カードに、R4 の件数（1169）と `reference-allowlist.tsv` の sha256 の更新を入れる。

判定: REVISE
