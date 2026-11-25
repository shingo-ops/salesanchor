# 審査報告 便2b 設計（第2回）

本報告は design-bin2b.md 第2版（63e6edc3a）の設計審査である。

- 審査役: クラウドの Architect（コードは直さない）。審査日 2026-11-25
- 対象: `docs/handoff/schedule-settings/design-bin2b.md` 第2版（枝 `release/schedule-settings-bin2b`）。作業場所で `git log -1 --oneline` が `63e6edc3a` を確認し、`git rev-parse HEAD` と `origin/release/schedule-settings-bin2b` が同じ `63e6edc3a29a4587bbd6d8374697d12680b2d47b` であることも確認した
- 実物の基準: 行番号は、この作業場所（`63e6edc3a`）の実物。`origin/main` を fetch 済み（設計の基準は `5a72c083f`）
- 前回: `docs/handoff/schedule-settings/review-architect-bin2b-1.md`（第1版 `ef7443eac`・REVISE・R1〜R7・S1〜S12）
- 本番の値（F8・F9・F15・F21）は、この審査では本番を読んでいないため「未確認」（設計担当の記録として受け取る）

## 1 前回指摘の照合

| # | 判定 | 第2版の直し方と、実物での照合 |
|---|---|---|
| R1 この予定だけ | **△ 直し方は合う・書き方に矛盾が残る（新 R1）** | 裏側は「元の行の対応と違うときだけ 422」（§3-3 L139・B11）。`check_recurrence_request` は既に `async` で `db` を持ち（`calendar_service.py:807`）、`calendar_type` の判定も「違うときだけ」（`:859-860`）なので、同じ形で足せる。ただし画面側の記述が実物と合わず、B11 とも食い違う（新 R1） |
| R2 呼ぶ決まり | ○ | §3-3 L133-139 に呼ぶ場所を 5 つ固定。実物と照合: 作る `:434` の commit の前・単発 `:533` の前・D1 `if fields:` `:1165`／`_commit` `:1169`・「これ以降」`_insert_row` `:1134`／`_commit` `:1135`・単発→繰り返し `_commit`（設計は `:1233`、実物は `:1234`＝1 行ずれ・S1）。`PATCH` は `model_dump(exclude_none=True)`（`routers/calendar.py:595`）なので `team_ids: []` は鍵が残り、`team_ids` だけの送りも `no_fields_to_update`（`:604`）にならない。`field_map`（`calendar_service.py:502-513`）に `team_ids` が無く、`UPDATE` の列に混ざらない |
| R3 CHECK の入れ替え | ○ | §3-2 に仮の名前 `_v2`→`NOT VALID`→`VALIDATE`→古いものを `pg_constraint` から定義で探して消す→`RENAME CONSTRAINT`。実物で、`calendar_type` を使う CHECK は `tenant.py:1608` の 1 本だけ、`default_share` を使う CHECK も `tenant.py:1563` の 1 本だけ（`calendar_categories_name_check` は `default_share` を含まない: `create_calendar_categories.sql:43`）。ほかの CHECK を巻き込まない。`078_...sql:47-48` は名前なし CHECK で、定義で探す手順が効く。F15 の本番の名前は記録として受け取る（**未確認**） |
| R4 RLS | ○ | §3-1 L84 に「付けない」と理由。実物: `tenant.py` の `ENABLE ROW LEVEL SECURITY`・`CREATE POLICY` に `calendar_events`・`calendar_categories` は 0 件（grep 0）。`teams` の ENABLE `:2352`・方針 `tenant_isolation_teams`（`tenant_id` で絞る）、`team_members` の ENABLE `:2353`・方針（`teams` を引く）は実在 |
| R5 分類 | ○ | §3-2 L100: `calendar_category_teams.category_key` を `mask`、数の列は不要。実物: `_PASS_TYPES` に `int4` あり（`test_ai_cloud_views.py:52-55`）。`calendar_categories.key` が `mask`（`create_ai_cloud_views.sql:371`・`stage1-column-class.tsv:564`）。件数 `== n0 == 1169`（`test_ai_cloud_views.py:486`）→ +1 で 1170 |
| R6 F7 | ○ | F7 が「営業・仕入・発送には無い／マネージャーには有る（`tenant.py:81`）」に直り、§7 の理由も同じ。実物と一致 |
| R7 B8 | **× 直っていない（新 R2）** | B8 を 4 つの `git grep` にしたが、①が自分の新しい定義に当たる（下の新 R2） |
| S1〜S12 | ○（S1 は F21・持ち主の決め方、S2 は B4、S3・S4 は §3-4・B12、S5 は §4-2・§4-4・§5、S6 は §3-4、S7 は §6、S8 は B7・§5、S9 は F20・§3-4、S10 は §3-2・§3-3、S11 は F15・F21 の時刻、S12 は §3-3 の `vis_where`・説明文）。実物: `list_events` 内の変数 `visibility_sql`（`:240-246`・`:344-347`）の改名は漏れなく §3-3 L142 にある。S9: `invalid_team_ids` だけを足す方針と、`test_api_error_reason_sync.py` の並び（27 本・`:41-69`）が実物と合う |

## 2 新しい照合

### 2-1 F15〜F21・§1 の事実

| # | 判定 | 実物 |
|---|---|---|
| F15 | 一部○ | ひな形の名前 `tenant.py:1608`・`:1563` と、古い移行 `078_...sql:47-48` の名前なし CHECK は実物と合う。本番 5 社の名前は **未確認** |
| F16 | ○ | `:533`（`if not set_clauses`）・`:1165`・`:434`・`:1134-1135` 実物と合う |
| F17 | ○ | `:858-860`（`scope == "this"` の中で `payload["calendar_type"] != event.get("calendar_type")`） |
| F18 | ○ | 上の R4 |
| F19 | ○ | 上の R5 |
| F20 | ○ | 上の S9 |
| F21 | 未確認 | 本番の値。ただし「直す・消すの持ち主は `user_id` が無ければ `created_by_user_id`」は実物（`routers/calendar.py:624`・`:731`）。作る道は `user_id` に作った人を必ず入れる（`calendar_service.py:422` の `"uid": user_id`）ので、`user_id` が NULL の行は Google 取り込み由来に限られる |

### 2-2 見え方の正本と持ち主の変更（一覧・探す・直す・消す・例外の問い合わせ）

| 道 | 判定 | 根拠 |
|---|---|---|
| 一覧・探す | ○ | `visibility_sql()` が `COALESCE(user_id, created_by_user_id)` で持ち主を決める。今の `ce.user_id = :me`（`:244`）と違うのは「`user_id` が NULL の `personal`」だけで、本番 0 件（F21・未確認）。`personal` 絞り（`:228-229`）の `user_id = :uid` は触らない |
| 例外の行の問い合わせ（`:344-347`） | ○ | 同じ関数に追従。`COALESCE(recurring_event_id, id)` で元の行のチームに届く。例外の行の `calendar_type` は元の行から写る（`_row_values` `:973`） |
| 直す・消す | ○ | `can_see_event(db, owner_row["id"], user.id)` は、今の判定（personal かつ持ち主でなければ 404: `routers/calendar.py:626-627`・`:731-732`）の上位互換で、shared は通る。元の行の id を渡すので `COALESCE(recurring_event_id, id)` は自分自身になり正しい。404 のあとの 403（`:629-630`・`:734-737`）は変えない |
| 例外の行・回の `team_ids` | ○ | SELECT の `COALESCE((SELECT array_agg(...)), '{}')` は元の行の id で引くので、回・例外の行にも同じ値が付く |
| Google の取り込み | ○ | `upsert_from_google` は新規を `personal` で入れ、既存行の `calendar_type`・`user_id` を上書きしない（`:1742-1743`・`:1815-1820`）。アプリ起源の繰り返しの回は `_apply_app_instance_from_google` に回る（`:1753-1755`）が、判定は元の行で行うので `team` の予定に追従する |
| RLS 越しの `teams`・`team_members` | ○（試験で確かめる設計） | 会社の番号は受け口が入れる。`can_see_event` は commit より前に呼ぶ位置（直す・消すの冒頭）なので `app.tenant_id` は有効。空になる方向（見えない）に倒れる |

### 2-3 移行 §3-2・表 §3-1

- ひな形の表の並び: `teams`（`tenant.py:530`）は `calendar_events`（`:1600` 台）より前にあり、外部キーの順は問題ない。
- `RENAME CONSTRAINT` は CHECK でも使える（PostgreSQL 9.2 以降）。`NOT VALID` の追加と `VALIDATE` を同じ取引で行う書き方も可能。ロックは短い（ADR-1037・本番 38 行）。
- 付随ファイル（`scripts/run_all_migrations.sh:1491-1492`・`scripts/migration-guard/reference-allowlist.tsv:7`・`backend/tests/rls_bootstrap.py:189` の件数表・`backend/tests/test_tenant_loop_migration_guard.py:52`・`:72`・`:81`）は便2a の合流で触ったものと同じ組で、実在。
- 新しい移行名 `20261127_100000_...` は main の最新 `20261126_100000_...` より後。○

### 2-4 受入条件 B1〜B12 が試験で ○× 判定できるか

| 基準 | 判定 | 指摘 |
|---|---|---|
| B1〜B3・B5・B6・B9・B10・B12 | ○ | 5 人の表・3 通り・3 通りなどで測れる |
| B4 | △ | 「`team` になるとき `team_ids` が要る。欠け → 422」と、§3-3 L135「送らなければ今の対応のまま」が食い違う（新 R1） |
| B7 | ○ | 移行の試験（前後の件数・3 人それぞれの件数）で CI で測れ、本番の件数は反映後の確かめと分けて書いてある |
| B8 | **×** | ①が自分で定義する `SHARE_VALUES = ("shared", "personal", "team")` に当たる（新 R2） |
| B11 | △ | 試験の中身（「画面と同じく今と同じ `team_ids` も送る」）が、§4-2 の「画面は `team_ids` を送らない」と逆（新 R1） |

### 2-5 画面の金型と i18n

- `SelectControl`（`variant="editor-filled"`）・`MultiSelect` の必須 props（`label`・`options`・`selected`・`onChange`・`clearLabel`・`allLabel`・`countLabel`）は実物と合う（`MultiSelect.tsx:36-62`）。文字は §4-4 の 11 + 1 キーで足りる。部品の置き換えだけで、色の直書きは無い。○
- 設定ページ `ScheduleSettingsPage.tsx:346-355` は 2 値前提（`=== "self" ? "self" : "all"`）。§4-3 で 3 値にする旨があり、実装役が気づく範囲（S3）。
- 消す文字（`shareWithStaff`・`categoryShareSelf`・`categoryShareAll`）の使い手（`ScheduleSettingsPage.tsx:351-352`・`SchedulePageImpl.test.tsx` の 4 か所）は §5 にある。○

## 3 指摘

### 必須

| # | 指摘 | 根拠 | 直し方 |
|---|---|---|---|
| R1 | **「直す」で `calendar_type` と `team_ids` を送る／送らないの決まりが 3 か所で食い違い、実装役が 2 通りに作れる**。①§4-2 L171 は「`calendar_type` を今と同じなら送らない今の形にそろえる」と書くが、実物の画面は `canChangeVisibility` なら毎回 `body.calendar_type` を送る（`SchedulePageImpl.tsx:1024-1025`）。「今の形」は無い。②B11 の試験は「画面と同じく今と同じ `team_ids` も送る」、§4-2 は「画面は `team_ids` を送らない」で逆。③B4（欠け → 422）と §3-3 L135（「送らなければ今の対応のまま」）が、「今が `team`・`calendar_type: "team"` だけ送って `team_ids` が無い」場合で食い違う。`validate_team_ids(db, calendar_type, team_ids, current_type)` は今の対応を知らないので、`None` を 422 にするか通すかを決められない | ①のままだと、「この予定だけ」で `calendar_type: "team"` を送る画面が B4 の字面どおり 422 になる（持ち主の通常の保存が落ちる）。実装役が B4 に従うと R1（第1回）の再発になる | PATCH の決まりを 1 つの表にして §3-3 に置く。行＝(今の共有・送った `calendar_type`・送った `team_ids`)、列＝(結果・対応の書き方)。最低限: (a) 今 `team`・`calendar_type` が `team` か無し・`team_ids` 無し → 通す・対応は今のまま（`validate_team_ids` は `None` を返し `set_event_teams` を呼ばない）／(b) 今が `team` 以外・`calendar_type="team"`・`team_ids` 無しか空 → 422／(c) `team_ids: []` 明示 → 常に 422（`team` のとき）。B4 の「欠け」は (b) のこと、と書き直す。B11 の試験は「`team_ids` を送らない（`calendar_type` は今と同じ `team` を送る）で 200」と「今と同じ `team_ids` を送って 200」の 2 つにする。§4-2 L171 は「画面は『この予定だけ』のとき `team_ids` を送らない（`calendar_type` は今と同じ値のまま送ってよい）」に直し、「今の形」の語を消す |
| R2 | **B8 ①が測れない**。`git grep -n '"shared", "personal"' -- backend/app` を「0 件」とするが、設計が §3-3 で足す `SHARE_VALUES = ("shared", "personal", "team")` が `"shared", "personal"` を含むので、実装後は **1 件**（定義）になる。0 件を合格にすると正しい実装が不合格になる（今の 2 件は `routers/calendar.py:542`・`:633`＝実物で確認）。前回 R7 の「測れない」が別の形で残った | `git grep -n '"shared", "personal"' -- backend/app` を今実行すると `routers/calendar.py:542`・`:633` の 2 件。実装後は `calendar_service.py` の定義 1 件 | ①を、定義に当たらない形にする。例: `git grep -n '"shared", "personal")' -- backend/app` が 0 件（閉じ括弧まで含める。定義は `"personal", "team")` で当たらない）。②〜④はそのままでよい（④は実装後 `useCalendarCategories.ts` の型 `"self" \| "all" \| "team"` の 1 件で合う。ほかに `"self" \| "all"` の綴りは今も無い） |

### 推奨

| # | 指摘 |
|---|---|
| S1 | 行番号のずれ: §3-3 L137「単発→繰り返しの `:1233` の `_commit`」は実物 `:1234`。実装役が位置を見失わない程度 |
| S2 | `MultiSelect` の `selected`・`options.value` は文字（`string[]`）。チームの id は整数なので、画面の `useCalendarTeams` から `MultiSelect` に渡すとき・`teamIds` に戻すときの文字↔数の変換を §4-2 に 1 行書くと迷わない |
| S3 | 設定ページのフォームの状態に `defaultTeamIds` を足す旨（`ScheduleSettingsPage.tsx:346-355` は今 `defaultShare` だけ）を §4-3 に 1 行 |
| S4 | 画面の型 `ScheduleItem.calendarType: "shared" \| "personal" \| "team"`（§4-1）は裏側の値の型で、B8 ④の対象外。B8 の「画面の型 1 つ」は `CalendarShare` のことと注を付けると読み手が迷わない |
| S5 | F21 の「`user_id` が NULL の行は Google 取り込み由来」を、`create_event` が `user_id` に作った人を必ず入れる（`calendar_service.py:422`）事実と一緒に書くと、持ち主の決め方（`COALESCE`）の根拠が実物で閉じる |
| S6 | `_apply_app_instance_from_google`（アプリ起源の繰り返しの回・`:1753-1755`）が `team` の元の行の例外の行を作るときも、判定は元の行の対応で足りる旨を §3-3 に 1 行（試験 B3 の「例外の行」で確かめる） |

## 4 結論

- 前回 R1〜R7 のうち、R2〜R6 は第2版で実物どおり直った。R1 は直し方は合うが書き方に矛盾が残り（新 R1）、R7 は B8 ①の書き方が自分の定義に当たり直っていない（新 R2）。
- 新しい F15〜F21・B11・B12・§3-2 の入れ替え手順・§3-3 の呼ぶ場所・持ち主の `COALESCE` の変更は、一覧・探す・直す・消す・例外の問い合わせのどれでも実物と矛盾しない。移行の CHECK 入れ替えと付随ファイルも実在・実物の形に合う。
- 必須は 2 件。新 R1 は、持ち主の通常の保存（繰り返しのチーム予定の「この予定だけ」）が 422 になる実装を誘う。新 R2 は、正しい実装を不合格にする受入条件。どちらも設計の書き直しだけで直る。
- 本番の値（F8・F9・F15・F21）は **未確認**。

判定: REVISE
