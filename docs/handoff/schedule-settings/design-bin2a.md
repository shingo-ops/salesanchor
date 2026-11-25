# 設計: 便2a 予定の種類を DB の表 1 つへ（色・共有の初期値）

- 状態: 設計案（Opus 作成・2026-11-25）。審査はクラウドで行い、末尾「審査」に記録する
- 親の設計: `docs/handoff/schedule-settings/design.md` §1・§6（便2 の骨組み）
- 要件: `docs/handoff/schedule-settings/requirements.md`（PO 2026-11-25「1」で承認）の G4・G6
- 関わる ADR: ADR-1081（予定の色 24 色・正本 `backend/app/services/event_colors.py`）／ADR-144（UI 金型）／ADR-067（デザイントークン）／ADR-027（i18n）／ADR-072（commit 後の reset_tenant_context）／ADR-1037（移行のロック待ち）／ADR-135・136（危険 PR の GO）

## 0 便2 を 2 つに分ける（設計判断）

便2 は「種類を表へ」と「チーム共有」を一度に入れると、見え方（だれに見えるか）の変更と表の作り直しが同じ PR に混ざる。見え方の変更は漏れると他人の予定が見えてしまうため、単独で試験・審査したい。

| 便 | 中身 | 見え方 |
|---|---|---|
| 便2a（この文書） | 種類の表・種類の保存の直し・種類を選ぶと色と共有（自分だけ／全員）が入る・設定ページで種類を管理 | 変えない |
| 便2b（別の文書） | 共有「チームを選ぶ」・予定とチームの対応表・見え方の条件 | 変える |

要件 G4 の「チームを選ぶ」は便2b で満たす。便2a の共有の初期値は `self` / `all` の 2 つ。

## 1 現在地（実物・2026-11-25 origin/main b4940fe2e）

| # | 事実 | 根拠 |
|---|---|---|
| F1 | 種類は 7 つで固定。DB の決まりと画面の表の 2 か所に書いてある | `backend/app/services/tenant.py:1579`（CHECK）・`frontend/src/features/schedule/calendars.config.ts:3-62` |
| F2 | 予定を作る・直す受け口の入力の形に `category` が無い。画面は `category` を送るが、受け口で捨てられる | `backend/app/routers/calendar.py:122-160`（CreateEventBody / UpdateEventBody に欄なし）・`frontend/src/pages/schedule/SchedulePageImpl.tsx:1006`（送っている） |
| F3 | そのため本番の予定 35 件はすべて種類が `meeting` | 読むだけの鍵で数えた（2026-11-25 14:31 JST）: 会社1 3 件・会社4 32 件、どれも `meeting` |
| F4 | 作る道は `payload.get("category", "meeting")` を入れる | `backend/app/services/calendar_service.py:423` |
| F5 | 直す道で変わった欄を拾う表 `_TEXT_FIELDS` に `category` が無い（読む列の表 `EVENT_COLUMNS` と繰り返しの写し `_row_values` には有る） | `backend/app/services/calendar_service.py:682`・`:742`・`:152`・`:973` |
| F6 | 画面で種類を選ぶと、作るときだけ「personal なら社員に見せない」に切り替わる | `frontend/src/pages/schedule/ScheduleDraftFields.tsx:284-290` |
| F7 | 種類の札の色は画面の表の `badgeVariant` で決まる。一覧では名前だけ出す | `frontend/src/pages/schedule/SchedulePageImpl.tsx:319`・`:344`・`:723-736` |
| F8 | 色の選び方の金型 `ColorSwatchPicker` があり、予定の色で使っている | `frontend/src/pages/schedule/ScheduleDraftFields.tsx:11`・`:330-345` |
| F9 | 本番 5 社（1・3・4・5・6）全部に `calendar_events` がある | 読むだけの鍵のビュー一覧 |
| F10 | 移行の手本と登録 4 か所は ADR-1081 便1 のカード | `docs/handoff/event-color/card-bin1.md` §4-2・§4-3 |
| F11 | 管理者の判定は `is_tenant_admin(await get_user_system_keys(db, user.id))` | `backend/app/routers/calendar.py:523` |

## 2 受入条件

| 基準 | 内容 | 検証方法 |
|---|---|---|
| A1 | 全社に種類の表があり、今の 7 種が入っている | 移行の試験（2 回流して同じ）＋本番で読むだけの鍵で 5 社 × 7 行 |
| A2 | 予定の `category` は種類の表にある鍵だけ入る（外部キー）。固定の CHECK は無くなる | 移行の試験（無い鍵の INSERT が失敗）＋本番で制約の一覧を読む |
| A3 | 予定を作る・直すときに選んだ種類が保存される | 裏側の試験（作る→読むで `shipping`・直す→`billing`）。本番は PO が予定を 1 件作り、一覧の種類の名前で目視 |
| A4 | 使わなくした種類・無い鍵で作ると 422 `invalid_category`。直すときに今の種類のままなら、使わなくした種類でも通る | 裏側の試験 |
| A5 | 管理者は種類を足す・名前を変える・色を決める・共有の初期値を決める・使わなくするができる。管理者でない人は 403 | 裏側の試験 |
| A6 | 種類を選ぶと、その種類の色（無ければ「デフォルト」）と共有の初期値が入る。あとで変えられる | 画面の試験＋本番で PO 目視 |
| A7 | 種類の選び方に出るのは使っている種類だけ。使わなくした種類の予定は名前がそのまま出る | 画面の試験 |
| A8 | 設定ページに「予定の種類」区画があり、管理者だけに見える | 画面の試験＋本番で PO 目視 |
| A9 | 今ある予定の見え方は変わらない（要件 G6） | 本番で移行の前後に `calendar_type` ごとの件数を読むだけの鍵で数え、同じ（会社1 personal 1・shared 2／会社4 personal 24・shared 8） |
| A10 | 種類の一覧の正本が 1 か所 | `git grep -n "'procurement'" -- backend/app frontend/src` が `tenant.py`（初期の 7 行）だけ。`calendars.config.ts` が無い |
| A11 | 新しい文字はすべて `t()`、ja/en 同じキー。部品は金型だけ | i18n 点検・UI governance gate・Lint & Dark Mode Check |

## 3 裏側の変更

### 3-1 表（新しい会社の形 `backend/app/services/tenant.py` と移行の両方）

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
- 色は NULL＝「種類の色なし（今どおりデフォルト）」。今の札の色から 24 色へ写す表を作らない（根拠の無い対応を作らないため）。
- 予定の表: `calendar_events_category_check` を外し、`calendar_events_category_fkey FOREIGN KEY (category) REFERENCES {schema}.calendar_categories(key)`（`ON UPDATE RESTRICT ON DELETE RESTRICT`）を `NOT VALID` で足して `VALIDATE` する。種類の行は消さない（使わなくするだけ）ので RESTRICT で足りる。
- `tenant.py` では `calendar_categories` の作成と 7 行を `calendar_events` より前に置き、`calendar_events` の CHECK の行を外部キーの行に置き換える。
- 更新時刻の自動更新は、`calendar_events` と同じ形のトリガを足す（`tenant.py:2241` の手本）。

### 3-2 移行（新規 `migrations/20261126_100000_create_calendar_categories.sql`）

- `^tenant_\d+$` の部屋ごとに、`calendar_events` が無い部屋は飛ばす（手本 `migrations/20261119_120000_add_calendar_events_color_key.sql`）。
- 順に: 表を作る → 7 行 → トリガ → 予定の外部キーを `NOT VALID` で足す → `VALIDATE` → 古い CHECK を外す。何度流しても同じ。
- 登録 4 か所と AI 用の写しの分類表（新しい表の欄を全部・件数の注記と試験の数）は、手本のカード `docs/handoff/event-color/card-bin1.md` §4-2・§4-3 と同じ形で足す。分類は、秘密の欄が無いので全部 `allow`。
- 戻し方: コードの PR を戻すだけ。表と外部キーは残す（古いコードは表を読まず、`category` は 7 種のどれかなので外部キーに当たらない）。消す移行は作らない。

### 3-3 正本の読み書き（新規 `backend/app/services/calendar_categories.py`）

- `list_categories(db) -> list[dict]`: `sort_order, key` の順で全行（使わなくした行も `is_active` 付きで返す）。
- `get_category(db, key) -> dict | None`
- `create_category(db, tenant_id, name, color_key, default_share) -> dict`: 鍵は `custom_` ＋ 今ある `custom_` の最大の数＋1。`sort_order` は最大＋1。
- `update_category(db, tenant_id, key, fields) -> dict | None`: `name`（7 種は空の文字で NULL に戻せる。`custom_` は空にできず 422）・`color_key`（空の文字で NULL）・`default_share`・`is_active`。
- 書いたあとは `await db.commit()` の直後に `await reset_tenant_context(db, tenant_id)`（ADR-072）。

### 3-4 受け口（`backend/app/routers/calendar.py`）

| 道 | だれ | 中身 |
|---|---|---|
| `GET /calendar/categories` | ログインした人 | 全行（`key, name, color_key, default_share, sort_order, is_active`） |
| `POST /calendar/categories` | 管理者（F11） | `{name(1〜50 字), color_key?, default_share}` → 201 で 1 行 |
| `PATCH /calendar/categories/{key}` | 管理者 | 上の欄の一部。無い鍵は 404 `not_found:calendar_category` |

- 消す道は作らない（A5 の「使わなくする」で足りる。外部キーで消せないため）。
- 色の値の確かめは既存の `_check_color_key`（`calendar.py:115`）を使う。共有の初期値は `self`/`all` 以外 422。
- 予定の作る・直す入力に `category: Optional[str] = None` を足す。
  - 作る: 指定が無ければ `meeting`。表に無い・使っていない鍵は 422 `invalid_category`（下の try の前で判定）。
  - 直す: 指定があり、今の種類と違うときだけ同じ判定。同じなら通す（A4）。
  - サービスの `_TEXT_FIELDS`（F5）に `category` を足し、繰り返しの 3 択（`_row_values`・`_merged`・`_update_single_to_recurring`）でも元の行の種類を引き継ぐ（今は `master["category"]` を使っている所はそのまま）。
- 種類を選んでも、裏側は色と共有を自動で書き換えない（初期値を入れるのは画面。送られた値をそのまま保存する）。

## 4 画面の変更

### 4-1 種類の正本を画面から消す

- `frontend/src/features/schedule/calendars.config.ts` と `calendars.config.test.ts` を消す。`CalendarId` は `string` にする。
- 新規 `frontend/src/features/schedule/useCalendarCategories.ts`: react-query で `GET /calendar/categories`（鍵 `["calendar", "categories"]`）。名前を出す関数 `categoryLabel(cat, t)` = `cat.name ?? t(\`schedule.calendarLabels.${cat.key}\`)`。
- 予定の札（`SchedulePageImpl.tsx:319`・`:344`）と一覧の名前（`:723-736`）: `Badge variant="neutral"` に種類の名前。種類に色があれば、名前の前に色の点（`eventColorVar(color_key)` を背景にした既存の点の部品。無ければ `schedule.css` に CSS 変数だけで足す）。表に無い鍵（読み込み前など）は鍵の i18n 名で出す。

### 4-2 種類を選ぶと初期値が入る（`ScheduleDraftFields.tsx` の `DraftCategoryField`）

- 選び方の中身は、使っている種類（`is_active`）の `sort_order` 順。今の予定の種類が使わなくした種類なら、それも 1 つ足す（A7）。
- 変えたとき: `colorKey = cat.color_key`（NULL ならデフォルト）。作るとき（`mode === "create"`）は `visibleToStaff = cat.default_share === "all"`（今の F6 の条件の置き換え）。直すときは今どおり共有を自動で変えない（持ち主でない人は変えられないため・`SchedulePageImpl.tsx:1068`）。
- 新しい予定の初期値（`SchedulePageImpl.tsx:954`・`:1203`）: 種類 `meeting`（使っていなければ並びの最初の種類）と、その種類の色・共有の初期値。
- 作る・直す送り先の本文に `category` を入れる（作るは `:1006` で既に入れている。直すは変わったときだけ入れる）。

### 4-3 設定ページの「予定の種類」区画（`ScheduleSettingsPage.tsx`）

- 管理者だけに出す（便1 の Google 区画と同じ条件 `isTenantAdmin === true`）。左の並び（金型 SubMenu）に 1 項目足す。
- 金型 `SectionCard` の中に、種類ごとに 1 行: 名前（金型 TextField）・色（金型 `ColorSwatchPicker`、先頭に「種類の色なし」）・共有の初期値（金型 Select: 自分だけ／全員）・使う（金型 Toggle）・保存（金型 Button）。7 種の名前の欄は空にでき、空なら i18n の名前に戻ると下に書く。
- 下に「種類を足す」（金型 Button）。押すと空の行が出て、名前を入れて保存で作る。
- 保存の成功・失敗は便1 と同じ帯の部品で出す。失敗の文は「起きたこと＋次にすること」（ADR-1071）。

### 4-4 新しい文字（ja/en 同じキー・`schedule` の中）

区画の見出し・説明・各欄の名前・「種類の色なし」・自分だけ／全員・使う・保存・足す・成功・失敗・空の名前の説明。実装担当が使う分だけ足し、使わないキーは足さない。

## 5 試験

- 裏側: 種類の受け口（一覧・足す・直す・403・404・422）、予定の作る・直すの種類（保存・`invalid_category`・使わなくした種類のまま直す）、繰り返しの直すで種類が引き継がれる、移行（2 回流して同じ・7 行・外部キー・古い CHECK が無い・無い鍵の INSERT が失敗）、分類表の件数。
- 画面: 種類を選ぶと色と共有が入る（作る）・直すでは共有が変わらない・使わなくした種類が選び方に出ない／今の予定の種類なら出る・設定の区画が管理者だけ・足す・保存の失敗の文。
- 既存の試験で `calendars.config` を使うものは、表の取り込みの擬似の値に置き換える。

## 6 触らない

- 見え方の条件（`calendar_service.py:241-246`）・`calendar_type` の値・作る／直す／消すの権限の判定。便2b で扱う。
- Google への色の送り（ADR-1081）。種類の色は予定の `color_key` に入るので、今の送り方がそのまま効く。
- Google からの取り込み（`upsert_from_google`）。種類は欄の既定値 `meeting` のまま。
- 秘書（`assistant.py`）の予定作成。種類は既定の `meeting`。
- `calendar_owner_settings` と人ごとの色。便3 で扱う。

## 7 代替案

| 案 | 採らない理由 |
|---|---|
| 画面の固定表に色と共有を足す | 種類を足す・名前を変える（要件）ができない。会社ごとに変えられない |
| 種類の表に数の id を主キーにする | 予定の `category` は今文字の鍵。鍵を主キーにすれば予定の表を書き直さずに外部キーで結べる |
| 今の札の色を 24 色へ写して初期の色にする | 写し方に根拠が無い。初期は「色なし」で今の見た目の予定の色を変えない |
| 便2 を 1 つの PR で出す | §0 のとおり見え方の変更を単独で試験・審査するため分ける |

## 8 危うさと手当て

| 危うさ | 手当て |
|---|---|
| 外部キーを足すときに、表に無い種類の予定があると失敗する | 本番は 35 件すべて `meeting`（F3）。移行は 7 行を先に入れてから足す。さらに `NOT VALID`→`VALIDATE` で長いロックを避ける（ADR-1037） |
| 札の色が種類ごとの色から灰色＋色の点に変わる | 本番の予定は全部「会議」なので、今見えている札は青の「会議」1 種だけ。PO に目視で確かめてもらう（A6 と同じ時） |
| 種類の保存の直しで、今まで送っても捨てられていた値が入り始める | 直しそのものが目的（F2）。既存の予定は変わらない |

## 9 外部・過去事例

- Google カレンダーは「カレンダー」ごとに色と共有を持ち、予定を作るときに選んだカレンダーの色と共有が入る（support.google.com/calendar の「カレンダーを作成する」「共有する」。日付は未確認）。今回の「種類を選ぶと色と共有の初期値が入る」の形の参考。数値の根拠には使わない。

## 10 維持の仕組み

- 種類の一覧の正本は種類の表 1 つ。A10 の `git grep` を審査役の確かめに入れる。
- 外部キーで、表に無い種類は DB が止める。
- 守り手: CI（pytest・vitest・i18n 点検・UI governance gate・Lint & Dark Mode Check・移行の試験）。設計の持ち主は Opus（設計担当）。

## 11 審査

（クラウドの審査の結果をここに書く）
