# Design: schedule settings, bin 3a (move person colors onto the shared component, remove dead columns, stop showing deactivated teams, move separators into t())

- Status: design draft (written by Opus). Review runs on the cloud, and the result is recorded in §12 "Review".
- Parent: `docs/handoff/schedule-settings/design.md` §1 (bin table) and §7 (bin 3 skeleton). Requirements: `docs/handoff/schedule-settings/requirements.md` (approved by the PO on 2026-11-25 with "1").
- Related ADRs: ADR-1081 (the 24 event colors; the source of truth is `backend/app/services/event_colors.py`), ADR-144 (UI components), ADR-067 (design tokens), ADR-027 (i18n), ADR-072 (reset_tenant_context after commit), ADR-1037 (migration lock timeout), ADR-1052 (AI copy classification), ADR-135 and ADR-136 (GO for risky PRs).
- How bin 3 is split: the skeleton (design.md §7) put "per-person defaults", "person colors" and "deleting dead columns" into one bin. Following the "one change at a time" rule, it is split in two.
  - **Bin 3a (this document)**: person colors, dead columns, deactivated teams, separators. Includes a DB change.
  - **Bin 3b (`design-bin3b.md`, to be written after bin 3a reaches production)**: per-person defaults (initial view, week start, event length, Meet, whose events to show). Requirement G7. Includes a DB change.

## 0 What this bin does and does not do

| Does | Does not |
|---|---|
| Changes person colors from free color picking (`<input type="color">`) to choosing one of the 24 colors with the shared component `ColorSwatchPicker` | Per-person defaults (bin 3b) |
| Removes the three unused columns of `calendar_owner_settings`: `color` (the free color value), `is_visible` and `share_mode`. Adds `color_key` | Who may change person colors (stays as now: people with `staff.view`) |
| Stops returning deactivated teams in an event's teams | Turning the person-color section into SectionCard (that is a page layout change, so it is not in this bin) |
| Moves the hardcoded ": " and ", " separators on the schedule screen and the settings page into `t()` | |

## 1 Current state (actual code, origin/main 314eeef1e)

- **F1** The person color table, `backend/app/services/tenant.py:1652-1660` (template):
  - `color varchar(32) DEFAULT '#1a73e8'`
  - `is_visible boolean DEFAULT false`
  - `share_mode varchar(16) DEFAULT 'self'`, constrained by `CHECK calendar_owner_settings_share_mode_check`
  - The PK is `staff_id`, which is an FK to `public.users(id)`.
- **F2** Production row counts, checked with the read-only key (audit 2026-11-25T17:27:41Z): **0 rows** of `calendar_owner_settings` in each of the 5 companies (001, 003, 004, 005, 006). Nobody has saved a person color, so there are no existing values to carry over.
- **F3** Readers of `is_visible` and `share_mode`:
  - Back end: `backend/app/routers/calendar.py:83-84`, `:94-95` (request and response models), `:404-405`, `:430-431` (roster), `:462-470` (save), `:502` (columns to save), `:529-530`, `:553-554` (re-read after save).
  - Front end: `frontend/src/pages/schedule/schedule-owner.ts:10-11`, `:45-46`.
  - None of them change what the screen does. Bin 1 already removed the input fields: design.md §2 K9.
- **F4** The person color today:
  - Saved as a free color value: `ScheduleSettingsPage.tsx:426` `<input type="color">`.
  - The back-end default is the free value `_DEFAULT_OWNER_COLOR = "#1a73e8"` (`calendar.py:53`).
  - On the front end, a missing owner falls back to `DEFAULT_OWNER_COLOR = "var(--calendar-google-blue)"` (`schedule-owner.ts:35`).
  - Event colors are already the 24 keys plus `ColorSwatchPicker`: `ScheduleDraftFields.tsx:353-357`, and for categories `ScheduleSettingsPage.tsx` `categoryColorOptions`.
- **F5** Uses of the person color on the screen:
  - `SchedulePageImpl.tsx:262` (`owner?.color ?? DEFAULT_OWNER_COLOR`)
  - `:612`, `:618`, `:641`, `:647` (the people list)
  - `:705`, `:776`, `:1323`, `:1334` (via `eventDisplayColor`)
  - `:1445`
  - `ScheduleSettingsPage.tsx:79` (`OwnerBadge`), `:292` (save)
  - All of them use the value as the `color` string of `CalendarOwner`.
- **F6** Readers of an event's teams:
  - `backend/app/services/calendar_service.py:381-383` (the `team_ids` of the event list) and `:226-232` (`event_team_ids`) **do not look at whether a team is active**.
  - The visibility check (`:210-211`) and the category's initial teams (`backend/app/services/calendar_categories.py:54-55`) already look only at active teams.
  - So an event whose team was later deactivated keeps that team's id in `team_ids`. The edit form then sends an id that is not among the choices, and saving it returns 422 `invalid_team_ids`.
- **F7** Hardcoded separators:
  - `SchedulePageImpl.tsx:346`: `` `${t("schedule.shareTeam")}: ${names.join(", ")}` ``
  - `ScheduleSettingsPage.tsx` Google section: `{t("schedule.settingsConnectedAt")}: {formatDateInput(...)}`
- **F8** AI copy classification, `migrations/20261024_100300_create_ai_cloud_views.sql:381-382`:
  - `calendar_owner_settings.color` = mask
  - `share_mode` = allow
  - Precedent: bin 2a added the `calendar_categories` rows to the same file. Its test is `backend/tests/ops/test_ai_cloud_views.py:1061`.
- **F9** At the start of every migration run, the AI views are dropped (`scripts/run_all_migrations.sh:412`, `:416`) and rebuilt at the end. Dropping a column is therefore not blocked by a view dependency. Precedent: `migrations/20261109_200000_drop_staff_firebase_uid.sql`.
- **F10** Where a migration is registered. Same places as the bin 2b precedent, `20261127_100000_add_calendar_team_share.sql`:
  - `scripts/run_all_migrations.sh`: a new line right after `:1495` (the bin 2b line), before `mr_report_summary`
  - `backend/app/services/tenant.py:1632` (the template comment)
  - `backend/tests/rls_bootstrap.py:190` (the mapping, count 1)
  - `backend/tests/test_calendar_sync_tenant_reset_pg.py:56` (append to the end of the run order)
  - `backend/tests/test_tenant_loop_migration_guard.py` `_REVIEWED` (review 2 R1):
    - Add the new migration name to the existing sets of `rls_bootstrap.py` (next to `:53`) and `test_calendar_sync_tenant_reset_pg.py` (next to `:74`). Both files will contain the name, so the guard (`:342`, `:364`) finds them.
    - One entry for each new test file: the test that runs the migration is `scoped`; the test that only reads the migration file as text (the 24-pair check) is `text_only` with a reason (`:380-392` fails `text_only` without one). If both live in one file, one entry.
    - The A6/A8 test needs no entry if its file does not contain the migration name.
    - Do not touch `:83`, which is the `test_calendar_team_share.py` entry (review 1 R4).
- **F11** Other places CI checks against (review R1–R3):
  - `.github/workflows/api-contract-check.yml:38-58` fails when `frontend/api-contract/openapi.json` differs from the exported API. `OwnerRosterItem` is at `:25683-25747` and `OwnerSettingsBody` at `:25788-25824`.
  - `scripts/migration-guard/reference-allowlist.tsv:7` holds the sha256 of `20261024_100300_create_ai_cloud_views.sql`. A different sha256 fails (rule at `:5`). Bin 2b fixed it the same way (`7b60986c7`).
  - `backend/tests/ops/test_ai_cloud_views.py:486` fixes the `column_class` count at `== 1170`.

## 2 Acceptance criteria

| Criterion | What it means | How it is checked |
|---|---|---|
| A1 | Person colors on the settings page are chosen from the 24 colors plus "default color". There is no `<input type="color">` | Screen test, plus `git grep -n 'type="color"' -- frontend/src` returns 0 hits |
| A2 | After choosing and saving, the people list on the schedule screen and events without their own color show that color. Choosing "default color" returns to the current blue (`var(--calendar-google-blue)`) | Screen test (display after save), back-end test (`color_key` saved, null resets to default) |
| A3 | Saving a color that is not one of the 24 gets 422 `invalid_color_key`, and nothing is saved | Back-end test |
| A4 | `calendar_owner_settings` has no `color`, `is_visible` or `share_mode` columns. It has `color_key`, and the CHECK allows only NULL or the 24 keys | Real PostgreSQL migration test, plus a production read with the read-only key (information_schema and pg_constraint) |
| A5 | The old names are gone from product code, including comments | The command below §2 returns 0 hits |
| A6 | An event whose team was deactivated does not include that team in `team_ids` (event list and after save) | Back-end test on real PostgreSQL |
| A7 | No `": "` or `", "` written directly into the share line or the Google connection date line. The new text is ja/en with matching keys | `git grep -n -F '}: ${names.join(", ")}' -- frontend/src` returns 0 hits, `git grep -n -F '{t("schedule.settingsConnectedAt")}: ' -- frontend/src` returns 0 hits, and the i18n check |
| A8 | The team filter (§3-3) changes only which ids appear in `team_ids`. It does not remove any event from the list (requirement G6) | Back-end test on real PostgreSQL: the list count is the same before and after deactivating the team. In production, count the events for t1 and t4 with the read-only key before and after the deploy |
| A9 | Running the migration twice gives the same result | Real PostgreSQL migration test (run it twice) |

A5 command (plain `|` inside `-E`; review R5):

```bash
git grep -n -E 'is_visible|share_mode|_DEFAULT_OWNER_COLOR' -- backend/app frontend/src
```

Today it finds 38 lines: `calendar.py` 53, 83-84, 94-95, 404-405, 410, 429-431, 462-470, 502, 529-530, 537, 552-554, `tenant.py` 1652, 1653, 1656, `schedule-owner.ts` 10-11, 34, 45-46 and the test fixtures. After this bin it must find 0. `_VALID_OWNER_SHARE_MODES` (upper case) is not matched; its removal is checked in the diff. Front-end tests must not write `is_visible` or `share_mode`; check the response keys by exact match instead (review 2 L1).

## 3 Back-end changes

### 3-1 Migration `migrations/20261128_100000_owner_color_key_drop_dead_columns.sql`

Put every tenant in one DO block. Skip any tenant that has no `calendar_owner_settings`. Each step must give the same result when run again.

Tenants are chosen in exactly one place, written on one line as `FOR schema_rec IN SELECT nspname FROM pg_namespace WHERE nspname ~ '^tenant_\d+$' LOOP`, with nothing between `WHERE` and the condition (precedent `20261127_100000_add_calendar_team_share.sql:18`). The final check (step 5) runs inside the same loop. `rls_bootstrap.py:171-172`, `:200-207` counts this selector and adds `AND nspname = …` right after it, so the count must stay 1 (review 2 L3, L5).

1. `ALTER TABLE %I.calendar_owner_settings ADD COLUMN IF NOT EXISTS color_key text`
2. If `calendar_owner_settings_color_key_check` is missing (check by name), add `CHECK (color_key IN (the 24 keys, in the same order as calendar_events_color_key_check, tenant.py:1607))`. PostgreSQL lets NULL through an IN check, so NULL (the default color) is allowed. The type `text` and this exact wording match the existing `color_key` columns (`tenant.py:1555`, `:1599`, `:1607`), so the template and the migration have one shape (review L2).
3. Only when the `color` column still exists (check with information_schema), carry the old value over to the matching key:

   ```sql
   UPDATE … SET color_key = CASE lower(btrim(color)) WHEN '#ad1457' THEN 'radicchio' … (24 lines) END WHERE color_key IS NULL
   ```

   The 24 `WHEN` lines are copied from `backend/app/services/event_colors.py:8-17` exactly. A test reads the migration file and checks that its 24 pairs equal `EVENT_COLORS` and that its CHECK keys equal `tenant.py:1607` (review L3; precedent `backend/tests/test_event_colors_tokens.py`).
   Rows whose value is not one of the 24 stay NULL, which means the default color. Production has 0 rows (F2).
   Every `information_schema` check filters on both `table_schema` and `table_name` (precedent `20261109_200000_drop_staff_firebase_uid.sql`).
4. `ALTER TABLE … DROP COLUMN IF EXISTS color, DROP COLUMN IF EXISTS is_visible, DROP COLUMN IF EXISTS share_mode`. Do not use CASCADE: if something depends on these columns, the migration should fail and stop. The share_mode CHECK goes away together with its column.
5. Final check: in every tenant that was processed, if any of the 3 old columns remains or `color_key` is missing, `RAISE EXCEPTION`, which rolls the whole migration back.

- Locks: `lock_timeout` (1s) from `run_sql` (ADR-1037). The table has 0 rows in production.
- Rollback, written in a comment: `ADD COLUMN color varchar(32) DEFAULT '#1a73e8' NOT NULL, is_visible boolean DEFAULT false NOT NULL, share_mode varchar(16) DEFAULT 'self' NOT NULL` plus the CHECK, and `DROP COLUMN color_key`. The values do not come back, but production has 0 rows.
- Registration: the same places as F10, as one set. In the template (`tenant.py:1649-1660`), replace the 3 old columns with `color_key text` and `CONSTRAINT calendar_owner_settings_color_key_check CHECK (color_key IN (…24 keys…))`, word for word the same as the migration.

### 3-2 API (`backend/app/routers/calendar.py`)

- `OwnerSettingsBody` holds only `color_key: Optional[str] = None`.
  - If the request does not send `color_key` (judged with `model_fields_set`), return 422 `no_fields_to_update` as now.
  - Sending `null` means "back to the default color".
  - Any other value not in `EVENT_COLOR_KEYS` (`backend/app/services/event_colors.py:18`, already imported at `calendar.py:43`) returns 422 `invalid_color_key`. This is raised inside the handler as `HTTPException(422, detail="invalid_color_key")`, the same form as `no_fields_to_update`; it is not a pydantic validator. The empty string `""` is not a key, so it also returns 422 (unlike events at `calendar.py:119`, which allow it).
- `OwnerRosterItem` gets `color_key: Optional[str]` in place of `color`, `is_visible` and `share_mode`.
- The roster and the re-read after save use `SELECT cos.color_key`. Remove `_DEFAULT_OWNER_COLOR`, `_VALID_OWNER_SHARE_MODES` and the `default_color` parameter.
- Saving is the current upsert with only the `color_key` column: `INSERT … ON CONFLICT (staff_id) DO UPDATE SET color_key = EXCLUDED.color_key, updated_at = NOW()`. Keep `commit` followed by `reset_tenant_context` (ADR-072).
- Regenerate the API contract and commit it (review R1): `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json`. `frontend/src/api/generated/` is not tracked, so no type file changes.

### 3-3 Event teams to active teams only (`backend/app/services/calendar_service.py`)

- `:381-383`: add `JOIN teams t ON t.id = cet.team_id AND t.is_active` to the subquery.
- `:226-232`, `event_team_ids`: add the same JOIN.
- Do not change the writer `set_event_teams` or the check `check_active_team_ids`. The visibility check already looks only at active teams.

### 3-4 AI copy classification (`migrations/20261024_100300_create_ai_cloud_views.sql:381-382`)

- Remove the 2 rows `color` (mask) and `share_mode` (allow).
- Add `('tenant_*','calendar_owner_settings',ARRAY['color_key'],'allow','値の決まり calendar_owner_settings_color_key_check で値が限られる')`, following the wording of the existing `calendar_categories` color_key row (Japanese, as in the real rows; review 3 L2).
- In `docs/handoff/cloud-case-ai/stage1-column-class.tsv`, remove `:579-580` and add one `color_key` row in the same 6-column form (type `text`). No check reads this table; it follows the bin 2a precedent of keeping it equal to the SQL (review 3 L1).
- Add one test following the precedent `backend/tests/ops/test_ai_cloud_views.py:1061`.
- Change the count at `backend/tests/ops/test_ai_cloud_views.py:486` from 1170 to **1169** (2 rows out, 1 in; review R3). Also fix the stale "1169 行" comment at line 3 of the SQL file so that it says 1169.
- After editing the SQL, put its new `sha256sum` into `scripts/migration-guard/reference-allowlist.tsv:7`, and add `/ schedule-settings 便3a（分類の入れ替え）` to the end of the reason column (review R2).

## 4 Screen changes

### 4-1 `frontend/src/pages/schedule/schedule-owner.ts`

- `ApiCalendarOwner`: `color_key: string | null`. Remove `color`, `is_visible` and `share_mode`.
- `CalendarOwner`: add `colorKey: EventColorKey | null` and keep `color: string`, the color to draw. Remove `visible`, `shareMode` and the `CalendarShareMode` type.
- `normalizeOwner`:
  - `colorKey = isEventColorKey(owner.color_key) ? owner.color_key : null`
  - `color = colorKey ? eventColorVar(colorKey) : DEFAULT_OWNER_COLOR` (`eventColors.ts`)
- The places in F5 keep reading `owner.color`, so they do not change.
- Rewrite the comment on `DEFAULT_OWNER_COLOR` to say that "the default color, when no color is set, lives in only this one place". The new comment must not contain the name `_DEFAULT_OWNER_COLOR`, because the A5 command would find it (review R5).

### 4-2 `frontend/src/pages/schedule/ScheduleSettingsPage.tsx`

- In `renderOwnerRow`, replace `<input type="color">` with `ColorSwatchPicker`, the same component the category color uses:
  - `label={t("schedule.settingsCalendarColor")}`
  - `name={\`owner-color-${owner.staffId}\`}`
  - `value={owner.colorKey}`
  - `options = [{ value: null, label: t("schedule.ownerColorDefault"), color: DEFAULT_OWNER_COLOR }, ...EVENT_COLOR_KEYS.map(key => ({ value: key, label: t(eventColorLabelKey(key)), color: eventColorVar(key) }))]`
  - `onChange`: `updateOwner(staffId, { colorKey: v, color: v ? eventColorVar(v) : DEFAULT_OWNER_COLOR })`
- Saving: `api.patch(\`/calendar/owners/${owner.userId}\`, { color_key: owner.colorKey })`.
- The Google connection date line: `t("schedule.settingsConnectedAtValue", { date: formatDateInput(...) })`.

### 4-3 `frontend/src/pages/schedule/SchedulePageImpl.tsx:346`

```ts
names.length > 0
  ? t("schedule.shareTeamWithNames", { names: names.join(t("schedule.nameListSeparator")) })
  : t("schedule.shareTeam")
```

### 4-4 New text (ja / en, same keys, under `schedule`)

| key | ja | en |
|---|---|---|
| ownerColorDefault | 標準の色 | Default color |
| shareTeamWithNames | チーム: {{names}} | Team: {{names}} |
| nameListSeparator | 、 | , (comma and a space) |
| settingsConnectedAtValue | 接続した日時: {{date}} | Connected on: {{date}} |

- `settingsConnectedAt` is no longer used by anything, so remove it from both files.
- Do not remove `shareTeam`; it is still used on its own.

## 5 Tests

- Back end:
  - Rewrite `backend/tests/test_calendar_owner_api.py` for color_key: save, null resets, out-of-range value returns 422, no fields returns 422, the response has no `is_visible` or `share_mode`.
    - Call the handler with real bodies, `OwnerSettingsBody(color_key=None)` and `OwnerSettingsBody()`, not `SimpleNamespace(...)` as at `:95` and `:113` today. `model_fields_set` needs the real model (pydantic 2.10.6, `backend/requirements.txt:8`). The order of `db.execute` side effects (staff, staff, INSERT, re-read) stays the same (review L4).
  - Add a real PostgreSQL test of the migration: carrying over the matching key, the non-matching value going to NULL, the 3 old columns being gone, the CHECK, and running twice.
    - How the old shape is made (review R6): the test tenant is built from the new template, so it already has the new shape. The test first turns it back into the old shape with `ALTER TABLE … ADD COLUMN color varchar(32) DEFAULT '#1a73e8' NOT NULL, ADD COLUMN is_visible boolean DEFAULT false NOT NULL, ADD COLUMN share_mode varchar(16) DEFAULT 'self' NOT NULL, DROP COLUMN color_key` (this also drops its CHECK), inserts rows with a matching hex (in upper case with spaces, to test `lower(btrim())`) and a non-matching hex, then runs the migration twice with `_apply_migration_on_conn(..., schema_name=...)`.
    - `scripts/check_test_schema_dup.py:28` only looks for `CREATE TABLE`, so `ALTER TABLE` in a test passes the gate.
    - Add this test file to `_REVIEWED` in `test_tenant_loop_migration_guard.py` as `scoped` with the new migration name (see F10).
    - After the migration, check that `format_type` of `color_key` is `text` and that `pg_get_constraintdef` of `calendar_owner_settings_color_key_check` has the same 24 keys in the same order as `calendar_events_color_key_check` in the same tenant. The template shape check cannot catch a difference here, because on the new template the migration does nothing (review 2 L2).
    - Insert the `public.users` rows first (foreign key at `tenant.py:1657`; precedent `_ensure_public_users`, `rls_bootstrap.py:236`). Use a tenant number no other test uses (precedent `test_calendar_team_share.py:37`, `_TENANT = 981`).
  - Add a real PostgreSQL test for A6 and A8: create one team event, set the team to `is_active = false`, and check that both the event list and `event_team_ids` no longer contain the team, and that the list count did not change.
  - Add the test that compares the 24 pairs and the CHECK keys (§3-1, review L3).
  - The test-only CREATE TABLE ban (test-schema-dup gate) applies. Tables are made by the template and the migration.
- Front end:
  - Remove `is_visible` and `share_mode` from the fake data in `ScheduleSettingsPage.test.tsx`, `SchedulePageImpl.test.tsx`, `SchedulePageCache.test.tsx` and `frontend/src/lib/query/batch3bPages.test.tsx`, and use `color_key`.
  - Settings page: there is no `type="color"`, choosing a color sends `color_key`, and "default color" sends `null`.
  - Schedule screen: a person's color key is drawn as `var(--event-color-…)`, the share line shows "チーム: A、B".
  - Fix the existing assertions: `SchedulePageImpl.test.tsx:1939` (now `shareTeam` + `: Team One, Team Two`) becomes the new text (ja `チーム: A、B`, en `Team: A, B`); `ScheduleSettingsPage.test.tsx:348` (`{ color: "rgb(17, 34, 51)" }`) becomes `color_key` (review L8).
  - The en value of `nameListSeparator` ends with a space. The implementer checks that no JSON formatter or i18n check trims values; if one does, stop and report.

## 6 Out of scope

- Who may change person colors (`staff.view`), and the person-color section's card shape (`schedule-settings__card`).
- The event and category color code (`eventColors.ts`, `event_colors.py`). This bin only reads them.
- Google color sync (ADR-1081). The person color is not sent to Google.

## 7 Alternatives

| Option | Why it is not taken |
|---|---|
| Keep the free color value and limit the picker to the hex values of the 24 colors | The colors would end up stored in two forms: hex for people, keys for events and categories. This goes against keeping one source of truth (ADR-1081) |
| Keep `color` and add `color_key` | It leaves a dead column, which goes against the purpose of this bin. Production has 0 rows, so there is nothing to keep |
| Hide deactivated teams only on the screen | The back end would still return the dead ids, so the save-time 422 would remain. Aligning the back end with how visibility is judged is the single source of truth |
| Write the separator with `Intl.ListFormat` | `frontend/tsconfig.json:5` sets lib to ES2020, so the types are missing (ES2021). It is also not used anywhere else, so `t()` is simpler |

## 8 Risks and mitigations

| Risk | Mitigation |
|---|---|
| During deployment, an old screen sends `{color: "#…"}` and gets 422 | The back end and screen go out in the same deploy. Reloading the screen fixes it. There are 0 rows in production and saving is rare |
| A test environment has a free value that is not one of the 24 | It goes to NULL, which shows the default color. Nothing is lost except the color |
| Removing a column breaks the AI views | They are removed at the start of every run and rebuilt at the end (F9). The classification is also updated in the same PR (§3-4) |
| An event whose team was deactivated shows an empty team selection | That is the right state: "no team chosen". The required message is already there (`ScheduleDraftFields.tsx:474`) |
| The old team mapping rows stay in the table | Copies of a recurring event (`calendar_service.py:1273-1275`) carry only active teams. If the team is made active again, events that were not re-saved show the old team again. Display does not change while it is inactive, because the visibility check already ignores inactive teams (review L5) |

## 9 External and past examples

- Google Calendar's own calendar colors are also chosen from a fixed palette, which ADR-1081 follows. No dated numbers are used, so this is not used as numeric evidence.
- Past precedents:
  - Dropping a column: `20261109_200000_drop_staff_firebase_uid.sql`
  - Migration form: `20261127_100000_add_calendar_team_share.sql`
  - Classification: bin 2a

## 10 How this is kept in place

- CI enforces this with:
  - The A1, A5 and A7 commands, written into the tests as greps.
  - The i18n check.
  - The UI governance gate (ADR-144) and Lint & Dark Mode Check (ADR-067).
  - The real PostgreSQL migration test.
  - `api-contract-check` (openapi.json), migration-guard (allowlist sha256), `test_ai_cloud_views.py` (count) and `test_tenant_loop_migration_guard.py` (`_REVIEWED`).
  - The template shape check `scripts/check_tenant_template_shape.py` (`tenant-template-shape`).
- Owner of the design: Opus (the design role).

## 11 PO visual check in production

- On the settings page, a person's color picker opens a list of colored circles. After choosing and saving, the schedule screen shows that color.

## 12 Review

- Round 1 (cloud Sonnet, architect): **REVISE**. Record `docs/handoff/schedule-settings/review-architect-bin3a-1.md` on branch `release/schedule-settings-bin3a-review1`.
  - R1 openapi.json → §3-2. R2 allowlist sha256 → §3-4. R3 count 1169 → §3-4. R4 `_REVIEWED` and the right lines → F10, §5. R5 A5 command → §2, §4-1. R6 how to make the old shape → §5.
  - L1 → §3-2. L2 → §3-1 (decided: `text` and the same CHECK wording as `calendar_events`). L3 → §3-1, §5. L4 → §5. L5 → §8. L8 → §5. L9 → A8.
  - L6 and L7 were records only (no change needed).
- Round 2 (cloud Sonnet, architect): **REVISE**. Record `review-architect-bin3a-2.md` on branch `release/schedule-settings-bin3a-review2`. All round 1 items confirmed in place.
  - R1 (`_REVIEWED` also needs the 2 existing sets) → F10.
  - L1 (A5 list) → §2. L2 (compare the migrated CHECK with the template) → §5. L3, L5 (one tenant selector on one line) → §3-1. L4, L6 were records only.
- Round 3 (cloud Sonnet, architect): **REVISE on the card only**. Record `review-architect-bin3a-3.md` on branch `release/schedule-settings-bin3a-review3`. All round 2 items confirmed in place; design line numbers and commands match.
  - R1: the card told the implementer to merge main and to commit the ledger, which the cloud rules forbid (`scripts/agent-hooks/cloud/rules.md:12`, `:15`) → card fixed: check `git rev-list --count HEAD..origin/main` is 0, else BLOCKED; the ledger is added by Opus.
  - L1 → §3-4 (stage1 table). L2 → §3-4 (Japanese reason). L3 → card (no need to add `invalid_color_key` to the reason table). L4: the production count for A8 is done by Opus after deploy (§11).
- Design status: **APPROVE after round 3 fixes** (only the card and two wording lines changed; no new R).
