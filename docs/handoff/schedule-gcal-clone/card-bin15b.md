# 実装カード schedule-gcal-clone 便15B — 予定の繰り返しの画面（選ぶ欄・詳しくの行・3 択の小窓・文言・試験）

> この文書は何か：予定の画面を Google カレンダーと同じ使い心地にする件の便15B（画面）の作業指示書です。便15A（裏側・PR #5454 本番済み）で受け口ができた繰り返しを、編集画面の選ぶ欄・詳しくの小窓の 1 行・直す／消す／動かすときの 3 択の小窓で使えるようにします。裏側は一覧の 1 件ごとに「1 回目か」の真偽を足すだけです。

- 設計: docs/handoff/schedule-gcal-clone/design.md §12.6・§12.6.1（G1〜G10）・§12.2 の成功条件 G69〜G75・G79。ADR-1075（Proposed）
- 状態: 設計 §12 は審査15 で APPROVE。§12.6.1 は本カードと同じ PR で足す細部。成功条件 G69〜G79 と実装の開始は PO 承認済み（2026-11-12 選択「1」・画面の部分は 2026-11-12 選択「1」）。本カードは設計の範囲を変えない
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番の `scripts/` を含まない）
- 担当: 実装 Sonnet（クラウド）／PR 作成・審査・マージ・本番反映の確認 Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§8） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§9） |
| 4 | 1便1目的 | ○（繰り返しの画面だけ。裏側は一覧の 1 欄だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/schedule-recurrence-frontend） |
| 6 | 書式は実例で示した | ○（§4 に変更前後のコード） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の 3・4 は試験の名前ごとの結果を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○（どれも `tail -n` か `head -n`） |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§9・受領確認・末尾） |
| 11 | 期待値は実物から | ○（行番号は origin/main 7c3d4adc6 で確かめた。b6b444eff から対象 14 件に差分なし） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§10） |

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1 手順 1 コマンド・出力に上限・プレースホルダなし）・11-lint.md（L01〜L33）。照合: `gh pr create` なし（L08）・`rm ` なし（L11）・`timeout ` なし（L16）・`--admin` `--auto` なし（L18）・`gh run view` なし（L21）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード schedule-gcal-clone 便15B の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. 裏側: 一覧 `list_events` の 1 件ごとに `is_first_occurrence`（真偽）を足す（§4-1）
2. 422 の文: 8 つの識別の文字を画面の共通の表に足し、ja・en の `apiError` に文を足す（§4-2）
3. 文言: ja・en の `schedule.recurrence`（§4-3）
4. `schedule-utils.ts`: 一覧の 4 欄＋1 欄を受ける・回ごとに違う id・選び方の並びと文字・3 択の並び（§4-4）
5. 編集画面: 終日のチェックの右に選ぶ欄・Meet の行の出し分け（§4-5）
6. ページ: 詳しくの小窓の 1 行・保存／削除／動かすときの 3 択の小窓・Esc の守り（§4-6）
7. CSS の 2 クラス（§4-7）
8. 試験（§4-8）

入れない:
- 作る小窓（appearance="popover"）の選ぶ欄（Google と同じく、選ぶ欄は全画面の編集だけ）
- スマホ幅の画面（Android 側の担当）
- `custom`（7 つの値で表せない決まり）を選ぶ・直す画面
- `migrations/`・`.github/workflows/`・`deploy.yml`・secrets・本番
- 台帳 `.claude-pipeline/active-work.d/release-schedule-recurrence-frontend.md` の commit（作るが commit しない）

## 2. 前提の事実（origin/main 7c3d4adc6）

- 受け口 `backend/app/routers/calendar.py:110-137`: `RecurrenceValue` は `none` `daily` `weekly` `monthly_nth` `monthly_last` `yearly` `weekdays` の 7 つ（`custom` は送れない）。`RecurrenceScope` は `this` `following` `all`。直す本文は `recurrence`・`scope`・`occurrence_start`。消すは問い合わせの `scope`・`occurrence_start`。422 の `detail` は 8 つの識別の文字（`:427` ほか）。
- 判定 `backend/app/services/calendar_service.py` `check_recurrence_request`: 単発に `scope` → `recurrence_scope_not_allowed`／繰り返しに `scope` 無し → `recurrence_scope_required`／`this` で `calendar_type` を変える・選び方を変える → `recurrence_this_not_allowed`／1 回目への `following` は `all` と同じに扱う。
- 決まりの作り方 `build_rule`: `monthly_nth` は開始日が 1〜28 日のときだけ、`monthly_last` は開始日の 7 日後が別の月のときだけ。ほかの決まりは `rule_to_recurrence` が `"custom"` を返す。
- 一覧 `list_events`: 予定 1 行の読み方 `_item`（`calendar_service.py:271-296`）。元の行が同じ結果に無いときの引き直し（`:302-308`）。広げた回（`:346-358`）。1 回目の判定 `rec.is_first_occurrence(元の始まり, 終日か, 回の始まり)`（`backend/app/services/calendar_recurrence.py:233`）。
- 画面: `frontend/src/pages/schedule/SchedulePageImpl.tsx` の `saveEvent`（`:961`）・`deleteEvent`（`:1006`）・`patchMoved`（`:1192`）・近道（`:1221`）・近道の一覧（`:1539`）・全画面の編集の `onClose`（`:1566`）。詳しくの小窓の日時の行（`:349`）。
- 部品: 金型 `ConfirmModal`（default export。`open` `title` `message`（ReactNode）`confirmLabel` `cancelLabel` `onConfirm` `onCancel`。中は金型 Modal の size sm）。金型 `Radio`（named export・`label` は t() 済みの文字・`<label htmlFor>` で包むので名前は label）。金型 Modal と金型 EditorPage はどちらも document の keydown で Esc を受ける（`frontend/src/components/Modal.tsx:79`・`frontend/src/components/EditorPage.tsx:76`）。同じ document の上なので `stopPropagation` ではもう一方は止まらない。
- 誤りの文の表 `frontend/src/lib/apiErrorReason.ts:11-21`（9 行）。突き合わせの試験 `frontend/src/lib/apiErrorReason.test.ts:76`（`toBe(9)`）と `backend/tests/test_api_error_reason_sync.py:41-51`（9 個の並び）。CI の `check-error-text-next-action.js` は ja の文が「失敗・エラー・できません」を含むとき「もう一度・お試し・連絡・確認して・ください」のどれかを求める。
- 本カードで決めた細部（設計 §12.6.1 と同じ）:
  1. 回の始まりは id から読み直さず、一覧の 1 件に `occurrenceStart` として持たせる（§12.6 の「id から回の始まり」の書き方を置き換える）。id は回ごとに元の行の id と回の元の始まりのミリ秒をつないだ形（例 `event-12-1762909200000`）にし、`eventNumericId` はその前半の数を返す。
  2. 3 択の小窓は 1 つの状態 `scopeRequest`（何をするか・選べる値・OK で呼ぶ関数・キャンセルで呼ぶ関数）で開く。
  3. 選べる値は `scopeChoices`（§4-4）1 か所で決める。

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `backend/app/services/calendar_service.py` | 一覧に `is_first_occurrence`（§4-1） |
| `backend/tests/test_calendar_service.py` | `TestListRecurrence` に試験 3 つ（§4-8） |
| `backend/tests/test_api_error_reason_sync.py` | 並びに 8 個（§4-2） |
| `frontend/src/lib/apiErrorReason.ts` | 表に 8 行（§4-2） |
| `frontend/src/lib/apiErrorReason.test.ts` | `toBe(9)` → `toBe(17)`（§4-2） |
| `frontend/src/locales/ja.json` | `schedule.recurrence` と `apiError` の 8 つ（§4-2・§4-3） |
| `frontend/src/locales/en.json` | 同じキー（§4-2・§4-3） |
| `frontend/src/pages/schedule/schedule-utils.ts` | 型・`normalizeEvent`・`eventNumericId`・新しい関数（§4-4） |
| `frontend/src/pages/schedule/schedule-utils.test.ts` | 試験の追加（§4-8） |
| `frontend/src/pages/schedule/ScheduleDraftFields.tsx` | 選ぶ欄・Meet の行（§4-5） |
| `frontend/src/pages/schedule/ScheduleFullEditor.tsx` | `item` を渡す 1 か所（§4-5） |
| `frontend/src/pages/schedule/SchedulePageImpl.tsx` | 下書き・詳しくの行・3 択（§4-6） |
| `frontend/src/pages/schedule/SchedulePageImpl.test.tsx` | 試験の追加（§4-8） |
| `frontend/src/pages/schedule.css` | 2 クラス（§4-7） |

## 4. 変更前後

### 4-1. 一覧に `is_first_occurrence`（`backend/app/services/calendar_service.py`）

1. `_item`（`:271-296`）の最後の行 `"occurrence_start": ...,` の次に 1 行足す:

```python
            "is_first_occurrence": bool(r[19]) and r[20] is None,
```

（元の行は真、単発の行は偽。例外の行と広げた回は下で上書きする）

2. 変更前（`:298-308`）:

```python
    masters = [r for r in rows if r[19]]
    master_rules: dict = {r[0]: r[19] for r in masters}
    exception_rows = [r for r in rows if r[20] is not None]
    # 例外の行の recurrence は元の行の選び方。同じ結果に元の行が無いときだけ 1 本で引く
    missing_ids = sorted({r[20] for r in exception_rows if r[20] not in master_rules})
    if missing_ids:
        found = await db.execute(
            text("SELECT id, recurrence_rule FROM calendar_events WHERE id = ANY(:ids)"),
            {"ids": missing_ids},
        )
        for mid, mrule in found.fetchall():
            master_rules[mid] = mrule
```

変更後:

```python
    masters = [r for r in rows if r[19]]
    master_rules: dict = {r[0]: r[19] for r in masters}
    # 1 回目かの判定に使う元の行の始まりと終日（design §12.6.1 G1）
    master_starts: dict = {r[0]: (r[7], bool(r[9])) for r in masters}
    exception_rows = [r for r in rows if r[20] is not None]
    # 例外の行の recurrence と 1 回目かは元の行から決める。同じ結果に元の行が無いときだけ 1 本で引く
    missing_ids = sorted({r[20] for r in exception_rows if r[20] not in master_rules})
    if missing_ids:
        found = await db.execute(
            text("SELECT id, recurrence_rule, start_datetime, is_all_day FROM calendar_events WHERE id = ANY(:ids)"),
            {"ids": missing_ids},
        )
        for mid, mrule, mstart, mall_day in found.fetchall():
            master_rules[mid] = mrule
            master_starts[mid] = (mstart, bool(mall_day))
```

3. 変更前（`:310-317` の中）:

```python
        item = _item(r)
        if r[20] is not None:
            item["recurrence"] = rec.rule_to_recurrence(master_rules.get(r[20]))
        items.append(item)
```

変更後:

```python
        item = _item(r)
        if r[20] is not None:
            item["recurrence"] = rec.rule_to_recurrence(master_rules.get(r[20]))
            ms = master_starts.get(r[20])
            item["is_first_occurrence"] = bool(
                ms and ms[0] and r[21] and rec.is_first_occurrence(ms[0], ms[1], r[21])
            )
        items.append(item)
```

4. 広げた回（`:346-358`）の `item["occurrence_start"] = occ.isoformat()` の次に 1 行足す:

```python
                item["is_first_occurrence"] = rec.is_first_occurrence(m_start, all_day, occ)
```

### 4-2. 422 の文（ADR-1071）

`frontend/src/lib/apiErrorReason.ts` の表の最後の行 `merge_target_archived: "apiError.mergeTargetArchived",` の次に 8 行:

```ts
  recurrence_meet_not_allowed: "apiError.recurrenceMeetNotAllowed",
  recurrence_not_available: "apiError.recurrenceNotAvailable",
  recurrence_after_until: "apiError.recurrenceAfterUntil",
  recurrence_scope_not_allowed: "apiError.recurrenceScopeNotAllowed",
  recurrence_google_source: "apiError.recurrenceGoogleSource",
  recurrence_scope_required: "apiError.recurrenceScopeRequired",
  recurrence_occurrence_invalid: "apiError.recurrenceOccurrenceInvalid",
  recurrence_this_not_allowed: "apiError.recurrenceThisNotAllowed",
```

`frontend/src/lib/apiErrorReason.test.ts:76` の `toBe(9)` → `toBe(17)`。

`backend/tests/test_api_error_reason_sync.py` `test_table_rows_are_read` の並びの最後 `"merge_target_archived",` の次に、上と同じ順で 8 個の識別の文字（`"recurrence_meet_not_allowed",` … `"recurrence_this_not_allowed",`）。

`ja.json` と `en.json` の `apiError` の `"mergeTargetArchived"`（どちらも 6149 行目）の次に 8 つ（en の `"` は JSON の中なので `\"` と書く）:

| キー | ja | en |
|---|---|---|
| `recurrenceMeetNotAllowed` | 繰り返しの予定には Google Meet を付けられません。Meet を外すか、繰り返さない予定にしてから保存してください。 | Google Meet can't be added to a recurring event. Remove Meet or set it to not repeat, then save again. |
| `recurrenceNotAvailable` | この開始日ではその繰り返しは選べません。繰り返しの選び方か開始日を変えてから保存してください。 | That repeat option can't be used with this start date. Change the repeat option or the start date, then save again. |
| `recurrenceAfterUntil` | 新しい開始日が、繰り返しの終わりの日より後になっています。開始日を終わりの日より前にしてから保存してください。 | The new start date is after the date the repeat ends. Choose a start date before that date, then save again. |
| `recurrenceScopeNotAllowed` | この予定は繰り返しの予定ではないため、対象の選び方は使えません。画面を読み込み直してからもう一度お試しください。 | This event doesn't repeat, so you can't choose which events to change. Reload the page and try again. |
| `recurrenceGoogleSource` | Google カレンダーから取り込んだ予定には繰り返しを付けられません。Google カレンダーで設定してください。 | You can't set a repeat on an event imported from Google Calendar. Set it in Google Calendar instead. |
| `recurrenceScopeRequired` | 繰り返しの予定では、変える対象（この予定・これ以降・すべて）を選ぶ必要があります。画面を読み込み直してからもう一度お試しください。 | For a recurring event, choose which events to change (this, following, or all). Reload the page and try again. |
| `recurrenceOccurrenceInvalid` | 選んだ回が見つかりませんでした。予定が変わった可能性があります。画面を読み込み直してからもう一度お試しください。 | The selected occurrence wasn't found. The event may have changed. Reload the page and try again. |
| `recurrenceThisNotAllowed` | 「この予定」だけでは、繰り返しの選び方や社員への見せ方を変えられません。「これ以降のすべての予定」か「すべての予定」を選んでください。 | You can't change the repeat or who can see it for just this event. Choose "This and following events" or "All events". |

### 4-3. 文言 `schedule.recurrence`

`ja.json` と `en.json` の `schedule` の `"shareWithStaff"`（どちらも 3413 行目）の次に、入れ子の 1 つのまとまり `"recurrence": { ... }` を足す:

| キー | ja | en |
|---|---|---|
| `label` | 繰り返し | Repeat |
| `none` | 繰り返さない | Does not repeat |
| `daily` | 毎日 | Daily |
| `weekly` | 毎週 {{weekday}} | Weekly on {{weekday}} |
| `monthlyNth` | 毎月 {{ordinal}} {{weekday}} | Monthly on the {{ordinal}} {{weekday}} |
| `ordinal1` | 第 1 | first |
| `ordinal2` | 第 2 | second |
| `ordinal3` | 第 3 | third |
| `ordinal4` | 第 4 | fourth |
| `monthlyLast` | 毎月 最終{{weekday}} | Monthly on the last {{weekday}} |
| `yearly` | 毎年 {{date}} | Annually on {{date}} |
| `weekdays` | 毎週平日（月～金） | Every weekday (Monday to Friday) |
| `editTitle` | 定期的な予定の編集 | Edit recurring event |
| `deleteTitle` | 定期的な予定の削除 | Delete recurring event |
| `scopeThis` | この予定 | This event |
| `scopeFollowing` | これ以降のすべての予定 | This and following events |
| `scopeAll` | すべての予定 | All events |

### 4-4. `frontend/src/pages/schedule/schedule-utils.ts`

1. `ApiCalendarEvent`（`:15-35`）の最後 `meet_url?: string | null;` の次に:

```ts
  recurrence_rule?: string | null;
  recurrence?: string | null;
  recurring_event_id?: number | null;
  occurrence_start?: string | null;
  is_first_occurrence?: boolean;
```

2. `ScheduleItem`（`:49-66`）の最後 `googleEventId?: string | null;` の次に:

```ts
  /** 繰り返しの選び方（design §12.6）。単発は "none" */
  recurrence?: ScheduleRecurrence;
  /** 回のとき元の行の id。単発は null */
  recurringEventId?: number | null;
  /** 回の元の始まり（直した回でも元の日時）。単発は null */
  occurrenceStart?: Date | null;
  /** 1 回目の回か（サーバーが決める・§12.6.1 G1） */
  isFirstOccurrence?: boolean;
```

3. `normalizeEvent`（`:339-363`）。変更前:

```ts
  const ownerName = event.owner_name ?? event.created_by_name ?? null;
  return {
    id: `event-${event.id}`,
```

変更後:

```ts
  const ownerName = event.owner_name ?? event.created_by_name ?? null;
  const occurrenceStart = event.occurrence_start ? parseLocalDate(event.occurrence_start) : null;
  return {
    // 回は同じ元の行から何件も出るので、回の元の始まりで id を分ける（design §12.6.1）
    id: occurrenceStart ? `event-${event.id}-${occurrenceStart.getTime()}` : `event-${event.id}`,
```

同じ関数の最後 `googleEventId: event.google_event_id ?? null,` の次に:

```ts
    recurrence: toScheduleRecurrence(event.recurrence),
    recurringEventId: event.recurring_event_id ?? null,
    occurrenceStart,
    isFirstOccurrence: event.is_first_occurrence === true,
```

4. `eventNumericId`（`:407-411`）。変更前:

```ts
/** "event-12" → 12。シフト・仮の箱など予定でない id は null */
export function eventNumericId(id: string): number | null {
  const m = /^event-(\d+)$/.exec(id);
```

変更後:

```ts
/** "event-12" と回の "event-12-1762909200000" → 12。シフト・仮の箱など予定でない id は null */
export function eventNumericId(id: string): number | null {
  const m = /^event-(\d+)(?:-\d+)?$/.exec(id);
```

5. ファイルの最後に足す（`Translate` と `addDays` は同じファイルにある）:

```ts
/** 繰り返しの選び方（backend/app/routers/calendar.py の RecurrenceValue と、表せない決まりの "custom"） */
export type ScheduleRecurrence =
  | "none" | "daily" | "weekly" | "monthly_nth" | "monthly_last" | "yearly" | "weekdays" | "custom";

const RECURRENCE_VALUES: readonly ScheduleRecurrence[] = [
  "none", "daily", "weekly", "monthly_nth", "monthly_last", "yearly", "weekdays", "custom",
];

export function toScheduleRecurrence(value: string | null | undefined): ScheduleRecurrence {
  return RECURRENCE_VALUES.includes(value as ScheduleRecurrence) ? (value as ScheduleRecurrence) : "none";
}

/** 開始日で選べる値（design §12.2 G70。サーバーの build_rule と同じ決まり） */
export function recurrenceChoicesFor(date: Date): ScheduleRecurrence[] {
  const choices: ScheduleRecurrence[] = ["none", "daily", "weekly"];
  if (date.getDate() <= 28) choices.push("monthly_nth");
  if (addDays(date, 7).getMonth() !== date.getMonth()) choices.push("monthly_last");
  choices.push("yearly", "weekdays");
  return choices;
}

/** 選ぶ欄に並べる値。すでに繰り返している予定の今の値（keep）は開始日で選べなくても残す（§12.6.1 G5） */
export function recurrenceOptionsFor(date: Date, keep: ScheduleRecurrence | null): ScheduleRecurrence[] {
  const choices = recurrenceChoicesFor(date);
  return RECURRENCE_VALUES.filter((v) => v !== "custom" && (choices.includes(v) || v === keep));
}

const ORDINAL_KEYS = [
  "schedule.recurrence.ordinal1",
  "schedule.recurrence.ordinal2",
  "schedule.recurrence.ordinal3",
  "schedule.recurrence.ordinal4",
] as const;

/** 選び方の文字（例「毎週 木曜日」）。日付が読めないときと custom は空 */
export function recurrenceLabel(value: ScheduleRecurrence, date: Date, t: Translate, language: string): string {
  if (Number.isNaN(date.getTime())) return "";
  const weekday = new Intl.DateTimeFormat(language, { weekday: "long" }).format(date);
  switch (value) {
    case "none":
      return t("schedule.recurrence.none");
    case "daily":
      return t("schedule.recurrence.daily");
    case "weekly":
      return t("schedule.recurrence.weekly", { weekday });
    case "monthly_nth":
      return t("schedule.recurrence.monthlyNth", {
        ordinal: t(ORDINAL_KEYS[Math.min(Math.ceil(date.getDate() / 7), 4) - 1]),
        weekday,
      });
    case "monthly_last":
      return t("schedule.recurrence.monthlyLast", { weekday });
    case "yearly":
      return t("schedule.recurrence.yearly", {
        date: new Intl.DateTimeFormat(language, { month: "long", day: "numeric" }).format(date),
      });
    case "weekdays":
      return t("schedule.recurrence.weekdays");
    default:
      return "";
  }
}

/** 新しい予定・単発の予定で開始日を変えたとき、使えなくなった「第 N」「最終」をもう一方へ入れ替える（§12.6.1 G5） */
export function fitRecurrenceToDate(value: ScheduleRecurrence, date: Date): ScheduleRecurrence {
  if (Number.isNaN(date.getTime())) return value;
  if (value !== "monthly_nth" && value !== "monthly_last") return value;
  if (recurrenceChoicesFor(date).includes(value)) return value;
  return value === "monthly_nth" ? "monthly_last" : "monthly_nth";
}

export type RecurrenceScope = "this" | "following" | "all";
export type ScopeKind = "save" | "delete" | "move";

/**
 * 3 択の小窓に出す値（design §12.2 G73・G75・G79、§12.6.1 G9）。
 * changesSeries は「選び方か社員への見せ方を変えた」（サーバーは「この予定」で 422 にする）。
 */
export function scopeChoices(kind: ScopeKind, isFirst: boolean, changesSeries: boolean): RecurrenceScope[] {
  if (kind === "move") return isFirst ? ["this", "all"] : ["this", "following"];
  if (kind === "save" && changesSeries) return isFirst ? ["all"] : ["following", "all"];
  return isFirst ? ["this", "all"] : ["this", "following", "all"];
}

/** 繰り返しの予定の回（または検索で返る元の行）か */
export function isRecurringItem(item: ScheduleItem): boolean {
  return item.recurringEventId != null || (item.recurrence != null && item.recurrence !== "none");
}

/** 送る回の始まり。回の元の始まりが無いとき（検索で返る元の行）は予定の始まり */
export function occurrenceStartOf(item: ScheduleItem): Date {
  return item.occurrenceStart ?? item.start;
}
```

### 4-5. 編集画面の選ぶ欄（`ScheduleDraftFields.tsx`・`ScheduleFullEditor.tsx`）

1. `ScheduleDraftFields.tsx:21` の読み込みを変える。変更前:

```ts
import { formatDraftDateLine, shiftDraftStart, type ScheduleItem } from "./schedule-utils";
```

変更後:

```ts
import {
  combineDateTime,
  fitRecurrenceToDate,
  formatDraftDateLine,
  isRecurringItem,
  occurrenceStartOf,
  recurrenceLabel,
  recurrenceOptionsFor,
  shiftDraftStart,
  type ScheduleItem,
  type ScheduleRecurrence,
} from "./schedule-utils";
```

2. `DraftDateFields`（`:94-101`）の引数（同じ形の引数がほかに 2 つあるので `mode,` の行から合わせる）。変更前:

```tsx
  mode,
  draft,
  onDraftChange,
  creating = false,
  expanded = false,
}: FieldProps & { creating?: boolean; expanded?: boolean }) {
```

変更後:

```tsx
  mode,
  draft,
  onDraftChange,
  creating = false,
  expanded = false,
  item = null,
}: FieldProps & { creating?: boolean; expanded?: boolean; item?: ScheduleItem | null }) {
```

3. 同じ関数の `changeStartDate`・`changeStartTime`（`:115-118`）。変更前:

```tsx
  const changeStartDate = (value: string) =>
    onDraftChange(shiftsStart ? shiftDraftStart(draft, value, draft.startTime) : { ...draft, startDate: value });
  const changeStartTime = (value: string) =>
    onDraftChange(shiftsStart ? shiftDraftStart(draft, draft.startDate, value) : { ...draft, startTime: value });
```

変更後:

```tsx
  // 繰り返し（design §12.6・§12.6.1 G4・G5）。Google から取り込んだ予定・Meet のある予定・custom の予定には出さない
  const series = item ? isRecurringItem(item) : false;
  const startDay = combineDateTime(draft.startDate, "00:00");
  const labelDay = Number.isNaN(startDay.getTime()) ? (item ? occurrenceStartOf(item) : new Date()) : startDay;
  const keepRecurrence = series && item?.recurrence ? item.recurrence : null;
  const recurrenceOptions = recurrenceOptionsFor(labelDay, keepRecurrence);
  const showRecurrence = item?.source !== "google" && !item?.meetUrl && draft.recurrence !== "custom";
  const changeRecurrence = (value: ScheduleRecurrence) =>
    onDraftChange({ ...draft, recurrence: value, addMeet: value === "none" ? draft.addMeet : false });
  const fitRecurrence = (next: ScheduleDraft): ScheduleDraft =>
    series ? next : { ...next, recurrence: fitRecurrenceToDate(next.recurrence, combineDateTime(next.startDate, "00:00")) };

  const changeStartDate = (value: string) =>
    onDraftChange(fitRecurrence(shiftsStart ? shiftDraftStart(draft, value, draft.startTime) : { ...draft, startDate: value }));
  const changeStartTime = (value: string) =>
    onDraftChange(fitRecurrence(shiftsStart ? shiftDraftStart(draft, draft.startDate, value) : { ...draft, startTime: value }));
```

4. 同じ関数の page の枝の終日の段（`:158-164`）。変更前:

```tsx
        <div>
          <Checkbox
            label={t("schedule.allDay")}
            checked={draft.allDay}
            onChange={(event) => changeAllDay(event.target.checked)}
          />
        </div>
```

変更後:

```tsx
        <div className="schedule-editor-all-day-row">
          <Checkbox
            label={t("schedule.allDay")}
            checked={draft.allDay}
            onChange={(event) => changeAllDay(event.target.checked)}
          />
          {showRecurrence && (
            <SelectControl
              variant="editor-filled"
              aria-label={t("schedule.recurrence.label")}
              value={draft.recurrence}
              onChange={(event) => changeRecurrence(event.target.value as ScheduleRecurrence)}
            >
              {recurrenceOptions.map((value) => (
                <option key={value} value={value}>
                  {recurrenceLabel(
                    value,
                    value === keepRecurrence && item ? occurrenceStartOf(item) : labelDay,
                    t,
                    i18n.language,
                  )}
                </option>
              ))}
            </SelectControl>
          )}
        </div>
```

popover の枝（作る小窓）は変えない。

5. `DraftMeetField` の `addRow`（`:298`）。変更前:

```tsx
  const addRow =
    meetAvailable && !item?.meetUrl ? (
```

変更後（繰り返しの予定には Meet を付けない・サーバーは 422 `recurrence_meet_not_allowed`）:

```tsx
  const addRow =
    meetAvailable && !item?.meetUrl && draft.recurrence === "none" ? (
```

6. `ScheduleFullEditor.tsx:79`。変更前:

```tsx
          <DraftDateFields {...common} mode={mode} />
```

変更後:

```tsx
          <DraftDateFields {...common} mode={mode} item={item} />
```

### 4-6. ページ（`SchedulePageImpl.tsx`）

1. 読み込み: `./schedule-utils` からの読み込み（`:33-69`）に `isRecurringItem`・`occurrenceStartOf`・`recurrenceLabel`・`scopeChoices`・`type RecurrenceScope`・`type ScheduleRecurrence`・`type ScopeKind` を足す。`:21` の `Modal` の次に 2 行:

```ts
import ConfirmModal from "../../components/ConfirmModal";
import { Radio } from "../../components/Radio";
```

2. `ScheduleDraft`（`:80-93`）の `addMeet` の次に `recurrence: ScheduleRecurrence;`。`createDraft`（`:118-135`）の `addMeet: false,` の次に `recurrence: item?.recurrence ?? "none",`。`openCreate`（`:927`）と `openCreateRange`（`:1120`）の下書きの `addMeet: false,` の次に `recurrence: "none",`（ほかに `ScheduleDraft` を組み立てる所があれば同じく `"none"` を足す。tsc が教える）。

3. `ScheduleDraft` の型の次（モジュールの上の方）に足す:

```ts
/** 繰り返しの予定を直す・消す・動かすときの 3 択の小窓（design §12.6.1） */
type ScopeRequest = {
  kind: ScopeKind;
  choices: RecurrenceScope[];
  run: (scope: RecurrenceScope) => Promise<void>;
  cancel?: () => void;
};

const SCOPE_LABEL_KEYS: Record<RecurrenceScope, string> = {
  this: "schedule.recurrence.scopeThis",
  following: "schedule.recurrence.scopeFollowing",
  all: "schedule.recurrence.scopeAll",
};
```

4. 詳しくの小窓（`:349`）。変更前:

```tsx
            <p className="schedule-popover__time">{timeLabel}</p>
```

変更後:

```tsx
            <p className="schedule-popover__time">{timeLabel}</p>
            {item.recurrence && item.recurrence !== "none" && item.recurrence !== "custom" && (
              <p className="schedule-popover__meta">
                {recurrenceLabel(item.recurrence, occurrenceStartOf(item), t, i18n.language)}
              </p>
            )}
```

5. 状態（`:808` の `fullEditOpen` の次）に足す:

```tsx
  // 繰り返しの予定の 3 択の小窓（design §12.6.1 G3・G6）
  const [scopeRequest, setScopeRequest] = useState<ScopeRequest | null>(null);
  const [scopeChoice, setScopeChoice] = useState<RecurrenceScope>("this");
  const askScope = (request: ScopeRequest) => {
    setScopeChoice(request.choices[0]);
    setScopeRequest(request);
  };
  const confirmScope = () => {
    const request = scopeRequest;
    if (!request) return;
    setScopeRequest(null);
    void request.run(scopeChoice);
  };
  const cancelScope = () => {
    const cancel = scopeRequest?.cancel;
    setScopeRequest(null);
    cancel?.();
  };
```

6. `saveEvent`（`:961-1004`）を置き換える:

```tsx
  const saveEvent = async () => {
    try {
      const body: Record<string, unknown> = {
        title: draft.title,
        start_datetime: combineDateTime(draft.startDate, draft.allDay ? "00:00" : draft.startTime).toISOString(),
        end_datetime: combineDateTime(draft.endDate, draft.allDay ? "23:59" : draft.endTime).toISOString(),
        is_all_day: draft.allDay,
        category: draft.category,
        description: draft.description || undefined,
        location: draft.location || undefined,
      };
      if (canChangeVisibility) {
        body.calendar_type = draft.visibleToStaff ? "shared" : "personal";
      }
      // Meet を付けるのは、つないだ本人で、Toggle が入っていて、まだ Meet が無い、繰り返さない予定だけ
      const wantsMeet = meetAvailable && draft.addMeet && !popover?.item?.meetUrl && draft.recurrence === "none";
      if (wantsMeet) {
        body.add_meet = true;
      }
      const editing = popover?.mode === "edit" && popover.item ? popover.item : null;
      // 繰り返しは今の値と違うときだけ送る（作るときは「繰り返さない」以外のとき・§12.6.1 G4）
      const recurrenceChanged = draft.recurrence !== "custom" && draft.recurrence !== (editing?.recurrence ?? "none");
      if (recurrenceChanged) {
        body.recurrence = draft.recurrence;
      }

      let numericId: number | null = null;
      if (editing) {
        numericId = eventNumericId(editing.id);
        if (numericId === null) {
          setError(t("common.saveError"));
          return;
        }
      }

      type SaveResult = { id: number; meet_url: string | null };
      const send = async (scope: RecurrenceScope | null) => {
        try {
          let saved: SaveResult | undefined;
          if (editing && numericId !== null) {
            const payload = scope
              ? { ...body, scope, occurrence_start: occurrenceStartOf(editing).toISOString() }
              : body;
            saved = await api.patch<SaveResult>(`/calendar/events/${numericId}`, payload);
          } else {
            saved = await api.post<SaveResult>("/calendar/events", body);
          }
          setPopover(null);
          setError(null);
          setFullEditOpen(false);
          if (wantsMeet && !saved?.meet_url) {
            // 予定そのものは保存済み。Meet だけ付かなかったことを知らせる
            setBanner({ type: "error", message: t("schedule.meetFailed") });
          }
          void invalidate(["calendar", "events"]);
        } catch (err) {
          setError(err instanceof Error ? err.message : t("common.saveError"));
        }
      };

      if (editing && isRecurringItem(editing)) {
        const visibilityChanged =
          canChangeVisibility && (draft.visibleToStaff ? "shared" : "personal") !== editing.calendarType;
        const choices = scopeChoices("save", editing.isFirstOccurrence === true, recurrenceChanged || visibilityChanged);
        if (choices.length === 1) {
          await send(choices[0]);
          return;
        }
        askScope({ kind: "save", choices, run: send });
        return;
      }
      await send(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };
```

7. `deleteEvent`（`:1006-1021`）を置き換える:

```tsx
  const deleteEvent = async () => {
    const item = popover?.item;
    if (!item) return;
    const numericId = eventNumericId(item.id);
    if (numericId === null) {
      setError(t("common.deleteError"));
      return;
    }
    const send = async (scope: RecurrenceScope | null) => {
      try {
        const query = scope
          ? `?${new URLSearchParams({ scope, occurrence_start: occurrenceStartOf(item).toISOString() }).toString()}`
          : "";
        await api.delete(`/calendar/events/${numericId}${query}`);
        setPopover(null);
        setError(null);
        void invalidate(["calendar", "events"]);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("common.deleteError"));
      }
    };
    if (isRecurringItem(item)) {
      askScope({ kind: "delete", choices: scopeChoices("delete", item.isFirstOccurrence === true, false), run: send });
      return;
    }
    await send(null);
  };
```

8. `patchMoved`（`:1192-1217`）。`const endValue = ...;` の次の `try { ... } catch { ... }` を置き換える（前半の確かめと 3 つの値はそのまま）:

```tsx
    const send = async (scope: RecurrenceScope | null) => {
      try {
        const body: Record<string, unknown> = {
          title: item.title,
          start_datetime: combineDateTime(startDay, startTime).toISOString(),
          end_datetime: endValue.toISOString(),
          is_all_day: allDay,
          description: item.description || undefined,
          location: item.location || undefined,
        };
        await api.patch(
          `/calendar/events/${numericId}`,
          scope ? { ...body, scope, occurrence_start: occurrenceStartOf(item).toISOString() } : body,
        );
        setError(null);
        void invalidate(["calendar", "events"]);
      } catch (err) {
        revert();
        setError(err instanceof Error ? err.message : t("common.saveError"));
      }
    };
    if (isRecurringItem(item)) {
      // キャンセルと Esc で元の位置に戻す（§12.6.1 G6）
      askScope({ kind: "move", choices: scopeChoices("move", item.isFirstOccurrence === true, false), run: send, cancel: revert });
      return;
    }
    await send(null);
```

9. 近道（`:1221` の `shortcutRef.current = (event: KeyboardEvent) => {` の中）の最初の行 `if (fullEditOpen) return;` の前に:

```tsx
    // 3 択の小窓が開いている間は何もしない（Esc は金型 Modal が受ける・§12.6.1 G3）
    if (scopeRequest) return;
```

10. 描き方: `<ScheduleShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />`（`:1539`）の次に:

```tsx
      <ConfirmModal
        open={scopeRequest !== null}
        title={t(scopeRequest?.kind === "delete" ? "schedule.recurrence.deleteTitle" : "schedule.recurrence.editTitle")}
        message={
          <div className="schedule-scope-choices">
            {(scopeRequest?.choices ?? []).map((choice) => (
              <Radio
                key={choice}
                name="schedule-recurrence-scope"
                value={choice}
                label={t(SCOPE_LABEL_KEYS[choice])}
                checked={scopeChoice === choice}
                onChange={() => setScopeChoice(choice)}
              />
            ))}
          </div>
        }
        confirmLabel={t("common.ok")}
        cancelLabel={t("common.cancel")}
        onConfirm={confirmScope}
        onCancel={cancelScope}
      />
```

11. 全画面の編集の `onClose`（`:1566`）。変更前:

```tsx
        onClose={() => { setFullEditOpen(false); setError(null); if (popover?.mode === "edit") setPopover(null); }}
```

変更後（3 択の小窓の Esc で編集画面まで閉じない・§12.6.1 G3）:

```tsx
        onClose={() => { if (scopeRequest) return; setFullEditOpen(false); setError(null); if (popover?.mode === "edit") setPopover(null); }}
```

### 4-7. `frontend/src/pages/schedule.css`

`.schedule-editor-dates__sep`（`:539-543`）の次に足す（色・寸法の直値は書かない・ADR-067）:

```css
/* 終日のチェックと繰り返しの選ぶ欄を 1 段に並べる（design §12.6.1 G8） */
.schedule-editor-all-day-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}

/* 3 択の小窓の選び方を縦に並べる（design §12.6.1 G7） */
.schedule-scope-choices {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
```

### 4-8. 試験

`backend/tests/test_calendar_service.py` の `TestListRecurrence`（`:1478`）に足す（`_master_row`・`_FakeDB`・`_jt` を使う。名前はこのとおり）:
- `test_is_first_occurrence_on_expanded`: `test_weekly_master_expands` と同じ入力で、`[o["is_first_occurrence"] for o in out] == [True, False, False]`
- `test_is_first_occurrence_missing_master`: 結果は例外の行 2 つだけ（元の行 id 1。1 つは `r[21] = _jt(2026, 11, 12)`、もう 1 つは `r[21] = _jt(2026, 11, 19)`。どちらも `r[19] = None`・`r[20] = 1`）。handlers に `("SELECT id, recurrence_rule, start_datetime, is_all_day", [(1, "FREQ=WEEKLY;BYDAY=TH", _jt(2026, 11, 12), False)])` を入れる。返る 2 件の `is_first_occurrence` が 11/12 の方は True、11/19 の方は False、どちらも `recurrence == "weekly"`
- `test_is_first_occurrence_single_and_search`: 単発の行（`r[19] = None`・`r[20] = None`）は False。`list_events(..., search="定例")` のように広げないで返る元の行は True（今の `test_search_does_not_expand` と同じ呼び方）

`frontend/src/pages/schedule/schedule-utils.test.ts` の最後に `describe("recurrence（便15B）", ...)` を足す（日本語の文字はファイルの頭の eslint の除外のまま書いてよい）:
- `recurrenceChoicesFor`: `new Date(2026, 10, 12)` は `monthly_nth` だけを含み `monthly_last` を含まない／`new Date(2026, 10, 26)` は両方／`new Date(2026, 10, 30)` は `monthly_last` だけ（G70）
- `recurrenceLabel`（`i18n` を ja にして）: `new Date(2026, 10, 12)` の weekly が `"毎週 木曜日"`（G72）・monthly_nth が `"毎月 第 2 木曜日"`・`new Date(2026, 10, 30)` の monthly_last が `"毎月 最終月曜日"`・yearly が `"毎年 11月12日"`・`new Date("x")` は `""`
- `recurrenceOptionsFor(new Date(2026, 10, 30), "monthly_nth")` は `monthly_nth` を含む・`recurrenceOptionsFor(new Date(2026, 10, 30), null)` は含まない・どちらも `custom` を含まない
- `fitRecurrenceToDate`: 11/30 の `monthly_nth` → `monthly_last`・11/12 の `monthly_last` → `monthly_nth`・`weekly` はそのまま
- `scopeChoices`: save 1 回目 → `["this","all"]`／save 2 回目 → `["this","following","all"]`／save 2 回目で変えた → `["following","all"]`／save 1 回目で変えた → `["all"]`／delete 2 回目 → 3 つ／move 1 回目 → `["this","all"]`／move 2 回目 → `["this","following"]`
- `normalizeEvent` と `eventNumericId`: `occurrence_start` のある予定の id が `event-1-<getTime()>` で、`eventNumericId` がそれを 1 にする・`"event-1"` も 1・`occurrenceStart` と `isFirstOccurrence` と `recurrence` が入る・`occurrence_start` の無い予定の id は今と同じ `event-1`

`frontend/src/pages/schedule/SchedulePageImpl.test.tsx` の最後に `describe("SchedulePage recurring events (G69-G79)", ...)` を足す。回の予定は `apiEvent({ recurrence_rule: "FREQ=WEEKLY;BYDAY=TH", recurrence: "weekly", recurring_event_id: 1, occurrence_start: todayAt(10), is_first_occurrence: false })`。開き方は今の試験と同じ（題の文字を押す → `schedule.editEvent` の [0] → `editorDialog()` → その中の `common.save`。消すは `schedule.deleteEvent` の [0]）。3 択の小窓は `screen.findByRole("dialog", { name: i18n.t("schedule.recurrence.editTitle") })`（消すは `deleteTitle`）で探し、選び方は `within(小窓).getAllByRole("radio")`。名前はこのとおり:
- `shows the repeat line under the time in the detail popover`: 詳しくの小窓に `i18n.t("schedule.recurrence.weekly", { weekday: new Intl.DateTimeFormat("ja", { weekday: "long" }).format(new Date(todayAt(10))) })` の文字がある（G72）
- `asks this/following/all on save and sends nothing on cancel`: 保存で小窓が出て radio が 3 つ・`scopeThis` の radio が checked。`common.cancel` で `api.patch` が 0 回（G73）
- `sends scope this with the occurrence start on OK`: OK で `api.patch` の本文の `scope` が `"this"`・`occurrence_start` が `new Date(todayAt(10)).toISOString()`・`recurrence` を含まない
- `hides following on the first occurrence`: `is_first_occurrence: true` で radio が 2 つ（`scopeThis`・`scopeAll`）
- `drops this when the repeat changes and skips the dialog on the first occurrence`: 2 回目で選ぶ欄（`combobox` の名前 `schedule.recurrence.label`）を `daily` にして保存 → radio が 2 つ（`scopeFollowing`・`scopeAll`）。1 回目で同じ操作 → 小窓が出ず `api.patch` の `scope` が `"all"`・`recurrence` が `"daily"`（G79）
- `deletes with scope and occurrence start in the query`: 消す → `deleteTitle` の小窓 → OK で `api.delete` の引数が `` `/calendar/events/1?${new URLSearchParams({ scope: "this", occurrence_start: new Date(todayAt(10)).toISOString() })}` ``
- `asks two choices on move and reverts on cancel`: `calendarProps.current?.onEventMove(回の id, ...)` で小窓（`editTitle`）に radio が 2 つ（`scopeThis`・`scopeFollowing`）。キャンセルで `revert` が 1 回・`api.patch` が 0 回（G75）。回の id は `` `event-1-${new Date(todayAt(10)).getTime()}` ``
- `closes only the scope dialog on Escape`: 編集画面で保存 → 小窓 → `fireEvent.keyDown(document, { key: "Escape" })` → 小窓が無くなり、`editorDialog()` は残る
- `has no repeat select for a Google event or a Meet event`: `source: "google"` の予定と `meet_url` のある予定の編集画面に `schedule.recurrence.label` の combobox が無い（G79）
- `shows the repeat select right of all-day with does-not-repeat first`: 単発の予定の編集画面で combobox の値が `"none"`（G69）
- `hides the Meet row when a repeat is chosen and sends no add_meet`: Meet の試験と同じ `enableMeet` の条件・`google_event_id: "g1"` の自分の予定で、Meet の行を押してから選ぶ欄を `weekly` にすると Meet の行が無くなり、保存の本文に `add_meet` が無く `recurrence` が `"weekly"`
- `shows no dialog for a single event`: 単発の予定の保存・削除で小窓が出ず、`api.patch`・`api.delete` の引数に `scope` が無い（G77）

今の試験（特に `T6`・`T7`・Meet の試験）は変えずに通ること。

## 5. 確かめ（担当が行う）

5-1. commit の前（どれも 1 回の Bash で `cd` から始める。作業場所は `$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend`）:
1. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/backend" && python -m pytest tests/test_calendar_service.py tests/test_api_error_reason_sync.py -q 2>&1 | tail -n 30` … 最後の行に `failed` と `error` が無い
2. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/frontend" && npx vitest run src/pages/schedule src/lib/apiErrorReason.test.ts 2>&1 | tail -n 60` … `Tests` の行に `failed` が無い
3. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/backend" && python -m pytest tests/test_calendar_service.py -v 2>&1 | grep -E "test_is_first_occurrence" | head -n 10` … §4-8 の 3 つの名前がすべて PASSED
4. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/frontend" && npx vitest run src/pages/schedule/SchedulePageImpl.test.tsx -t "recurring events" --reporter=verbose 2>&1 | grep -E "✓|×|FAIL" | head -n 30` … §4-8 の 12 の名前がすべて ✓
5. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/frontend" && npx tsc --noEmit -p tsconfig.json 2>&1 | tail -n 30` … 出力が空
6. `cd "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/frontend" && npm run check:all 2>&1 | tail -n 40` … 終わりの行に失敗が無い（`eslint`・`i18n-missing-keys`・`stylelint`・`css-class-naming`・`error-text-next-action`・`page-size` を含む）

5-2. commit の後・push の前: `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" diff --stat origin/main...HEAD | tail -n 20` … 変わったファイルが §3 の表の 14 件だけ（台帳は入らない）。違えば止まる

5-3. push の後: `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" log origin/release/schedule-recurrence-frontend -1 --oneline` が `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" log -1 --oneline` と同じ

## 6. 止まる条件

- origin/main の行番号や中身が §2・§4 と違い、§4 の書き方が当てはまらない（どこが違うかを出して止まる）
- 今ある試験が落ち、直すには試験の期待そのものを変える必要がある（§4-2 の数 2 か所を除く）
- `check:all` の検査が、§4 のとおりに書いたのに落ち、直すには金型・トークン・検査の決まりの外の書き方が要る
- §3 の表に無いファイルを変える必要が出た
- 設計 §12・§12.6.1 と本カードが食い違い、どちらに従うか決められない

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 編集画面の終日の右に「繰り返さない」初めの選ぶ欄（G69） | §5-1 の 4 の `shows the repeat select right of all-day with does-not-repeat first`。本番の画面は Opus が確かめる |
| 選び方の並びが開始日から作られる（G70） | §5-1 の 2 の `recurrenceChoicesFor` の 3 日の試験 |
| 詳しくの小窓の繰り返しの行（G72） | §5-1 の 4 の `shows the repeat line under the time in the detail popover`・`recurrenceLabel` の試験 |
| 3 択の題・選び方・初め・1 回目は 2 択・キャンセルで送らない（G73） | §5-1 の 4 の 3 択の試験 |
| 動かすときの 2 択とキャンセルで戻る（G75） | §5-1 の 4 の `asks two choices on move and reverts on cancel` |
| 選び方を変えたときの 2 択・1 回目は小窓なしで all・Google の予定に選ぶ欄なし（G79） | §5-1 の 4 の 2 つの試験 |
| 単発の予定は今と同じ（G77） | `shows no dialog for a single event` と今の T6・T7 |
| 422 の 8 つが「起きたこと＋次にすること」の文で出る（ADR-1071） | §5-1 の 1・2 の突き合わせの試験と `check:all` の `error-text-next-action` |
| 金型・トークン・i18n（ADR-144・ADR-067・ADR-027） | §5-1 の 6 |
| CI 緑（G78） | Opus が PR で確かめる |

## 8. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/schedule-recurrence-frontend`（origin/main 起点。`--claude` は付けない）。作成後に `git worktree list` で実在を確かめ、以後はその作業場所で行う
2. `ls "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend/docs/handoff/schedule-gcal-clone/card-bin15b.md"` で、このカードが作業場所（origin/main）にあることを確かめる
3. 台帳 `.claude-pipeline/active-work.d/release-schedule-recurrence-frontend.md` を Write ツールで作る（1 行目 `branch: release/schedule-recurrence-frontend`、空行、表の頭 `| ブランチ名 | 担当機能エリア | 開始日時 | 状態 | PR# | main | 備考 |` と区切りの行、`| release/schedule-recurrence-frontend | 予定の繰り返しの画面（ADR-1075 便15B） | 2026-11-13 | IN_PROGRESS | | | |`）。この台帳は commit しない（§8 の 5 の add にも入れない）
4. §4 のとおりに書く（既にあるファイルは Edit ツール。パスは作業場所の絶対パス）。§5-1 を通す
5. commit（`git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" add backend/app/services/calendar_service.py backend/tests/test_calendar_service.py backend/tests/test_api_error_reason_sync.py frontend/src/lib/apiErrorReason.ts frontend/src/lib/apiErrorReason.test.ts frontend/src/locales/ja.json frontend/src/locales/en.json frontend/src/pages/schedule/schedule-utils.ts frontend/src/pages/schedule/schedule-utils.test.ts frontend/src/pages/schedule/ScheduleDraftFields.tsx frontend/src/pages/schedule/ScheduleFullEditor.tsx frontend/src/pages/schedule/SchedulePageImpl.tsx frontend/src/pages/schedule/SchedulePageImpl.test.tsx frontend/src/pages/schedule.css`（§3 の 14 件だけを名前で足す。`-A`・`.` は使わない）と `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" commit`。`--no-verify` は使わない。文: `feat(schedule): recurring events UI (ADR-1075 bin15B)`）→ `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" log -1 --oneline` → §5-2
6. `git -C "$HOME/worktrees/salesanchor/release-schedule-recurrence-frontend" push -u origin release/schedule-recurrence-frontend` → §5-3

クラウドでの決まり: 作業の前の `./scripts/dev/executor-preflight.sh` の FAIL が `[1/3]` と `[2/3]` の 2 つだけなら続けてよい（クラウドの写しの形による）。ほかの FAIL があれば止まる。クラウドでは `gh` を使わない。

## 9. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1〜§5-3 の出力（生のまま）・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 10. 委任の定型

- sleep は使わない。CI は待たない
- ファイルの編集は Edit ツール、新しいファイルは Write ツールで行う（ヒアドキュメントで書かない）。rm は使わない
- PR は作らない。main にマージしない。本番・倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 11. 報告欄（担当が追記）

（未記入）

END OF CARD
