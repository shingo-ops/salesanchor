# 審査報告 便2b 設計（第1回）

本報告は design-bin2b.md 第1版（ef7443eac）の設計審査である。

- 審査役: クラウドの Architect（コードは直さない）。審査日 2026-11-25
- 対象: `docs/handoff/schedule-settings/design-bin2b.md` 第1版（枝 `release/schedule-settings-bin2b`）。作業場所で `git log -1 --oneline` が `ef7443eac` を確認し、`git rev-parse HEAD` と `origin/release/schedule-settings-bin2b` が同じ `ef7443eac1d6f23c07b6f75bb9b6f0c9eeb3f454` であることも確認した
- 実物の基準: 設計の基準 `5a72c083f` と、いまの `origin/main`（`5a72c083f4e5fe5b2d1efda185302d7fc058ab3d`）は同じ。下の行番号は、この作業場所（`ef7443eac`）の実物
- 前回: なし（第1回）
- 本番の値（F8・F9）は、この審査では本番を読んでいないため「未確認」と書く（設計担当の記録として受け取る）

## 1 §1 現在地 F1〜F14 の照合

| # | ○× | 実物で確かめたこと |
|---|---|---|
| F1 | ○ | `calendar_service.py:240-246` に `visibility_sql`（`user_id is None` なら `ce.calendar_type = 'shared'`、あれば `(… 'shared' OR ce.user_id = :me)`） |
| F2 | ○ | `routers/calendar.py:282`・`:310` が `cal_svc.list_events`。`git grep -n "list_events("` で `backend/app` の呼び手はこの 2 つだけ（`routers/ops.py:360`・`routers/google_calendar.py:303` は同名の別の関数） |
| F3 | ○ | `routers/calendar.py:626-627`（personal の 404）・`:629-630`（403）、`:731-732`・`:734-737` |
| F4 | ○ | `tenant.py:1608`、`routers/calendar.py:542`・`:633`。移行 `078_create_calendar_events_tenant.sql:47-48` の CHECK は列の中に名前なしで書かれ、自動の名前になる。本番 5 社で名前が `calendar_events_calendar_type_check` かは **未確認**（R3） |
| F5 | ○ | `calendar_service.py:859-860`（`this` で `calendar_type` が違えば `recurrence_this_not_allowed`）・`:970-990`（`_row_values` が `calendar_type` を写す）・`:1100-1135`（「これ以降」で `_insert_row`） |
| F6 | ○ | `tenant.py:530-548`。`teams.is_active` は `BOOLEAN DEFAULT TRUE`（NOT NULL ではない・S10） |
| F7 | **×** | 「マネージャーの役には `teams.view` が無い」は**誤り**。`tenant.py:69`（マネージャー）の権限に `:81` で `"teams.view", "teams.manage_members"` がある。`teams.view` を持たないのは営業（`:100-123`）・仕入れ（`:149-165`）・発送（`:168-184`）。`routers/teams.py:55-58` の `require_permission("teams.view")` は実在。結論（`GET /teams` だけでは選べない人がいる）は正しいが、理由の名指しが違う（R6） |
| F8 | 未確認 | 本番 5 社のチーム・メンバー数 |
| F9 | 未確認 | 本番の予定の件数 |
| F10 | ○ | `migrations/20261126_100000_create_calendar_categories.sql:41`（CHECK `calendar_categories_default_share_check`。ひな形 `tenant.py:1563` も同じ文）・`routers/calendar.py:167`（`_VALID_CATEGORY_SHARES = ("self", "all")`）・`useCalendarCategories.ts:9` |
| F11 | ○ | `SchedulePageImpl.tsx:100`・`:159`・`:959`・`:1025`・`:1085`、`ScheduleDraftFields.tsx:300`・`:426-430` |
| F12 | ○ | `schedule-utils.ts:372`（`event.calendar_type === "personal" ? "personal" : "shared"`） |
| F13 | ○ | `google_webhook.py:376-380`（`publish_change(TOPIC_CALENDAR_EVENTS, SCOPE_TENANT, tenant_id)`・中身は送らない） |
| F14 | ○ | `MultiSelect.tsx:36-77`（props は `label`・`options`・`selected`・`onChange`・`clearLabel`・`allLabel`・`countLabel` が必須、`emptyLabel`・`layout` は任意）。`frontend/src/components/Select.tsx` に `SelectControl`（設計は `components/Select` と書き、ファイル名 `.tsx` を省く・軽い） |

## 2 審査

### (1) §1 の事実の照合

上の §1 のとおり。食い違いは F7（事実の誤り）1 つ。F8・F9 は未確認。

### (2) 見え方の条件が全部の道で 1 か所か

`git grep -n "calendar_type" -- backend/app` と `git grep -n "calendar_events" -- backend/app`（`calendar_service.py`・`routers/calendar.py`・`tenant.py` を除く）を全部確かめた。見え方を `calendar_type` や `user_id` で決めている道は次の 3 か所だけで、設計はすべて拾っている。

| 道 | 実物 | 設計 |
|---|---|---|
| 一覧・探す | `calendar_service.py:240-246` の `visibility_sql`（探すも同じ関数） | ○ `visibility_sql()` に置き換え |
| 回に広げるときの例外の行を引く文 | `:344-351` の `exc_where` が `visibility_sql` を再利用（`:340` の `exc_params` が `me` を写す） | ○ 同じ関数を使うので追従する。ただし設計の本文にこの道の言及が無い（S12） |
| 直す・消す | `routers/calendar.py:626-627`・`:731-732` | ○ `can_see_event` に置き換え |

ほかの道（秘書・Google・通知・会議・提案）:

- 秘書: 予定を作るだけ（`assistant.py:441`・`:462` が `personal`）。予定を読む道は無い（`git grep -n "list_events\|calendar_events" -- backend/app/routers/assistant.py` が 0 件）。○
- Google の取り込み・送り: `calendar_service.py:1742`・`:1815-1820` は `personal` で入れる。`upsert_from_google` は既にある行の `calendar_type`・`user_id` を上書きしない（`:1743`）。○（設計 §6 と一致）
- Google の一覧・直す・消す `GET/PATCH/DELETE /google-calendar/events`（`routers/google_calendar.py:300-400`）: Google から直接引く、会社単位の道で `require_calendar_owner` が前提。見え方の判定を持たない。今も `personal` の予定が Google に送られていれば同じ扱いで、チーム予定だけの新しい穴ではない。ただし設計 §6 に載っていないので、書くと G5 の説明が閉じる（S7）
- 通知・会議・提案: `git grep -n -i "calendar_event"` は `google_webhook.py:355`（取り込みの削除）・`calendar_categories.py`・`calendar_recurrence.py`・`realtime/topics.py` のみ。予定の見え方を決める道は無い。○
- 一覧の絞り `type` の値（`routers/calendar.py:276`・`calendar_service.py:226-231`）: `shared` で絞るとチーム予定は出ない。画面は `type` を送っていない（`git grep -n "type=" -- frontend/src/pages/schedule` に API の呼び出しは無い）ので実害は無い。docstring（`:207-209`）と受け口の説明（`:276`）が古くなる点は軽い（S12）

見え方の正本を 1 つにする方針は、読み書きの道を全部拾えている。ただし、**そのうえで** 次の「直す」の道に抜けがある（R1・R2）。

### (3) 繰り返しの回・例外・これ以降・単発から繰り返しで対応表が正しいか

| 場面 | 判定 | 根拠 |
|---|---|---|
| 回（元の行から広げる） | ○ | 元の行が `calendar_event_teams` を持つ。`COALESCE(recurring_event_id, id)` で元の行を引く |
| 例外の行 | ○ | `_row_values`（`:973`）が元の行の `calendar_type` を写すので、`'team'` のまま `COALESCE(...)` で元の行の対応に届く |
| 「すべて」D1 | △ | `fields` は `_TEXT_FIELDS`（`:683`）の変わった項目だけ。`team_ids` は入らないので、チームだけの変更では `fields` が空になり `if fields:`（`:1165`）の中に入らない。`set_event_teams` を `fields` の外で呼ぶ旨が無い（R2） |
| 「すべて」D2・D3 | ○ | 元の行の id は変わらず、対応は残る。D3（繰り返しを解く）も同じ id |
| 「これ以降」C | ○ | 新しい元の行（`new_id`）に写す・送られたものを入れる、が設計にある。古い元の行は切られるだけで対応は残る。新しい行は例外の行を持たない。`_commit`（`:1106` 以降の流れ）の前で呼ぶ旨は S12 |
| 「この予定だけ」 | **×** | 設計は「`team_ids` を送ると 422」。画面は持ち主なら `calendar_type`・`team_ids` を毎回送る（`SchedulePageImpl.tsx:1024-1025`）ので、持ち主が繰り返しのチーム予定の 1 回だけを直すと必ず 422 になる（R1） |
| 単発→繰り返し A | ○ | 同じ行が元の行になる（`:1225`）。`set_event_teams(event_id)` の id は変わらない |
| チーム→別の共有の「すべて」 | ○ | `fields` に `calendar_type` が入り、元の行と例外の行が全部変わる。`set_event_teams(master, [])` で対応が消える。設計 §3-3 のとおり |

### (4) 移行・表の CHECK・UNIQUE・FK を全部の書き込みの道に照らす

書き込みの道: 作る（`create_event` `:391-436`）・単発の直し（`update_event` `:490-541`）・繰り返しの直し（`:1028-1250`）・消す・Google の取り込み（`:1742-1836`）。

- PK `(event_id, team_id)` に対して、`set_event_teams` が `team_ids` の重複を落とさなければ `IntegrityError` で 500（S2）
- `team_id` の FK（`teams(id) ON DELETE CASCADE`）: 検証と挿入の間にチームが消えると FK 違反（まれ・S2）
- `event_id` の FK（`calendar_events(id) ON DELETE CASCADE`）: 消す道（`:663`・`:1110`・`:1203`・`:1335`・`google_webhook.py:355`）はすべて行を消すだけで、対応は連鎖で消える。○
- 「`team` の予定は対応が 1 つ以上」は DB では守られない（チームを消す／使わなくすると 0 件になりうる）。設計 §8 が「持ち主には見える」と書いている。これは受け入れてよい（B1 のテストに入っている）
- `calendar_type`・`default_share` の値の幅: どちらも `varchar(10)`（`tenant.py:1581`・移行 `create_calendar_categories.sql:15`）。`'team'` は 4 字で入る。○
- CHECK の入れ替え: 名前の扱いが決まっていない（R3）
- ひな形と移行: R3・R4・R5
- RLS: 決まっていない（R4）

### (5) 受入条件 B1〜B10 が試験で ○× 判定できるか

| 基準 | ○× | 指摘 |
|---|---|---|
| B1 | ○ | 5 人 × 一覧・探すで測れる |
| B2 | ○ | 404 の試験で測れる。メンバーの管理者が直せる側も §5 にある |
| B3 | ○ | 3 通り（回・例外・これ以降）で測れる。「メンバーでない人には 3 つとも出ない」も §5 にある |
| B4 | △ | 「6 通り」の内訳が書かれていない（本文 B4 は 欠け・空・無い id・使っていない id・`team` 以外で送る の 5 つ。6 つ目は「この予定だけ」か重複か、未確認）。S9 |
| B5 | ○ | 外す・入れ替える・持ち主でない人の 403 で測れる。ただし「持ち主でない人が `team_ids` だけ送る」は R2 の `calendar_type` を省いた道と関わる |
| B6 | ○ | 裏側＋画面で測れる |
| B7 | △ | 本番の件数は反映後に PO・Opus が読むもので CI の合否ではない。CI で測れるのは「移行の前後で `shared`/`personal` の行が同じ」だけ。要件 G6 は「人ごとの見える予定の件数が同じ」。B7 は種類別の件数なので G6 より弱い。移行の試験に「移行の前後で、ある人の一覧が同じ」を 1 つ足すと G6 に届く（S8） |
| B8 | **×** | `git grep -n "('shared', 'personal')" -- backend/app ':!backend/app/services/tenant.py'` は**今でも 0 件**（実物の書き方は二重引用符 `("shared", "personal")` で、`routers/calendar.py:542`・`:633` の 2 行）。設計を実装する前も後も 0 件で、変更を測れない。さらに「裏側の定数 1 つ」は、`routers/calendar.py:167` の `_VALID_CATEGORY_SHARES`（`self/all/team`）が別に残るので 2 つになる。どれを 1 つにするのか決まっていない（R7） |
| B9 | ○ | 既存の点検で測れる |
| B10 | ○ | `check_tenant_template_shape.py` が表・列・索引・制約を比べる。ただし R3・R4 が決まらないと、同じ形かの確かめが定まらない |

### (6) 画面が金型と i18n を守るか

- 金型: `SelectControl`・`MultiSelect`・`Toggle` の置き換えは金型の中。色の直書きの指定も無い。○
- `MultiSelect` の必須の props（`clearLabel`・`allLabel`・`countLabel`、`MultiSelect.tsx:39-50`）に使う文字が §4-4 の 7 つに入っていない。既に `common` 側にある文字（`locales/ja.json:143` に `"clear": "クリア"`）を使うのか、新しい文字か。`layout` も未指定（`"inline"` は「浮かせられない所＝Drawer の中」とコメントがある）。予定の画面の小窓と全画面の編集でどれを使うか（S5）
- `schedule.calendarTypeValues`（`ja.json:3538`）は `shared`・`personal` の 2 つで、詳しい表示の `categoryName ?? t("schedule.calendarTypeValues.shared")`（`SchedulePageImpl.tsx:402`）が使う。`team` の値が要るかが書かれていない（S5）
- §4-4 の新しいキー 7 つは、`ja.json`・`en.json` に今は無い（`grep` が 0 件）ので衝突しない。○。消す 3 つ（`shareWithStaff`・`categoryShareSelf`・`categoryShareAll`）は `SchedulePageImpl.test.tsx:171`・`:1047`・`:1403`・`:1433` と `ScheduleSettingsPage.tsx:351-352` が使っている。設計 §5 の「既存の試験で `visibleToStaff` を使うものは新しい形に直す」には、`getByRole("switch", …)`（`Toggle` から `SelectControl` に替わる）の試験も入ると書き足すと迷わない（S5）
- 設定ページ（`ScheduleSettingsPage.tsx:353-354`）の `onChange` は `event.target.value === "self" ? "self" : "all"` で 2 値を前提にしている。3 値にする旨は §4-3 にあるが、`defaultTeamIds` をフォームの状態に足す旨は無い（実装役が自然に気づく範囲）

### (7) 実装役が迷う所

R1〜R7 と S1〜S12 に分けた。

## 3 指摘の一覧

### 必須（7 件）

| # | 指摘 | 根拠 | 直し方 |
|---|---|---|---|
| R1 | **持ち主が繰り返しのチーム予定の「この予定だけ」を直すと必ず 422 になる**。設計 §3-3（L115）は「この予定だけ」で `team_ids` を送ると 422 `recurrence_this_not_allowed` としつつ、§4-1（L133）は「送るとき `team` なら `team_ids` も送る」。画面は持ち主なら `calendar_type` を毎回送る（`SchedulePageImpl.tsx:1024-1025`）。`calendar_type` は「今と同じなら通る」（`calendar_service.py:859-860` が `!= event.get("calendar_type")` で比べる）が、`team_ids` にはその比べる相手が無い（`read_event`・`EVENT_COLUMNS_SQL` は `team_ids` を持たない） | B3 の「この予定だけの例外の行」を持ち主が作れない。試験が裏側の直接呼びだけだと見つからない | 次のどちらかに決めて書く。(a) 裏側: 「この予定だけ」では、元の行の対応と**違うときだけ** 422（比べる相手は `calendar_event_teams` の元の行の昇順の id）。(b) 画面: 「この予定だけ」のときは `team_ids` を送らない・`calendar_type` だけ送る。(a)(b) の両方を勧める。試験に「持ち主が team の繰り返しの 1 回だけを直して 200」を足す |
| R2 | **チームの対応を書く呼び場所の抜け 3 つ**。①単発の直し `update_event` は、`set_clauses` が空だと `if not set_clauses:` で返る（`calendar_service.py:533-537`）。`team_ids` だけ変える直し（B5「チームを変えると入れ替わる」）は `field_map` に項目が無く、空のまま返って対応が書かれない。②「すべて」D1 は `fields` が `_TEXT_FIELDS` の変わった項目だけで、`team_ids` は入らない。チームだけの変更では `if fields:`（`:1165`）に入らず対応が書かれない。③`validate_team_ids(db, calendar_type, team_ids)` は直すとき `calendar_type` を省いた `team_ids` だけの送りを、「team 以外で team_ids」と見て 422 にするのか、元の行の今の種類で判定するのかが決まっていない | 設計 §3-3 L111-115 は「送られた `calendar_type` か `team_ids` があれば呼ぶ」とだけ書く。B5 の試験を API の直接呼びで書くと、①②で空振りする | §3-3 に「`set_event_teams` は `set_clauses`・`fields` の空とは別に、`team_ids` か `calendar_type` が送られたら必ず呼ぶ。呼ぶ位置は、各書き込みの `commit` の前（同じ取引）」「直すときの有効な種類 = 送られた `calendar_type`、無ければ元の行（`owner_row`）の今の種類」を書く。試験に「`team_ids` だけを送って入れ替わる」「チームだけ変えて `calendar_type` を送らない」を足す |
| R3 | **移行の CHECK の入れ替えが、そのままでは書けない**。「新しい CHECK を `NOT VALID` で足す → `VALIDATE` → 古いものを消す」（§3-2 L79）は、新しい CHECK が古いものと同じ名前 `calendar_events_calendar_type_check` なら、古いものがある間は名前がぶつかって足せない。最後の名前（ひな形 `tenant.py:1608` と同じにする必要がある・B10）、足すときの仮の名前と最後の付け替え、古い CHECK の見つけ方（名前か `pg_constraint` で `calendar_type` を含む CHECK を引くか）が書かれていない。`default_share` の CHECK `calendar_categories_default_share_check` も同じ。F4 の根拠はひな形の行だけで、本番 5 社の CHECK の名前の確認が無い（便2a の審査 `review-architect-bin2a-2.md` §1 R5 は、読み取りの鍵で名前を確かめる F9 を入れた） | `migrations/078_create_calendar_events_tenant.sql:47-48` は名前なしの CHECK で自動の名前。本番の名前は**未確認** | §3-2 に次を書く。仮の名前（例 `…_check_v2`）で足して `VALIDATE`、古いものを消し、最後に最終の名前へ `RENAME CONSTRAINT`。古いものは `pg_constraint` から `calendar_type` を使う CHECK を引いて外す（名前に頼らない）。本番の制約名は読み取りの鍵で確かめた値を F に足す。確かめ「ちょうど 1 つで `team` を含む」は `contype = 'c'`・`pg_get_constraintdef` の文字で。便2a の移行（`create_calendar_categories.sql`）の手順 5 と同じ形に揃えると実装役が迷わない |
| R4 | **RLS の指示が実物と食い違い、どちらにするか決まっていない**。§3-1 L74 は「`team_members` と同じ扱い」「`tenant.py:2340-2363` に足す」。実物: `team_members` は RLS あり（ENABLE が `:2353`、ポリシー `tenant_isolation_team_members` が `:2467` の別の場所、`teams.tenant_id` を引く形）。一方、**隣の予定の表は RLS が無い**: `tenant.py` に `calendar_events`・`calendar_categories` の `ENABLE ROW LEVEL SECURITY` は 0 行、`migrations/*.sql` で `calendar` を含み `ROW LEVEL SECURITY` も含むのは `20261016_010000_add_google_config_rls.sql` だけ（Google の設定の表）。`:2340-2363` は ENABLE の並びで、ポリシーは別の `DO` ブロック（`:2467`）。移行側にも ENABLE とポリシーの両方が要るが、設計に書かれていない | 実装役が RLS を付けるか付けないか迷う。付けるなら、ひな形（`tenant.py` の ENABLE とポリシー）・移行（部屋ごとの ENABLE とポリシー）・`rls_bootstrap.py`・形の差の検査まで揃える必要がある。付けないなら、`calendar_events` と同じで `teams` の RLS に頼る形になる | どちらかに決めて書く。推奨: `calendar_event_teams`・`calendar_category_teams` も `calendar_events`・`calendar_categories` と同じく**RLS なし**（部屋ごとのスキーマで分けられた表で、親の予定の表も RLS なし）。付ける場合は、ポリシーを `team_members` と同じ形（`teams.tenant_id` を引く）で、ひな形・移行の両方に書き、`tenant.py` の 2 か所（ENABLE と ポリシー）を明記する。どちらでも B10 で同じ形になることを書く |
| R5 | **AI 用の写しの分類の指示が実物と合わない**。§3-2 L81「新しい 2 表の列の分類は、`team_members` の列と同じ分類にする」。実物: `team_members` は分類表に**1 行も無い**（`grep -c team_members` が `create_ai_cloud_views.sql` で 0・`stage1-column-class.tsv` で 0）。`team_members` の列は int4・timestamptz だけなので、型だけで通り分類が要らない（`test_ai_cloud_views.py:52-55` の `_PASS_TYPES`）。新しい表では `calendar_event_teams`（`event_id`・`team_id` は int4）は分類不要だが、`calendar_category_teams.category_key`（`character varying(50)`）は型で通らず、分類が要る。便2a は `calendar_categories.key` を mask にした（`create_ai_cloud_views.sql:371`）。件数 1165 の試験（`test_ai_cloud_views.py:486`）に何を足すかが決まらない | 実装役が「`team_members` と同じ」を実行すると分類 0 行になり、`category_key` が未分類で試験が落ちる（落ち方は実装前なので未確認。ただし便2a の R4 は同じ型の指摘で、そこで分類の足りなさが落ちる前提で直された） | §3-2 に「`calendar_category_teams.category_key` を `mask`（理由: `calendar_categories.key` と同じ・形だけの決まり）で足す。`event_id`・`team_id` は int4 なので不要」と、件数の増え方（1165 + 1 欄 = 1166。`stage1-column-class.tsv` は `data_type`＝`character varying` まで書く）を書く |
| R6 | **F7 の事実が誤り、§7 の理由が崩れる**。「マネージャーの役には `teams.view` が無い」は誤り（上の §1）。マネージャーは `tenant.py:81` に `teams.view` を持ち、持たないのは営業・仕入れ・発送。§7 の「`GET /teams` から読むと、マネージャーの役に `teams.view` が無く選べない」も同じ誤りに依っている。方針（`GET /calendar/teams` を別に置く）自体は、営業・仕入れ・発送が `teams.view` を持たない事実で成り立つ | 設計の事実の根拠が誤りのまま実装カードに渡ると、カードで「マネージャーは選べるはず」と食い違う | F7 を「営業・仕入れ・発送の役には `teams.view` が無い（`tenant.py:100-123`・`:149-165`・`:168-184`）。マネージャー・CS には有る」に直し、§7 の理由も同じに直す。役の権限は会社ごとに画面で変えられるので、「ひな形の既定では」と書き添える（本番の役の中身は未確認） |
| R7 | **B8 が測れない**（上の §2 (5)）。`git grep -n "('shared', 'personal')"` は今も 0 件で、実装の前後を区別しない。「裏側の定数 1 つ」も、`_VALID_CATEGORY_SHARES`（`routers/calendar.py:167`）が別に残るため、どれが 1 つなのかが決まらない | 受入条件が空振りで必ず ○ になる | B8 を次のように測れる形にする: `git grep -n '"shared", "personal"' -- backend/app` が 0 件（今は `routers/calendar.py:542`・`:633` の 2 件）、`git grep -n "SHARE_VALUES" -- backend/app` で定義が 1 件。種類の共有 `self/all/team` の定数は別の集合なので、「予定の共有の定数 1 つ」「種類の共有の定数 1 つ」の 2 つと明記する。画面側は `git grep -n '"self" | "all" | "team"' -- frontend/src` が型 1 件 |

### 推奨

| # | 指摘 | 直し方 |
|---|---|---|
| S1 | `can_see_event(db, owner_row, user_id)` は `owner_row` を使わず id だけ使う書き方に見える（設計 L103-105）。今の判定は `event_owner = user_id か created_by`（`routers/calendar.py:625`・`:730`）で見るのに対し、`visibility_sql` は `ce.user_id = :me` だけ。`user_id` が NULL で作成者が本人の `personal` の行（`user_id` は `ON DELETE SET NULL`・`tenant.py:1616`）は、今は直せるが新しい判定では 404 になる。B7「今の見え方は変わらない」の例外。現実にはほぼ無いが、引数を `event_id` にするか、この差を §8 に 1 行書く |
| S2 | `team_ids` の重複を `validate_team_ids` で落とす（PK 違反の 500 を防ぐ）。asyncpg の int4 の範囲を超える id（例 `99999999999`）が 422 でなく 500 になる点も、`validate_team_ids` で範囲を見るか、試験に入れる。検証と挿入の間にチームが消える競合は、500 でなく 422 に寄せるか「まれ・許容」と書く |
| S3 | `PATCH /calendar/categories` の `default_share = 'team'` の確かめ「1 つ以上の使っているチームが要る」は、本文に `default_team_ids` が無い（`name` だけ直す、`default_share: "team"` だけ送る）とき、今ある対応で足りるのか、必ず送らせるのかが決まっていない。「`default_team_ids: []` は 422」「省略は今の対応を保つ」を書く（`calendar_categories.py:109` `update_category` の既存の組み立て方 `_FIELD_COLUMNS` に合わせる） |
| S4 | 種類の `default_team_ids` には、後で使わなくなったチームが残りうる。画面が種類を選んだときに `teamIds: default_team_ids` をそのまま入れると、使っていないチームの id が混ざって保存で 422（B4）。§4-2 に「`useCalendarTeams` の一覧にある id だけを入れる。全部落ちたら 0 個（保存不可）」と書く |
| S5 | §4 の画面の細部: `MultiSelect` の必須 props の文字（`clearLabel`・`allLabel`・`countLabel`）と `layout`（`"popover"`・`"inline"`）の選び方、`schedule.calendarTypeValues.team` の要否、`SelectControl` の `variant`（同じ画面の種類の選択は `editor-filled`・`ScheduleDraftFields.tsx:322-323`）を書く。既存の `getByRole("switch")` の試験（`SchedulePageImpl.test.tsx:1047`・`:1403`・`:1433`）が `SelectControl` に変わる旨も |
| S6 | `GET /calendar/teams` は、`teams.view` の無い人にも**会社の使っているチームの名前を全部**見せる（設計 §3-4 L123）。チームの名前は `teams.view` で守られていた情報。意図なら「チームの名前は予定の共有の選び方のために全員に見せる」と PO の確認を 1 行足す。自分が入っているチームだけにする案も、§7 の代替案に 1 行書くと比べられる（ただし「共有するチームを選ぶ」には会社の全チームが要るので、全件のほうが自然） |
| S7 | §6 に「`/google-calendar/events` の一覧・直す・消す（`routers/google_calendar.py:300-400`）は見え方を判定しない会社単位の道で、`personal` の予定が Google に送られているときと同じ扱い（`require_calendar_owner` が前提）。チーム予定も同じ」と書く。G5 の「チーム外の人で開いて見えない」の範囲を、アプリの予定の画面と API に限ると明記する |
| S8 | B7 は種類別の件数。G6（人ごとの見える予定の件数）に届かせるため、移行の試験に「移行の前後で、持ち主・ほかの人のそれぞれの一覧の件数が同じ」を 1 つ足す |
| S9 | 軽い指し先: B4 の試験の「6 通り」の内訳・§3-4 L125 の「便2a の直し2 と同じく理由の語の表に足す」は、`origin/main` の `apiErrorReason.ts` に `invalid_category`・`category_conflict` の行が**無い**（`git grep -n "invalid_category" -- frontend/src backend/tests/test_api_error_reason_sync.py` が 0 件・表の行は 27 本、`test_api_error_reason_sync.py:40-68`）。「便2a の直し2」はまだ main に入っていない可能性があり、`invalid_team_ids` だけを足せばよいのか、表の形をどう揃えるのかを、いま main にあるものに合わせて書く（便2a が先に入るなら、その後の形に合わせる旨でもよい） |
| S10 | 移行: `calendar_events` はあるが `teams` が無い部屋は、FK で失敗して全体が戻る。`to_regclass(teams)` の守りを 1 行入れる（ひな形は Phase 1 から `teams` を持つので実害は低い）。`teams.is_active` は NOT NULL でない（`tenant.py:535-539`）ので、`t.is_active` は NULL を「使っていない」に倒す。意図なら 1 行書く |
| S11 | F8・F9 は審査では未確認。実装前に、設計担当が読むだけの鍵の結果（日時つき）を記録として残す |
| S12 | 実装の細部: `create_event` は INSERT のあとすぐ `commit`（`calendar_service.py:434`）するので、`set_event_teams` は `commit` の前に呼ぶ（B5 の「同じ取引」）。「これ以降」C も `_insert_row` と `_commit` の間。`list_events` の docstring（`:207-209`）と `type` の説明（`routers/calendar.py:276`）に `team` を足す。`exc_where`（`:344-351`）が同じ `visibility_sql` を使うことを §3-3 に 1 行書くと、置き換えの漏れが減る。`GET /calendar/teams` の `topics.py` の登録は、設計どおり試験の失敗で確かめてよい |

## 4 結論

- §1 の事実 F1〜F14 のうち、F7 は事実の誤り（R6）。F8・F9 は本番で未確認
- 見え方の読み方の道は、一覧・探す・回に広げる文・直す・消すの 3 系統に集約でき、設計はすべて拾っている。秘書・Google・通知・会議・提案に、予定の見え方を決める道は無い
- 一方、書く側に抜けがある。持ち主が繰り返しのチーム予定の 1 回だけを直すと必ず 422（R1）、`team_ids` だけを変えると対応が書かれない道が 2 つある（R2）
- 移行は CHECK の名前の扱いが書けない形（R3）、RLS は実物と食い違う指示（R4）、AI 用の写しの分類は実物と合わない指示（R5）で、実装役が迷う
- 受入条件 B8 は空振りで測れない（R7）。B7 は G6 より弱い（S8）
- 必須 R1〜R7 が残るため、判定は REVISE。R1〜R7 が入れば、推奨は実装カードに入れれば足りる（S1〜S12）

判定: REVISE
