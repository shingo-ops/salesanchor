# 実装カード 予定ごとの色 便1 — 裏側（色の欄・受け口・Google への書き込みと取り込み）

> この文書は何か：予定ごとの色（Google と同じ 24 色＋デフォルト）の便1 の作業指示書です。各社の予定の表に色の欄を 1 つ足し、画面から受けた色を保存し、Google カレンダーへ名札（予定のラベル）として送り、Google で付けた色を取り込みます。画面（色を選ぶ部品・トークン）は便2 で、この便では触りません。

- 設計: docs/handoff/event-color/design.md §4-1〜§4-6（審査 2 回目 APPROVE・軽 3 件を直した版）
- 現状の調べ: docs/handoff/event-color/recon.md
- 対象ADR: ADR-1081（本テーマ・Proposed）、ADR-136（危険 PR の GO 手順）、ADR-135（main マージ＝本番投入可）、ADR-1037（移行のロック待ち）、ADR-1075（繰り返し）、ADR-1059（Google からの取り込み）
- 状態: 設計審査済み（クラウドの Architect・2 回目 APPROVE）。PO の実装承認は 2026-11-19 の常時の指示「PRマージ、デプロイまで完走」で受けている。本番の GO は PO 本人の「GO #番号」が別に要る
- 危険便: はい（`migrations/` を含む）。担当は PR を作るまで。マージしない
- 担当: 実装 Sonnet（クラウド）／審査・GO 手順・マージ・反映確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§10） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§11） |
| 4 | 1便1目的 | ○（裏側で色を持って行き来させるだけ。画面は便2） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○ |
| 6 | 書式は実例で示した | ○（§4 に変更前後のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 は `-v` で試験名を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（行番号は origin/main 12000ef94 で確かめた。fba2172b8 から対象ファイルの差は 0） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§12） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 予定ごとの色 便1 の実行結果である」と書くこと。

## 1. 範囲

入れる（設計 §4-1〜§4-6）:
1. 色の一覧の正本 `backend/app/services/event_colors.py`（新規）
2. 移行 `migrations/20261119_120000_add_calendar_events_color_key.sql`（新規）と、その登録 4 か所・新しい会社の表の形
3. AI 用の写しの分類表に 1 行と、件数の試験・tsv・欄の試験
4. Google の道具 `backend/app/services/google_calendar.py` に名札の表を読む関数と、色の印の扱い
5. 予定の流れ `backend/app/services/calendar_service.py` に `color_key` を通す
6. 受け口 `backend/app/routers/calendar.py` に `color_key`
7. 取り込みの呼び元 `backend/app/services/google_webhook.py` で名札の表を渡す
8. 試験（§4-9）

入れない:
- 画面（`frontend/` のすべて）・色のトークン・トークンと値の一致の試験（便2）
- Google 側の名札を作る・変える・消すこと（`calendars.patch`）
- 古い `colorId` を書くこと
- `calendar_owner_settings`・持ち主の色
- `get_events`（`backend/app/services/google_calendar.py:349`）の呼び方

## 2. 前提の事実

| # | 事実 | 出典 |
|---|---|---|
| F1 | 色の欄は無い | `migrations/078_create_calendar_events_tenant.sql:44`〜`:66` |
| F2 | 受け口は `model_dump(exclude_none=True)` で渡す。`None` は落ちる | `backend/app/routers/calendar.py:440`・`:465` |
| F3 | 更新は、繰り返しでない予定なら `cal_svc.update_event`、繰り返しなら 3 択の道へ行く | `backend/app/routers/calendar.py:532`〜`:545` |
| F4 | Google の本文は `_to_google_event_body`（`:1446`）で作り、`_google_body_for`（`:169`）は表の 1 行から作る | `backend/app/services/calendar_service.py` |
| F5 | `_google_body_for` の呼び元は `:1062`・`:1121`・`:1138`・`:1177`・`:1200`。`_to_google_event_body` の直の呼び元は作成 `:436`・更新 `:539` | 同上（Architect 2 回目の `git grep` で 7 か所と確認） |
| F6 | 「この予定だけ」の道は `:1027`〜`:1065`。例外の行があれば `row = event` か `_find_exception(...)`、無ければ元の行から `_row_values` で作る | 同上 |
| F7 | Google の書き込みは `events().insert`（`backend/app/services/google_calendar.py:391`〜`:406`）と `events().patch`（`:411`〜`:426`）。Meet のときだけ `conferenceDataVersion=1` を足す（`:403`・`:423`） | 同上 |
| F8 | 取り込みは `upsert_from_google`（`backend/app/services/calendar_service.py:1342`）。呼び元は `backend/app/services/google_webhook.py:332` だけ。その前の `events().list` は `calendarId="primary"` 固定（`:300`〜`:314`） | 同上 |
| F9 | 移行の並びの末尾は `scripts/run_all_migrations.sh:1472`。新しい手順は `mr_report_summary` の行より上の末尾に足す決まり（`:1475` の注記） | 同上 |
| F10 | 移行の手本 `migrations/20261112_170000_add_calendar_events_recurrence.sql`（DO で `^tenant_\d+$` を回し、`NOT VALID` → `VALIDATE`） | 同上 |
| F11 | 分類表の件数の注記は 1163 行（`migrations/20261024_100300_create_ai_cloud_views.sql:3`）、試験は `backend/tests/ops/test_ai_cloud_views.py:486` で `== 1163` | 同上 |

## 3. 触るファイル（これ以外は触らない）

- 新規: `backend/app/services/event_colors.py`・`migrations/20261119_120000_add_calendar_events_color_key.sql`・`backend/tests/test_event_colors.py`
- 変更: `backend/app/services/calendar_service.py`・`backend/app/services/google_calendar.py`・`backend/app/services/google_webhook.py`・`backend/app/routers/calendar.py`・`backend/app/services/tenant.py`・`migrations/20261024_100300_create_ai_cloud_views.sql`・`docs/handoff/cloud-case-ai/stage1-column-class.tsv`・`scripts/run_all_migrations.sh`
- 試験の変更: `backend/tests/rls_bootstrap.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`・`backend/tests/test_tenant_loop_migration_guard.py`・`backend/tests/ops/test_ai_cloud_views.py`・`backend/tests/test_calendar_service.py`・`backend/tests/test_calendar_owner_api.py`
- このカード: `docs/handoff/event-color/card-bin1.md`（§13 の報告欄だけ追記してよい）

## 4. 作り方

### 4-1. `backend/app/services/event_colors.py`（新規）

設計 §4-1 のコードのとおり。`EVENT_COLORS` の 24 個の鍵と値は設計 §4-1 の表から 1 文字も変えずに写す。`key_for_hex` は前後の空白を落として小文字にしてから引き、無ければ `None`。`None` や空の文字を受けたら `None`。

### 4-2. 移行（新規 `migrations/20261119_120000_add_calendar_events_color_key.sql`）

手本（F10）の形で、欄 1 つと値の決まり 1 つだけ。値の決まりの式は 24 の鍵を `IN (...)` に並べる（並びは設計 §4-1 の表の順）。

```sql
-- ADR-1081 便1: 予定ごとの色（design.md §4-2）
-- 各会社の部屋の calendar_events に color_key（NULL＝デフォルト）と値の決まり 1 つを足す。何度流しても同じになる。
-- 欄は NULL 可なので表を書き直さない（ADR-1037 のロック待ちの決まりの中）。
DO $cal_color_key$
DECLARE
  schema_rec RECORD;
  tbl regclass;
BEGIN
  FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP
    IF to_regclass(format('%I.calendar_events', schema_rec.nspname)) IS NULL THEN
      CONTINUE;
    END IF;
    tbl := format('%I.calendar_events', schema_rec.nspname)::regclass;
    EXECUTE format('ALTER TABLE %s ADD COLUMN IF NOT EXISTS color_key TEXT', tbl);
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint WHERE conrelid = tbl AND conname = 'calendar_events_color_key_check'
    ) THEN
      EXECUTE format(
        'ALTER TABLE %s ADD CONSTRAINT calendar_events_color_key_check CHECK (color_key IN (%s)) NOT VALID',
        tbl,
        '''radicchio'',''cherry_blossom'', … 24 個 …'
      );
      EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT calendar_events_color_key_check', tbl);
    END IF;
  END LOOP;
END
$cal_color_key$;
```

`… 24 個 …` は省略の印。実物には 24 個すべてを書く（プレースホルダを残さない）。

登録（手本の繰り返しの移行の登録の仕方をなぞる）:
- `scripts/run_all_migrations.sh`: `:1472` の行（とその次のロールバック用の注記の行）の後、`mr_report_summary` の注記より上に、注記 1 行（`# ADR-1081 便1: 予定ごとの色（calendar_events に color_key・CHECK 1 つ・冪等）`）と `run_sql migrations/20261119_120000_add_calendar_events_color_key.sql` を足す。
- `backend/tests/rls_bootstrap.py`・`backend/tests/test_calendar_sync_tenant_reset_pg.py`・`backend/tests/test_tenant_loop_migration_guard.py`: 繰り返しの移行 `20261112_170000_add_calendar_events_recurrence.sql` が書かれている各所に、同じ形でこの移行を足す（`git grep -n 20261112_170000 -- backend/tests` で場所を出してから直す）。
- `backend/app/services/tenant.py`: `:1569`（`recurrence_rule text,`）の後に `color_key text,` を足し、値の決まり `CONSTRAINT calendar_events_color_key_check CHECK (color_key IN (...24 個...)),` を `:1575` の並びに足す。

### 4-3. AI 用の写しの分類表

設計 §4-3 のとおり 4 か所を同時に直す（手本 f0df9074a）:
- `migrations/20261024_100300_create_ai_cloud_views.sql` の `calendar_events` の行（`:371`〜`:375`）に `('tenant_*','calendar_events',ARRAY['color_key'],'allow','値の決まり calendar_events_color_key_check で値が限られる'),` を 1 行。`:3` の「1163 行」を「1164 行」に。
- `backend/tests/ops/test_ai_cloud_views.py:486` の `1163` を `1164` に。
- `docs/handoff/cloud-case-ai/stage1-column-class.tsv` の `calendar_events` の行（`:562`〜`:572`）の並びに `color_key` の行（allow・text）を 1 行。
- `backend/tests/ops/test_ai_cloud_views.py` に `test_t10_calendar_color_key_is_classified_on_bootstrapped_db` を `:587` の型で足す。

### 4-4. Google の道具（`backend/app/services/google_calendar.py`）

設計 §4-4 の 1〜3 のとおり。要点:
- 新しい関数 `async def get_event_label_colors(db, tenant_id, calendar_id: str) -> Optional[dict[str, str]]`。`calendars().get(calendarId=calendar_id)` を 1 回。`labelProperties.eventLabels` を「id → 色の値（小文字）」の表で返す。名札が無ければ `{}`、例外は `logger.warning` 1 行で `None`。
- `create_event`・`update_event` の中で、本文に `_sa_color_key` の鍵があるとき（値が `None` でも鍵があれば対象）:
  1. `color_key = body.pop("_sa_color_key")`
  2. 今使っているカレンダーの id（その関数がすでに使っている会社の設定の `calendar_id`・無ければ `primary`）で `get_event_label_colors` を呼ぶ
  3. 表が `None` → `eventLabelId` も `eventLabelVersion` も付けない
  4. 表がある → `color_key` が `None` なら `body["eventLabelId"] = ""`。鍵があれば `EVENT_COLORS[color_key]` と同じ値の名札の id、無ければ `""` と `logger.info("event_label_missing color_key=%s", color_key)`
  5. `events().insert(...)` / `events().patch(...)` の引数に `eventLabelVersion=1` を足す（`conferenceDataVersion` と同じ足し方。両方付くこともある）
- 鍵が無い本文は今と同じ。

### 4-5. 予定の流れ（`backend/app/services/calendar_service.py`）

設計 §4-5 のとおり。触る場所の一覧（すべて origin/main 12000ef94 の行）:
- `EVENT_COLUMNS`（`:151`）に `"color_key"`。
- 一覧の SELECT（`:251`〜）の最後に `ce.color_key`、返し（`:279` 付近）に `"color_key": r[<位置>]`。位置は SELECT の並びを数えて決める（審査の数えでは 22）。
- 作成の INSERT（`:402`〜`:418`）に `color_key` と `payload.get("color_key")`。
- `field_map`（`:490`〜`:499`）に `"color_key": "color_key"`。
- `_TEXT_FIELDS`（`:661`）・`:1030` の `("title", "description", "location")`・`:1188` の並びに `"color_key"`。`_row_values`（`:948`〜）・`:1098` にも足す。
- `_insert_row`（`:925`〜`:944`）の INSERT の欄と値に `color_key` / `:color_key`。
- `_to_google_event_body(payload, send_color: bool = False)`（`:1446`）: 末尾で `if send_color: body["_sa_color_key"] = payload.get("color_key")`。
- `_google_body_for(ev, send_color: bool = False)`（`:169`）: `_to_google_event_body` に渡す payload に `color_key` を入れ、`send_color` をそのまま渡す。

呼び元ごとの `send_color`（ここが Google の色を勝手に外さないための肝。全部この通りにする）:

| 呼び元 | `send_color` |
|---|---|
| 作成 `:436` | `payload.get("color_key") is not None` |
| 更新 `update_event`（`:480`〜）の `:539` | UPDATE の前に `SELECT color_key FROM calendar_events WHERE id = :id` で今の値 `prev` を読み、`"color_key" in payload and payload["color_key"] != prev` |
| 「この予定だけ」`:1062` | 直す前の行の色と比べる: `prev = (row if row is not None else master).get("color_key")` を `row_fields` を当てる前に取り、`"color_key" in payload and payload["color_key"] != prev`（設計 §4-5 の追記・Architect 2 回目 軽1） |
| 「これ以降」「すべて」で直す道 `:1138` | `"color_key" in plan["changed_fields"]` |
| 作る道 `:1121`・`:1177`・`:1200` | 渡す行の `color_key is not None` |

「この予定だけ」の前と後（`:1028` 付近）:

```python
# 前
        row = event if is_exc else await _find_exception(db, master["id"], occ)
        row_fields: dict = {k: payload[k] for k in ("title", "description", "location") if k in payload}
# 後
        row = event if is_exc else await _find_exception(db, master["id"], occ)
        prev_color = (row if row is not None else master).get("color_key")
        send_color = "color_key" in payload and payload["color_key"] != prev_color
        row_fields: dict = {
            k: payload[k] for k in ("title", "description", "location", "color_key") if k in payload
        }
```

そして `:1062` を `_google_body_for(row, send_color=send_color)` にする。

取り込み `upsert_from_google`（`:1342`）: 設計 §4-5 のとおり、引数 `label_colors: Optional[dict[str, str]] = None`。表があるときだけ `eventLabelId` → 色の値 → `key_for_hex` で鍵を出し、INSERT と `DO UPDATE SET` に `color_key` を入れる。表が `None` なら INSERT・UPDATE の両方で `color_key` に触らない（SQL を 2 通り持つか、`COALESCE` を使わず「触らない」を守る形にする。どちらでもよいが、表が `None` の更新で既存の色が NULL に変わらないことを試験で示す）。`colorId` だけの予定の数を `logger.info("event_color_legacy_colorid count=%d", n)` で 1 回の取り込みに 1 行。

### 4-6. 取り込みの呼び元（`backend/app/services/google_webhook.py`）

`:332` の `upsert_from_google` を呼ぶ前（1 回の取り込みに 1 回）に `label_colors = await get_event_label_colors(db, tenant_id, "primary")` を呼び、`upsert_from_google(..., label_colors=label_colors)` で渡す。

### 4-7. 受け口（`backend/app/routers/calendar.py`）

- `CreateEventBody`（`:114`）・`UpdateEventBody`（`:126`）に `color_key: Optional[str] = None`。
- 値の確かめ: 24 の鍵と `""` だけを受け、それ以外は 422。一覧は `EVENT_COLOR_KEYS` から取る（書き写さない）。pydantic の `field_validator` で書く。
- `:440` の作成と `:465` の更新の `model_dump(exclude_none=True)` の直後で、`payload.get("color_key") == ""` なら `payload["color_key"] = None`（鍵は残す）。作成は `payload=body.model_dump(...)` を一度変数に受けてから直す。

### 4-8. 版の確かめ（U1）

設計 §4-4 の 4。`backend/tests/test_event_colors.py` に、`googleapiclient.discovery` の手元の API 説明（`build_from_document` か、道具の部品に入っている `calendar.v3.json`）で `events.insert`・`events.patch` の引数に `eventLabelVersion` があることを確かめる試験を書く。ネットに出ない形で書く。部品に入っている説明の置き場が分からなければ、その原文を報告に貼って NEEDS_DECISION:。

### 4-9. 試験（設計 §9 の便1 の行をすべて）

| 試験 | 置き場 |
|---|---|
| `EVENT_COLORS` が 24 個・値が `#` と 6 桁の小文字・`key_for_hex` が大文字も引ける・無い値は None | `backend/tests/test_event_colors.py` |
| U1（§4-8） | 同上 |
| 移行が冪等で、全社の `calendar_events` に欄と値の決まりができる（2 回流して同じ）・`'red'` は値の決まりの違反 | `backend/tests/test_calendar_sync_tenant_reset_pg.py` |
| 受け口が 24 の鍵と `""` だけを受ける（`'red'` は 422） | `backend/tests/test_calendar_owner_api.py` |
| 作成で色ありなら Google に `eventLabelId` と `eventLabelVersion=1`、色なしなら付けない | `backend/tests/test_calendar_service.py`（Google の道具は偽物） |
| 更新で色を変えたら送る・同じ色なら付けない・`""` でデフォルトに戻すと `eventLabelId=""` と版 | 同上 |
| 名札の表が `None` なら版の指定を付けない | 同上 |
| 取り込みで `eventLabelId` から鍵を書く・表が `None` なら既存の色を変えない・`colorId` だけは NULL | 同上 |
| 3 択それぞれで色が正しい行に入る（例外の回・これ以降の新しい予定を含む）・`""` を送っても値の決まりに当たらない | 同上 |
| 色に触らない保存では版の指定が付かない（作成・更新・3 択） | 同上 |
| 「この予定だけ」で例外の行の色を元の行と同じ色に戻すと Google に送る | 同上 |
| 分類表の件数 1164・欄の分類 | `backend/tests/ops/test_ai_cloud_views.py` |

## 5. 確かめ方（担当が実行し、出力を報告に貼る。生出力は作業場所の外の /tmp/CC報告ファイル/event-color/bin1/ に置く）

1. 新しく足した試験と、触った試験ファイルを `-v` で流す: `cd <作業場所>/backend && python -m pytest tests/test_event_colors.py tests/test_calendar_service.py tests/test_calendar_owner_api.py -v > /tmp/CC報告ファイル/event-color/bin1/pytest.txt 2>&1; echo rc=$?; grep -c PASSED /tmp/CC報告ファイル/event-color/bin1/pytest.txt; grep -E "FAILED|ERROR" /tmp/CC報告ファイル/event-color/bin1/pytest.txt | head -20`。DB が要る試験が手元で流せないときは「流せなかった」と書き、CI に任せる（記録のみで続行）。
2. 値の一覧を書き写していないこと: `git grep -n "cherry_blossom" -- backend/app` の結果が `backend/app/services/event_colors.py` だけ（`tenant.py` の値の決まりと移行の SQL は別に数え、件数を報告する）。
3. 触ったファイルが §3 だけで、main との差に削除の塊が無いこと: `git diff --stat origin/main...HEAD` を貼る。

## 6. 分岐ごとの対処

- §2 の行や §4 の「前」のコードが作業場所の origin/main と合わない → 合わない部分の原文を貼って NEEDS_DECISION:（直さずに止める）
- 一覧の SELECT の位置が 22 でない → 数えた位置で作り、その数え方を報告に書く（記録のみで続行）
- U1 の試験が落ちる（部品が `eventLabelVersion` を受けない）→ 試験は消さず、落ちた原文を貼って NEEDS_DECISION:
- CI の pytest が落ちる → 担当は待たない。Opus が読む

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| §4-9 の試験がすべて pass | CI の pytest の記録で試験名が passed |
| 色に触らない保存で Google の色を外さない | 同上（§4-9 の該当の試験） |
| 24 色の正本が 1 か所 | §5-2 |
| 触ったファイルが §3 だけ | §5-3 |
| 必須チェックがすべて緑 | PR の checks |

## 8. 反映の手順（Opus が行う。担当はしない）

1. CI 緑 → 審査役（reviewer・opus）APPROVE → PR に「確認済み：」コメント。
2. 危険 PR の GO 手順（ADR-136）: PO に対象・変更 3 行・直前の写しの確認を出し、PO 本人の「GO #番号」を受けるまでマージしない。
3. マージ後、配備の記録で移行が流れたこと、全社の `calendar_events` に `color_key` があることを読み取り専用の鍵で確かめる。

## 9. 弊害と戻し方

- 欄は NULL 可で、古いコードは読まない。戻すときはコードの PR を戻すだけ（欄は残す。消す移行は作らない）。
- Google の色を外す危険は §4-5 の表で防ぐ。試験で縛る。

## 10. PR

- 作業場所: `cd /Users/tanizawashingo/salesanchor && bash scripts/new-worktree.sh release/event-color-bin1 --claude`（origin/main 起点）。クラウドで clone した場合も、commit の前に必ずこの手順で作業場所を作る。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめる。以後の作業はすべてその作業場所に `cd` してから行う
- push は `git push -u origin HEAD`。commit の後に `git log -1 --oneline`、push の後に `git log origin/release/event-color-bin1 -1 --oneline` で実在を確かめる。`--no-verify` は使わない
- PR は `scripts/gh-pr-create-safe.sh` に、先に Write ツールで作った本文ファイルを絶対パスで渡して作る（`$変数` を使わない）
- 作成前に `gh auth status` で `shingo-cc` 名義であることを確かめる
- PR は ready で作る（`--draft` を付けない）。base は main。担当はマージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に、recon（docs/handoff/event-color/recon.md）・設計（docs/handoff/event-color/design.md）・このカード・ADR-1081 を書く。危険 PR なので `### GO記録` の欄は見出しだけ置き、中身は空（Opus が PO の GO の後に書く）
- `触るファイル:` と `削除するファイル:` は 1 行・カンマ区切り・バッククォートなし・注記なし。良い例: `触るファイル: backend/app/services/event_colors.py, backend/app/services/calendar_service.py` ／ 禁止形: 行を分ける・バッククォートで囲む・「（新規）」などの注記を付ける
- 作成前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し exit 0 を確かめる（2 分以上かかるので timeout を長めにする）

## 11. 報告

- 完了報告の本文に: 冒頭の受領文／§5-1〜5-3 の出力（長いものは生出力のパスと要点の行）／PR の URL／判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文
- 1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか

## 12. 委任の定型

- sleep しない。CI・デプロイは待たない（待ちは Opus が行う）
- ファイルの作成と編集は Write/Edit ツールで行う（ヒアドキュメントで書かない）
- PR を作る前に `scripts/dev/validate-pr-body.sh` で exit 0 を確かめる
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 13. 報告欄（担当が追記）

（未記入）

以上（カードの終わり）
