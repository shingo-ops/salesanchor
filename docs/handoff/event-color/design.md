# 設計 — 予定ごとの色（Google と同じ 24 色＋デフォルト）

状態: 設計案（審査 2 回目 APPROVE（軽 3 件を直した版））。目標 K1〜K7 は PO 承認済み（2026-11-19 チャットで「1」）。実装の承認と本番の GO は兼ねない。基準: `origin/main` fba2172b8。便2 の前に §4-7〜§4-9 を origin/main 5db804b78 の実物で確かめ直し、§4-8（色の一覧を `Popover` で出さない）と §4-9 の足した点を直した（2026-11-20）。
現状: [recon.md](recon.md)（`docs/handoff/event-color/recon.md`）。決まりの記録: `docs/adr/ADR-1081-event-color-labels.md`（Proposed）。
関係: ADR-1057・ADR-1059（Google との行き来）・ADR-1065・ADR-1074（予定の画面の金型と `--gcal-*`）・ADR-1075（繰り返し）・ADR-067・ADR-144・ADR-027。

## 1. 目的と PO の決定

- 予定の 1 件ずつに色を付けられるようにする。Google カレンダーと同じ 24 色と「デフォルト」から選ぶ。
- PO の決定: 2026-11-19「予定ごとの色」・「1. Google と同じ24色にする【おすすめ】」・目標 K1〜K7 に「1」。

## 2. 目標（PO 承認済み）と確かめ方

| 基準 | 検証方法 |
|------|---------|
| K1 作成と編集の画面で、24 色＋デフォルトの 25 個から 1 つ選べる | 画面の試験で選択肢が 25 個。本番で PO が目で見る |
| K2 選んだ色が、週と月の画面の予定の箱に出る | 画面の試験で箱に色のトークンが付く。本番で PO が目で見る |
| K3 アプリで付けた色が、Google でも同じ色で出る | 裏側の試験で `eventLabelId` と `eventLabelVersion=1` を送る。本番で 1 件付けて Google の画面を見る |
| K4 Google で付けた色が、次に開いたときアプリに出る | 裏側の試験で取り込みが `color_key` を書く。本番で Google で作った予定に色を付けて見る |
| K5 繰り返しの予定の色を変えると「この予定だけ／これ以降／すべて」の 3 択が出る | 裏側の試験で 3 択それぞれの行の色。画面の試験で 3 択の窓が出る |
| K6 色を付けていない予定は今と同じ持ち主の色 | 画面の試験で色なしの箱は持ち主の色のまま |
| K7 色はデザイントークンに登録し、色の値を直に書かない | 見張りの試験（`--gcal-` の場所・トークンと裏側の値の一致）が通る |

K4 の範囲（§5-4）: Google で作った予定が対象。アプリで作った予定を Google で直したときは、今はどの欄もアプリに戻らない（recon.md §3）。色もそれに合わせる。広げるかは PO に聞く。

## 3. 対象と対象外

- 対象: 予定の表に色の欄 1 つ・受け口・一覧の返し・繰り返しの 3 択・Google への書き込みと取り込み・色を選ぶ部品（新しい金型）・色のトークン・AI 用の写しの分類表。
- 対象外:
  - Google 側に名札を新しく作る・名を付ける・消すこと。
  - 古いやり方の `colorId` を書くこと。
  - 持ち主の色の仕組み（`calendar_owner_settings.color`）。
  - スマホ幅の予定の画面（Android 側の担当）。
  - 暗い画面専用の色の値（Google の暗い画面の値を測っていないため。v1 は明るい画面と同じ値）。

## 4. 変更の中身（ファイルごとの前と後）

### 4-1. 色の一覧の正本（新規 backend/app/services/event_colors.py）

- 前: 無い。
- 後: 24 色の鍵と Google の色の値は、このファイル 1 か所だけに書く。鍵は Google の英語の名を小文字にしたもの。

```python
# 予定の色（ADR-1081）。Google カレンダーの予定のラベル 24 色と同じ並び・同じ値。
EVENT_COLORS: dict[str, str] = {
    "radicchio": "#ad1457", "cherry_blossom": "#d81b60", "flamingo": "#e67c73",
    "tomato": "#d50000", "tangerine": "#f4511e", "pumpkin": "#ef6c00",
    "mango": "#f09300", "banana": "#f6bf26", "citron": "#e4c441",
    "avocado": "#c0ca33", "pistachio": "#7cb342", "basil": "#0b8043",
    "sage": "#33b679", "eucalyptus": "#009688", "peacock": "#039be5",
    "cobalt": "#4285f4", "lavender": "#7986cb", "blueberry": "#3f51b5",
    "wisteria": "#b39ddb", "amethyst": "#9e69af", "grape": "#8e24aa",
    "cocoa": "#795548", "graphite": "#616161", "birch": "#a79b8e",
}
EVENT_COLOR_KEYS: tuple[str, ...] = tuple(EVENT_COLORS)

def key_for_hex(hex_value: str | None) -> str | None:
    """Google の色の値（大文字小文字を問わない）から鍵を返す。無ければ None。"""
```

| 鍵 | 画面の名（ja） | 画面の名（en） | 値 |
|----|---------------|---------------|----|
| radicchio | ワイン | Radicchio | #ad1457 |
| cherry_blossom | ローズ | Cherry Blossom | #d81b60 |
| flamingo | フラミンゴ | Flamingo | #e67c73 |
| tomato | トマト | Tomato | #d50000 |
| tangerine | ミカン | Tangerine | #f4511e |
| pumpkin | パンプキン | Pumpkin | #ef6c00 |
| mango | マンゴー | Mango | #f09300 |
| banana | バナナ | Banana | #f6bf26 |
| citron | レモン | Citron | #e4c441 |
| avocado | アボカド | Avocado | #c0ca33 |
| pistachio | ピスタチオ | Pistachio | #7cb342 |
| basil | バジル | Basil | #0b8043 |
| sage | セージ | Sage | #33b679 |
| eucalyptus | ユーカリ | Eucalyptus | #009688 |
| peacock | ピーコック | Peacock | #039be5 |
| cobalt | コバルト | Cobalt | #4285f4 |
| lavender | ラベンダー | Lavender | #7986cb |
| blueberry | ブルーベリー | Blueberry | #3f51b5 |
| wisteria | ライラック | Wisteria | #b39ddb |
| amethyst | アメジスト | Amethyst | #9e69af |
| grape | グレープ | Grape | #8e24aa |
| cocoa | ココア | Cocoa | #795548 |
| graphite | グラファイト | Graphite | #616161 |
| birch | シラカバ | Birch | #a79b8e |
| （NULL） | デフォルト | Default | 持ち主の色 |

名と値は Google の画面で 2026-11-19 に読んだもの（recon.md §5）。

### 4-2. 保存の場所（新しい移行 1 本・各社の `calendar_events` に欄 1 つ）

- 前: 色の欄は無い。
- 後: `color_key text NULL`。NULL はデフォルト（持ち主の色）。値の決まり `calendar_events_color_key_check CHECK (color_key IN (<24 の鍵>))`。
- 新しい移行 migrations/<実装時の日時>_add_calendar_events_color_key.sql。手本は `migrations/20261112_170000_add_calendar_events_recurrence.sql`:
  - `^tenant_\d+$` の部屋を DO で回し、`calendar_events` がある部屋だけ `ADD COLUMN IF NOT EXISTS color_key text`。
  - 値の決まりは `pg_constraint` に無いときだけ `NOT VALID` で足し、続けて `VALIDATE CONSTRAINT`（今は全行 NULL なので速い）。
  - 何度流しても同じ結果（冪等）。消す・書き換える操作は無い。
- 新しい会社の表の形 `backend/app/services/tenant.py:1549` に `color_key text` と値の決まりを足す（`:1575` の書き方）。
- 登録: `scripts/run_all_migrations.sh` の繰り返しの移行（`:1453`）の後・`backend/tests/rls_bootstrap.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`（移行の一覧と、欄と値の決まりができる試験）・`backend/tests/test_tenant_loop_migration_guard.py`。
- 戻し方: 欄は NULL を許すので、古い版のコードは欄を読まずに動く。消す移行は作らない（使わない欄が残るだけ）。

### 4-3. AI 用の写しの分類表（`migrations/20261024_100300_create_ai_cloud_views.sql`）

- `calendar_events` の行（`:371`〜`:375`）に 1 行足す:
  `('tenant_*','calendar_events',ARRAY['color_key'],'allow','値の決まり calendar_events_color_key_check で値が限られる'),`
- 先頭の件数の注記（`:3` の「1163 行」）を 1164 行に直す。
- 件数の試験 `backend/tests/ops/test_ai_cloud_views.py:486` の `== 1163` を `== 1164` に直す。
- 分類表の写し `docs/handoff/cloud-case-ai/stage1-column-class.tsv` の `calendar_events` の行（`:562`〜`:572`）に、同じ並びで `color_key` の行（allow・text）を 1 行足す。
- `backend/tests/ops/test_ai_cloud_views.py` に `test_t10_calendar_color_key_is_classified_on_bootstrapped_db` を足す（`:587` の型）。
- 3 か所を同時に直す手本は f0df9074a（meet_url の行を足したとき。SQL・件数の試験・tsv の 3 つ）。

### 4-4. Google の道具（`backend/app/services/google_calendar.py`）

1. 新しい関数 `async def get_event_label_colors(db, tenant_id, calendar_id: str) -> Optional[dict[str, str]]`:
   - `service.calendars().get(calendarId=calendar_id)` を 1 回呼ぶ。どのカレンダーを読むかは呼び元が渡す。
   - 書き込み（`create_event`・`update_event`）は、今その中で使っているカレンダー（会社の設定の `calendar_id`・無ければ `primary`）を渡す。
   - 取り込み（`backend/app/services/google_webhook.py:300` は `calendarId="primary"` 固定で読む）は `"primary"` を渡す。読む予定と同じカレンダーの名札の表を使うため。
   - `labelProperties.eventLabels` を「名札の id → 色の値（小文字）」の表にして返す。
   - 名札が無ければ空の表。呼べなかったら `None`（ログに 1 行・例外は外へ出さない）。
2. `create_event`・`update_event` の本文に内部の印 `_sa_color_key` があるとき:
   - 印を本文から取り除く（Google へは送らない）。
   - 鍵 → `EVENT_COLORS` の値 → 名札の表で同じ値の名札の id を探す。
   - 本文に `eventLabelId` を入れる（鍵が NULL か、合う名札が無ければ `""`）。
   - 呼び出しに `eventLabelVersion=1` を足す（`conferenceDataVersion` と同じ足し方）。
   - 合う名札が無いときはログ `event_label_missing color_key=<鍵>` を 1 行。名札は作らない。
   - 名札の表が `None` のときは `eventLabelVersion` も `eventLabelId` も付けない（今の Google の色を消さない）。
3. 印が無い本文は今と同じ（版の指定を付けない）。
4. 新しい試験: 道具の部品に入っている API 説明で `events.insert`・`events.patch` が `eventLabelVersion` を受けることを確かめる（U1）。受けなければ試験が落ち、`backend/requirements.txt:43` の下限を上げる話になる。

### 4-5. 予定の流れ（`backend/app/services/calendar_service.py`）

`location` の通り道（recon.md §3）に `color_key` を同じように通す。

- 前提: 受け口が `""` を `None` に直してから渡す（§4-6）。この層に `""` は来ない。`color_key` の鍵がある＝色を決めた（`None` はデフォルト）、鍵が無い＝色に触らない。
- `EVENT_COLUMNS`（`:151`）に `"color_key"`。
- 一覧の SELECT（`:251`〜）の最後に `ce.color_key` を足し、返し（`:279` 付近）に `"color_key": r[<その位置>]`（審査の数えでは `r[22]`。実装時に数え直す）。
- 作成の INSERT（`:402`〜`:418`）に `color_key`（`payload.get("color_key")`）。
- 更新の欄の表 `field_map`（`:490`〜`:499`）に `"color_key": "color_key"`。
- `_TEXT_FIELDS`（`:661`）・`:1030`・`:1188` の並びに `"color_key"`。`_row_values`（`:948`〜）・`:1098` にも足す。
- `_insert_row`（`:925`〜`:944`）の INSERT の欄と値の並びに `color_key` / `:color_key` を足す。これが無いと「この予定だけ」で作る例外の回と「これ以降」で作る新しい予定（`:1092`）に色が入らない。
- これで K5 の 3 択が色でも動く。`_plan`（`:720`〜`:722`）は `None` 同士を同じと見るので、色を変えていない保存で色が「直した欄」に入らない。
- Google に色を送る決まり（Google の色を勝手に外さないため・§6）:
  - 予定を直す道（`patch`）: 今回の保存で色が変わったときだけ送る。
  - 予定を作る道（`insert`・消して作り直す道）: 色が NULL でないときだけ送る。
  - 送らないときは本文に印を入れない＝版の指定が付かない＝Google の名札はそのまま。
- Google の本文:
  - `_to_google_event_body(payload, send_color: bool = False)`（`:1446`）: `send_color` が真のときだけ本文に `_sa_color_key`（鍵か None）を入れる。
  - `_google_body_for(ev, send_color: bool = False)`（`:169`）: 表の 1 行の `color_key` を使い、`send_color` をそのまま渡す。
- 呼び元ごとの `send_color`:
  - 作成 `:436`: `payload.get("color_key") is not None`。
  - 更新 `update_event`（`:480`）: UPDATE の前に `SELECT color_key FROM calendar_events WHERE id = :id` で今の値を読み、`"color_key" in payload and payload["color_key"] != 今の値` を `send_color` にして `:539` に渡す。
  - 繰り返しで直す道 `:1062`・`:1138`: `"color_key" in plan["changed_fields"]`（`:1025` の `fields`）。
    - ただし「この予定だけ」で、すでにある例外の行を `_find_exception` で見つけて直すとき（`:1030`〜`:1062`）は、`changed_fields` ではなく、直す前のその例外の行の `color_key` と `payload["color_key"]` を比べて決める（`"color_key" in payload and payload["color_key"] != 例外の行の color_key`）。元の行と比べると、例外の行の色を元の行と同じ色に戻したときに Google へ送られないため。
  - 繰り返しで作る道 `:1121`・`:1177`・`:1200`（`_recreate_in_google` は消して `create_event` で作る・`:978`）: 渡す行の `color_key is not None`。
- Google からの取り込み `upsert_from_google`（`:1342`）:
  - 引数 `label_colors: Optional[dict[str, str]] = None` を足す。
  - 表があるとき: `eventLabelId` → 色の値 → `key_for_hex` で鍵を出し、INSERT と `DO UPDATE SET` に `color_key` を足す。合わない値は NULL。
  - 表が `None` のとき: `color_key` に触らない（今ある色を消さない）。
  - `colorId` だけの予定は NULL のまま。数は `backend/app/services/google_webhook.py` の取り込みの繰り返し（`:330`〜`:332`）で数え、繰り返しの後にログ `event_color_legacy_colorid count=<数>` で 1 回出す（`upsert_from_google` は 1 件ずつ呼ばれるので、その中では数えない）。
- 取り込みの呼び元 `backend/app/services/google_webhook.py:332` の手前（`events().list` の前後どちらでもよい・1 回の取り込みに 1 回）で、`get_event_label_colors(db, tenant_id, "primary")` を呼び、表を渡す。

### 4-6. 受け口（`backend/app/routers/calendar.py`）

- `CreateEventBody`（`:114`）・`UpdateEventBody`（`:126`）に `color_key: Optional[str] = None`。
- 受けてよい値は 24 の鍵と `""`（デフォルトに戻す）。それ以外は 422。値の一覧は `EVENT_COLOR_KEYS` から取る（書き写さない）。
- `""` を使うのは、`model_dump(exclude_none=True)`（`:440`・`:465`）で `None` が落ちるため。
- `:440`・`:465` の `model_dump` の直後で、`payload.get("color_key") == ""` なら `payload["color_key"] = None` に直してから次へ渡す（鍵は残す）。
  これで作成・更新・繰り返しの 3 択のどの道にも `""` が届かず、DB の値の決まりに当たらない。

### 4-7. 色のトークン（`frontend/src/tokens.css`）

- `tokens.css` の `:root` に `--event-color-<鍵>: <値>;` を 24 個（値は Google の色・`EVENT_COLORS` と同じ）。部品と画面はこれだけを使う。
  v1 は暗い画面も同じ値なので、暗い画面の区画には足さない。
  `.gcal-colors` の範囲の中には置かない。予定の画面の外（部品の見本 stories など）でも色が出るようにするため。
- `index.css` には足さない（`--gcal-event-*` は作らない）。
  - 2026-11-20 の直し（初版は `index.css` に `--gcal-event-*` を 48 行置き、`tokens.css` から `var()` で引く 2 段だった）。
  - 理由: 色の直書きの数の見張り `scripts/check-design-token-ratchet.sh` は `frontend/src/tokens.css` を数えず、`frontend/src/index.css` は数える（`:62`〜`:64`）。
    `index.css` の例外は Google の画面の色 13 個だけで、足すには PO の承認が要る（`:15`〜`:19`）。初版の形では 171→219 で赤になった（PR の確かめ guard-hex-increase）。
  - `tokens.css` は色の直書きの検査 `frontend/scripts/check-css-hardcoded-colors.js:20` でも定義ファイルとして除かれている。既に `--color-success: #15803d;` などの前例がある（`frontend/src/tokens.css:640`）。
  - 値を置く場所は 1 か所のまま（画面側は `tokens.css` だけ・裏側の正本は backend/app/services/event_colors.py・両者の一致は下の試験が照らす）。
- 裏側の試験 backend/tests/test_event_colors_tokens.py（新規）:
  - `frontend/src/tokens.css` の `--event-color-<鍵>` 24 個が `EVENT_COLORS` と鍵・値とも一致すること（鍵の `_` はトークンでは `-`）。
  - `frontend/src/index.css` に `--gcal-event-` も `--event-color-` も無いこと（置き場所が 2 つに割れるのを防ぐ）。
  - frontend/src/pages/schedule/eventColors.ts の鍵の並びが `EVENT_COLOR_KEYS` と一致すること。
  - 画面の文字（ja・en）に 24 色＋デフォルトの名があること。
  - 画面のファイルを裏側の試験で読む手本は `backend/tests/seed_data.py:22`。

### 4-8. 色を選ぶ部品（新しい金型 frontend/src/components/ColorSwatchPicker.tsx）

- ADR-144 の金型。.tsx・.css・.stories.tsx・.test.tsx の 4 つ。
- 中身（便2 の前の調べで直した版。直した理由は下の「`Popover` を使わない理由」）:
  - 欄には「今の色の丸＋色の名」のボタン（金型 `Button` の `ghost`）を出す。押すと、その下に色の丸の一覧を開く・もう一度押すと閉じる。
  - 一覧は `Popover` を使わず、部品の中にそのまま出す（体の外へ移さない）。
  - 一覧は `role="radiogroup"`。丸 1 つは `<label>` で、中に金型 `RadioControl`（見えなくして丸全体に広げる）を入れる。
    `docs/CC_UI_GOVERNANCE.md` の「色見本など単独の欄は `RadioControl`」に合わせる。手本は `frontend/src/pages/roles/RolesPage.tsx:497`〜`:528` と `frontend/src/pages-layout.css:271`〜`:315`。
  - 本物のラジオなので、矢印キーで選べる・選んだ丸は `checked`・読み上げは丸ごとの色の名（`aria-label`）。
  - 丸の地は `style={{ background: <色のトークンの文字> }}`。文字は `var(--event-color-<鍵>)` か持ち主の色。色の値は部品に書かない。
  - 部品は予定のことを知らない。選択肢の一覧（値・名の文・色）と今の値と `onChange` を受けるだけ。
  - 「デフォルト」の丸は、渡された色（持ち主の色）で描く。
  - 部品の見た目は部品の CSS（`comp-color-swatch-picker*`）に持つ。`pages-layout.css` の `.color-swatch` は使い回さない（ページの CSS に頼る金型にしない）。
- CSS の色・余白・角の丸みはトークンだけを使う（ADR-067）。
- `Popover` を使わない理由（origin/main 5db804b78 の実物で確かめた事実）:
  - `Popover` は一覧を体の直下へ移し、重なりの順 `var(--z-dropdown)`（`frontend/src/components/Popover.css:201`）で出す。
    予定を作る窓と全体の編集の画面は `var(--z-modal)`（`frontend/src/pages/schedule.css:344`・`frontend/src/components/EditorPage.css:10`）で、こちらが上。一覧が窓の下に隠れる。
  - 予定を作る窓は、窓の外を押すと閉じる（`frontend/src/pages/schedule/SchedulePageImpl.tsx:297`〜`:309`）。体の直下へ移した一覧を押すと「窓の外」と見なされ、色を選ぶ前に窓が閉じる。
  - 全体の編集の画面は中にだけ移る動き（`frontend/src/components/EditorPage.tsx:81` の `useFocusTrap`）を持つので、外に移した一覧へはキーボードで行けない。
- 予定の色の一覧（新規 frontend/src/pages/schedule/eventColors.ts）: 24 の鍵の並びと、名の文の鍵 `schedule.eventColors.<鍵>`、トークン名を返す関数。色の値は書かない。
- 画面の文字: `frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に `schedule.eventColor`（欄の名）・`schedule.eventColors.default` と 24 色の名を足す（表は §4-1）。

### 4-9. 予定の画面（`frontend/src/pages/schedule/`）

- 下書きに `colorKey: EventColorKey | null` を足す:
  - `frontend/src/pages/schedule/SchedulePageImpl.tsx:99`・`:156`・`:974`・`:1210`
  - `frontend/src/pages/schedule/schedule-utils.ts:21`・`:66`・`:372`
- 保存の中身（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1019`）にいつも `color_key: draft.colorKey ?? ""` を入れる。
  裏側は「色が変わったときだけ Google に送る」（§4-5）ので、色に触らない保存で Google の色は外れない（§6）。
- `frontend/src/pages/schedule/ScheduleDraftFields.tsx` に `DraftColorField` を足す。`ColorSwatchPicker` を使う。
  - 置き場所は `DraftCategoryField` の直後。小さな窓（`frontend/src/pages/schedule/ScheduleDraftFields.tsx:508`）と全体の編集の画面（`frontend/src/pages/schedule/ScheduleFullEditor.tsx:88`）の両方。
- 予定の箱の色（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1272`）:
  - 前: `color: getOwnerMeta(...).color`
  - 後: `color: item.colorKey ? eventColorVar(item.colorKey) : getOwnerMeta(...).color`
  - `eventColorVar` は `var(--event-color-<鍵>)` を返す。`frontend/src/components/CalendarView.tsx:338` がそのまま CSS の値として付ける。
  - 色なしは今と同じ（K6）。
- 便2 の前の調べで足した点（origin/main 5db804b78）:
  - 予定の色を決める場所を 1 つにする。`frontend/src/pages/schedule/eventColors.ts` に `eventDisplayColor(colorKey, ownerColor)` を置き（中身は上の「後」の式・置き場所は実装カード card-bin2.md と同じ）、
    `frontend/src/pages/schedule/SchedulePageImpl.tsx` の箱（`:1272`）・日ごとの一覧の丸（`:653`）・予定の一覧の丸（`:721`）の 3 か所はこれを通す。箱だけ色が変わり一覧の丸が持ち主の色のまま、を防ぐ。
  - 作っている途中の仮の箱（`:1260`〜`:1262`）も `draft.colorKey` を通す。依存の並び（`:1277`〜`:1281`）に `draft.colorKey` を足す。
  - 「デフォルト」の丸に渡す持ち主の色: 直すときは `getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId).color`、作るときは `currentOwnerUserId` の色（どちらも `getOwnerMeta` から取り、色を書き写さない）。
  - 動かす・長さを変える保存（`patchMoved`・`:1284`〜）は `color_key` を送らない（送らなければ「変えない」・§4-6）。
  - 繰り返しの予定で色だけ変えたときは 3 択をすべて出す。`scopeChoices`（`frontend/src/pages/schedule/schedule-utils.ts:532`〜`:536`）の「繰り返しの形が変わった」の印に色を入れない。
  - 欄の印の絵は `SCHEDULE_POPOVER_ICONS`（`frontend/src/constants/icons.tsx:372`）に `color`（heroicons の `SwatchIcon`・2.2.0 に在る）を 1 つ足す。
  - 窓が開いている間の Esc は今のまま窓ごと閉じる（`frontend/src/pages/schedule/SchedulePageImpl.tsx:1336`〜`:1342`）。色の一覧だけを閉じる Esc は作らない。

### 4-10. 触らない範囲

- `calendar_owner_settings` と持ち主の色の設定画面。
- `CalendarView.css` の箱の描き方（`:146`〜`:150`）。
- Google の名札の作成・変更（`calendars.patch`）。
- `get_events`（`backend/app/services/google_calendar.py:349`）の呼び方。
- スマホ幅の予定の画面。

## 5. 代わりの案と選んだ理由

1. Google の古い 11 色（`colorId`）を使う → 選ばない。Google の今の画面は 24 色の名札で、11 色と合わない。名札を使う版では `colorId` は無視される。
2. 名札の id を DB に持つ → 選ばない。id は UUID で、カレンダーごとに違うかが【未確認】（recon.md U4）。色の値で照らせば、どのカレンダーでも同じ鍵になる。
3. 色の値（`#ad1457`）を DB に持つ → 選ばない。決まった 24 個以外が入り、トークンを通さない色の直書きになる（K7）。鍵なら値の決まりで 24 個に限れる。
4. 名札が無いカレンダーにはアプリが名札を作る → 選ばない。相手のカレンダーの設定を書き換える。PO の承認の範囲の外。
5. 自由な色を選べるようにする → 選ばない。PO の決定は Google と同じ 24 色。

### 5-4. K4 の範囲

- 今の取り込みは、アプリで作った予定を Google から読まない（無限の往復を防ぐ・recon.md §3）。
- 色だけ読むようにすると、その決まり（ADR-1059）を変えることになる。v1 は今の決まりのまま、Google で作った予定だけを K4 の対象にする。
- 広げるかは PO が決める。

## 6. 危ない点と手当て（弊害）

| 危ない点 | 手当て |
|---------|-------|
| `eventLabelVersion=1` で `eventLabelId` を送らないと、Google の色が外れる | 版の指定は、本文に色の印があるときだけ付ける。印は「直す道では色が変わったとき」「作る道では色があるとき」だけ入れる（§4-5） |
| 配備の前に取り込んだ Google の予定は、Google に色があってもアプリでは NULL（取り込みは差分だけ読む・`backend/app/services/google_webhook.py:300`〜`:314`） | 色に触らない保存では Google に色を送らないので、Google の色は残る。アプリの箱は Google で次にその予定が直されるまで持ち主の色。全件の読み直しは v1 ではしない |
| 上の予定を、Google で消して作り直す道（繰り返しの「これ以降」で分ける・D2・D3・単発を繰り返しにする道 A）で直すと、新しい予定に Google の色が付かない（今のコードでも同じ動きで、悪化ではない） | アプリが知らない色は運べない。v1 の限り。色を選び直せば付く |
| 名札の表が読めない（Google の不調） | 版の指定を付けない（Google の色に触らない）。取り込みでは色の欄に触らない |
| カレンダーにその色の名札が無い | Google には色なしで送る。アプリには色が残る。ログに出して数える |
| `colorId` だけの古い予定 | 色なしで取り込む。ログに数を出す |
| 道具の部品の版が古く `eventLabelVersion` を受けない | 試験で落とす（§4-4 の 4） |
| Google を 1 回多く呼ぶ（`calendars.get`） | 書き込み 1 件と取り込み 1 回に 1 回だけ。読み取りなので費用は増えない |
| 明るい色（バナナ等）の上の白い文字が読みにくい | 今の持ち主の色と同じ描き方。直すのは別の話として数えておく |
| 移行で全社の表に欄を足す | 欄の追加と値の決まりだけ。ロック待ちの上限の決まり（ADR-1037）に従う |

## 7. 古い版と新しい版が混ざる間

- 移行が先に入り、古いコードが動く間: 欄は NULL のまま。何も変わらない。
- 新しいコードは欄があることが前提。移行とコードは同じ便で、移行が先に流れる（今の配備の順）。

## 8. 進め方（2 便）

- 便1（裏側）: §4-1〜§4-6。`migrations/` を含むので危険な PR（CLAUDE.md の「危険PRのGO手順」・ADR-136）。PO 本人の「GO #番号」が要る。
- 便2（画面）: §4-7〜§4-9。§4-7 のトークンと裏側の値の一致の試験も便2 に入れる（`index.css` と eventColors.ts は便2 で足すため、便1 に入れると落ちる）。便1 の本番反映の後。
- 1 つの PR にまとめない（変更は一度に 1 つ）。

## 9. 受け入れの条件と確かめ方

| 基準 | 検証方法 |
|------|---------|
| 移行が冪等で、全社の `calendar_events` に `color_key` と値の決まりができる | `backend/tests/test_calendar_sync_tenant_reset_pg.py` に足す試験。2 回流して同じ |
| 24 の鍵以外は DB が拒む | 同じ試験で `'red'` を入れて値の決まりの違反になる |
| 受け口が 24 の鍵と `""` だけを受ける | `backend/tests/test_calendar_owner_api.py` に足す試験（422） |
| 作成・更新で Google に `eventLabelId` と `eventLabelVersion=1` を送る | `backend/tests/test_calendar_service.py` に足す試験（Google の道具は偽物） |
| 名札の表が `None` のとき版の指定を付けない | 同上 |
| 取り込みで `eventLabelId` から鍵を書く・表が `None` なら触らない | 同上 |
| 3 択それぞれで色が正しい行に入る（例外の回・これ以降の新しい予定を含む） | `backend/tests/test_calendar_service.py` の繰り返しの試験に色の場合を足す |
| 受け口の `""` は NULL で書かれ、3 択でも値の決まりに当たらない | 同上（`""` を送る 3 択の試験） |
| 色に触らない保存では Google に版の指定を付けない（作成・更新・3 択） | 同上（偽物の Google に届いた引数を見る） |
| 分類表の件数 1164 と tsv の行 | `backend/tests/ops/test_ai_cloud_views.py` の件数の試験 |
| トークンと裏側の値が一致 | test_event_colors_tokens.py |
| AI 用の写しの分類表に行がある | `test_t10_calendar_color_key_is_classified_on_bootstrapped_db` |
| 色の部品が 25 個の丸を出し、キーボードで選べる | ColorSwatchPicker.test.tsx |
| 箱・日ごとの一覧の丸・予定の一覧の丸・作っている途中の仮の箱が同じ色の決め方を通る | `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` に足す試験 |
| 動かす保存は `color_key` を送らない・繰り返しで色だけ変えると 3 択がすべて出る | 同上 |
| 色なしの箱は持ち主の色・色ありはトークン | `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` に足す試験 |
| K1〜K4 | 本番で PO が目で見る（§2） |

## 10. 外部・過去事例の参照と我々への応用

- Google の公式文書（recon.md §5）: 名札の付け方と、版の指定が無いと名札が処理されないこと、空にすると外れること。§4-4 と §6 の手当てはこれに合わせた。
- 社内の過去事例: Meet の欄（`meet_url`）と繰り返しの欄を足したときの移行・試験・分類表の足し方（f0df9074a・c770f6483）。同じ手順をなぞる。
- 他社の導入の数値の事例は使わない。今回は Google の色に合わせる話で、効果を数値で比べる対象が無いため。

## 11. 維持の仕組み

守り手: 裏側の試験（トークンと値の一致・分類表）と `frontend/src/components/gcalColorsUsage.test.ts` を CI の必須チェックで毎回流す。持ち主は設計者（Opus）。

- 24 色の正本は backend/app/services/event_colors.py 1 か所。画面のトークンと鍵の並びは、裏側の試験が毎回照らす。
- `--gcal-` の置き場は `frontend/src/components/gcalColorsUsage.test.ts` が見張る。
- AI 用の写しの分類の漏れは `test_t10_*` が見張る。
- 名札が無くて送れなかった件数は、ログの `event_label_missing` で数える。

## 12. 接触面

- DB: 各社の `calendar_events` に欄 1 つ。
- Google: `calendars.get` を新しく呼ぶ。`events.insert`・`events.patch` に版の指定と `eventLabelId`。
- 画面: 予定の作成の窓・全体の編集の画面・週と月の箱。
- AI 用の写し: 分類表に 1 行。
- 他の画面（受信箱・秘書の予定の下書き）: 触らない。秘書が作る予定は色なし（デフォルト）。

## 13. 未確認（便の中で確かめる。確かめるまで次に進まない）

- U1（道具の版）: 便1 の試験で確かめる。落ちたら止めて下限の版を上げる案を出す。
- U2（`events.list` の返事に `eventLabelId` が入るか）: 便1 の本番反映の後、PO が Google で作った予定に色を付け、アプリで確かめる（K4）。出なければ止めて、`events.get` で読み直す案を出す。
- U3・U4: §6 の手当てで扱う。件数はログで数える。
